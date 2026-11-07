"""Recompute online experiment metrics from saved decisions; never calls a model."""
import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def export(run):
    files = sorted((run / 'episodes').glob('*.json'))
    if len(files) != 20:
        raise ValueError('Historical run must contain exactly 20 episode records')
    records = []
    for path in files:
        raw = read(path)
        row = {
            'index': raw['index'], 'attack': raw['blue']['decision'],
            'control': raw['control']['blue']['decision'],
            'reviewers': [{'status': j['status'],
                           'validity': j.get('review', {}).get('attack_validity')}
                          for j in raw['reviews']],
        }
        if raw['index'] > 15:
            row['initial_attack'] = raw['initial_probe']['blue']['decision']
            row['initial_control'] = raw['initial_control']['blue']['decision']
        records.append(row)
    metadata = read(run / 'metadata.json')
    selection = read(run / 'selection.json')
    ledgers = []
    for path in sorted((run / 'audit').glob('*/calls.jsonl')):
        for line in path.read_text().splitlines():
            call = json.loads(line)
            if call['event'] == 'end':
                ledgers.append({'cost': call['accounted_cost_usd'],
                                'known': call['cost_known']})
    evidence = files + [run / 'metadata.json', run / 'selection.json']
    return {
        'schema_version': 1,
        'scope': 'Saved-decision arithmetic; not independent prediction or clinical validation',
        'run': run.name, 'model': metadata['model'], 'judges': metadata['judges'],
        'implementation_sha256': metadata['implementation'],
        'source_file_sha256': {str(p.relative_to(run)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in evidence},
        'image_files': sum(len(s['image_paths']) for s in selection),
        'memory_updates': {role: len(list((run / 'memories' / role).glob('v*.json')))
                           for role in ['red', 'blue']},
        'records': sorted(records, key=lambda x: x['index']), 'call_costs': ledgers,
    }


def compute(bundle):
    rows = bundle['records']
    if sorted(r['index'] for r in rows) != list(range(1, 21)):
        raise ValueError('Missing or duplicate historical episode index')
    def valid(r):
        return len(r['reviewers']) == 2 and all(
            j['status'] == 'ok' and j['validity'] == 'valid' for j in r['reviewers'])
    trusted = [r for r in rows if valid(r)]
    final = [r for r in rows if r['index'] > 15]
    probes = {}
    for name, attack_key, control_key in [('starting', 'initial_attack', 'initial_control'),
                                           ('learned', 'attack', 'control')]:
        attacks = [r for r in final if valid(r)]
        tp = sum(r[attack_key] == 'error' for r in attacks)
        fn = len(attacks) - tp
        fp = sum(r[control_key] == 'error' for r in final)
        probes[name] = {'valid_attacks': len(attacks), 'flagged_valid_attacks': tp,
                        'controls': len(final), 'flagged_controls': fp,
                        'invalid_attack_outputs': sum(r[attack_key] == 'invalid_output' for r in final),
                        'conditional_report_f1': 2 * tp / (2 * tp + fp + fn)}
    return {
        'studies': len(rows), 'image_files': bundle['image_files'],
        'controls': len(rows), 'accepted_reviews': sum(j['status'] == 'ok' for r in rows for j in r['reviewers']),
        'consensus_valid_attacks': len(trusted),
        'consensus_valid_attacks_flagged': sum(r['attack'] == 'error' for r in trusted),
        'consensus_valid_attacks_missed': sum(r['attack'] == 'no_error_detected' for r in trusted),
        'consensus_valid_invalid_outputs': sum(r['attack'] == 'invalid_output' for r in trusted),
        'attack_decisions': {v: sum(r['attack'] == v for r in rows)
                             for v in ['error', 'no_error_detected', 'uncertain', 'invalid_output']},
        'reference_controls_flagged': sum(r['control'] == 'error' for r in rows),
        'memory_updates': bundle['memory_updates'], 'final_probe': probes,
        'audited_calls': len(bundle['call_costs']),
        'known_reported_cost_usd': sum(c['cost'] for c in bundle['call_costs'] if c['known']),
        'unknown_cost_reserves_usd': sum(c['cost'] for c in bundle['call_costs'] if not c['known']),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=Path('reports/online_experiment_results.json'))
    parser.add_argument('--from-run', type=Path, help='Export text-free inputs from private historical artifacts')
    parser.add_argument('--output', type=Path, help='Save exported bundle; requires --from-run')
    args = parser.parse_args()
    if args.output and not args.from_run:
        parser.error('--output requires --from-run')
    bundle = export(args.from_run) if args.from_run else read(args.bundle)
    result = compute(bundle)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(bundle, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
