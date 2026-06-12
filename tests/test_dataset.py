"""Tests for held-out eval-instance construction and stratified sampling."""
import collections

from o1 import dataset as ds
from o1 import wikidata as wd

ENTITIES = [
    {
        "qid": "Q1", "label_en": "Head Shrine", "label_ja": "頭",
        "description_en": "a popular shrine", "sitelinks": 30,
        "popularity_bucket": "head",
        "statements": {
            "P17": [{"type": "entity", "value": "Q17"}],
            "P571": [{"type": "time", "value": "+0700-00-00T00:00:00Z"}],
            "P625": [{"type": "coordinate", "value": [34.0, 135.0]}],
        },
    },
    {
        "qid": "Q2", "label_en": "Tail Shrine", "label_ja": "尾",
        "description_en": None, "sitelinks": 0, "popularity_bucket": "tail",
        "statements": {
            "P17": [{"type": "entity", "value": "Q17"}],
        },
    },
]


def test_build_eval_set_one_instance_per_present_property():
    insts = ds.build_eval_set(ENTITIES)
    # Q1 has 3 target properties, Q2 has 1 -> 4 instances total.
    assert len(insts) == 4
    ids = {i["id"] for i in insts}
    assert ids == {"Q1__P17", "Q1__P571", "Q1__P625", "Q2__P17"}


def test_held_out_property_removed_from_context():
    insts = ds.build_eval_set(ENTITIES)
    p571 = next(i for i in insts if i["id"] == "Q1__P571")
    # The held-out property must NOT leak into the context...
    assert "P571" not in p571["context"]["statements"]
    # ...but the other statements remain as context.
    assert "P17" in p571["context"]["statements"]
    assert "P625" in p571["context"]["statements"]
    # ...and the true value is captured.
    assert p571["true_values"][0]["value"] == "+0700-00-00T00:00:00Z"


def test_instance_carries_bucket_and_property_label():
    insts = ds.build_eval_set(ENTITIES)
    p17_tail = next(i for i in insts if i["id"] == "Q2__P17")
    assert p17_tail["popularity_bucket"] == "tail"
    assert p17_tail["target_property"] == "country"


def test_bucket_stratified_sample_covers_cells_and_caps():
    insts = (
        [{"id": f"a{i}", "target_pid": "P17", "popularity_bucket": "head"} for i in range(10)]
        + [{"id": f"b{i}", "target_pid": "P17", "popularity_bucket": "tail"} for i in range(10)]
        + [{"id": f"c{i}", "target_pid": "P31", "popularity_bucket": "head"} for i in range(2)]
    )
    out = ds.bucket_stratified_sample(insts, per_pid_bucket=3)
    cells = collections.Counter((i["target_pid"], i["popularity_bucket"]) for i in out)
    assert cells[("P17", "head")] == 3   # capped
    assert cells[("P17", "tail")] == 3   # capped
    assert cells[("P31", "head")] == 2   # smaller than cap -> all kept
    # deterministic
    assert [i["id"] for i in out] == [i["id"] for i in ds.bucket_stratified_sample(insts, 3)]


def test_bucket_summary_counts():
    insts = ds.build_eval_set(ENTITIES)
    summary = ds.bucket_summary(insts)
    assert summary["head"] == {"P17": 1, "P571": 1, "P625": 1}
    assert summary["tail"] == {"P17": 1}


# ---- stratified sampling (wikidata module) ----

def test_popularity_bucket_thresholds():
    assert wd.popularity_bucket(0) == "tail"
    assert wd.popularity_bucket(1) == "torso"
    assert wd.popularity_bucket(5) == "torso"
    assert wd.popularity_bucket(6) == "head"
    assert wd.popularity_bucket(50) == "head"


def test_stratified_sample_is_deterministic_and_balanced():
    rows = (
        [{"qid": f"Q{i:04d}", "sitelinks": 10, "bucket": "head"} for i in range(100)]
        + [{"qid": f"R{i:04d}", "sitelinks": 2, "bucket": "torso"} for i in range(100)]
        + [{"qid": f"S{i:04d}", "sitelinks": 0, "bucket": "tail"} for i in range(100)]
    )
    a = wd.stratified_sample(rows, per_bucket=10, seed=0)
    b = wd.stratified_sample(rows, per_bucket=10, seed=0)
    assert [r["qid"] for r in a] == [r["qid"] for r in b]  # deterministic
    buckets = [r["bucket"] for r in a]
    assert buckets.count("head") == 10
    assert buckets.count("torso") == 10
    assert buckets.count("tail") == 10


def test_stratified_sample_handles_small_bucket():
    rows = [{"qid": f"Q{i}", "sitelinks": 10, "bucket": "head"} for i in range(3)]
    out = wd.stratified_sample(rows, per_bucket=10, seed=0)
    assert len(out) == 3  # cannot exceed available


def test_fetch_ancestors_parses_and_includes_self():
    def fake_getter(url, params=None):
        return {"results": {"bindings": [
            {"a": {"value": "http://www.wikidata.org/entity/Q_city"}},
            {"a": {"value": "http://www.wikidata.org/entity/Q_pref"}},
        ]}}
    anc = wd.fetch_ancestors("Q_city", "P131", getter=fake_getter)
    assert anc == {"Q_city", "Q_pref"}
    # property without a defined hierarchy path -> empty
    assert wd.fetch_ancestors("Q1", "P571", getter=fake_getter) == set()


def test_fetch_ancestors_degrades_gracefully_on_failure():
    def boom(url, params=None):
        raise RuntimeError("502 Bad Gateway")
    # retries=0 to keep the test fast; must fall back to {qid}, not raise
    anc = wd.fetch_ancestors("Q_city", "P131", getter=boom, retries=0)
    assert anc == {"Q_city"}


def test_parse_popularity_rows():
    sparql = {"results": {"bindings": [
        {"item": {"value": "http://www.wikidata.org/entity/Q5"},
         "sitelinks": {"value": "8"}},
        {"item": {"value": "http://www.wikidata.org/entity/Q6"},
         "sitelinks": {"value": "0"}},
    ]}}
    rows = wd.parse_popularity_rows(sparql)
    assert rows[0] == {"qid": "Q5", "sitelinks": 8, "bucket": "head"}
    assert rows[1]["bucket"] == "tail"
