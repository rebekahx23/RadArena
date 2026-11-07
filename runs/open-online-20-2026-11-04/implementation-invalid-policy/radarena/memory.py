"""Load a single explicit role checkpoint; never scan another agent's notes."""
import hashlib
import json
from pathlib import Path


def load_memory(path, role):
    if role not in {'red', 'blue'}:
        raise ValueError('Memory role must be red or blue')
    if path is None:
        return [], {'condition': 'none', 'role': role}
    raw = Path(path).read_bytes()
    record = json.loads(raw)
    if record.get('role') != role:
        raise ValueError(f'Expected {role} memory; refusing another role checkpoint')
    rules = record.get('rules')
    if not isinstance(rules, list) or len(rules) > 5 or any(
            not isinstance(r, str) or not r.strip() or len(r) > 400 for r in rules):
        raise ValueError('Memory requires at most five nonempty rules of at most 400 characters')
    memory_hash = hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()
    if memory_hash != record.get('memory_sha256'):
        raise ValueError('Memory checkpoint content hash mismatch')
    # Only rules cross the agent boundary; explanation, training IDs and path do not.
    return rules, {'condition': 'learned', 'role': role, 'round': record.get('round'),
                   'checkpoint_sha256': hashlib.sha256(raw).hexdigest(), 'memory_sha256': memory_hash}
