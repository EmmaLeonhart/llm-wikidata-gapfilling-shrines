#!/usr/bin/env python
"""o1 entry point — reproduces dataset -> predictions -> scoring -> figures.

This is the stub that CI and humans invoke. Stages are filled in as the
queue items (R2-R6) land; for now it documents the intended pipeline and
exits cleanly so the harness is runnable from day one.

Usage (intended, as stages come online):
    python scripts/run.py sample      # R2: pull shrine entities from Wikidata
    python scripts/run.py build       # R3: build the held-out eval set
    python scripts/run.py predict     # R4/R6: run predict-only over a sample
    python scripts/run.py score       # R5: compute precision/recall metrics
    python scripts/run.py all         # the full chain
"""
from __future__ import annotations

import sys

STAGES = ("sample", "build", "predict", "score", "all")


def main(argv: list[str]) -> int:
    stage = argv[1] if len(argv) > 1 else "all"
    if stage not in STAGES:
        print(f"unknown stage {stage!r}; choose one of {', '.join(STAGES)}")
        return 2
    # Stages are wired up by queue items R2-R6. Until then this is a no-op
    # that proves the entry point imports and runs.
    print(f"[o1] stage {stage!r}: not yet implemented (see queue.md R2-R6)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
