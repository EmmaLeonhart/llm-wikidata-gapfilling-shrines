"""Predict-then-verify pass (Chain-of-Verification style).

Takes a predict-only result (R4) and asks the model to **independently** check
the proposed value, then KEEP / REVISE / WITHDRAW it with a self-reported
confidence. The independence (re-deriving the fact rather than re-affirming the
first answer) is the mechanism CoVe shows reduces hallucination — and the
literature also warns naive self-correction can backfire, so the verified output
is scored the same way as predict-only and the *lift* is measured, not assumed.

The output record has the **same shape as a prediction** (id/qid/target_pid/
popularity_bucket/abstain/raw_answer/predicted) so ``score.score`` runs on it
unchanged, plus a ``verify`` block recording the decision/confidence/raw text and
the pre-verification answer for audit.

Client and resolver are injected, so the whole pass is unit-tested offline.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from o1.predict import PROPERTY_PROMPTS, normalize_answer, ClientFn, ResolverFn

_DECISION_RE = re.compile(r"\b(KEEP|REVISE|WITHDRAW)\b", re.IGNORECASE)
_REVISE_RE = re.compile(r"REVISE\s*:?\s*(.+)", re.IGNORECASE)
_CONF_RE = re.compile(r"(?:confidence[^0-9]*)?(\b0?\.\d+|\b1(?:\.0+)?\b|\b0\b)")


def build_verify_prompt(instance: dict[str, Any], proposed_raw: str) -> str:
    ctx = instance["context"]
    ask, _ = PROPERTY_PROMPTS[instance["target_pid"]]
    name = ctx.get("label_en") or instance["qid"]
    lines = [
        f"Shrine: {name}",
    ]
    if ctx.get("label_ja"):
        lines.append(f"Japanese name: {ctx['label_ja']}")
    lines += [
        "",
        f"A proposed answer for {ask} of this Shinto shrine is: "
        f"\"{proposed_raw}\".",
        "Independently verify this. First, from your own knowledge, state what "
        f"{ask} actually is for this shrine (do not assume the proposal is "
        "right). Then judge the proposal.",
        "",
        "Respond on a single final line as exactly one of:",
        "  KEEP (confidence 0-1)",
        "  REVISE: <corrected value> (confidence 0-1)",
        "  WITHDRAW (confidence 0-1)",
    ]
    return "\n".join(lines)


def parse_verification(text: str) -> tuple[str, Optional[str], Optional[float]]:
    """Return ``(decision, revised_raw, confidence)``.

    decision is 'keep' | 'revise' | 'withdraw' (defaults to 'keep' if no marker).
    """
    t = (text or "").strip()
    dmatch = _DECISION_RE.search(t)
    decision = dmatch.group(1).lower() if dmatch else "keep"
    revised = None
    if decision == "revise":
        rm = _REVISE_RE.search(t)
        if rm:
            revised = rm.group(1)
            # strip a trailing "(confidence ...)" tail from the revised value
            revised = re.sub(r"\(?\s*confidence.*$", "", revised, flags=re.IGNORECASE)
            revised = revised.strip().strip("`\"'").strip()
            if not revised:
                revised = None
    conf = None
    cm = _CONF_RE.search(t)
    if cm:
        try:
            conf = float(cm.group(1))
        except ValueError:
            conf = None
    return decision, revised, conf


def verify_prediction(
    instance: dict[str, Any],
    prediction: dict[str, Any],
    client: ClientFn,
    resolver: Optional[ResolverFn] = None,
) -> dict[str, Any]:
    """Run the verify pass on one predict-only result; return a prediction-shaped record."""
    base = {
        "id": prediction["id"],
        "qid": prediction["qid"],
        "target_pid": prediction["target_pid"],
        "popularity_bucket": prediction.get("popularity_bucket"),
    }
    # Nothing to verify if the model already abstained.
    if prediction.get("abstain") or prediction.get("predicted") is None:
        return {
            **base,
            "abstain": True,
            "raw_answer": prediction.get("raw_answer"),
            "predicted": None,
            "verify": {"decision": "skipped", "confidence": None, "raw": None},
            "pre_verify": {"abstain": True, "predicted": None},
        }

    proposed_raw = prediction.get("raw_answer") or ""
    response = client(build_verify_prompt(instance, proposed_raw))
    decision, revised_raw, conf = parse_verification(response)

    abstain = False
    raw_answer = proposed_raw
    predicted = prediction["predicted"]

    if decision == "withdraw":
        abstain, predicted, raw_answer = True, None, proposed_raw
    elif decision == "revise" and revised_raw:
        new_pred = normalize_answer(revised_raw, prediction["target_pid"], resolver=resolver)
        if new_pred is None:
            # unparseable revision -> withdraw rather than keep a value we can't type
            abstain, predicted = True, None
        else:
            predicted, raw_answer = new_pred, revised_raw
    # decision == "keep" (or revise with no value) -> keep original prediction

    return {
        **base,
        "abstain": abstain,
        "raw_answer": raw_answer,
        "predicted": predicted,
        "verify": {"decision": decision, "confidence": conf, "raw": response},
        "pre_verify": {
            "abstain": prediction.get("abstain", False),
            "predicted": prediction["predicted"],
            "raw_answer": proposed_raw,
        },
    }


def verify_all(
    instances: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    client: ClientFn,
    resolver: Optional[ResolverFn] = None,
) -> list[dict[str, Any]]:
    by_id = {inst["id"]: inst for inst in instances}
    out: list[dict[str, Any]] = []
    for pred in predictions:
        inst = by_id.get(pred["id"])
        if inst is None:
            continue
        out.append(verify_prediction(inst, pred, client, resolver=resolver))
    return out
