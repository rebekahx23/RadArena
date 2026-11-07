"""Small paired context ablation. $0.05 audited cap per condition; no automatic retry."""
import os
from pathlib import Path

from radarena.evaluate import run_evaluation
from radarena.tracing import AuditSession, audit_context


def main():
    os.environ['RADARENA_TEXT_MODEL'] = 'google/gemma-3-27b-it'
    os.environ['RADARENA_VISION_MODEL'] = 'google/gemma-3-27b-it'
    base = Path('runs/indication-ablation-2026-11-04')
    for condition in ('none', 'indication'):
        output = base / condition
        with audit_context(AuditSession(output / 'audit', .05, 80)):
            run_evaluation(Path('data/processed/synthetic_benchmark_v2.jsonl'), output,
                           study_ids=['1094', '1106', '2036'],
                           knowledge_file=Path('knowledge/reporting_v1.json'),
                           indications_csv=Path('data/raw/iu_xray/indiana_reports.csv') if condition == 'indication' else None)


if __name__ == "__main__":
    main()
