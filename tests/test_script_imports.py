"""Research entry points must be safe to inspect without launching experiments."""

import os
import runpy
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.mark.parametrize("name", [
    "analyze_open_online.py",
    "analyze_ten_study_batch.py",
    "build_learning_walkthrough.py",
    "compare_stronger_blue.py",
    "recover_batch_reviews.py",
    "run_indication_pilot.py",
    "run_open_online.py",
    "run_ten_study_batch.py",
    "summarize_indication_pilot.py",
])
def test_research_script_import_has_no_execution_side_effects(name, tmp_path, monkeypatch):
    from radarena import batch, open_online, runtime

    def unexpected_inference(*args, **kwargs):
        pytest.fail("Importing a research script attempted to run an experiment")

    monkeypatch.setattr(batch, "run_batch", unexpected_inference)
    monkeypatch.setattr(open_online, "run", unexpected_inference)
    monkeypatch.setattr(runtime, "make_models", unexpected_inference)
    monkeypatch.setattr(runtime, "make_judge_model", unexpected_inference)
    monkeypatch.chdir(tmp_path)
    before = dict(os.environ)

    namespace = runpy.run_path(str(SCRIPTS / name), run_name="research_script_import")

    assert callable(namespace["main"])
    assert dict(os.environ) == before
    assert list(tmp_path.iterdir()) == []
