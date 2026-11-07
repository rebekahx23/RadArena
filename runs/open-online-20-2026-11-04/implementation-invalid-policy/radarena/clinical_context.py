"""Explicit, indication-only IU context; never expose diagnostic indexing columns."""

import csv
import hashlib
import io
from pathlib import Path


class Indications:
    def __init__(self, path):
        raw = Path(path).read_bytes()
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if not {"uid", "indication"} <= set(reader.fieldnames or []):
            raise ValueError("Indication CSV requires uid and indication columns")
        self.values = {}
        for row in reader:
            uid = row["uid"].strip()
            if not uid or uid in self.values:
                raise ValueError("Indication CSV contains empty or duplicate study IDs")
            self.values[uid] = (row["indication"] or "").strip()
        self.sha256 = hashlib.sha256(raw).hexdigest()

    def get(self, study_id):
        if str(study_id) not in self.values:
            raise ValueError(f"Study {study_id} missing from indication CSV")
        return self.values[str(study_id)]

    def metadata(self):
        return {"condition": "indication", "source_csv_sha256": self.sha256,
                "fields": ["indication"], "reports": len(self.values),
                "reports_with_indication": sum(bool(v) for v in self.values.values()),
                "missing_policy": "empty indication retained; unknown study ID fails before calls"}
