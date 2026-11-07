"""Read-only adapters for the saved learning and open-ended online run formats.

These adapters inspect artifacts only. They never import or invoke either runner.
"""

import re
from collections import defaultdict

from .viewer import (input_field, judge_warnings, localization_score, normalize_calls,
                     read_json, read_rows)


class Artifacts:
    def __init__(self, store, root):
        self.store, self.root = store, root

    def allowed(self, path):
        return not path.is_symlink() and path.resolve().is_relative_to(self.store.root)

    def json(self, path, default=None):
        return read_json(path, default) if self.allowed(path) else default

    def rows(self, path):
        return read_rows(path) if self.allowed(path) else []


def rules_from(record):
    if isinstance(record.get("rules"), list):
        return record["rules"]
    library = record.get("library", record)
    return [rule for category in sorted(library) for rule in library[category]
            if isinstance(rule, str)] if isinstance(library, dict) and all(isinstance(v, list) for v in library.values()) else []


def recorded_rules(calls, fallback):
    for field in ("own_rules", "strategies", "previous_own_rules", "previous_rules"):
        value = input_field(calls, field)
        if isinstance(value, list):
            return value
    return fallback


def has_images(calls):
    return any(part.get("type") == "image_url" for call in calls
               for message in call["inputs"].get("messages") or []
               for part in (message.get("content") if isinstance(message.get("content"), list) else []))


def review_item(review_id, raw, calls):
    analysis = raw.get("analysis") or raw.get("review")
    record = dict(raw, analysis=analysis)
    record.setdefault("judge_model", raw.get("model") or next((c["model"] for c in calls), "Unknown model"))
    record.setdefault("image_review", has_images(calls) if calls else None)
    record.setdefault("agent_feedback", "Consensus-filtered feedback can update role-private memories after each training round.")
    record.setdefault("rubric_version", "Open-ended review")
    for call in calls:
        call["judge_id"] = review_id
        call["audit_call_number"] = call["number"]
        for output in call["outputs"]:
            if not isinstance(output, dict) or "review" not in output:
                continue
            if raw.get("status") == "ok" and output["review"] == analysis:
                call["review_disposition"] = "accepted"
            else:
                attempt = next((a for a in raw.get("attempts", []) if a.get("review") == output["review"]), {})
                rejected = bool(attempt.get("validation_error")) or attempt.get("accepted") is False
                call["review_disposition"] = "rejected" if rejected else "superseded" if raw else "raw"
                call["review_validation_error"] = attempt.get("validation_error")
    return {"id": review_id, "record": record if raw else None, "status": raw.get("status", "recording"),
            "calls": calls, "model": record["judge_model"], "cost": sum(c["cost"] for c in calls),
            "cost_known": bool(calls) and all(c["cost_known"] for c in calls), "has_trace": bool(calls),
            "warnings": []}


def base_episode(artifacts, episode_id, study_id, source, candidate, calls, **extra):
    study = artifacts.store.study(study_id)
    return {"id": episode_id, "study_id": study_id, "source": source or [], "candidate": candidate or [],
            "variant": "red_blue", "activity_type": "report", "attacker_kind": "model", "attack": {},
            "calls": calls, "image_paths": study.get("image_paths", []), "views": study.get("image_views", []),
            "judges": [], "judge": None, "verdict": None, "observations": [], "score": None,
            "status": "recording", **extra}


def call_status(calls, saved):
    if saved:
        return "complete"
    return "failed" if calls and calls[-1]["status"] == "failed" else "recording"


def memory_context(artifacts, metadata, role, calls, checkpoint, sha=None):
    if isinstance(checkpoint, int):
        saved = artifacts.json(artifacts.root / "memories" / role / f"v{checkpoint}.json", {}) if checkpoint else {}
        fallback = rules_from(saved) if checkpoint else rules_from(metadata.get("initial_memories", {}).get(role, {}))
        version = f"v{checkpoint}" if checkpoint else "initial"
    else:
        saved, fallback, version = {}, [], checkpoint
    rules = recorded_rules([c for c in calls if c["role"] == role], fallback)
    return {"version": version, "rules": rules, "sha256": sha or saved.get("memory_sha256"),
            "explanation": saved.get("explanation")}


def memory_episode(artifacts, stage, saved, calls, metadata, checkpoint):
    role = "red" if re.search(r"(?:^|/|-)red(?:/|-)", stage) else "blue"
    old = memory_context(artifacts, metadata, role, calls, max(checkpoint - 1, 0))
    return base_episode(artifacts, stage, "—", [], [], calls,
        variant="memory_update", activity_type="memory_update", attacker_kind="none",
        status=call_status(calls, saved), image_paths=[], memory_role=role, checkpoint=f"v{checkpoint}",
        memories={role: old}, memory_update=saved, memory_rules=rules_from(saved), stage_label=stage)


def add_call_ids(calls, audit_id):
    for call in calls:
        call["audit_id"] = audit_id
        call["id"] = f"{audit_id}:{call['number']}"
    return calls


def load_open(artifacts, metadata):
    root = artifacts.root
    selection = artifacts.json(root / "selection.json", [])
    selection_by_id = {s["study_id"]: s for s in selection}
    records = {p.stem: artifacts.json(p, {}) for p in sorted((root / "episodes").glob("*.json"))}
    stages = {p.stem: artifacts.json(p, {}) for p in sorted((root / "stages").glob("*.json"))}
    groups, all_calls = {}, []
    for path in sorted((root / "audit").glob("*/calls.jsonl")):
        calls = add_call_ids(normalize_calls(artifacts.rows(path)), path.parent.relative_to(root).as_posix())
        groups[path.parent.name] = calls
        all_calls.extend(calls)
    tags = sorted({match[0] for name in [*records, *stages, *groups]
                   if (match := re.match(r"^\d+-[^-]+", name))})
    episodes, used = [], set()
    for tag in tags:
        index, study_id = tag.split("-", 1)
        index = int(index)
        study = selection_by_id.get(study_id, artifacts.store.study(study_id))
        row, red, blue = records.get(tag, {}), stages.get(tag + "-red", {}), stages.get(tag + "-blue", {})
        red_calls, blue_calls = groups.get(tag + "-red", []), groups.get(tag + "-blue", [])
        used.update([tag + "-red", tag + "-blue"])
        source = row.get("source") or red.get("source") or input_field(red_calls, "source") or study.get("sentences", [])
        candidate = row.get("candidate") or red.get("candidate") or blue.get("candidate") or input_field(blue_calls, "candidate") or []
        changes = row.get("changes", red.get("changes", []))
        attack = {"has_error": bool(changes), "changes": changes,
                  "changed_sentence_ids": sorted({sid for change in changes for sid in change.get("source_ids", []) + change.get("candidate_ids", [])}),
                  "rationale": row.get("rationale", red.get("rationale", "")),
                  "error_type": ", ".join(dict.fromkeys(change.get("category", "unspecified") for change in changes))}
        calls = red_calls + blue_calls
        verdict = row.get("blue", blue.get("blue"))
        observations = row.get("observations", blue.get("observations", []))
        live_demo = metadata.get("live_demo", False)
        checkpoint = (index - 1 if metadata.get("options", {}).get("learn") else 0) if live_demo else min((index - 1) // 5, 3)
        if red or red_calls:
            attack["has_error"] = bool(changes) if red else None
        memories = {role: memory_context(artifacts, metadata, role, calls, checkpoint,
                       (red if role == "red" else blue).get("memory_sha256")) for role in ("red", "blue")}
        episode = base_episode(artifacts, tag + ":attack", study_id, source, candidate, calls,
            variant="online_attack", experiment_format="open_online", score_scope="open_report",
            attack=attack, verdict=verdict, observations=observations, memories=memories,
            round=index if live_demo else min((index - 1) // 5 + 1, 4), study_index=index,
            phase="live demo" if live_demo else "frozen paired probe" if index > 15 else "online training",
            indication=row.get("indication") or input_field(blue_calls, "indication") or input_field(red_calls, "indication"),
            image_paths=row.get("image_paths") or study.get("image_paths", []),
            status="invalid_output" if verdict and verdict.get("decision") == "invalid_output" else call_status(calls, row or blue))
        judge_numbers = {int(match[1]) for name in [*groups, *stages]
                         if (match := re.fullmatch(re.escape(tag) + r"-judge(\d+)", name))}
        judge_numbers.update(range(1, len(row.get("reviews", [])) + 1))
        for number in sorted(judge_numbers):
            name = f"{tag}-judge{number}"
            raw = stages.get(name) or (row.get("reviews", [])[number - 1] if len(row.get("reviews", [])) >= number else {})
            review_calls = groups.get(name, [])
            review = review_item(name, raw, review_calls)
            review["warnings"] = judge_warnings(review["record"] or {}, verdict)
            episode["judges"].append(review)
            episode["calls"] = episode["calls"] + review_calls
            used.add(name)
        episode["judge"] = episode["judges"][0]["record"] if episode["judges"] else None
        from .outcomes import study_outcome
        episode["outcome"] = study_outcome(row or red, verdict,
            [review["record"] for review in episode["judges"] if review["record"]],
            final=bool(row) or artifacts.json(root / "live.json", {}).get("status") in {"complete", "failed", "stopped", "interrupted"},
            control=(row.get("control") or stages.get(tag + "-control", {})).get("blue"),
            panel_size=len(metadata.get("judges", [None, None])), policy=metadata.get("review_policy", "unanimous"))
        episodes.append(episode)
        for suffix, field, variant in [("control", "control", "unchanged_control"),
                                       ("initial-probe", "initial_probe", "initial_memory_probe"),
                                       ("initial-control", "initial_control", "initial_memory_control")]:
            name = f"{tag}-{suffix}"
            saved = stages.get(name) or row.get(field, {})
            stage_calls = groups.get(name, [])
            used.add(name)
            if not saved and not stage_calls:
                continue
            control = "control" in suffix
            blue_memory = memory_context(artifacts, metadata, "blue", stage_calls, 0 if suffix.startswith("initial") else checkpoint,
                                         saved.get("memory_sha256"))
            episodes.append(base_episode(artifacts, name, study_id, source,
                saved.get("candidate") or input_field(stage_calls, "candidate") or (source if control else candidate), stage_calls,
                variant=variant, experiment_format="open_online", score_scope="open_report",
                attacker_kind="none" if control else "reused", attack={"has_error": False} if control else attack,
                verdict=saved.get("blue"), observations=saved.get("observations", []), memories={"blue": blue_memory},
                round=episode["round"], study_index=index, phase=episode["phase"], indication=episode["indication"],
                image_paths=episode["image_paths"],
                status="invalid_output" if saved.get("blue", {}).get("decision") == "invalid_output" else call_status(stage_calls, saved)))
    for stage in sorted(set(groups) | set(stages)):
        if stage in used:
            continue
        match = re.fullmatch(r"round-(\d+)-(red|blue)-memory", stage)
        if match:
            episodes.append(memory_episode(artifacts, stage, stages.get(stage, {}), groups.get(stage, []), metadata, int(match[1])))
            used.add(stage)
    for stage in sorted(set(groups) - used):
        calls = groups[stage]
        episodes.append(base_episode(artifacts, stage, "unknown", [], input_field(calls, "candidate") or [], calls,
            variant="recorded_stage", stage_label=stage, status=call_status(calls, False), attacker_kind="none"))
    return episodes, all_calls, {"completed_studies": sum(bool(r) for r in records.values()), "expected_studies": len(selection),
                                 "study_count": len(tags)}


def load_learning(artifacts, metadata):
    root = artifacts.root
    selected = artifacts.json(root / "organizer/selection.json", [])
    cases = {row["case_id"]: row for row in selected}
    by_study = {row["study_id"]: row for row in selected}
    all_calls = add_call_ids(normalize_calls(artifacts.rows(root / "audit/calls.jsonl")), "audit")
    groups = defaultdict(list)
    for call in all_calls:
        groups[call["context"].get("stage", "unknown")].append(call)
    episodes, used = [], set()

    def report_episode(episode_id, stage_names, variant, attacker_kind, checkpoint, generated=None):
        calls = [call for stage in stage_names for call in groups.get(stage, [])]
        saved = artifacts.json(root / (stage_names[-1] + ".json"), {})
        generated = generated or {}
        case_id = saved.get("case_id") or stage_names[-1].split("/")[-1]
        study_id = saved.get("study_id") or generated.get("study_id") or cases.get(case_id, {}).get("study_id", "unknown")
        case = cases.get(case_id) or by_study.get(study_id, {})
        study = artifacts.store.study(study_id)
        source = generated.get("source") or case.get("source") or study.get("sentences", [])
        candidate = saved.get("candidate") or generated.get("candidate") or input_field(calls, "candidate") or []
        changed = saved.get("changed_sentence_ids", generated.get("changed_sentence_ids", []))
        attack = {"has_error": bool(changed), "changed_sentence_ids": changed, "edits": generated.get("edits", []),
                  "rationale": generated.get("red_rationale"), "error_type": saved.get("error_type", generated.get("error_type"))}
        episode = base_episode(artifacts, episode_id, study_id, source, candidate, calls,
            variant=variant, attacker_kind=attacker_kind, experiment_format="learning", attack=attack,
            verdict=saved.get("blue"), observations=saved.get("observations", []), score=saved.get("score"),
            image_paths=case.get("image_paths", study.get("image_paths", [])),
            checkpoint=checkpoint, stage_label=episode_id, indication=saved.get("clinical_context"),
            status=call_status(calls, saved))
        cp = 3 if checkpoint == "after" else 0
        match = re.search(r"round-(\d+)", episode_id)
        if match:
            episode["round"] = int(match[1]); cp = int(match[1]) - 1
        episode["memories"] = {role: memory_context(artifacts, metadata, role, calls, cp,
            saved.get("blue_memory_sha256") if role == "blue" else generated.get("red_memory_sha256")) for role in ("red", "blue")}
        episode["score"] = episode["score"] or localization_score(episode)
        episodes.append(episode); used.update(stage_names)

    for stage in sorted(groups, key=lambda stage: ("/after/" in stage, stage)):
        if stage.startswith("blue_eval/"):
            checkpoint = stage.split("/")[1]
            report_episode(stage, [stage], f"blue_eval_{checkpoint}", "seed", checkpoint)
    rounds = sorted({match[1] for stage in groups if (match := re.match(r"train/(round-\d+)/", stage))})
    for round_id in rounds:
        prefix = f"train/{round_id}"
        generated = artifacts.json(root / (prefix + "/red_attack.json"), {})
        report_episode(prefix + ":attack", [prefix + "/red_attack", prefix + "/blue_attack"], "learned_attack", "model", round_id, generated)
        if prefix + "/blue_control" in groups:
            report_episode(prefix + ":control", [prefix + "/blue_control"], "unchanged_control", "none", round_id)
    for checkpoint in ("before", "after"):
        prefix = f"red_eval/{checkpoint}"
        if prefix + "/attack" not in groups:
            continue
        generated = artifacts.json(root / (prefix + "/attack.json"), {})
        report_episode(prefix, [prefix + "/attack", prefix + "/blue_fixed"], f"red_probe_{checkpoint}", "model", checkpoint, generated)
    for stage in sorted(groups):
        match = re.fullmatch(r"memories/(red|blue)/v(\d+)", stage)
        if match:
            saved = artifacts.json(root / (stage + ".json"), {})
            episodes.append(memory_episode(artifacts, stage, saved, groups[stage], metadata, int(match[2])))
            used.add(stage)
    # Any interrupted or future stage remains inspectable instead of disappearing.
    for stage in sorted(set(groups) - used):
        calls = groups[stage]
        episodes.append(base_episode(artifacts, stage, "unknown", [], input_field(calls, "candidate") or [], calls,
            variant="recorded_stage", stage_label=stage, status=call_status(calls, False), attacker_kind="none"))
    return episodes, all_calls, {"study_count": len({e["study_id"] for e in episodes if e["study_id"] not in ("—", "unknown")})}


def load_experiment(store, run_id, root, format_id):
    artifacts = Artifacts(store, root)
    metadata = artifacts.json(root / "metadata.json", {})
    summary = artifacts.json(root / "summary.json", {})
    loader = load_open if format_id == "open_online" else load_learning
    episodes, calls, progress = loader(artifacts, metadata)
    unique = {call["id"]: call for call in calls}
    assert len(unique) == len(calls), "Audit request IDs must be unique within a run"
    return {"id": run_id, "kind": "Live demo" if metadata.get("live_demo") else "Open-ended online" if format_id == "open_online" else "Learning pilot",
            "format": format_id, "episodes": episodes, "calls_count": len(calls),
            "live_demo": metadata.get("live_demo", False),
            "cost": sum(c["cost"] for c in calls),
            "agent_cost": sum(c["cost"] for c in calls if c["role"] != "judge"),
            "judge_cost": sum(c["cost"] for c in calls if c["role"] == "judge"),
            "known_cost": sum(c["cost"] for c in calls if c["cost_known"]),
            "unknown_calls": sum(not c["cost_known"] for c in calls), "budget": {},
            "complete": summary.get("complete", False), "summary": summary,
            "protocol": metadata.get("protocol") or metadata.get("learning"), **progress}
