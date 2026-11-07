"""Read-only local observer for recorded and in-progress RadArena traces.

No model configuration or invocation is performed by this module.
"""

import argparse
import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


STATIC = Path(__file__).with_name("viewer_static")
TOOLS = [
    {"id": "judge", "name": "JudgeEpisode", "role": "judge", "description": "Independent post-hoc attack and evidence review. Fallible researcher analysis; never fed to contestants.", "inputs": "Source · candidate · private edits · agent outputs · study images"},
    {"id": "attack", "name": "MakeAttack", "role": "red", "description": "Edit a report attribute using the source report and study images.", "inputs": "Source sentences · study images · error family · reference notes"},
    {"id": "plan", "name": "PlanChecks", "role": "blue", "description": "Plan up to three focused, neutral image questions.", "inputs": "Candidate report · reference notes"},
    {"id": "inspect", "name": "InspectImage", "role": "blue", "description": "Inspect the study images for one question. Report observations and limitations.", "inputs": "Study images · one question"},
    {"id": "assess", "name": "AssessReport", "role": "blue", "description": "Compare candidate claims with tool observations and cite evidence IDs.", "inputs": "Candidate report · image observations · reference notes"},
    {"id": "direct", "name": "DirectImageCheck", "role": "blue", "description": "Direct vision baseline: assess the candidate alongside images.", "inputs": "Candidate report · study images · reference notes"},
    {"id": "text", "name": "TextOnlyCheck", "role": "blue", "description": "Text baseline: assess the candidate without images.", "inputs": "Candidate report · reference notes"},
    {"id": "handbook", "name": "SelectChapters", "role": "both", "description": "Select role-permitted handbook chapters when a handbook is enabled.", "inputs": "Role-specific index · report"},
]


def read_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def read_rows(path):
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except ValueError:
            # A writer may still be appending the final JSONL record.
            continue
    return rows


def clean(value):
    """Defensive redaction without importing model clients or reading .env."""
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if any(s in k.lower() for s in
                ("api_key", "authorization", "password", "secret")) else clean(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"sk-or-v1-[A-Za-z0-9_-]+", "[REDACTED]", value)
        return re.sub(r"data:image/[^\s\"']+", "[inline image omitted]", value)
    return value


def prompt_text(start):
    parts = []
    for message in start.get("inputs", {}).get("messages") or []:
        content = message.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            parts.extend(p.get("text", "") for p in content if isinstance(p, dict))
    return "\n".join(parts) + (start.get("inputs", {}).get("prompt") or "")


def input_field(calls, name):
    """Recover structured DSPy inputs before a final episode file is written."""
    for call in reversed(calls):
        text = prompt_text({"inputs": call["inputs"]})
        matches = re.findall(r"\[\[ ## " + re.escape(name) + r" ## \]\]\s*([\s\S]*?)(?=\[\[ ##|$)", text)
        for match in reversed(matches):
            try:
                value, _ = json.JSONDecoder().raw_decode(match.strip())
                return value
            except ValueError:
                continue
    return None


def action_for(start):
    if start.get("context", {}).get("role") == "judge":
        return "judge"
    text = prompt_text(start)
    inputs = text.split("Your output fields")[0]
    if start.get("context", {}).get("role") == "red" and "source_sentences" in inputs:
        return "attack"
    if "question`" in inputs or "[[ ## question ## ]]" in text:
        return "inspect"
    if "observations`" in inputs:
        return "assess"
    if "images`" in inputs and "candidate`" in inputs:
        return "direct"
    if "questions" in text and "candidate`" in inputs:
        return "plan"
    if "chapters" in text or "chapter_paths" in text:
        return "handbook"
    if start.get("context", {}).get("variant") == "text_only":
        return "text"
    return "assess"


def normalize_calls(rows):
    starts = {r["call_number"]: r for r in rows if r.get("event") == "start"}
    ends = {r["call_number"]: r for r in rows if r.get("event") == "end"}
    calls = []
    for number, start in sorted(starts.items()):
        end = ends.get(number, {})
        action = action_for(start)
        outputs = end.get("outputs") or []
        parsed = []
        for output in outputs:
            try:
                parsed.append(json.loads(output) if isinstance(output, str) else output)
            except ValueError:
                parsed.append(output)
        history = end.get("history", [])
        usage = {key: sum((h.get("usage") or {}).get(key, 0) or 0 for h in history)
                 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
        calls.append({"number": number, "context": start.get("context", {}),
                      "action": action, "name": next(t["name"] for t in TOOLS if t["id"] == action),
                      "role": "judge" if action == "judge" else "red" if start.get("context", {}).get("role") == "red" else "blue",
                      "model": start.get("model", "unknown"),
                      "timestamp": start.get("timestamp_utc"),
                      "status": "failed" if end.get("exception_type") else "complete" if end else "pending",
                      "elapsed": end.get("elapsed_seconds"), "usage": usage,
                      "cost": end.get("accounted_cost_usd", start.get("reserved_cost_usd", 0)),
                      "cost_known": end.get("cost_known", False),
                      "inputs": start.get("inputs", {}), "outputs": parsed,
                      "error": end.get("exception_message")})
    return calls


class RunStore:
    def __init__(self, runs, manifest):
        self.root = Path(runs).resolve()
        self.manifest = Path(manifest).resolve()
        self.studies = {}
        self.manifest_stamp = None

    def study(self, study_id):
        stamp = self.manifest.stat().st_mtime_ns if self.manifest.exists() else None
        if stamp != self.manifest_stamp:
            self.studies = {r["study_id"]: r for r in read_rows(self.manifest)}
            self.manifest_stamp = stamp
        return self.studies.get(study_id, {})

    def discover(self):
        found = {}
        if not self.root.exists():
            return found
        for tape in sorted(self.root.rglob("calls.jsonl")):
            directory = tape.parent
            if not directory.resolve().is_relative_to(self.root) or any(p.is_symlink() for p in [tape, directory, *directory.parents]):
                continue
            if any(p.name == "judge" or p.name.endswith(".judges") for p in directory.parents if p != self.root):
                continue
            if directory.name == "audit" and directory.parent.name != "judge":
                source = directory.parent
                found[source.relative_to(self.root).as_posix()] = (source, directory, False)
            elif directory.name.endswith(".audit") and not directory.name.endswith(".judge.audit") and directory.parent.name != "judge":
                stem = directory.name.removesuffix(".audit")
                source = directory.parent / (stem + ".json")
                found[source.relative_to(self.root).with_suffix("").as_posix()] = (source, directory, True)
        return found

    def run(self, run_id):
        entry = self.discover().get(run_id)
        if not entry:
            raise KeyError("Run not found")
        source, audit, demo = entry
        calls = normalize_calls(read_rows(audit / "calls.jsonl"))
        budget = read_json(audit / "budget.json", {})
        episodes = []
        if demo:
            result = read_json(source, {})
            study_id = result.get("study_id") or next((c["context"].get("study_id") for c in calls), "unknown")
            study = self.study(study_id)
            original = result.get("source") or input_field(calls, "source_sentences") or study.get("sentences", [])
            candidate = result.get("candidate") or input_field(calls, "candidate") or []
            if not candidate:
                attack_outputs = [c["outputs"][0] for c in calls if c["action"] == "attack" and c["outputs"]]
                if attack_outputs and isinstance(attack_outputs[-1], dict):
                    replacements = {e["sentence_id"]: e["replacement"] for e in attack_outputs[-1].get("edits", [])}
                    candidate = [dict(s, text=replacements.get(s["id"], s["text"])) for s in original]
            attack = result.get("private_attack", {})
            if result:
                attack = dict(attack, has_error=bool(attack.get("edits")))
            episodes.append({"id": "demo", "study_id": study_id, "variant": "red_blue",
                             "source": original, "candidate": candidate,
                             "attack": attack,
                             "verdict": result.get("blue"), "observations": result.get("observations", []),
                             "score": result.get("score"), "image_paths": result.get("image_paths") or study.get("image_paths", []),
                             "views": study.get("image_views", []), "calls": calls,
                             "status": "complete" if result else "recording"})
        else:
            cases = {c["case_id"]: c for c in read_rows(source / "cases.jsonl")}
            predictions = {(r["case_id"], r["variant"]): r for r in read_rows(source / "predictions.jsonl")}
            groups = {}
            for call in calls:
                context = call["context"]
                key = (context.get("case_id", "unknown"), context.get("variant", "unknown"))
                groups.setdefault(key, []).append(call)
            for key in predictions:
                groups.setdefault(key, [])
            for (case_id, variant), group in groups.items():
                case, result = cases.get(case_id, {}), predictions.get((case_id, variant), {})
                study_id = case.get("study_id") or result.get("study_id") or next((c["context"].get("study_id") for c in group), "unknown")
                study = self.study(study_id)
                episodes.append({"id": f"{case_id}:{variant}", "study_id": study_id, "variant": variant,
                                 "source": case.get("source", []), "candidate": case.get("candidate") or input_field(group, "candidate") or [],
                                 "attack": case.get("private_label", {}), "verdict": result.get("verdict"),
                                 "observations": result.get("observations", []), "score": result.get("score"),
                                 "image_paths": case.get("image_paths", study.get("image_paths", [])), "views": study.get("image_views", []),
                                 "calls": group, "status": result.get("status", "recording")})
        judge_calls = []
        untraced_judge_cost = 0
        untraced_judge_calls = 0
        for episode in episodes:
            if demo:
                judge_path = source.with_suffix(".judge.json")
            else:
                case_id, variant = episode["id"].split(":", 1)
                judge_path = source / "judge" / f"{case_id}.{variant}.json"
            # Preserve the existing single-review convention; an optional sibling
            # .judges/ directory can hold separately recorded model/rubric reviews.
            review_directory = judge_path.with_name(judge_path.stem.removesuffix(".judge") + ".judges")
            review_paths = [judge_path]
            if review_directory.is_dir() and not review_directory.is_symlink():
                review_paths.extend(sorted(review_directory.glob("*.json")))
            episode["judges"] = []
            for path in review_paths:
                if path.is_symlink() or not path.resolve().is_relative_to(self.root):
                    continue
                reviewed = read_json(path, {})
                review_calls = normalize_calls(read_rows(path.with_suffix(".audit") / "calls.jsonl"))
                if not reviewed and not review_calls:
                    continue
                if reviewed and not any(key in reviewed for key in ("judge_model", "analysis", "status")):
                    continue
                review_id = path.relative_to(self.root).as_posix()
                for call in review_calls:
                    call["audit_call_number"] = call["number"]
                    call["judge_id"] = review_id
                    for output in call["outputs"]:
                        if not isinstance(output, dict) or "review" not in output:
                            continue
                        if reviewed.get("status") == "ok" and output["review"] == reviewed.get("analysis"):
                            call["review_disposition"] = "accepted"
                        else:
                            attempt = next((a for a in reviewed.get("attempts", []) if a.get("review") == output["review"]), None)
                            call["review_disposition"] = "rejected" if attempt and not attempt.get("accepted") else "superseded" if reviewed else "raw"
                            if attempt:
                                call["review_validation_error"] = attempt.get("validation_error")
                cost = sum(c["cost"] for c in review_calls)
                if not review_calls:
                    cost = reviewed.get("accounted_cost_usd", 0) or 0
                    untraced_judge_cost += cost
                    untraced_judge_calls += reviewed.get("calls", 0) or 0
                episode["judges"].append({"id": review_id, "record": reviewed or None,
                    "status": reviewed.get("status", "recording"), "calls": review_calls,
                    "model": reviewed.get("judge_model") or next((c["model"] for c in review_calls), "Unknown model"),
                    "cost": cost, "cost_known": bool(review_calls) and all(c["cost_known"] for c in review_calls),
                    "has_trace": bool(review_calls), "warnings": judge_warnings(reviewed, episode.get("verdict"))})
                episode["calls"] = episode["calls"] + review_calls
                judge_calls.extend(review_calls)
            episode["judge"] = episode["judges"][0]["record"] if episode["judges"] else None
            if not episode.get("score"):
                episode["score"] = localization_score(episode)
        all_calls = calls + judge_calls
        return {"id": run_id, "kind": "Red × Blue" if demo else "Baseline evaluation", "episodes": episodes,
                "calls_count": len(all_calls) + untraced_judge_calls, "cost": sum(c["cost"] for c in all_calls) + untraced_judge_cost,
                "agent_cost": sum(c["cost"] for c in calls), "judge_cost": sum(c["cost"] for c in judge_calls) + untraced_judge_cost,
                "untraced_judge_calls": untraced_judge_calls, "untraced_judge_cost": untraced_judge_cost,
                "known_cost": sum(c["cost"] for c in all_calls if c["cost_known"]),
                "unknown_calls": sum(not c["cost_known"] for c in all_calls) + untraced_judge_calls, "budget": budget}

    def listing(self):
        result = []
        for run_id in self.discover():
            run = self.run(run_id)
            result.append({k: v for k, v in run.items() if k not in ("episodes", "budget")}
                          | {"episode_count": len(run["episodes"])})
        return sorted(result, key=lambda r: (r["kind"] != "Red × Blue", r["id"]))


def localization_score(episode):
    """Display edit matching separately from a model's qualitative assessment."""
    attack, verdict = episode.get("attack", {}), episode.get("verdict")
    if verdict is None:
        return None
    changed = set(attack.get("changed_sentence_ids") or [e["sentence_id"] for e in attack.get("edits", [])])
    flagged = {f["sentence_id"] for f in verdict.get("findings", [])}
    return {"localization_tp": len(changed & flagged), "localization_fp": len(flagged - changed),
            "localization_fn": len(changed - flagged), "ground_truth_scope": "synthetic edits only"}


def judge_warnings(record, verdict):
    """Surface explicit output tensions, without evaluating clinical truth."""
    if record.get("status") != "ok" or not verdict:
        return []
    flagged = {f["sentence_id"] for f in verdict.get("findings", [])}
    return [{"sentence_id": review["sentence_id"],
             "message": "Blue flagged this claim as an error, while the judge describes the cited evidence as supporting the report."}
            for review in (record.get("analysis") or {}).get("flag_reviews", [])
            if review.get("sentence_id") in flagged and review.get("evidence_relation") == "supports_report"]


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send_content(self, data, content_type, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlparse(self.path)
            query = parse_qs(url.query)
            try:
                if url.path == "/api/runs":
                    payload = {"runs": store.listing(), "tools": TOOLS}
                elif url.path == "/api/run":
                    payload = store.run(query.get("id", [""])[0])
                    for episode in payload["episodes"]:
                        paths = episode.pop("image_paths")
                        episode["images"] = [{"index": i, "name": Path(p).name,
                            "view": episode["views"][i] if i < len(episode["views"]) else f"View {i+1}"}
                            for i, p in enumerate(paths)]
                elif url.path == "/api/image":
                    run = store.run(query.get("run", [""])[0])
                    episode = next(e for e in run["episodes"] if e["id"] == query.get("episode", [""])[0])
                    index = int(query.get("index", ["0"])[0])
                    if index < 0:
                        raise ValueError("Invalid image index")
                    path = Path(episode["image_paths"][index]).resolve()
                    if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                        raise ValueError("Unsupported image")
                    self.send_content(path.read_bytes(), mimetypes.guess_type(path.name)[0] or "image/png")
                    return
                elif url.path in ("/", "/app.js", "/style.css"):
                    path = STATIC / ({"/": "index.html"}.get(url.path, url.path[1:]))
                    self.send_content(path.read_bytes(), mimetypes.guess_type(path.name)[0] + "; charset=utf-8")
                    return
                else:
                    raise KeyError("Not found")
                self.send_content(json.dumps(clean(payload)).encode(), "application/json; charset=utf-8")
            except (KeyError, StopIteration, IndexError, ValueError, OSError):
                self.send_content(b'{"error":"Requested run, episode, or image is unavailable"}', "application/json", 404)
    return Handler


def serve(runs=Path("runs"), manifest=Path("data/processed/iu.jsonl"), port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(RunStore(runs, manifest)))
    print(f"RadArena observer: http://127.0.0.1:{server.server_port}", flush=True)
    print("Read-only local traces. No model calls. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=Path("runs"))
    parser.add_argument("--manifest", type=Path, default=Path("data/processed/iu.jsonl"))
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(args.runs, args.manifest, args.port)
