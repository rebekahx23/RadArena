"""Ten-study paired Red/Blue batch with independent post-hoc image judges."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import dspy

from .agents import BlueVerifier, Edit, MakeAttack, apply_edits, score_edits
from .benchmark import read_benchmark
from .clinical_context import Indications
from .data import Sentence
from .judge import run_judge
from .knowledge import load_pack
from .memory import load_memory
from .runtime import make_models, model_config
from .tracing import AuditSession, audit_context

BASE = Path('runs/red-blue-judge-10-2026-11-04')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def total_cost(root):
    return sum(json.loads(p.read_text())['accounted_cost_usd'] for p in Path(root).rglob('budget.json'))


def stage_cap(root, audit_dir, ceiling, total_cap):
    own_path = audit_dir / 'budget.json'
    own = json.loads(own_path.read_text())['accounted_cost_usd'] if own_path.exists() else 0
    return min(ceiling, total_cap - total_cost(root) + own)


def select_cases(cases):
    """Ten unused development studies, balanced 4/3/3; no outcome filtering."""
    excluded = {'1094', '1106', '2036', '2088', '1411', '2070'}
    result = []
    for family, n in [('laterality', 4), ('presence_absence', 3), ('severity', 3)]:
        eligible = sorted((c for c in cases if c['split'] == 'dev' and c['private_label']['has_error']
                           and c['private_label']['error_type'] == family and c['study_id'] not in excluded),
                          key=lambda c: int(c['study_id']))
        if len(eligible) < n:
            raise ValueError('Insufficient unused development studies')
        result += eligible[:n]
    return result


def run_batch(output=BASE, max_cost=1.0):
    if not 0 < max_cost <= 1:
        raise ValueError('Batch total cap must be positive and at most $1')
    output = Path(output)
    cases, benchmark_meta = read_benchmark(Path('data/processed/midpoint-v2.jsonl'))
    selected = select_cases(cases)
    indications = Indications('data/archive (1)/indiana_reports.csv')
    memory_root = Path('runs/learning-pilot-2026-11-04/memories')
    red_rules, red_meta = load_memory(memory_root/'red/v3.json', 'red')
    blue_rules, blue_meta = load_memory(memory_root/'blue/v3.json', 'blue')
    pack = load_pack(Path('knowledge/reporting_v1.json'))
    # Verify all evidence before the first paid call.
    for case in selected:
        indications.get(case['study_id'])
        for path, expected in zip(case['image_paths'], case['image_sha256'], strict=True):
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
                raise ValueError('Frozen image content changed')
    from .runtime import load_environment
    load_environment()
    config = {'format_version': 1, 'benchmark_sha256': benchmark_meta['benchmark_sha256'],
              'models': model_config(), 'judge_model': 'google/gemini-2.5-flash',
              'max_cost_usd': max_cost, 'max_checks': 2, 'clinical_context': indications.metadata(),
              'strategy_memories': {'red': red_meta, 'blue': blue_meta}, 'knowledge': pack.metadata(),
              'selection': [{'study_id': c['study_id'], 'error_type': c['private_label']['error_type'],
                             'image_count': len(c['image_paths'])} for c in selected],
              'implementation_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in sorted(Path(__file__).parent.glob('*.py'))},
              'protocol': 'Frozen memories. Ten generated attacks plus ten unchanged controls. Image judge on attacks. No judge feedback to agents.'}
    meta_path = output/'metadata.json'
    if meta_path.exists() and json.loads(meta_path.read_text()) != config:
        raise ValueError('Batch configuration changed; use a new directory')
    write(meta_path, config)
    write(output/'organizer/selected_cases.json', selected)
    # Archive the exact implementation without credentials.
    for path in Path(__file__).parent.glob('*.py'):
        target = output/'implementation/radarena'/path.name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())

    def failure(study_id, phase, exc):
        with (output/'failures.jsonl').open('a') as f:
            f.write(json.dumps({'study_id': study_id, 'phase': phase, 'exception_type': type(exc).__name__})+'\n')
        print(f'FAILED {study_id} {phase}: {type(exc).__name__}', flush=True)

    for case in selected:
        uid = case['study_id']
        kind = case['private_label']['error_type']
        for control in (False, True):
            stem = f'study-{uid}.{"control" if control else "attack"}'
            path = output/(stem+'.json')
            audit_dir = output/(stem+'.audit')
            if not path.exists():
                # At most one explicit retry of a transient provider failure; checkpoint Red separately.
                for attempt in range(2):
                    try:
                        cap = stage_cap(output, audit_dir, .10, max_cost)
                        with audit_context(AuditSession(audit_dir, cap, 20)) as _:
                            from .tracing import ACTIVE_AUDIT
                            audit = ACTIVE_AUDIT.get()
                            text_lm, vision_lm = make_models()
                            images = [dspy.Image.from_path(p) for p in case['image_paths']]
                            source = [Sentence.model_validate(s) for s in case['source']]
                            clinical = indications.get(uid)
                            edits, rationale, candidate = [], 'Unchanged source report control', source
                            if not control:
                                red_path = output/'private'/(stem+'.red.json')
                                if red_path.exists():
                                    attack = json.loads(red_path.read_text())
                                else:
                                    audit.set_context(study_id=uid, role='red', phase='attack')
                                    predictor = dspy.Predict(MakeAttack);predictor.set_lm(vision_lm)
                                    red = predictor(images=images, source_sentences=source, clinical_context=clinical,
                                                    report_claims=[], error_type=kind, strategies=red_rules,
                                                    reference_notes=pack.render('red'))
                                    attack = {'edits': [Edit.model_validate(e).model_dump() for e in red.edits],
                                              'rationale': red.private_rationale}
                                    write(red_path, attack)
                                edits = [Edit.model_validate(e) for e in attack['edits']]
                                candidate = apply_edits(source, edits)
                                rationale = attack['rationale']
                            audit.set_context(study_id=uid, role='verifier', phase='control' if control else 'verification')
                            result = BlueVerifier(text_lm=text_lm, vision_lm=vision_lm, max_checks=2)(
                                candidate=candidate, images=images, clinical_context=clinical,
                                strategies=blue_rules, reference_notes=pack.render('verifier'), report_claims=[])
                            record = {'study_id': uid, 'split': 'dev', 'models': model_config(),
                                      'source': case['source'], 'candidate': [s.model_dump() for s in candidate],
                                      'image_paths': case['image_paths'], 'clinical_context': clinical,
                                      'clinical_context_config': indications.metadata(),
                                      'private_attack': {'edits': [e.model_dump() for e in edits], 'rationale': rationale,
                                          'requested_error_type': None if control else kind, 'clinical_validity': 'not_adjudicated'},
                                      'blue': result.verdict.model_dump(), 'observations': result.observations,
                                      'score': score_edits([e.sentence_id for e in edits], result.verdict),
                                      'strategy_memories': {'red': red_meta, 'blue': blue_meta},
                                      'knowledge': pack.metadata(), 'memory_learning': 'frozen; no updates during batch'}
                            write(path, record)
                        print(f'COMPLETE {uid} {"control" if control else "attack"}', flush=True)
                        break
                    except Exception as exc:
                        failure(uid, stem, exc)
                        if attempt or type(exc).__name__ not in {'LMTimeoutError', 'LMRateLimitError', 'Timeout', 'ReadTimeout'}:
                            break
            if not control and path.exists():
                judge_path = path.with_suffix('.judge.json')
                if not judge_path.exists():
                    try:
                        judge_audit = judge_path.with_suffix('.audit')
                        cap = stage_cap(output, judge_audit, .50, max_cost)
                        run_judge(path, max_cost=cap)
                        print(f'COMPLETE {uid} judge', flush=True)
                    except Exception as exc:
                        failure(uid, 'judge', exc)
            summarize_batch(output)
    return summarize_batch(output)


def summarize_batch(output):
    output = Path(output)
    meta = json.loads((output/'metadata.json').read_text())
    rows = []
    counts = Counter()
    tp = fp = fn = 0
    for item in meta['selection']:
        uid = item['study_id']
        ap, cp = output/f'study-{uid}.attack.json', output/f'study-{uid}.control.json'
        jp = ap.with_suffix('.judge.json')
        attack = json.loads(ap.read_text()) if ap.exists() else None
        control = json.loads(cp.read_text()) if cp.exists() else None
        judge = json.loads(jp.read_text()) if jp.exists() else None
        row = {'study_id': uid, 'requested_error_type': item['error_type'],
               'attack_status': 'complete' if attack else 'failed_or_pending',
               'control_status': 'complete' if control else 'failed_or_pending',
               'judge_status': judge.get('status') if judge else 'missing'}
        if attack:
            score = attack['score'];counts['attacks_completed'] += 1
            counts['syntactic_edits_localized'] += bool(score['injected_edit_detected'])
            counts['attack_abstentions'] += attack['blue']['decision'] == 'uncertain'
            counts['category_localized_hits'] += any(f['sentence_id'] in {e['sentence_id'] for e in attack['private_attack']['edits']}
                and f['error_type'] == item['error_type'] for f in attack['blue']['findings'])
            tp += score['localization_tp'];fp += score['localization_fp'];fn += score['localization_fn']
            row.update(blue_decision=attack['blue']['decision'], edit_localized=score['injected_edit_detected'],
                       changed_ids=[e['sentence_id'] for e in attack['private_attack']['edits']],
                       flagged_ids=[f['sentence_id'] for f in attack['blue']['findings']])
        if control:
            counts['controls_completed'] += 1
            counts['reference_control_false_alarms'] += control['blue']['decision'] == 'error'
            counts['control_abstentions'] += control['blue']['decision'] == 'uncertain'
            fp += control['score']['localization_fp']
            row['control_decision'] = control['blue']['decision']
        if judge and judge.get('status') == 'ok':
            analysis = judge['analysis'];counts['judges_completed'] += 1
            counts['judge_attack_'+analysis['attack_validity']] += 1
            counts['judge_blue_'+analysis['blue_assessment']] += 1
            counts['judge_red_'+judge['red_outcome']] += 1
            for mode in set(analysis['failure_modes']):counts['failure_mode_'+mode] += 1
            row.update(judge_attack_validity=analysis['attack_validity'], judge_blue_assessment=analysis['blue_assessment'],
                       judge_red_outcome=judge['red_outcome'], judge_explanation=analysis['explanation'],
                       judge_attack_explanation=analysis['attack_explanation'],
                       judge_confidence=analysis['confidence'], judge_limitations=analysis['limitations'])
        rows.append(row)
    result = {'complete': counts['attacks_completed']==10 and counts['controls_completed']==10 and counts['judges_completed']==10,
              'expected_studies': 10, 'image_files': sum(c['image_count'] for c in meta['selection']),
              'counts': dict(counts), 'localization_counts': {'tp':tp,'fp':fp,'fn':fn},
              'localization_f1_completed': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
              'accounted_cost_usd': total_cost(output), 'rows': rows,
              'limitations': ['Frozen-memory dev batch, not a learning-improvement comparison or untouched final test.',
                'Code metrics score injected edits; unchanged source reports are not adjudicated error-free.',
                'LLM judges are fallible, may be inconsistent, and do not establish clinical ground truth.',
                'Failed/missing stages remain in denominators and raw logs; no outcome-based case substitution.']}
    write(output/'summary.json', result)
    lines = ['# Ten-study Red → Blue → Judge batch', '',
             f"Completed attacks: {counts['attacks_completed']}/10; controls: {counts['controls_completed']}/10; judges: {counts['judges_completed']}/10.",
             f"Images: {result['image_files']}. Audit accounting: ${result['accounted_cost_usd']:.6f} (includes unknown-cost reserves).", '',
             '| Study | Requested edit | Edit located | Blue | Control | Judge: attack | Judge: Blue | Judge: Red outcome |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in rows:
        lines.append('| '+' | '.join(str(v) for v in [r['study_id'],r['requested_error_type'], r.get('edit_localized','missing'),
            r.get('blue_decision','missing'),r.get('control_decision','missing'),r.get('judge_attack_validity',r['judge_status']),
            r.get('judge_blue_assessment','missing'),r.get('judge_red_outcome','missing')])+' |')
    lines += ['', '## Aggregate counts', '', '```json', json.dumps(result['counts'], indent=2), '```',
              '', f"Localization F1 on completed outputs: {result['localization_f1_completed']}", '', *result['limitations']]
    for r in rows:
        if 'judge_explanation' in r:
            lines += ['', f"## Study {r['study_id']}: judge analysis", '', r['judge_attack_explanation'], '',
                      r['judge_explanation'], '', 'Limitations: '+r['judge_limitations']]
    (output/'results.md').write_text('\n'.join(lines)+'\n')
    return result
