"""Finish unattempted episodes after a run stops, preserving every attempted failure.

This does not retry or replace failed predictions. It uses the frozen agent code,
configuration, graph artifact, benchmark and persistent audit budget of the run.
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

from radarena.benchmark import read_benchmark
from radarena.evaluate import read_records, summarize_run, verify_case
from radarena.knowledge import load_pack
from radarena.report_graph import ReportGraphStore
from radarena.runtime import make_models, model_config
from radarena.tracing import ACTIVE_AUDIT, AuditSession, audit_context


def finish(output, benchmark, knowledge_file, report_graphs, max_cost):
    meta = json.loads((output / "metadata.json").read_text())
    cases, bm = read_benchmark(benchmark)
    knowledge, store = load_pack(knowledge_file), ReportGraphStore(report_graphs)
    done = {(r["case_id"], r["variant"]) for r in read_records(output / "predictions.jsonl")}
    implementation = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(Path("src/radarena").glob("*.py"))}
    assert hashlib.sha256(json.dumps(implementation, sort_keys=True).encode()).hexdigest() == meta["implementation_sha256"]
    assert bm["benchmark_sha256"] == meta["benchmark_sha256"]
    assert knowledge.metadata() == meta["knowledge"] and store.metadata() == meta["report_graphs"]
    audit = AuditSession(output / "audit", max_cost, 60)
    with audit_context(audit):
        text_lm, vision_lm = make_models()
        assert model_config() == meta["models"]
        for case in cases:
            if case["case_id"] not in meta["case_ids"]:
                continue
            for path, expected in zip(case["image_paths"], case["image_sha256"], strict=True):
                assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
            for variant in meta["variants"]:
                if (case["case_id"], variant) in done:
                    continue
                audit.set_context(case_id=case["case_id"], study_id=case["study_id"], variant=variant,
                                  run=str(output), role="verifier", continuation="unattempted_only")
                offsets = [len(lm.history) for lm in [text_lm, vision_lm]]
                start = time.monotonic()
                r = {"case_id": case["case_id"], "study_id": case["study_id"], "variant": variant,
                     "private_label": case["private_label"]}
                try:
                    verdict, observations = verify_case(case, variant, text_lm, vision_lm, knowledge, store)
                    r.update(status="ok", verdict=verdict.model_dump(), observations=observations,
                             report_claims=store.for_sentences(case["candidate"]))
                except Exception as exc:
                    r.update(status="failed", exception_type=type(exc).__name__)
                history = [h for lm, offset in zip([text_lm, vision_lm], offsets) for h in lm.history[offset:]]
                r.update(elapsed_seconds=round(time.monotonic()-start, 3), model_calls=[{
                    "model": h.get("model"), "usage": h.get("usage"), "reported_cost": h.get("cost"),
                    "cache_hit": h.get("cache_hit")} for h in history])
                with (output / "predictions.jsonl").open("a") as f:
                    f.write(json.dumps(r)+"\n")
                print(variant, case["case_id"], r["status"], flush=True)
                if r["status"] != "ok":
                    break
    return summarize_run(output)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--benchmark", type=Path, required=True)
    p.add_argument("--knowledge-file", type=Path, required=True)
    p.add_argument("--report-graphs", type=Path, required=True)
    p.add_argument("--max-cost", type=float, required=True)
    a = p.parse_args()
    result = finish(a.run, a.benchmark, a.knowledge_file, a.report_graphs, a.max_cost)
    print(json.dumps({"complete": result["complete"]}))
