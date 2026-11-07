"""Offline data preparation and one real DSPy/OpenRouter episode."""

import argparse
import json
from pathlib import Path

from .data import Study, load_iu, load_iu_csv


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check configuration without making model calls")
    viewer = sub.add_parser("viewer", help="Observe local traces in a read-only arena UI; no model calls")
    viewer.add_argument("--runs", type=Path, default=Path("runs"))
    viewer.add_argument("--manifest", type=Path, default=Path("data/processed/iu.jsonl"))
    viewer.add_argument("--port", type=int, default=8765)
    prepare = sub.add_parser("prepare", help="Parse XML; provide --images to require matched files")
    prepare.add_argument("--reports", type=Path, required=True)
    prepare.add_argument("--format", choices=["iu-xml", "iu-csv"], default="iu-xml")
    prepare.add_argument("--projections", type=Path)
    prepare.add_argument("--images", type=Path)
    prepare.add_argument("--output", type=Path, default=Path("data/processed/iu.jsonl"))
    demo = sub.add_parser("demo", help="Run one paid episode; defaults to a training study")
    demo.add_argument("--manifest", type=Path, default=Path("data/processed/iu.jsonl"))
    demo.add_argument("--study-id")
    demo.add_argument("--control", action="store_true", help="Use the unchanged source report")
    demo.add_argument("--radgraph", action="store_true", help="Extract source claims for Red and candidate claims separately for Blue, locally")
    demo.add_argument("--error-type", choices=["presence_absence", "laterality", "severity"], default="laterality")
    demo.add_argument("--output", type=Path, default=Path("runs/demo.json"))
    demo.add_argument("--max-cost", type=float, default=0.5, help="Audited Qwen pilot budget in USD (at most 1)")
    demo.add_argument("--max-calls", type=int, default=80)
    demo.add_argument("--knowledge-file", "--handbook", dest="knowledge_file", type=Path,
                      help="Reference JSON pack or role-routed handbook directory")
    demo.add_argument("--handbook-condition", choices=["full", "no_domain", "no_medical", "none"], default="full")
    benchmark = sub.add_parser("make-benchmark", help="Freeze paired controls/seed attacks without model calls")
    benchmark.add_argument("--manifest", type=Path, default=Path("data/processed/iu.jsonl"))
    benchmark.add_argument("--output", type=Path, default=Path("data/processed/midpoint-v2.jsonl"))
    benchmark.add_argument("--train-studies", type=int, default=50)
    benchmark.add_argument("--dev-studies", type=int, default=20)
    benchmark.add_argument("--test-studies", type=int, default=30)
    benchmark.add_argument("--seed", default="midpoint-v2")
    evaluation = sub.add_parser("evaluate", help="Paid baseline comparisons on a frozen benchmark")
    evaluation.add_argument("--benchmark", type=Path, default=Path("data/processed/midpoint-v2.jsonl"))
    evaluation.add_argument("--split", choices=["train", "dev", "test"], default="dev")
    evaluation.add_argument("--variants", nargs="+", choices=["text_only", "direct_vlm", "blue_tools"],
                            default=["text_only", "direct_vlm", "blue_tools"])
    evaluation.add_argument("--limit-studies", type=int)
    evaluation.add_argument("--study-ids", nargs="+", help="Exact study IDs from the selected split")
    evaluation.add_argument("--report-graphs", type=Path, help="Candidate-only RadGraph artifact from extract-graphs")
    evaluation.add_argument("--max-cost", type=float, default=0.5, help="Audited Qwen pilot budget in USD (at most 1)")
    evaluation.add_argument("--max-calls", type=int, default=80)
    evaluation.add_argument("--output", type=Path, required=True)
    evaluation.add_argument("--knowledge-file", "--handbook", dest="knowledge_file", type=Path,
                            help="Same reference JSON pack or handbook directory for all variants")
    evaluation.add_argument("--handbook-condition", choices=["full", "no_domain", "no_medical", "none"], default="full")
    knowledge = sub.add_parser("show-knowledge", help="Inspect a reference pack without model calls")
    knowledge.add_argument("--file", type=Path, default=Path("knowledge/reporting_v1.json"))
    knowledge.add_argument("--role", choices=["red", "verifier"], default="verifier")
    knowledge.add_argument("--condition", choices=["full", "no_domain", "no_medical", "none"], default="full")
    knowledge.add_argument("--chapter", help="Read an exact allowed chapter path instead of the bootstrap index")
    summary = sub.add_parser("summarize", help="Generate metrics/table/error cases from recorded predictions")
    summary.add_argument("--run", type=Path, required=True)
    review = sub.add_parser("export-review", help="Export blinded human review inputs and a separate organizer key")
    review.add_argument("--benchmark", type=Path, default=Path("data/processed/midpoint-v2.jsonl"))
    review.add_argument("--split", choices=["train", "dev", "test"], default="test")
    review.add_argument("--studies", type=int, default=12)
    review.add_argument("--output", type=Path, default=Path("data/processed/review"))
    graphs = sub.add_parser("extract-graphs", help="Local CPU RadGraph extraction; no OpenRouter calls")
    graphs.add_argument("--benchmark", type=Path, default=Path("data/processed/midpoint-v2.jsonl"))
    graphs.add_argument("--split", choices=["train", "dev", "test"], default="dev")
    graphs.add_argument("--study-ids", nargs="+", required=True)
    graphs.add_argument("--model-type", choices=["radgraph", "radgraph-xl"], default="radgraph-xl")
    graphs.add_argument("--output", type=Path, required=True)
    judge = sub.add_parser("judge", help="Independent privileged post-hoc review; never feeds agents")
    judge.add_argument("--run", type=Path, required=True, help="Recorded demo JSON or evaluation directory")
    judge.add_argument("--case-id")
    judge.add_argument("--variant", choices=["text_only", "direct_vlm", "blue_tools"], default="blue_tools")
    judge.add_argument("--model", default="google/gemini-2.5-flash")
    judge.add_argument("--max-cost", type=float, default=0.5)
    judge.add_argument("--evidence-only", action="store_true", help="Audit text/citations without image interpretation")
    judge.add_argument("--manifest", type=Path, default=Path("data/processed/iu.jsonl"))
    for command in (demo, evaluation):
        command.add_argument("--indications-csv", type=Path, help="Opt in to IU indication context from this CSV; omit for no context")
    demo.add_argument("--red-memory", type=Path, help="Explicit Red-only learned strategy checkpoint")
    demo.add_argument("--blue-memory", type=Path, help="Explicit Blue-only learned strategy checkpoint")
    evaluation.add_argument("--blue-memory", type=Path, help="Blue-tools learned checkpoint; baseline methods remain unchanged")
    demo.add_argument("--strict-attacks", action="store_true", help="Reject edits outside conservative controlled error-family constraints")
    demo.add_argument("--structured-blue", action="store_true", help="Derive verdicts from a full-report evidence ledger")
    evaluation.add_argument("--structured-blue", action="store_true", help="Use the full-report evidence ledger in the Blue-tools arm")
    learn = sub.add_parser("learn", help="Paid role-private strategy-learning pilot and before/after dev comparison")
    learn.add_argument("--output", type=Path, required=True)
    learn.add_argument("--benchmark", type=Path, default=Path("data/processed/midpoint-v2.jsonl"))
    learn.add_argument("--indications-csv", type=Path, default=Path("data/archive (1)/indiana_reports.csv"))
    learn.add_argument("--max-cost", type=float, default=.5)
    learn.add_argument("--max-calls", type=int, default=100)
    args = parser.parse_args()
    try:
        if args.command == "viewer":
            from .viewer import serve
            serve(args.runs, args.manifest, args.port)
        elif args.command == "prepare":
            if args.format == "iu-csv":
                if args.projections is None or args.images is None:
                    raise ValueError("iu-csv requires --projections and --images")
                studies, summary = load_iu_csv(args.reports, args.projections, args.images)
            else:
                studies, summary = load_iu(args.reports, args.images)
            if not studies:
                raise ValueError(f"No eligible studies: {summary}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text("".join(s.model_dump_json() + "\n" for s in studies))
            write_json(args.output.with_suffix(".summary.json"), summary)
            print(json.dumps(summary, indent=2))
        elif args.command == "doctor":
            import os
            import importlib.metadata
            from .runtime import load_environment, model_config
            load_environment()
            print(json.dumps({"dspy": importlib.metadata.version("dspy"),
                              "openrouter_key_configured": bool(os.getenv("OPENROUTER_API_KEY", "").strip()),
                              "models": model_config(), "network_calls": 0}, indent=2))
        elif args.command == "make-benchmark":
            from .benchmark import build_benchmark
            print(json.dumps(build_benchmark(args.manifest, args.output,
                {"train": args.train_studies, "dev": args.dev_studies, "test": args.test_studies}, args.seed), indent=2))
        elif args.command == "evaluate":
            from .evaluate import run_evaluation
            from .tracing import AuditSession, audit_context
            with audit_context(AuditSession(args.output / "audit", args.max_cost, args.max_calls)):
                result = run_evaluation(args.benchmark, args.output, args.split,
                                       args.variants, args.limit_studies, args.knowledge_file,
                                       args.handbook_condition, args.study_ids, args.report_graphs, args.indications_csv, args.blue_memory, args.structured_blue)
            print(json.dumps(result, indent=2))
        elif args.command == "show-knowledge":
            from .knowledge import load_pack
            pack = load_pack(args.file, condition=args.condition)
            if args.chapter:
                if not hasattr(pack, "read"):
                    raise ValueError("Chapter reading requires a handbook directory")
                print(pack.read(args.chapter, args.role))
            else:
                print(pack.render(args.role))
                if hasattr(pack, "catalog"):
                    print(json.dumps(pack.catalog(args.role), indent=2))
            print(json.dumps(pack.metadata(), indent=2))
        elif args.command == "summarize":
            from .evaluate import summarize_run
            print(json.dumps(summarize_run(args.run), indent=2))
        elif args.command == "export-review":
            export_review(args)
        elif args.command == "extract-graphs":
            extract_graphs(args)
        elif args.command == "learn":
            from .learning import run_learning
            result = run_learning(args.output, args.benchmark, args.indications_csv, args.max_cost, args.max_calls)
            print(json.dumps(result, indent=2))
        elif args.command == "judge":
            from .judge import run_judge
            result, output = run_judge(args.run, args.case_id, args.variant, args.model,
                                      args.max_cost, not args.evidence_only, args.manifest)
            print(json.dumps({"judge_output": str(output), "status": result["status"],
                              "red_outcome": result.get("red_outcome"),
                              "accounted_cost_usd": result["accounted_cost_usd"]}, indent=2))
        else:
            from .tracing import AuditSession, audit_context
            with audit_context(AuditSession(args.output.parent / (args.output.stem + ".audit"),
                                            args.max_cost, args.max_calls)):
                run_demo(args)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"radarena: {exc}\n")


def export_review(args):
    from .benchmark import digest, read_benchmark
    if args.studies < 1:
        raise ValueError("Review study count must be positive")
    if args.output.exists():
        raise ValueError("Review output already exists; use a new directory")
    cases, metadata = read_benchmark(args.benchmark)
    candidates = [c for c in cases if c["split"] == args.split]
    attacks = [c for c in candidates if c["private_label"]["has_error"]]
    # Round-robin categories with deterministic ordering; include both variants.
    from collections import defaultdict
    groups = defaultdict(list)
    for case in attacks:
        groups[case["private_label"]["error_type"]].append(case)
    selected = []
    for group in groups.values():
        group.sort(key=lambda c: digest(["review-v1", c["case_id"]]))
    while len(selected) < args.studies and any(groups.values()):
        for kind in sorted(groups):
            if groups[kind] and len(selected) < args.studies:
                selected.append(groups[kind].pop()["study_id"])
    if len(selected) < args.studies:
        raise ValueError("Not enough studies for the requested review subset")
    subset = [c for c in candidates if c["study_id"] in selected]
    args.output.mkdir(parents=True)
    reader_cases = [{"case_id": c["case_id"], "image_paths": c["image_paths"],
                     "candidate": c["candidate"], "reviewer_id": None,
                     "image_report_verdict": None, "error_sentence_ids": None,
                     "error_types": None, "rationale": None, "review_status": "pending"}
                    for c in subset]
    key = [{"case_id": c["case_id"], "study_id": c["study_id"], "source": c["source"],
            "private_label": c["private_label"]} for c in subset]
    for name, rows in [("blinded_cases.jsonl", reader_cases), ("organizer_key.jsonl", key)]:
        (args.output / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
    write_json(args.output / "metadata.json", {"benchmark_sha256": metadata["benchmark_sha256"],
               "studies": len(selected), "cases": len(subset), "review_status": "pending",
               "instruction": "Reviewer sees only blinded_cases initially. Keep organizer_key separate."})
    print(json.dumps({"studies": len(selected), "cases": len(subset), "output": str(args.output)}, indent=2))


def extract_graphs(args):
    from .benchmark import read_benchmark
    from .report_graph import RadGraphExtractor
    if args.output.exists():
        raise ValueError("Graph output already exists; use a new path")
    cases, meta = read_benchmark(args.benchmark)
    cases = [c for c in cases if c["split"] == args.split and c["study_id"] in args.study_ids]
    if set(args.study_ids) != {c["study_id"] for c in cases}:
        raise ValueError("Choose study IDs within the requested split")
    extractor = RadGraphExtractor(args.model_type)
    graphs = {}
    for case in cases:
        graph = extractor.extract(case["candidate"])  # Never pass source/private labels.
        graphs[graph["report_sha256"]] = graph
        print(f"Extracted candidate {case['case_id']}", flush=True)
    write_json(args.output, {"format_version": 2, "extractor": extractor.metadata,
                            "benchmark_sha256": meta["benchmark_sha256"], "split": args.split,
                            "graphs": graphs})
    print(json.dumps({"candidate_reports": len(cases), "unique_graphs": len(graphs), "output": str(args.output)}))


def run_demo(args):
    import time
    import dspy
    from .agents import BlueVerifier, MakeAttack, apply_edits, score_edits
    from .runtime import make_models, model_config
    from .knowledge import load_pack, reference_context

    knowledge = load_pack(getattr(args, "knowledge_file", None),
                          condition=getattr(args, "handbook_condition", "full"))

    from .memory import load_memory
    red_rules, red_memory = load_memory(getattr(args, "red_memory", None), "red")
    blue_rules, blue_memory = load_memory(getattr(args, "blue_memory", None), "blue")
    studies = [Study.model_validate_json(line) for line in args.manifest.read_text().splitlines() if line.strip()]
    selected = [s for s in studies if s.study_id == args.study_id] if args.study_id else [s for s in studies if s.split == "train" and s.image_paths]
    if not selected:
        raise ValueError("No matching paired study. Run prepare with --images first.")
    study = selected[0]
    if not study.image_paths or any(not Path(p).is_file() for p in study.image_paths):
        raise ValueError("Study needs matched local image files. Run prepare with --images.")
    from .clinical_context import Indications
    indications = Indications(args.indications_csv) if getattr(args, "indications_csv", None) else None
    clinical_context = indications.get(study.study_id) if indications else ""
    images = [dspy.Image.from_path(p) for p in study.image_paths]
    extractor = None
    source_claims, candidate_claims = [], []
    if getattr(args, "radgraph", False):
        from .report_graph import RadGraphExtractor
        extractor = RadGraphExtractor()
        source_graph = extractor.extract(study.sentences)
        source_claims = [{"sentence_id": r["sentence_id"], "claims": r["claims"]} for r in source_graph["sentences"]]
    text_lm, vision_lm = make_models()
    start = time.monotonic()
    edits, rationale = [], "unchanged control"
    handbook_access = {}
    candidate = study.sentences
    if not args.control:
        from .tracing import ACTIVE_AUDIT
        if ACTIVE_AUDIT.get():
            ACTIVE_AUDIT.get().set_context(study_id=study.study_id, role="red", phase="attack")
        attack = dspy.Predict(MakeAttack)
        # Red sees images, so use the vision-capable model for this call too.
        attack.set_lm(vision_lm)
        red_reference = reference_context(knowledge, "red", study.sentences, text_lm)
        if hasattr(knowledge, "last_access"):
            handbook_access["red"] = list(knowledge.last_access)
        result = attack(images=images, clinical_context=clinical_context, source_sentences=study.sentences,
                        error_type=args.error_type, strategies=red_rules,
                        reference_notes=red_reference, report_claims=source_claims)
        from .agents import Edit
        edits = [Edit.model_validate(e) for e in result.edits]
        if getattr(args,"strict_attacks",False):
            from .attack_validation import validate_attack_family
            candidate = validate_attack_family(study.sentences,edits,args.error_type)
        else:
            candidate = apply_edits(study.sentences, edits)
        rationale = result.private_rationale
    # Only candidate text and images cross this boundary; original/edit metadata do not.
    if getattr(args,"structured_blue",False):
        from .structured_blue import StructuredBlueVerifier
        blue = StructuredBlueVerifier(text_lm=text_lm,vision_lm=vision_lm)
    else:
        blue = BlueVerifier(text_lm=text_lm, vision_lm=vision_lm)
    from .tracing import ACTIVE_AUDIT
    if ACTIVE_AUDIT.get():
        ACTIVE_AUDIT.get().set_context(study_id=study.study_id, role="verifier", phase="verification")
    blue_reference = reference_context(knowledge, "verifier", candidate, text_lm)
    if extractor:
        candidate_graph = extractor.extract(candidate)
        candidate_claims = [{"sentence_id": r["sentence_id"], "claims": r["claims"]} for r in candidate_graph["sentences"]]
    result = blue(candidate=candidate, clinical_context=clinical_context, images=images, strategies=blue_rules, reference_notes=blue_reference,
                  report_claims=candidate_claims)
    if hasattr(knowledge, "last_access"):
        handbook_access["verifier"] = list(knowledge.last_access)
    score = score_edits([e.sentence_id for e in edits], result.verdict)
    history = [row for lm in (text_lm, vision_lm) for row in lm.history]
    record = {
        "study_id": study.study_id, "split": study.split, "models": model_config(),
        "clinical_context": clinical_context,
        "clinical_context_config": indications.metadata() if indications else {"condition": "none"},
        "source": [s.model_dump() for s in study.sentences],
        "candidate": [s.model_dump() for s in candidate],
        "private_attack": {"edits": [e.model_dump() for e in edits], "rationale": rationale,
                           "requested_error_type": None if args.control else args.error_type,
                           "clinical_validity": "not_adjudicated"},
        "blue": result.verdict.model_dump(), "observations": result.observations,
        "claim_assessments": getattr(result,"assessments",[]),
        "structured_blue": getattr(args,"structured_blue",False),
        "strict_attacks": getattr(args,"strict_attacks",False),
        "score": score, "elapsed_seconds": round(time.monotonic() - start, 2),
        "model_calls": [{"model": h.get("model"), "usage": h.get("usage"),
                         "reported_cost": h.get("cost"), "cache_hit": h.get("cache_hit")}
                        for h in history],
        "strategy_memories": {"red": red_memory, "blue": blue_memory},
        "memory_learning": "frozen explicit checkpoints; no online updates during demo",
        "knowledge": knowledge.metadata() if knowledge else None,
        "handbook_access": handbook_access,
        "report_claims": {"source_private": source_claims, "candidate": candidate_claims,
                          "extractor": extractor.metadata if extractor else None},
    }
    write_json(args.output, record)
    print(json.dumps({"study_id": study.study_id, "blue": record["blue"],
                      "score": score, "trace": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
