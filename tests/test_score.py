"""Tests for typed matching and metric aggregation."""
from o1 import score as sc


def test_extract_year_handles_wikidata_and_bare_and_bce():
    assert sc.extract_year("+1879-00-00T00:00:00Z") == 1879
    assert sc.extract_year("1879") == 1879
    assert sc.extract_year("-0004-00-00T00:00:00Z") == -4
    assert sc.extract_year(None) is None


def test_match_time():
    assert sc.match_time({"value": "1168"},
                         [{"value": "+1168-00-00T00:00:00Z"}]) is True
    assert sc.match_time({"value": "1200"},
                         [{"value": "+1168-00-00T00:00:00Z"}]) is False


def test_match_coordinate_within_tolerance():
    true = [{"value": [34.295, 132.319]}]
    assert sc.match_coordinate({"value": [34.30, 132.32]}, true) is True   # within 0.05
    assert sc.match_coordinate({"value": [35.0, 132.32]}, true) is False   # lat off
    assert sc.match_coordinate({"value": "nope"}, true) is False


def test_match_entity_by_qid():
    assert sc.match_entity({"value": "Q17"}, [{"value": "Q17"}]) is True
    assert sc.match_entity({"value": "Q99"}, [{"value": "Q17"}]) is False
    # resolver returned no QID -> conservatively wrong
    assert sc.match_entity({"value": None, "label": "Japan"}, [{"value": "Q17"}]) is False


def test_match_string_normalized():
    assert sc.match_string({"value": "Shinto "}, [{"value": "shinto"}]) is True


def test_classify_correct_wrong_abstain():
    inst_true = [{"type": "entity", "value": "Q17"}]
    correct = {"target_pid": "P17", "abstain": False,
               "predicted": {"type": "entity", "value": "Q17"}}
    wrong = {"target_pid": "P17", "abstain": False,
             "predicted": {"type": "entity", "value": "Q99"}}
    abstain = {"target_pid": "P17", "abstain": True, "predicted": None}
    assert sc.classify(correct, inst_true) == "correct"
    assert sc.classify(wrong, inst_true) == "wrong"
    assert sc.classify(abstain, inst_true) == "abstain"


def test_score_aggregates_precision_recall_abstain():
    instances = [
        {"id": "A", "true_values": [{"type": "entity", "value": "Q17"}]},
        {"id": "B", "true_values": [{"type": "entity", "value": "Q17"}]},
        {"id": "C", "true_values": [{"type": "entity", "value": "Q17"}]},
        {"id": "D", "true_values": [{"type": "time", "value": "+1700-00-00T00:00:00Z"}]},
    ]
    predictions = [
        # P17: 1 correct, 1 wrong, 1 abstain
        {"id": "A", "target_pid": "P17", "popularity_bucket": "head",
         "abstain": False, "predicted": {"type": "entity", "value": "Q17"}},
        {"id": "B", "target_pid": "P17", "popularity_bucket": "head",
         "abstain": False, "predicted": {"type": "entity", "value": "Q99"}},
        {"id": "C", "target_pid": "P17", "popularity_bucket": "tail",
         "abstain": True, "predicted": None},
        # P571: 1 correct
        {"id": "D", "target_pid": "P571", "popularity_bucket": "head",
         "abstain": False, "predicted": {"type": "time", "value": "1700"}},
    ]
    out = sc.score(predictions, instances)
    p17 = out["by_property"]["P17"]
    assert p17["n"] == 3 and p17["correct"] == 1 and p17["wrong"] == 1 and p17["abstain"] == 1
    assert p17["precision"] == 0.5   # 1 correct of 2 answered
    assert abs(p17["recall"] - 1 / 3) < 1e-9
    assert abs(p17["abstain_rate"] - 1 / 3) < 1e-9
    # bucket split
    assert out["by_property_bucket"]["P17"]["head"]["n"] == 2
    assert out["by_property_bucket"]["P17"]["tail"]["abstain"] == 1
    # overall: 2 correct of 4
    assert out["overall"]["correct"] == 2
    assert abs(out["overall"]["recall"] - 0.5) < 1e-9


def test_match_entity_hierarchy_lenient():
    # true value Q_city; model answered Q_pref (the prefecture above the city).
    # ancestors(Q_city) = {Q_city, Q_pref, Q_japan}; ancestors(Q_pref) = {Q_pref, Q_japan}
    anc = {
        "Q_city": {"Q_city", "Q_pref", "Q_japan"},
        "Q_pref": {"Q_pref", "Q_japan"},
    }
    ancestors = lambda q: anc.get(q, {q})
    pred_general = {"value": "Q_pref"}
    true = [{"value": "Q_city"}]
    # strict: prefecture != city -> wrong
    assert sc.match_entity(pred_general, true) is False
    # lenient: prefecture is an ancestor of the city -> credited
    assert sc.match_entity(pred_general, true, ancestors=ancestors) is True
    # model more specific than truth is also credited
    assert sc.match_entity({"value": "Q_city"}, [{"value": "Q_pref"}],
                           ancestors=ancestors) is True
    # genuinely unrelated entity stays wrong even when lenient
    assert sc.match_entity({"value": "Q_other"}, true, ancestors=ancestors) is False


def test_score_lenient_changes_entity_outcome():
    instances = [{"id": "A", "true_values": [{"type": "entity", "value": "Q_city"}]}]
    preds = [{"id": "A", "target_pid": "P131", "popularity_bucket": "head",
              "abstain": False, "predicted": {"type": "entity", "value": "Q_pref"}}]
    ancestors = lambda q: {"Q_city": {"Q_city", "Q_pref"}}.get(q, {q})
    strict = sc.score(preds, instances)
    lenient = sc.score(preds, instances, ancestors=ancestors)
    assert strict["by_property"]["P131"]["correct"] == 0
    assert lenient["by_property"]["P131"]["correct"] == 1


def test_score_reports_unmatched_predictions():
    out = sc.score([{"id": "ghost", "target_pid": "P17",
                     "abstain": True, "predicted": None}], [])
    assert out["unmatched_predictions"] == 1


def test_to_markdown_renders_table():
    instances = [{"id": "A", "true_values": [{"type": "entity", "value": "Q17"}]}]
    preds = [{"id": "A", "target_pid": "P17", "popularity_bucket": "head",
              "abstain": False, "predicted": {"type": "entity", "value": "Q17"}}]
    md = sc.to_markdown(sc.score(preds, instances), {"P17": "country"})
    assert "country" in md and "overall" in md and "precision" in md
