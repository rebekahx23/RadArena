"""Summarize paired clinical-context pilot, including incomplete and failed attempts."""
import json
from pathlib import Path
from radarena.evaluate import summarize_run, read_records


def main():
    base = Path('runs/indication-ablation-2026-11-04')
    result = {'conditions': {}, 'scope': 'Three dev studies, paired seed attacks and controls; not clinical validation.'}
    lines = ['# Indication pilot', '', '| Context | Method | Completed | Localization F1 | Control FPR |',
             '| --- | --- | --- | --- | --- |']
    for condition in ['none', 'indication']:
        path = base / condition
        if not (path / 'metadata.json').exists():
            result['conditions'][condition] = {'status': 'not_started'}
            continue
        summary = summarize_run(path)
        budget = json.loads((path / 'audit/budget.json').read_text())
        result['conditions'][condition] = dict(summary=summary, audit=budget)
        for variant, m in summary['variants'].items():
            def number(x):
                return 'N/A' if x is None else f'{x:.3f}'
            lines.append(f"| {condition} | {variant} | {m['completed']}/{m['expected']} | {number(m['localization_f1_completed'])} | {number(m['false_positive_rate_completed_controls'])} |")
    result['accounted_cost_usd'] = sum(c.get('audit', {}).get('accounted_cost_usd', 0) for c in result['conditions'].values())
    complete = all(c.get('summary', {}).get('complete', False) for c in result['conditions'].values())
    result['paired_comparison_complete'] = complete
    lines += ['', f'Both conditions complete: {complete}.',
              f"Audited accounting total: ${result['accounted_cost_usd']:.6f}; includes conservative reserves for failed requests with unknown billing.",
              'Metrics use completed verdicts; see summary.json for missing and failed cases.',
              'Source reports and synthetic edits have not been clinically adjudicated. The sample is too small for an improvement claim.',
              'All calls and failed attempts remain in each audit directory. No hidden model reasoning is exposed.']
    (base / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    (base / 'comparison.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == "__main__":
    main()
