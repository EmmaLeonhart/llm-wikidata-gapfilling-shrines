"""Smoke tests — prove the package imports and the entry point runs.

Real logic gets its own test files as R2-R6 land (test_wikidata.py,
test_dataset.py, test_predict.py, test_score.py).
"""
import subprocess
import sys
from pathlib import Path

import o1

ROOT = Path(__file__).resolve().parents[1]


def test_package_version():
    assert o1.__version__


def test_run_entry_point_usage_no_stage():
    # Bare invocation prints usage and exits 0 without running any stage
    # (so it stays offline-safe in CI — no network, no Ollama).
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "usage" in result.stdout.lower()


def test_run_entry_point_rejects_unknown_stage():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run.py"), "bogus"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
