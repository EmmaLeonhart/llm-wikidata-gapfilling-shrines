"""Test that figure generation writes non-empty PNGs from a scores dict."""
import os

from o1 import figures


SCORES = {
    "predict_only": {"by_property": {
        "P17": {"precision": 0.94, "recall": 0.94, "n": 18},
        "P31": {"precision": 0.83, "recall": 0.83, "n": 18},
        "P131": {"precision": 0.00, "recall": 0.00, "n": 18},
        "P625": {"precision": None, "recall": 0.00, "n": 18},
    }},
    "verify": {"by_property": {
        "P17": {"precision": 0.94}, "P31": {"precision": 0.78},
        "P131": {"precision": 0.00}, "P625": {"precision": None},
    }},
    "predict_only_lenient_entity": {
        "P131": {"precision": 0.62}, "P17": {"precision": 0.94},
        "P31": {"precision": 1.00},
    },
}


def test_make_figures_writes_three_pngs(tmp_path):
    out = figures.make_figures(SCORES, str(tmp_path))
    assert len(out) == 3  # precision, verify-lift, lenient
    for path in out:
        assert path.endswith(".png")
        assert os.path.getsize(path) > 1000  # a real image, not an empty file


def test_make_figures_handles_missing_optional_sections(tmp_path):
    minimal = {"predict_only": {"by_property": {
        "P17": {"precision": 1.0, "recall": 1.0, "n": 3},
    }}}
    out = figures.make_figures(minimal, str(tmp_path))
    assert len(out) == 1  # only the predict-only chart, no verify/lenient
