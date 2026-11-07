"""Run identical frozen cases through baselines; retain failures and uncertainty."""

import hashlib
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

import dspy

from .agents import (BlueVerifier, DirectImageCheck, TextOnlyCheck, Verdict,
                     validate_verdict)
from .benchmark import read_benchmark
from .data import Sentence

VARIANTS = ("text_only", "direct_vlm", "blue_tools")


def verify_case(case, variant, text_lm, vision_lm, knowledge=None, graph_store=None, clinical_context="", strategies=None):
    """Construct public inputs explicitly. Never pass the whole benchmark case."""
    candidate = [Sentence.model_validate(s) for s in case["candidate"]]
    report_claims = graph_store.for_sentences(candidate) if graph_store else []
    from .knowledge import reference_context
    reference_notes = reference_context(knowledge, "verifier", candidate, text_lm)
    if variant == "text_only":
        predict = dspy.Predict(TextOnlyCheck)
        predict.set_lm(text_lm)
        verdict = predict(candidate=candidate, clinical_context=clinical_context, report_claims=report_claims, reference_notes=reference_notes).verdict
        return validate_verdict(verdict, candidate, ["report_text"]), []
    images = [dspy.Image.from_path(p) for p in case["image_paths"]]
    if variant == "direct_vlm":
        predict = dspy.Predict(DirectImageCheck)
        predict.set_lm(vision_lm)
        verdict = predict(candidate=candidate, clinical_context=clinical_context, images=images, report_claims=report_claims, reference_notes=reference_notes).verdict
        return validate_verdict(verdict, candidate, ["direct_image"]), []
    if variant == "blue_tools":
        result = BlueVerifier(text_lm=text_lm, vision_lm=vision_lm)(
            candidate=candidate, clinical_context=clinical_context, images=images, strategies=strategies or [], reference_notes=reference_notes, report_claims=report_claims)
        return result.verdict, result.observations
    raise ValueError(f"Unknown variant: {variant}")


def run_evaluation(benchmark, output, split="dev", variants=VARIANTS, limit_studies=None, knowledge_file=None,
                   handbook_condition="full", study_ids=None, report_graphs=None, indications_csv=None, blue_memory=None):
    from .memory import load_memory
    blue_rules, memory_metadata = load_memory(blue_memory, "blue")
    from .runtime import make_models, model_config
    from .knowledge import load_pack
    knowledge = load_pack(knowledge_file, condition=handbook_condition)
    from .report_graph import ReportGraphStore
    graph_store = ReportGraphStore(report_graphs) if report_graphs else None
    cases, benchmark_meta = read_benchmark(benchmark)
    if not variants or len(set(variants)) != len(variants) or not set(variants) <= set(VARIANTS):
        raise ValueError(f"Choose distinct variants from {VARIANTS}")
    if limit_studies is not None and limit_studies < 1:
        raise ValueError("limit-studies must be positive")
    cases = [c for c in cases if c["split"] == split]
    if study_ids is not None:
        if limit_studies is not None or not set(study_ids) <= {c["study_id"] for c in cases}:
            raise ValueError("Use valid study IDs from this split, without limit-studies")
        cases = [c for c in cases if c["study_id"] in study_ids]
    if limit_studies is not None:
        selected = sorted({c["study_id"] for c in cases})[:limit_studies]
        cases = [c for c in cases if c["study_id"] in selected]
    if not cases:
        raise ValueError("No evaluation cases selected")
    from .clinical_context import Indications
    indications = Indications(indications_csv) if indications_csv else None
    contexts = {c["study_id"]: indications.get(c["study_id"]) if indications else "" for c in cases}
    if graph_store:
        for case in cases:
            graph_store.for_sentences(case["candidate"])  # Fail before paid calls if incomplete/mismatched.
    # Verify image content once per unique path before making paid requests.
    checked = {}
    for case in cases:
        for path, expected in zip(case["image_paths"], case["image_sha256"], strict=True):
            if path not in checked:
                checked[path] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            if checked[path] != expected:
                raise ValueError(f"Frozen image content changed: {path}")
    text_lm, vision_lm = make_models()
    implementation = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(Path(__file__).parent.glob("*.py"))}
    metadata = {"benchmark_sha256": benchmark_meta["benchmark_sha256"],
                "implementation_sha256": hashlib.sha256(json.dumps(implementation, sort_keys=True).encode()).hexdigest(),
                "split": split, "variants": list(variants), "models": model_config(),
                "case_ids": [c["case_id"] for c in cases], "seed": benchmark_meta["seed"],
                "scope": benchmark_meta["scope"], "memory": memory_metadata,
                "knowledge": knowledge.metadata() if knowledge else None,
                "report_graphs": graph_store.metadata() if graph_store else None,
                "clinical_context": indications.metadata() if indications else {"condition": "none"},
                "expected_records": len(cases) * len(variants)}
    output.mkdir(parents=True, exist_ok=True)
    meta_path, records_path = output / "metadata.json", output / "predictions.jsonl"
    if meta_path.exists() and json.loads(meta_path.read_text()) != metadata:
        raise ValueError("Run configuration differs from existing output. Use a new directory.")
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
    # Researcher-only snapshot for reproducing and reading each trace. Never sent whole to agents.
    (output / "cases.jsonl").write_text("".join(json.dumps(c)+"\n" for c in cases))
    previous = read_records(records_path)
    done = {(r["case_id"], r["variant"]) for r in previous if r["status"] == "ok"}
    for case in cases:
        for variant in variants:
            if (case["case_id"], variant) in done:
                continue
            offsets = [len(lm.history) for lm in (text_lm, vision_lm)]
            from .tracing import ACTIVE_AUDIT
            audit = ACTIVE_AUDIT.get()
            if audit:
                audit.set_context(case_id=case["case_id"], study_id=case["study_id"], variant=variant,
                                  run=str(output), role="verifier")
            start = time.monotonic()
            record = {"case_id": case["case_id"], "study_id": case["study_id"],
                      "variant": variant, "private_label": case["private_label"],
                      "clinical_context": contexts[case["study_id"]]}
            try:
                verdict, observations = verify_case(case, variant, text_lm, vision_lm, knowledge, graph_store, contexts[case["study_id"]], blue_rules)
                record.update(status="ok", verdict=verdict.model_dump(), observations=observations)
                if graph_store:
                    record["report_claims"] = graph_store.for_sentences(case["candidate"])
                if hasattr(knowledge, "last_access"):
                    record["handbook_access"] = list(knowledge.last_access)
            except Exception as exc:
                # API or parsing failures are never interpreted as a clean report.
                # Stop instead of repeating a credential/quota failure across cases.
                record.update(status="failed", exception_type=type(exc).__name__)
                with records_path.open("a") as stream:
                    stream.write(json.dumps(record) + "\n")
                raise RuntimeError(f"Evaluation stopped at {case['case_id']} / {variant}: {type(exc).__name__}. Completed cases can be resumed.") from exc
            history = [h for lm, offset in zip((text_lm, vision_lm), offsets) for h in lm.history[offset:]]
            record.update(elapsed_seconds=round(time.monotonic() - start, 3),
                          model_calls=[{"model": h.get("model"), "usage": h.get("usage"),
                                        "reported_cost": h.get("cost"), "cache_hit": h.get("cache_hit")}
                                       for h in history])
            with records_path.open("a") as stream:
                stream.write(json.dumps(record) + "\n")
            print(f"{variant}: {case['case_id']} complete", flush=True)
    return summarize_run(output)


def read_records(path):
    if not path.exists():
        return []
    # Resuming can replace a failed attempt. Keep the latest outcome per case/arm.
    latest = {}
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            latest[(row["case_id"], row["variant"])] = row
    return list(latest.values())


def ratio(a, b):
    return a / b if b else None


def f1(tp, fp, fn):
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0


def metrics(rows, expected=None):
    counts = Counter()
    category_total, category_hits = Counter(), Counter()
    latency, reported_cost = [], []
    runtime_calls, unknown_cost_calls = 0, 0
    for row in rows:
        if row["status"] != "ok":
            counts["runtime_failures"] += 1
            continue
        label, verdict = row["private_label"], row["verdict"]
        gold_error = label["has_error"]
        decision = verdict["decision"]
        predicted_error = decision == "error"
        counts["completed"] += 1
        counts["corrupted" if gold_error else "controls"] += 1
        counts["uncertain"] += decision == "uncertain"
        counts["strict_correct"] += decision == ("error" if gold_error else "no_error_detected")
        counts["detection_tp"] += gold_error and predicted_error
        counts["detection_fp"] += not gold_error and predicted_error
        counts["detection_fn"] += gold_error and not predicted_error
        gold = set(label["changed_sentence_ids"])
        flagged = {f["sentence_id"] for f in verdict["findings"]}
        counts["localization_tp"] += len(gold & flagged)
        counts["localization_fp"] += len(flagged - gold)
        counts["localization_fn"] += len(gold - flagged)
        if gold_error:
            kind = label["error_type"]
            category_total[kind] += 1
            category_hits[kind] += any(f["sentence_id"] in gold and f["error_type"] == kind for f in verdict["findings"])
        latency.append(row.get("elapsed_seconds", 0))
        for call in row.get("model_calls", []):
            runtime_calls += 1
            if isinstance(call.get("reported_cost"), (int, float)):
                reported_cost.append(call["reported_cost"])
            else:
                unknown_cost_calls += 1
    expected = len(rows) if expected is None else expected
    tp, fp, fn = (counts[k] for k in ["detection_tp", "detection_fp", "detection_fn"])
    ltp, lfp, lfn = (counts[k] for k in ["localization_tp", "localization_fp", "localization_fn"])
    completed = counts["completed"]
    return {
        "expected": expected, "attempted": len(rows), "completed": completed,
        "runtime_failures": counts["runtime_failures"], "not_attempted": expected-len(rows),
        "completion_rate": ratio(completed, expected),
        "strict_decision_accuracy_all_expected": ratio(counts["strict_correct"], expected),
        "detection_precision": ratio(tp, tp+fp), "detection_recall": ratio(tp, tp+fn),
        "detection_f1_completed": f1(tp, fp, fn) if completed else None,
        "localization_f1_completed": f1(ltp, lfp, lfn) if completed else None,
        "localization_counts": {"tp": ltp, "fp": lfp, "fn": lfn},
        "false_positive_rate_completed_controls": ratio(fp, counts["controls"]),
        "abstention_rate_completed": ratio(counts["uncertain"], completed),
        "decision_coverage_completed": ratio(completed-counts["uncertain"], completed),
        "category_localized_recall": {k: {"hits": category_hits[k], "n": n,
                                          "recall": category_hits[k]/n} for k, n in category_total.items()},
        "mean_elapsed_seconds": ratio(sum(latency), len(latency)),
        "reported_cost_usd_sum": sum(reported_cost), "calls_missing_cost": unknown_cost_calls,
        "recorded_model_calls": runtime_calls,
    }


def failure_tags(row):
    if row["status"] != "ok":
        return ["runtime_failure"]
    label, verdict = row["private_label"], row["verdict"]
    tags = []
    if verdict["decision"] == "uncertain":
        tags.append("uncertain")
    if label["has_error"]:
        gold = set(label["changed_sentence_ids"])
        flags = verdict["findings"]
        hit = [f for f in flags if f["sentence_id"] in gold]
        if not hit:
            tags.append("missed_edit")
        if any(f["sentence_id"] not in gold for f in flags):
            tags.append("wrong_location_or_additional_flag")
        if hit and not any(f["error_type"] == label["error_type"] for f in hit):
            tags.append("wrong_category")
    elif verdict["decision"] == "error":
        tags.append("control_false_alarm")
    return tags


def paired_interval(rows, baseline, variant="blue_tools", samples=1000):
    groups = defaultdict(dict)
    for row in rows:
        if row["variant"] in {baseline, variant}:
            groups[row["case_id"]][row["variant"]] = row
    if not groups or any(set(g) != {baseline, variant} or any(r["status"] != "ok" for r in g.values()) for g in groups.values()):
        return {"available": False, "reason": "Requires both variants complete on all paired cases"}
    by_study = defaultdict(list)
    for group in groups.values():
        by_study[group[baseline]["study_id"]].append(group)
    ids = sorted(by_study)
    def delta(selected):
        pairs = [g for sid in selected for g in by_study[sid]]
        return (metrics([g[variant] for g in pairs])["localization_f1_completed"] -
                metrics([g[baseline] for g in pairs])["localization_f1_completed"])
    rng = random.Random(0)
    boot = sorted(delta(rng.choices(ids, k=len(ids))) for _ in range(samples))
    return {"available": True, "metric": "localization_f1", "difference": delta(ids),
            "interval_95_percentile": [boot[int(.025*samples)], boot[min(int(.975*samples), samples-1)]],
            "bootstrap_studies": len(ids), "resamples": samples,
            "limitation": "Exploratory pilot interval; independent patient IDs unavailable"}


def summarize_run(output):
    metadata = json.loads((output / "metadata.json").read_text())
    rows = read_records(output / "predictions.jsonl")
    allowed = {(case, variant) for case in metadata["case_ids"] for variant in metadata["variants"]}
    if any((r["case_id"], r["variant"]) not in allowed for r in rows):
        raise ValueError("Prediction file contains records outside this run's configuration")
    arms = {v: metrics([r for r in rows if r["variant"] == v], len(metadata["case_ids"]))
            for v in metadata["variants"]}
    complete = len(rows) == metadata["expected_records"] and all(r["status"] == "ok" for r in rows)
    summary = {"scope": metadata["scope"], "split": metadata["split"], "complete": complete,
               "variants": arms,
               "paired_comparisons": {b: paired_interval(rows, b) for b in metadata["variants"]
                                      if b != "blue_tools" and "blue_tools" in arms} if complete else {}}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    failures = [dict(r, failure_tags=failure_tags(r)) for r in rows if failure_tags(r)]
    (output / "failure_cases.jsonl").write_text("".join(json.dumps(r) + "\n" for r in failures))
    lines = ["# Evaluation results", "", f"Split: {metadata['split']}. Complete: {complete}.",
             f"Scope: {metadata['scope']}.", "",
             "| Variant | Completed / expected | Detection F1 | Localization F1 | Control FPR | Abstention |",
             "| --- | --- | --- | --- | --- | --- |"]
    def show(v):
        return "N/A" if v is None else f"{v:.3f}"
    for v, m in arms.items():
        lines.append(f"| {v} | {m['completed']} / {m['expected']} | {show(m['detection_f1_completed'])} | {show(m['localization_f1_completed'])} | {show(m['false_positive_rate_completed_controls'])} | {show(m['abstention_rate_completed'])} |")
    lines += ["", "F1 and FPR use completed verdicts; strict accuracy and completion rate in summary.json also account for missing/failed cases.",
              "Controls are unchanged source reports, not adjudicated error-free clinical reports.",
              "No clinical or co-evolution conclusion follows from this synthetic benchmark alone."]
    (output / "results.md").write_text("\n".join(lines) + "\n")
    return summary
