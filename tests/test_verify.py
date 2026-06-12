"""Tests for the predict-then-verify pass — fully offline (fake client)."""
from o1 import verify as vf

INSTANCE = {
    "id": "Q1__P17", "qid": "Q1", "target_pid": "P17",
    "popularity_bucket": "head",
    "context": {"label_en": "Itsukushima Shrine", "label_ja": "厳島神社",
                "description_en": None, "statements": {}},
    "true_values": [{"type": "entity", "value": "Q17"}],
}
PRED_ANSWER = {
    "id": "Q1__P17", "qid": "Q1", "target_pid": "P17", "popularity_bucket": "head",
    "abstain": False, "raw_answer": "Japan",
    "predicted": {"type": "entity", "value": "Q17", "label": "Japan"},
}
PRED_ABSTAIN = {
    "id": "Q1__P17", "qid": "Q1", "target_pid": "P17", "popularity_bucket": "head",
    "abstain": True, "raw_answer": None, "predicted": None,
}


def test_build_verify_prompt_is_independent_framing():
    p = vf.build_verify_prompt(INSTANCE, "Japan")
    assert "Japan" in p
    assert "do not assume the proposal is right" in p
    assert "KEEP" in p and "REVISE" in p and "WITHDRAW" in p


def test_parse_verification_keep_revise_withdraw():
    assert vf.parse_verification("KEEP (confidence 0.9)") == ("keep", None, 0.9)
    d, rev, c = vf.parse_verification("REVISE: Mie Prefecture (confidence 0.7)")
    assert d == "revise" and rev == "Mie Prefecture" and c == 0.7
    assert vf.parse_verification("WITHDRAW (confidence 0.2)") == ("withdraw", None, 0.2)
    # no marker -> defaults to keep
    assert vf.parse_verification("looks fine to me")[0] == "keep"


def test_verify_keep_preserves_prediction():
    out = vf.verify_prediction(INSTANCE, PRED_ANSWER, client=lambda p: "KEEP (confidence 0.95)")
    assert out["abstain"] is False
    assert out["predicted"]["value"] == "Q17"
    assert out["verify"]["decision"] == "keep"
    assert out["verify"]["confidence"] == 0.95
    assert out["pre_verify"]["predicted"]["value"] == "Q17"


def test_verify_withdraw_becomes_abstain():
    out = vf.verify_prediction(INSTANCE, PRED_ANSWER, client=lambda p: "WITHDRAW (confidence 0.3)")
    assert out["abstain"] is True
    assert out["predicted"] is None
    assert out["verify"]["decision"] == "withdraw"
    # original answer retained for audit
    assert out["pre_verify"]["predicted"]["value"] == "Q17"


def test_verify_revise_replaces_value_via_resolver():
    out = vf.verify_prediction(
        INSTANCE, PRED_ANSWER,
        client=lambda p: "REVISE: Hiroshima Prefecture (confidence 0.8)",
        resolver=lambda s: "Q132751",
    )
    assert out["abstain"] is False
    assert out["predicted"]["value"] == "Q132751"
    assert out["raw_answer"] == "Hiroshima Prefecture"
    assert out["verify"]["decision"] == "revise"


def test_verify_unparseable_revision_withdraws():
    # P571 expects a year; a non-year revision can't be typed -> withdraw
    inst = {**INSTANCE, "target_pid": "P571"}
    pred = {**PRED_ANSWER, "target_pid": "P571", "raw_answer": "1200",
            "predicted": {"type": "time", "value": "1200"}}
    out = vf.verify_prediction(inst, pred, client=lambda p: "REVISE: I am not sure")
    assert out["abstain"] is True and out["predicted"] is None


def test_verify_skips_abstained_prediction_without_calling_client():
    called = {"n": 0}

    def client(p):
        called["n"] += 1
        return "KEEP"

    out = vf.verify_prediction(INSTANCE, PRED_ABSTAIN, client=client)
    assert called["n"] == 0  # no verification call for an already-abstained pred
    assert out["abstain"] is True
    assert out["verify"]["decision"] == "skipped"


def test_verify_all_joins_by_id():
    out = vf.verify_all([INSTANCE], [PRED_ANSWER], client=lambda p: "KEEP (0.9)")
    assert len(out) == 1 and out[0]["id"] == "Q1__P17"


def test_verified_output_scores_with_score_module():
    """The verify record must be scorable by score.score unchanged."""
    from o1 import score as sc
    verified = vf.verify_all([INSTANCE], [PRED_ANSWER], client=lambda p: "KEEP (0.9)")
    scored = sc.score(verified, [INSTANCE])
    assert scored["by_property"]["P17"]["correct"] == 1
