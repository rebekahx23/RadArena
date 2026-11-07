# RadGraph extraction audit

Actual local RadGraph-XL output on six development candidates. Researcher-only comparison; no original/candidate difference is supplied to Blue. No model API calls.

## Study 1094, s4

### unchanged

FINDINGS: Left lower lobe XXXX density XXXX representing atelectasis.

```json
[
  {
    "entity_id": "4",
    "observation": "density",
    "qualified_observation": "density",
    "status": "present",
    "anatomy": [
      "Left lower lobe"
    ],
    "modifiers": [],
    "relations": [
      {
        "type": "located_at",
        "target_entity_id": "3",
        "target_text": "Left lower lobe"
      },
      {
        "type": "suggestive_of",
        "target_entity_id": "5",
        "target_text": "atelectasis"
      }
    ]
  },
  {
    "entity_id": "5",
    "observation": "atelectasis",
    "qualified_observation": "atelectasis",
    "status": "present",
    "anatomy": [],
    "modifiers": [],
    "relations": []
  }
]
```

### edited

FINDINGS: Right lower lobe XXXX density XXXX representing atelectasis.

```json
[
  {
    "entity_id": "4",
    "observation": "density",
    "qualified_observation": "density",
    "status": "present",
    "anatomy": [
      "Right lower lobe"
    ],
    "modifiers": [],
    "relations": [
      {
        "type": "located_at",
        "target_entity_id": "3",
        "target_text": "Right lower lobe"
      },
      {
        "type": "suggestive_of",
        "target_entity_id": "5",
        "target_text": "atelectasis"
      }
    ]
  },
  {
    "entity_id": "5",
    "observation": "atelectasis",
    "qualified_observation": "atelectasis",
    "status": "present",
    "anatomy": [],
    "modifiers": [],
    "relations": []
  }
]
```

## Study 2036, s1

### unchanged

FINDINGS: There is mild cardiomegaly.

```json
[
  {
    "entity_id": "1",
    "observation": "mild",
    "qualified_observation": "mild",
    "status": "present",
    "anatomy": [],
    "modifiers": [],
    "relations": [
      {
        "type": "modify",
        "target_entity_id": "2",
        "target_text": "mild cardiomegaly"
      }
    ]
  },
  {
    "entity_id": "2",
    "observation": "cardiomegaly",
    "qualified_observation": "mild cardiomegaly",
    "status": "present",
    "anatomy": [],
    "modifiers": [
      "mild"
    ],
    "relations": []
  }
]
```

### edited

FINDINGS: There is severe cardiomegaly.

```json
[
  {
    "entity_id": "1",
    "observation": "severe",
    "qualified_observation": "severe",
    "status": "present",
    "anatomy": [],
    "modifiers": [],
    "relations": [
      {
        "type": "modify",
        "target_entity_id": "2",
        "target_text": "severe cardiomegaly"
      }
    ]
  },
  {
    "entity_id": "2",
    "observation": "cardiomegaly",
    "qualified_observation": "severe cardiomegaly",
    "status": "present",
    "anatomy": [],
    "modifiers": [
      "severe"
    ],
    "relations": []
  }
]
```

## Study 1106, s7

### unchanged

IMPRESSION: No pneumothorax.

```json
[
  {
    "entity_id": "1",
    "observation": "pneumothorax",
    "qualified_observation": "pneumothorax",
    "status": "absent",
    "anatomy": [],
    "modifiers": [],
    "relations": []
  }
]
```

### edited

IMPRESSION: pneumothorax.

```json
[
  {
    "entity_id": "1",
    "observation": "pneumothorax",
    "qualified_observation": "pneumothorax",
    "status": "absent",
    "anatomy": [],
    "modifiers": [],
    "relations": []
  }
]
```

The side and severity edits are represented. The fragment pneumothorax. is incorrectly labeled absent by the extractor, so graph equality does not mean the reports are equivalent. Original sentences remain essential.

[Setup and integration](../docs/RADGRAPH.md)
