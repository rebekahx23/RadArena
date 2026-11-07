"""Render recorded research traces as a readable Markdown case walkthrough; no API calls."""

import argparse
import json
from pathlib import Path

from radarena.evaluate import read_records, summarize_run


def build(output):
    summary = summarize_run(output)
    cases = [json.loads(x) for x in (output / "cases.jsonl").read_text().splitlines()]
    records = {(r["case_id"], r["variant"]): r for r in read_records(output / "predictions.jsonl")}
    metadata = json.loads((output / "metadata.json").read_text())
    lines = ["# Development smoke-test walkthrough", "",
             "Researcher-only: contains original reports and synthetic-edit labels. Do not feed this artifact to either agent.", "",
             f"Run complete: **{summary['complete']}**. Model settings: `{json.dumps(metadata['models'])}`.",
             "Six reports from three development studies are a behavior check, not a clinical-performance estimate.",
             "All arms use the same cases and fixed reference configuration. No memory learning is enabled.", "",
             "[Aggregate results](results.md) | [Ordered prompts and model outputs](audit/trace.md) | [Budget ledger](audit/budget.json)", "",
             "The ordered trace records explicit outputs, explanations and actions, not hidden internal reasoning. Clinical validity and image-evidence correctness still require qualified review.", ""]
    for case in cases:
        label = case["private_label"]
        kind = label["error_type"] if label["has_error"] else "unchanged control"
        lines += [f"## Study {case['study_id']}: {kind}", "", f"Case ID: `{case['case_id']}`.", ""]
        lines += [f"[Image {i+1}](<{p}>)" for i, p in enumerate(case["image_paths"])]
        lines += ["", "### Candidate seen by the verifier", ""]
        lines += [f"- **{s['id']}**: {s['text']}" for s in case["candidate"]]
        supplied_claims = next((r.get("report_claims") for (cid, _), r in records.items()
                                if cid == case["case_id"] and r.get("report_claims")), None)
        if supplied_claims:
            lines += ["", "### RadGraph claims supplied with this whole report", "",
                      "These describe candidate text, not independent image evidence.", "",
                      "```json", json.dumps(supplied_claims, indent=2), "```"]
        if label["has_error"]:
            source = {s["id"]: s["text"] for s in case["source"]}
            lines += ["", "### Researcher-only edit key", ""]
            for sid in label["changed_sentence_ids"]:
                lines += [f"- Original **{sid}**: {source[sid]}"]
        for variant in metadata["variants"]:
            lines += ["", f"### {variant}", ""]
            r = records.get((case["case_id"], variant))
            if not r:
                lines += ["Not attempted."]
                continue
            if r["status"] != "ok":
                lines += [f"Execution failed: `{r.get('exception_type')}`. This is not a clean verdict."]
                continue
            v = r["verdict"]
            lines += [f"Decision: **{v['decision']}**.", "", f"Limitations: {v['limitations']}"]
            for f in v["findings"]:
                lines += ["", f"Flagged **{f['sentence_id']}** ({f['error_type']}); cited {', '.join(f['tool_call_ids'])}.",
                          "", f["evidence"]]
            for o in r.get("observations", []):
                lines += ["", f"#### {o['tool_call_id']}", "", f"Question: {o['question']}",
                          "", f"Observation: {o['observation']}", "", f"Limitations: {o['limitations']}"]
        lines += [""]
    path = output / "walkthrough.md"
    path.write_text("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    print(build(parser.parse_args().run))
