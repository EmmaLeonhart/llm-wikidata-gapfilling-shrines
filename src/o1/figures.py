"""Render the report figures from a scored-results dict.

Kept in the package (not the run script) so it is unit-testable: a test passes a
synthetic ``scores`` dict and a tmp dir and checks PNGs are written. matplotlib
uses the headless Agg backend so it runs without a display / in CI.

``scores`` is the structure written by ``scripts/run.py score`` (see
``score.score``): ``{"predict_only": {...}, "verify": {...}?,
"predict_only_lenient_entity": {...}?}``.
"""
from __future__ import annotations

import os
from typing import Any, Optional

# Display order + short labels for the x axes.
ORDER = ["P17", "P31", "P140", "P571", "P131", "P1435", "P625"]
SHORT = {
    "P17": "country", "P31": "instance-of", "P140": "religion",
    "P571": "inception", "P131": "admin loc", "P1435": "heritage",
    "P625": "coords",
}
# Theme colours (match the report's warm palette).
C_PRED = "#b8553a"
C_SECOND = "#3f6487"
C_GREEN = "#5b7a4a"


def _nan(x: Optional[float]) -> float:
    return float("nan") if x is None else float(x)


def make_figures(scores: dict[str, Any], out_dir: str) -> list[str]:
    """Write the report figures; return the list of file paths created."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(out_dir, exist_ok=True)
    po = scores["predict_only"]["by_property"]
    props = [p for p in ORDER if p in po]
    xs = list(range(len(props)))
    names = [SHORT.get(p, p) for p in props]
    written: list[str] = []

    # --- Fig 1: predict-only precision & recall by property ---
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    w = 0.38
    ax.bar([x - w / 2 for x in xs], [_nan(po[p]["precision"]) for p in props],
           w, label="precision", color=C_PRED)
    ax.bar([x + w / 2 for x in xs], [_nan(po[p]["recall"]) for p in props],
           w, label="recall", color=C_SECOND)
    ax.set_xticks(xs)
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("score")
    ax.set_title("Predict-only: precision & recall by property (local Gemma)")
    ax.legend()
    fig.tight_layout()
    p1 = os.path.join(out_dir, "fig_precision.png")
    fig.savefig(p1, dpi=120)
    plt.close(fig)
    written.append(p1)

    # --- Fig 2: verify lift (predict-only vs predict+verify precision) ---
    verify = scores.get("verify", {}).get("by_property")
    if verify:
        fig, ax = plt.subplots(figsize=(7.5, 3.6))
        ax.bar([x - w / 2 for x in xs],
               [_nan(po[p]["precision"]) for p in props], w,
               label="predict-only", color=C_PRED)
        ax.bar([x + w / 2 for x in xs],
               [_nan(verify.get(p, {}).get("precision")) for p in props], w,
               label="predict+verify", color=C_GREEN)
        ax.set_xticks(xs)
        ax.set_xticklabels(names, rotation=30, ha="right")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("precision")
        ax.set_title("Self-verification lift (precision) — lower bars = verify hurt")
        ax.legend()
        fig.tight_layout()
        p2 = os.path.join(out_dir, "fig_verify_lift.png")
        fig.savefig(p2, dpi=120)
        plt.close(fig)
        written.append(p2)

    # --- Fig 3: strict vs hierarchy-lenient (entity properties) ---
    lenient = scores.get("predict_only_lenient_entity")
    if lenient:
        ent = [p for p in ORDER if p in lenient and lenient[p]]
        exs = list(range(len(ent)))
        fig, ax = plt.subplots(figsize=(7.0, 3.6))
        ax.bar([x - w / 2 for x in exs],
               [_nan(po[p]["precision"]) for p in ent], w,
               label="strict (exact QID)", color=C_SECOND)
        ax.bar([x + w / 2 for x in exs],
               [_nan(lenient[p]["precision"]) for p in ent], w,
               label="hierarchy-lenient", color=C_GREEN)
        ax.set_xticks(exs)
        ax.set_xticklabels([SHORT.get(p, p) for p in ent], rotation=30, ha="right")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("precision")
        ax.set_title("Entity properties: strict vs granularity-aware precision")
        ax.legend()
        fig.tight_layout()
        p3 = os.path.join(out_dir, "fig_lenient.png")
        fig.savefig(p3, dpi=120)
        plt.close(fig)
        written.append(p3)

    return written
