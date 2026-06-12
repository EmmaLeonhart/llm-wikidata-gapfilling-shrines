"""Tests for the predict-only pipeline — fully offline (fake client + resolver)."""
from o1 import predict as pr

INSTANCE_DATE = {
    "id": "Q1__P571", "qid": "Q1", "target_pid": "P571",
    "popularity_bucket": "head",
    "context": {
        "label_en": "Itsukushima Shrine", "label_ja": "厳島神社",
        "description_en": "Shinto shrine in Hatsukaichi, Japan",
        "statements": {"P17": [{"type": "entity", "value": "Q17"}]},
    },
}
INSTANCE_COUNTRY = {
    "id": "Q1__P17", "qid": "Q1", "target_pid": "P17",
    "popularity_bucket": "head",
    "context": {"label_en": "Itsukushima Shrine", "label_ja": None,
                "description_en": None, "statements": {}},
}
INSTANCE_COORD = {
    "id": "Q1__P625", "qid": "Q1", "target_pid": "P625",
    "popularity_bucket": "tail",
    "context": {"label_en": "Some Shrine", "label_ja": None,
                "description_en": None, "statements": {}},
}


def test_build_prompt_includes_context_and_excludes_nothing_extra():
    prompt = pr.build_prompt(INSTANCE_DATE)
    assert "Itsukushima Shrine" in prompt
    assert "厳島神社" in prompt
    assert "founded" in prompt  # P571 question clause
    assert "ANSWER:" in prompt and "ABSTAIN" in prompt
    # the one known fact is rendered as context
    assert "country" in prompt


def test_parse_response_answer_and_abstain():
    assert pr.parse_response("ANSWER: 1168") == (False, "1168")
    assert pr.parse_response("ABSTAIN") == (True, None)
    assert pr.parse_response("answer: Japan") == (False, "Japan")
    assert pr.parse_response("ANSWER: ABSTAIN") == (True, None)
    assert pr.parse_response("") == (True, None)
    # lenient: bare short reply treated as the answer
    assert pr.parse_response("Mie Prefecture") == (False, "Mie Prefecture")


def test_normalize_year():
    assert pr.normalize_answer("593", "P571") == {"type": "time", "value": "593"}
    assert pr.normalize_answer("founded in 1879", "P571")["value"] == "1879"
    assert pr.normalize_answer("no idea", "P571") is None


def test_normalize_coordinate():
    out = pr.normalize_answer("34.295, 132.319", "P625")
    assert out == {"type": "coordinate", "value": [34.295, 132.319]}
    assert pr.normalize_answer("somewhere", "P625") is None


def test_normalize_entity_uses_resolver():
    out = pr.normalize_answer("Japan", "P17", resolver=lambda s: "Q17")
    assert out == {"type": "entity", "value": "Q17", "label": "Japan"}
    # no resolver -> QID None but label kept
    out2 = pr.normalize_answer("Japan", "P17")
    assert out2 == {"type": "entity", "value": None, "label": "Japan"}


def test_predict_instance_answer():
    client = lambda prompt: "ANSWER: 1168"
    pred = pr.predict_instance(INSTANCE_DATE, client)
    assert pred["abstain"] is False
    assert pred["predicted"] == {"type": "time", "value": "1168"}
    assert pred["id"] == "Q1__P571"


def test_predict_instance_abstain():
    client = lambda prompt: "ABSTAIN"
    pred = pr.predict_instance(INSTANCE_COUNTRY, client)
    assert pred["abstain"] is True
    assert pred["predicted"] is None


def test_predict_instance_entity_resolves_qid():
    client = lambda prompt: "ANSWER: Japan"
    pred = pr.predict_instance(INSTANCE_COUNTRY, client, resolver=lambda s: "Q17")
    assert pred["predicted"]["value"] == "Q17"
    assert pred["predicted"]["label"] == "Japan"


def test_unparseable_typed_answer_becomes_abstain_but_keeps_raw():
    client = lambda prompt: "ANSWER: I really don't know"
    pred = pr.predict_instance(INSTANCE_COORD, client)
    # coordinate couldn't be parsed -> abstain, but raw_answer preserved for audit
    assert pred["abstain"] is True
    assert pred["predicted"] is None
    assert pred["raw_answer"] == "I really don't know"


def test_predict_all_runs_over_list():
    client = lambda prompt: "ANSWER: 1879"
    preds = pr.predict_all([INSTANCE_DATE, INSTANCE_DATE], client)
    assert len(preds) == 2
    assert all(p["predicted"]["value"] == "1879" for p in preds)
