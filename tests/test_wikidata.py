"""Tests for the Wikidata parsers — pure functions, no network.

A mock SPARQL result and a mock entity payload exercise the binding parser,
the snak-value normalizer, and the entity extractor. The network wrappers are
exercised via an injected fake ``getter`` so ``sample_shrines`` runs offline.
"""
from o1 import wikidata as wd

MOCK_SPARQL = {
    "results": {
        "bindings": [
            {
                "item": {"value": "http://www.wikidata.org/entity/Q1188121"},
                "itemLabel": {"value": "Ise Grand Shrine"},
                "sitelinks": {"value": "42"},
            },
            {
                "item": {"value": "http://www.wikidata.org/entity/Q999999"},
                "itemLabel": {"value": "Obscure Shrine"},
                "sitelinks": {"value": "1"},
            },
        ]
    }
}

MOCK_ENTITY = {
    "entities": {
        "Q1188121": {
            "labels": {"en": {"value": "Ise Grand Shrine"},
                       "ja": {"value": "伊勢神宮"}},
            "descriptions": {"en": {"value": "Shinto shrine in Mie, Japan"}},
            "sitelinks": {"enwiki": {}, "jawiki": {}, "frwiki": {}},
            "claims": {
                "P17": [{"mainsnak": {"snaktype": "value", "datavalue": {
                    "type": "wikibase-entityid", "value": {"id": "Q17"}}}}],
                "P571": [{"mainsnak": {"snaktype": "value", "datavalue": {
                    "type": "time",
                    "value": {"time": "-0004-00-00T00:00:00Z", "precision": 9}}}}],
                "P625": [{"mainsnak": {"snaktype": "value", "datavalue": {
                    "type": "globecoordinate",
                    "value": {"latitude": 34.45, "longitude": 136.72}}}}],
                # a novalue snak must be skipped
                "P140": [{"mainsnak": {"snaktype": "novalue"}}],
            },
        }
    }
}


def test_parse_shrine_bindings():
    rows = wd.parse_shrine_bindings(MOCK_SPARQL)
    assert [r["qid"] for r in rows] == ["Q1188121", "Q999999"]
    assert rows[0]["sitelinks"] == 42
    assert rows[1]["label"] == "Obscure Shrine"


def test_extract_snak_value_types():
    assert wd.extract_snak_value(
        {"type": "wikibase-entityid", "value": {"id": "Q17"}}
    ) == {"type": "entity", "value": "Q17"}
    coord = wd.extract_snak_value(
        {"type": "globecoordinate", "value": {"latitude": 1.0, "longitude": 2.0}}
    )
    assert coord["type"] == "coordinate" and coord["value"] == [1.0, 2.0]
    assert wd.extract_snak_value({"type": "unsupported", "value": {}}) is None


def test_extract_claim_values_skips_novalue():
    claims = MOCK_ENTITY["entities"]["Q1188121"]["claims"]
    assert wd.extract_claim_values(claims, "P17") == [{"type": "entity", "value": "Q17"}]
    # P140 is a novalue snak -> no concrete values
    assert wd.extract_claim_values(claims, "P140") == []
    # property absent entirely
    assert wd.extract_claim_values(claims, "P999") == []


def test_parse_entity():
    e = wd.parse_entity(MOCK_ENTITY, "Q1188121")
    assert e["label_en"] == "Ise Grand Shrine"
    assert e["label_ja"] == "伊勢神宮"
    assert e["sitelinks"] == 3  # three sitelinks in the mock
    assert "P17" in e["statements"]
    assert "P140" not in e["statements"]  # novalue dropped -> property omitted
    assert e["statements"]["P625"][0]["type"] == "coordinate"


def test_sample_shrines_offline_with_fake_getter():
    """sample_shrines should run end-to-end against an injected getter."""
    def fake_getter(url, params=None):
        if "sparql" in url:
            return MOCK_SPARQL
        # entity data: only Q1188121 has a rich payload; others return empty
        for qid in ("Q1188121", "Q999999"):
            if qid in url:
                return MOCK_ENTITY if qid == "Q1188121" else {"entities": {qid: {}}}
        return {"entities": {}}

    out = wd.sample_shrines(limit=2, getter=fake_getter, sleep_s=0)
    assert len(out) == 2
    assert out[0]["qid"] == "Q1188121"
    assert out[0]["statements"]["P17"][0]["value"] == "Q17"
    assert out[0]["sitelinks"] == 42  # SPARQL count is authoritative
