"""Build held-out gap-filling eval instances from sampled shrine entities.

Each instance holds out the true value of ONE target property and keeps the
rest of the entity as context. The model's job (R4) is to predict the held-out
value from that context; scoring (R5) compares against ``true_values``.

An instance::

    {
      "id": "Q191763__P571",
      "qid": "Q191763",
      "label_en": "Itsukushima Shrine",
      "label_ja": "厳島神社",
      "sitelinks": 41,
      "popularity_bucket": "head",
      "target_pid": "P571",
      "target_property": "inception",
      "true_values": [{"type": "time", "value": "+0593-..."}],
      "context": {                      # the held-out property is NOT here
        "label_en": "...", "label_ja": "...", "description_en": "...",
        "statements": {"P17": [...], "P131": [...], ...}
      }
    }
"""
from __future__ import annotations

import collections
from typing import Any, Iterable

from o1.wikidata import DEFAULT_TARGET_PROPERTIES, popularity_bucket


def instance_context(entity: dict[str, Any], exclude_pid: str) -> dict[str, Any]:
    """The entity as context for prediction, with ``exclude_pid`` removed."""
    statements = {
        pid: vals
        for pid, vals in entity.get("statements", {}).items()
        if pid != exclude_pid
    }
    return {
        "label_en": entity.get("label_en"),
        "label_ja": entity.get("label_ja"),
        "description_en": entity.get("description_en"),
        "statements": statements,
    }


def _bucket_for(entity: dict[str, Any]) -> str:
    if entity.get("popularity_bucket"):
        return entity["popularity_bucket"]
    return popularity_bucket(int(entity.get("sitelinks", 0) or 0))


def build_eval_set(
    entities: Iterable[dict[str, Any]],
    target_pids: Iterable[str] = tuple(DEFAULT_TARGET_PROPERTIES),
    property_labels: dict[str, str] = DEFAULT_TARGET_PROPERTIES,
) -> list[dict[str, Any]]:
    """One instance per (entity, target property that has a value)."""
    target_pids = tuple(target_pids)
    instances: list[dict[str, Any]] = []
    for entity in entities:
        qid = entity.get("qid")
        statements = entity.get("statements", {})
        bucket = _bucket_for(entity)
        for pid in target_pids:
            true_values = statements.get(pid)
            if not true_values:
                continue  # no ground-truth value to hold out for this property
            instances.append({
                "id": f"{qid}__{pid}",
                "qid": qid,
                "label_en": entity.get("label_en"),
                "label_ja": entity.get("label_ja"),
                "sitelinks": entity.get("sitelinks"),
                "popularity_bucket": bucket,
                "target_pid": pid,
                "target_property": property_labels.get(pid, pid),
                "true_values": true_values,
                "context": instance_context(entity, pid),
            })
    return instances


def bucket_stratified_sample(
    instances: Iterable[dict[str, Any]], per_pid_bucket: int
) -> list[dict[str, Any]]:
    """Deterministically pick up to ``per_pid_bucket`` instances per (property,
    popularity bucket) cell, so the run sample spans head/torso/tail for every
    property that reaches them — required to measure the popularity gradient (H2).
    """
    cells: dict[tuple, list[dict[str, Any]]] = collections.defaultdict(list)
    for inst in instances:
        cells[(inst["target_pid"], inst["popularity_bucket"])].append(inst)
    out: list[dict[str, Any]] = []
    for key in sorted(cells):
        items = sorted(cells[key], key=lambda x: x["id"])
        if len(items) <= per_pid_bucket:
            out.extend(items)
            continue
        step = len(items) / per_pid_bucket
        idxs = sorted({int(k * step) for k in range(per_pid_bucket)})
        out.extend(items[i] for i in idxs)
    return out


def bucket_summary(instances: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Counts of instances per popularity bucket x target property (for reporting)."""
    out: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: collections.defaultdict(int)
    )
    for inst in instances:
        out[inst["popularity_bucket"]][inst["target_pid"]] += 1
    return {b: dict(v) for b, v in out.items()}
