"""Compare two completed, matched development runs; no model calls."""

import argparse
import json
from pathlib import Path

from radarena.evaluate import read_records, summarize_run


def compare(baseline, treatment, output):
    configs = [json.loads((p / "metadata.json").read_text()) for p in [baseline, treatment]]
    for key in set(configs[0]) | set(configs[1]):
        if key != "report_graphs" and configs[0].get(key) != configs[1].get(key):
            raise ValueError(f"Unmatched run configuration: {key}")
    if configs[0].get("report_graphs") is not None or not configs[1].get("report_graphs"):
        raise ValueError("Expected no-graph baseline and a graph-enabled treatment")
    summaries = [summarize_run(p) for p in [baseline, treatment]]
    rows = [{(r["case_id"], r["variant"]): r for r in read_records(p / "predictions.jsonl")}
            for p in [baseline, treatment]]
    complete = all(s["complete"] for s in summaries)
    per_variant_complete = {v: all(s["variants"][v]["completed"] == s["variants"][v]["expected"]
                                   and s["variants"][v]["runtime_failures"] == 0 for s in summaries)
                            for v in configs[0]["variants"]}
    pairs = []
    for key in sorted(set(rows[0]) & set(rows[1])):
        before, after = [r[key] for r in rows]
        if before["private_label"] != after["private_label"]:
            raise ValueError("Paired records disagree on labels")
        label = before["private_label"]
        pair = {"case_id": key[0], "variant": key[1], "study_id": before["study_id"],
                "has_synthetic_error": label["has_error"], "error_type": label["error_type"]}
        for condition, row in [("no_radgraph", before), ("with_radgraph", after)]:
            verdict = row.get("verdict", {})
            flags = {f["sentence_id"] for f in verdict.get("findings", [])}
            pair[condition] = {"status": row["status"], "decision": verdict.get("decision"),
                               "flagged_ids": sorted(flags),
                               "localized_edit": bool(flags & set(label["changed_sentence_ids"])),
                               "control_false_alarm": not label["has_error"] and verdict.get("decision") == "error"}
        pairs.append(pair)
    result = {"complete": complete, "per_variant_complete": per_variant_complete,
              "scope": "three-study development behavior comparison; no clinical review",
              "conditions": {"no_radgraph": summaries[0], "with_radgraph": summaries[1]},
              "paired_cases": pairs, "configs_match_except_graphs": True,
              "limits": ["reused development cases", "single run per condition", "unreviewed synthetic labels",
                         "cache reuse affects cost and timing", "no three-way claim-assessment intervention"]}
    output.mkdir(parents=True, exist_ok=True)
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# Whole-report RadGraph development comparison", "",
             f"Both conditions complete: **{complete}**. Same six reports, model, code, references, and image tools.",
             "Only the candidate-text graph context changes. All reports are supplied whole; sentence IDs locate outputs.", "",
             "| Method | Localization F1, without → with | Control FPR, without → with | Abstention, without → with | Completed, without / with |",
             "| --- | --- | --- | --- | --- |"]
    def show(x):
        return "N/A" if x is None else f"{x:.3f}"
    for variant in configs[0]["variants"]:
        a, b = [s["variants"][variant] for s in summaries]
        changes = [f"{show(a[k])} → {show(b[k]) if per_variant_complete[variant] else 'incomplete'}" for k in
                   ["localization_f1_completed", "false_positive_rate_completed_controls", "abstention_rate_completed"]]
        lines += [f"| {variant} | {' | '.join(changes)} | {a['completed']}/{a['expected']} / {b['completed']}/{b['expected']} |"]
    lines += ["", "Counts and category metrics are in comparison.json. Only variants with all six verdicts in both conditions can support a paired descriptive comparison. No effect is claimed for an incomplete variant.",
              "This is an exploratory development sample of three studies, with one attack per category. Graph extraction can be wrong.",
              "No clinical accuracy or generalization claim follows from these scores. The proposed three-way claim assessor is not implemented.", "",
              "[Without RadGraph walkthrough](no_radgraph/walkthrough.md) | [With RadGraph walkthrough](with_radgraph/walkthrough.md)", ""]
    (output / "comparison.md").write_text("\n".join(lines))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--treatment", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = compare(args.baseline, args.treatment, args.output)
    print(json.dumps({"complete": result["complete"], "output": str(args.output)}))
