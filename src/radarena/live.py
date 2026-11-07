"""Local demo launch control. Model execution lives in an isolated worker process."""

import json
import math
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


MODEL = "google/gemini-2.5-flash"
JUDGES = ["google/gemma-3-27b-it", MODEL, "qwen/qwen3-vl-30b-a3b-instruct"]
JUDGE_BACKUPS = {"google/gemma-3-27b-it": "qwen/qwen3-vl-8b-instruct"}
ACTIVE = {"starting", "running", "stopping"}


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    """Readers never see a partially written state or checkpoint."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def options(raw):
    if not isinstance(raw, dict) or set(raw) - {"studies", "controls", "learn", "budget", "red_rules", "blue_rules", "launch_id"}:
        raise ValueError("Unsupported live run options")
    n = raw.get("studies", 1)
    budget = raw.get("budget", 1)
    if type(n) is not int or not 1 <= n <= 10:
        raise ValueError("Choose 1–10 studies")
    if type(budget) not in (int, float) or not math.isfinite(budget) or not .5 <= budget <= 3:
        raise ValueError("Choose a spending cap from $0.50 to $3")
    result = {"studies": n, "budget": budget}
    for name in ("controls", "learn"):
        if type(raw.get(name, True)) is not bool:
            raise ValueError(f"{name} must be true or false")
        result[name] = raw.get(name, True)
    for role in ("red", "blue"):
        rules = raw.get(role + "_rules", [])
        if not isinstance(rules, list) or len(rules) > 12 or any(not isinstance(r, str) or not r.strip() or len(r) > 350 for r in rules):
            raise ValueError("Each role can start with up to 12 rules, 350 characters per rule")
        result[role + "_rules"] = list(dict.fromkeys(r.strip() for r in rules))
    try:
        result["launch_id"] = str(uuid.UUID(raw["launch_id"]))
    except (KeyError, ValueError, TypeError, AttributeError):
        raise ValueError("A unique launch ID is required") from None
    return result


class LiveArena:
    def __init__(self, runs, manifest, spawn=None):
        self.runs, self.manifest = Path(runs).resolve(), Path(manifest).resolve()
        self.lock = threading.Lock()
        self.spawn = spawn or subprocess.Popen
        self.children = {}

    def ready(self):
        from dotenv import load_dotenv
        load_dotenv(Path.cwd() / ".env", override=False)
        missing = []
        if not os.getenv("OPENROUTER_API_KEY", "").strip():
            missing.append("Set OPENROUTER_API_KEY in the project .env")
        for path, name in [(self.manifest, "Study manifest"), (Path("data/raw/iu_xray/indiana_reports.csv"), "Study indications"), (Path("knowledge/reporting_v1.json"), "Reference knowledge")]:
            if not path.is_file():
                missing.append(name + " is unavailable")
        return {"ready": not missing, "issues": missing, "model": MODEL, "judges": JUDGES,
                "judge_backups": JUDGE_BACKUPS, "max_studies": 10, "max_budget": 3, "response_cache": False}

    def sessions(self):
        sessions = []
        for path in self.runs.glob("live-*/live.json"):
            if path.is_symlink() or not path.resolve().is_relative_to(self.runs):
                continue
            record = read(path, {})
            if not record:
                continue
            if record.get("status") in ACTIVE:
                child = self.children.get(path.parent.name)
                pid = record.get("pid")
                alive = child.poll() is None if child else False
                if child is None and type(pid) is int:
                    try:
                        os.kill(pid, 0)
                        alive = True
                    except (ProcessLookupError, PermissionError):
                        pass
                if not alive:
                    record.update(status="interrupted", message="Worker stopped. Partial results and request reserves are retained.", finished_at=now())
                    save(path, record)
            record = {k: v for k, v in record.items() if k != "pid"}
            record["stop_requested"] = (path.parent / "stop.requested").exists()
            if record["stop_requested"] and record["status"] in ACTIVE:
                record["status"] = "stopping"
            budgets = [read(p, {}) for p in path.parent.glob("audit/*/budget.json")]
            record["cost"] = sum(b.get("accounted_cost_usd", 0) for b in budgets)
            record["calls"] = sum(b.get("started_calls", 0) for b in budgets)
            from .outcomes import live_match
            record["outcome"] = live_match(path.parent, record, read)
            record["judges"] = read(path.parent / "metadata.json", {}).get("judges", record.get("judges", JUDGES[:2]))
            record["stage_states"] = {}
            tag = f"{record.get('study_index', 0):02d}-{record.get('study_id', '')}"
            for phase in ["red", "blue", "control", *[f"judge{n}" for n in range(1, len(record["judges"])+1)]]:
                stage = read(path.parent / "stages" / (tag + "-" + phase + ".json"))
                if stage is not None:
                    record["stage_states"][phase] = stage.get("status", "complete")
                    if stage.get("status") == "ok" and stage.get("fallback_used"):
                        record["stage_states"][phase] = "backup_used"
                    if phase == "red" and not stage.get("eligible"):
                        record["stage_states"][phase] = "no_attack"
            memory_stages = [read(path.parent / "stages" / f"round-{record.get('study_index', 0)}-{role}-memory.json") for role in ("red", "blue")]
            if all(memory_stages):
                record["stage_states"]["memory"] = "updated" if any(s.get("promoted") for s in memory_stages) else "retained"
            record["memories"] = {}
            for role in ("red", "blue"):
                checkpoints = sorted((path.parent / "memories" / role).glob("v*.json"), key=lambda p: int(p.stem[1:]))
                latest = read(checkpoints[-1], {}) if checkpoints else {}
                initial = record.get("options", {}).get(role + "_rules", [])
                record["memories"][role] = {"version": checkpoints[-1].stem if checkpoints else "initial",
                    "rules": latest.get("rules", initial), "explanation": latest.get("explanation", "Your supplied starting rules. Empty means no learned strategy.")}
            sessions.append(record)
        return sorted(sessions, key=lambda r: r.get("created_at", ""), reverse=True)

    def status(self):
        with self.lock:
            return {**self.ready(), "sessions": self.sessions()}

    def start(self, raw):
        config = options(raw)
        with self.lock:
            sessions = self.sessions()
            existing = next((s for s in sessions if s.get("options", {}).get("launch_id") == config["launch_id"]), None)
            if existing:
                return existing
            if any(s["status"] in ACTIVE for s in sessions):
                raise ValueError("A live run is already active. Stop it or let it finish before starting another.")
            readiness = self.ready()
            if not readiness["ready"]:
                raise ValueError(". ".join(readiness["issues"]))
            run_id = "live-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
            root = self.runs / run_id
            root.mkdir(parents=True)
            record = {"id": run_id, "status": "starting", "phase": "preparing", "message": "Selecting original studies; no prepared attacks are loaded.",
                "judges": JUDGES, "created_at": now(), "updated_at": now(), "completed_studies": 0, "study_index": 0, "options": config}
            save(root / "live.json", record)
            try:
                with (root / "worker.log").open("ab") as log:
                    child = self.spawn([sys.executable, "-m", "radarena.live_runner", "--root", str(root), "--manifest", str(self.manifest)],
                        cwd=Path.cwd(), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                self.children[run_id] = child
                # The worker waits for this PID handoff before updating state.
                record["pid"] = child.pid
                save(root / "live.json", record)
            except OSError:
                record.update(status="failed", message="Could not start the live worker", finished_at=now())
                save(root / "live.json", record)
                raise ValueError(record["message"]) from None
            return {k: v for k, v in record.items() if k != "pid"}

    def stop(self, run_id):
        with self.lock:
            session = next((s for s in self.sessions() if s["id"] == run_id), None)
            if not session:
                raise ValueError("Live run not found")
            if session["status"] in ACTIVE:
                # Cooperative cancellation preserves the in-flight request's cost/end event.
                (self.runs / run_id / "stop.requested").touch()
            return {"id": run_id, "stop_requested": session["status"] in ACTIVE}
