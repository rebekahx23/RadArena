"""Render a human-readable transcript of the actual saved learning checkpoints."""
import json
from pathlib import Path


def main():
    base = Path('runs/learning-pilot-2026-11-04')
    lines = ['# Real-data learning walkthrough', '',
             'These are saved model outputs from actual IU images/reports, not fabricated examples.',
             'Source reports and attacks have not been independently clinically adjudicated.',
             'The researcher can read all sections; each agent received only its role-specific inputs.', '']
    for number in range(1, 4):
        root = base / 'train' / f'round-{number}'
        attack_path = root / 'red_attack.json'
        if not attack_path.exists():
            continue
        attack = json.loads(attack_path.read_text())
        lines += [f'## Round {number}: study {attack["study_id"]}', '',
                  f'Requested error family: {attack["error_type"]}. Status: {attack["attack_status"]}.', '',
                  '### Red generated edit', '', '```json', json.dumps(attack['edits'], indent=2), '```', '',
                  'Red explanation: ' + attack['red_rationale'], '']
        for stem, label in [('blue_attack', 'Blue on the attack'), ('blue_control', 'Blue on the unchanged control')]:
            path = root / (stem + '.json')
            if not path.exists():continue
            row = json.loads(path.read_text())
            lines += ['### ' + label, '', f'Indication: {row["clinical_context"]}', '',
                      '```json', json.dumps({'verdict': row['blue'], 'score': row['score'], 'observations': row['observations']}, indent=2), '```', '']
        for role in ['red', 'blue']:
            path = base / 'memories' / role / f'v{number}.json'
            if not path.exists():continue
            memory = json.loads(path.read_text())
            lines += [f'### {role.title()} memory after this round', '', *['- ' + r for r in memory['rules']], '',
                      memory['explanation'], '', f'Memory SHA-256: `{memory["memory_sha256"]}`.', '']
    summary_path = base / 'summary.json'
    if summary_path.exists():
        lines += ['## Frozen development evaluation', '', (base / 'results.md').read_text()]
    else:
        lines += ['Run incomplete; no completed before/after summary is available.']
    (base / 'walkthrough.md').write_text('\n'.join(lines) + '\n')
    print(base / 'walkthrough.md')


if __name__ == "__main__":
    main()
