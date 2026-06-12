"""Score predictions against held-out ground truth.

Joins each prediction (R4) to its eval instance (R3) by ``id``, classifies it as
**correct / wrong / abstain**, and aggregates **precision, recall, and abstention
rate** per target property and per popularity bucket.

Definitions (per group of instances):
- ``abstain`` — the model declined (or gave an unparseable typed answer).
- ``answered`` = correct + wrong (non-abstain predictions).
- **precision** = correct / answered  — of what it *did* fill, how much is right
  (the "is it safe to auto-suggest?" metric).
- **recall**    = correct / total     — of all gaps, how many got filled correctly.

Matching is type-aware: entities by QID, dates by year, coordinates within a
tolerance, strings by normalized equality. Choices that bound the numbers (e.g.
a resolver that returned no QID counts as wrong) are documented here and surface
in FINDINGS.md.
"""
from __future__ import annotations

import collections
import re
from typing import Any, Iterable, Optional

COORD_TOLERANCE_DEG = 0.05  # ~5.5 km at the equator; shrines vary in pinpointing

_TIME_YEAR_RE = re.compile(r"([+-]?\d{1,4})")


def extract_year(value: Any) -> Optional[int]:
    """Pull a (possibly negative) year from a stored time value or a year string."""
    if value is None:
        return None
    s = str(value)
    # Wikidata time looks like '+1879-00-00T00:00:00Z'; a bare year is '1879'.
    m = _TIME_YEAR_RE.match(s.strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _norm_string(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s).strip().casefold())


def match_time(predicted: dict[str, Any], true_values: Iterable[dict[str, Any]]) -> bool:
    py = extract_year(predicted.get("value"))
    if py is None:
        return False
    return any(extract_year(tv.get("value")) == py for tv in true_values)


def match_coordinate(
    predicted: dict[str, Any],
    true_values: Iterable[dict[str, Any]],
    tol: float = COORD_TOLERANCE_DEG,
) -> bool:
    pv = predicted.get("value")
    if not (isinstance(pv, (list, tuple)) and len(pv) == 2):
        return False
    plat, plon = pv
    for tv in true_values:
        t = tv.get("value")
        if isinstance(t, (list, tuple)) and len(t) == 2:
            if abs(plat - t[0]) <= tol and abs(plon - t[1]) <= tol:
                return True
    return False


def match_entity(predicted: dict[str, Any], true_values: Iterable[dict[str, Any]]) -> bool:
    qid = predicted.get("value")
    if not qid:
        # resolver returned no QID -> cannot confirm a match. Counts as wrong
        # (a conservative, precision-lowering choice; documented above).
        return False
    return any(tv.get("value") == qid for tv in true_values)


def match_string(predicted: dict[str, Any], true_values: Iterable[dict[str, Any]]) -> bool:
    pv = _norm_string(predicted.get("value"))
    return any(_norm_string(tv.get("value")) == pv for tv in true_values)


def match_value(
    predicted: Optional[dict[str, Any]],
    true_values: Iterable[dict[str, Any]],
    target_pid: str,
    coord_tol: float = COORD_TOLERANCE_DEG,
) -> bool:
    if predicted is None:
        return False
    true_values = list(true_values)
    if target_pid == "P571":
        return match_time(predicted, true_values)
    if target_pid == "P625":
        return match_coordinate(predicted, true_values, tol=coord_tol)
    if predicted.get("type") == "entity":
        return match_entity(predicted, true_values)
    return match_string(predicted, true_values)


def classify(
    prediction: dict[str, Any],
    true_values: Iterable[dict[str, Any]],
    coord_tol: float = COORD_TOLERANCE_DEG,
) -> str:
    """Return 'abstain', 'correct', or 'wrong' for one prediction."""
    if prediction.get("abstain") or prediction.get("predicted") is None:
        return "abstain"
    ok = match_value(
        prediction["predicted"], true_values, prediction["target_pid"], coord_tol
    )
    return "correct" if ok else "wrong"


def _metrics(counts: dict[str, int]) -> dict[str, Any]:
    correct = counts.get("correct", 0)
    wrong = counts.get("wrong", 0)
    abstain = counts.get("abstain", 0)
    total = correct + wrong + abstain
    answered = correct + wrong
    return {
        "n": total,
        "correct": correct,
        "wrong": wrong,
        "abstain": abstain,
        "precision": (correct / answered) if answered else None,
        "recall": (correct / total) if total else None,
        "abstain_rate": (abstain / total) if total else None,
    }


def score(
    predictions: Iterable[dict[str, Any]],
    instances: Iterable[dict[str, Any]],
    coord_tol: float = COORD_TOLERANCE_DEG,
) -> dict[str, Any]:
    """Aggregate metrics overall, by property, and by property x popularity bucket."""
    by_id = {inst["id"]: inst for inst in instances}
    overall: dict[str, int] = collections.Counter()
    by_prop: dict[str, dict[str, int]] = collections.defaultdict(collections.Counter)
    by_prop_bucket: dict[str, dict[str, dict[str, int]]] = collections.defaultdict(
        lambda: collections.defaultdict(collections.Counter)
    )
    unmatched = 0
    for pred in predictions:
        inst = by_id.get(pred["id"])
        if inst is None:
            unmatched += 1
            continue
        outcome = classify(pred, inst["true_values"], coord_tol)
        pid = pred["target_pid"]
        bucket = pred.get("popularity_bucket") or inst.get("popularity_bucket")
        overall[outcome] += 1
        by_prop[pid][outcome] += 1
        by_prop_bucket[pid][bucket][outcome] += 1

    return {
        "overall": _metrics(overall),
        "by_property": {pid: _metrics(c) for pid, c in sorted(by_prop.items())},
        "by_property_bucket": {
            pid: {b: _metrics(c) for b, c in sorted(buckets.items())}
            for pid, buckets in sorted(by_prop_bucket.items())
        },
        "unmatched_predictions": unmatched,
    }


def to_markdown(scored: dict[str, Any], property_labels: dict[str, str]) -> str:
    """Render the by-property table as a compact markdown summary."""
    lines = ["| property | n | precision | recall | abstain |",
             "|---|---|---|---|---|"]

    def fmt(x: Optional[float]) -> str:
        return "—" if x is None else f"{x:.2f}"

    for pid, m in scored["by_property"].items():
        label = property_labels.get(pid, pid)
        lines.append(
            f"| {label} (`{pid}`) | {m['n']} | {fmt(m['precision'])} | "
            f"{fmt(m['recall'])} | {fmt(m['abstain_rate'])} |"
        )
    ov = scored["overall"]
    lines.append(
        f"| **overall** | {ov['n']} | {fmt(ov['precision'])} | "
        f"{fmt(ov['recall'])} | {fmt(ov['abstain_rate'])} |"
    )
    return "\n".join(lines)
