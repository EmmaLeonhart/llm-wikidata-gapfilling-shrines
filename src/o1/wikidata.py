"""Sample Shinto-shrine entities and their statements from Wikidata.

Split into **pure parsers** (unit-tested against saved mock JSON, no network)
and **thin network wrappers** (a single ``requests`` call each). The orchestrator
``sample_shrines`` ties them together and is what ``scripts/run.py sample`` calls.

Popularity proxy: Wikidata ``wikibase:sitelinks`` (number of linked Wikipedia
language editions) — a standard, cheap stand-in for entity prominence, which the
literature (Head-to-Tail, FACT-Bench) shows predicts LLM recall.
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable, Iterable, Optional

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
ENTITY_DATA = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
USER_AGENT = (
    "o1-research/0.1 (https://github.com/EmmaLeonhart/"
    "llm-wikidata-gapfilling-shrines; immanuelleleonhart@gmail.com)"
)

# Candidate target properties (the fixed set is decided in R3). pid -> label.
DEFAULT_TARGET_PROPERTIES: dict[str, str] = {
    "P17": "country",
    "P131": "located in admin territorial entity",
    "P140": "religion or worldview",
    "P31": "instance of",
    "P571": "inception",
    "P625": "coordinate location",
    "P1435": "heritage designation",
}

# All Shinto shrines = instances of (P31) Shinto shrine (Q845945) or a subclass.
SHRINE_SPARQL = """
SELECT ?item ?itemLabel ?sitelinks WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q845945 .
  ?item wikibase:sitelinks ?sitelinks .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ja". }}
}}
ORDER BY DESC(?sitelinks)
LIMIT {limit}
"""

# Every shrine + its sitelink count (popularity proxy), no label service so it
# stays light enough to return all ~31k rows for stratified sampling.
SHRINE_POPULARITY_SPARQL = """
SELECT ?item ?sitelinks WHERE {
  ?item wdt:P31/wdt:P279* wd:Q845945 .
  ?item wikibase:sitelinks ?sitelinks .
}
"""

# Popularity buckets, set from the observed distribution over 30,913 shrines:
# tail (0 sitelinks) ~76%, torso (1-5) ~23%, head (6+) ~0.7%.
POPULARITY_BUCKETS = ("head", "torso", "tail")


def popularity_bucket(sitelinks: int) -> str:
    """Map a sitelink count to head / torso / tail."""
    if sitelinks >= 6:
        return "head"
    if sitelinks >= 1:
        return "torso"
    return "tail"


# --------------------------------------------------------------------------
# Pure parsers (no network) — these carry the test coverage.
# --------------------------------------------------------------------------

def parse_shrine_bindings(sparql_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn a SPARQL JSON result into ``[{qid, label, sitelinks}, ...]``."""
    out: list[dict[str, Any]] = []
    for b in sparql_json.get("results", {}).get("bindings", []):
        uri = b.get("item", {}).get("value", "")
        qid = uri.rsplit("/", 1)[-1] if uri else ""
        if not qid:
            continue
        label = b.get("itemLabel", {}).get("value", "")
        try:
            sitelinks = int(b.get("sitelinks", {}).get("value", 0))
        except (TypeError, ValueError):
            sitelinks = 0
        out.append({"qid": qid, "label": label, "sitelinks": sitelinks})
    return out


def extract_snak_value(datavalue: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Normalize a Wikibase ``datavalue`` to ``{type, value}``.

    Returns None for value types we don't handle / "no value" snaks.
    """
    vtype = datavalue.get("type")
    value = datavalue.get("value")
    if vtype == "wikibase-entityid":
        return {"type": "entity", "value": value.get("id")}
    if vtype == "time":
        return {"type": "time", "value": value.get("time"),
                "precision": value.get("precision")}
    if vtype == "globecoordinate":
        return {"type": "coordinate",
                "value": [value.get("latitude"), value.get("longitude")]}
    if vtype == "monolingualtext":
        return {"type": "text", "value": value.get("text")}
    if vtype in ("string", "external-id"):
        return {"type": "string", "value": value}
    if vtype == "quantity":
        return {"type": "quantity", "value": value.get("amount")}
    return None


def extract_claim_values(
    claims: dict[str, Any], pid: str
) -> list[dict[str, Any]]:
    """All normalized values asserted for property ``pid`` on an entity."""
    values: list[dict[str, Any]] = []
    for stmt in claims.get(pid, []):
        mainsnak = stmt.get("mainsnak", {})
        if mainsnak.get("snaktype") != "value":
            continue  # novalue / somevalue carry no concrete object
        dv = mainsnak.get("datavalue")
        if not dv:
            continue
        parsed = extract_snak_value(dv)
        if parsed is not None:
            values.append(parsed)
    return values


def parse_entity(
    entity_json: dict[str, Any],
    qid: str,
    target_pids: Iterable[str] = tuple(DEFAULT_TARGET_PROPERTIES),
) -> dict[str, Any]:
    """Extract label/description/sitelinks/target-statements for one entity.

    ``entity_json`` is the Special:EntityData payload (``{"entities": {qid: ...}}``).
    """
    entity = entity_json.get("entities", {}).get(qid, {})
    labels = entity.get("labels", {})
    descriptions = entity.get("descriptions", {})
    claims = entity.get("claims", {})
    statements = {
        pid: extract_claim_values(claims, pid)
        for pid in target_pids
        if extract_claim_values(claims, pid)
    }
    return {
        "qid": qid,
        "label_en": labels.get("en", {}).get("value"),
        "label_ja": labels.get("ja", {}).get("value"),
        "description_en": descriptions.get("en", {}).get("value"),
        "sitelinks": len(entity.get("sitelinks", {})),
        "statements": statements,
    }


# --------------------------------------------------------------------------
# Thin network wrappers (one request each). Injectable for testing.
# --------------------------------------------------------------------------

def _get_json(url: str, params: Optional[dict[str, str]] = None) -> dict[str, Any]:
    import requests  # imported lazily so pure-parser tests need no dependency

    resp = requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT}, timeout=60
    )
    resp.raise_for_status()
    return resp.json()


def run_sparql(query: str, getter: Callable[..., dict] = _get_json) -> dict[str, Any]:
    return getter(SPARQL_ENDPOINT, {"query": query, "format": "json"})


def fetch_entity_json(qid: str, getter: Callable[..., dict] = _get_json) -> dict[str, Any]:
    return getter(ENTITY_DATA.format(qid=qid))


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------

def sample_shrines(
    limit: int = 60,
    target_pids: Iterable[str] = tuple(DEFAULT_TARGET_PROPERTIES),
    getter: Callable[..., dict] = _get_json,
    sleep_s: float = 0.3,
) -> list[dict[str, Any]]:
    """Fetch up to ``limit`` shrine entities (by sitelinks DESC) with statements."""
    sparql_json = run_sparql(SHRINE_SPARQL.format(limit=limit), getter=getter)
    rows = parse_shrine_bindings(sparql_json)
    entities: list[dict[str, Any]] = []
    for row in rows:
        ej = fetch_entity_json(row["qid"], getter=getter)
        entity = parse_entity(ej, row["qid"], target_pids=target_pids)
        # SPARQL sitelink count is authoritative for ordering; keep it.
        entity["sitelinks"] = row["sitelinks"]
        entity["sparql_label"] = row["label"]
        entities.append(entity)
        if sleep_s:
            time.sleep(sleep_s)
    return entities


def parse_popularity_rows(sparql_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the popularity query into ``[{qid, sitelinks, bucket}, ...]``."""
    out: list[dict[str, Any]] = []
    for b in sparql_json.get("results", {}).get("bindings", []):
        uri = b.get("item", {}).get("value", "")
        qid = uri.rsplit("/", 1)[-1] if uri else ""
        if not qid:
            continue
        try:
            sitelinks = int(b.get("sitelinks", {}).get("value", 0))
        except (TypeError, ValueError):
            sitelinks = 0
        out.append({"qid": qid, "sitelinks": sitelinks,
                    "bucket": popularity_bucket(sitelinks)})
    return out


def stratified_sample(
    rows: list[dict[str, Any]], per_bucket: int, seed: int = 0
) -> list[dict[str, Any]]:
    """Deterministically pick up to ``per_bucket`` entities from each bucket.

    Determinism: sort each bucket by qid and take evenly-spaced picks. No RNG,
    so the same input always yields the same sample (reproducible eval set).
    """
    by_bucket: dict[str, list[dict[str, Any]]] = {b: [] for b in POPULARITY_BUCKETS}
    for r in rows:
        by_bucket.setdefault(r["bucket"], []).append(r)
    picked: list[dict[str, Any]] = []
    for bucket in POPULARITY_BUCKETS:
        items = sorted(by_bucket.get(bucket, []), key=lambda r: r["qid"])
        if not items:
            continue
        if len(items) <= per_bucket:
            picked.extend(items)
            continue
        # Evenly spaced indices across the sorted bucket; offset by seed.
        step = len(items) / per_bucket
        idxs = sorted({int((i * step + seed) % len(items)) for i in range(per_bucket)})
        # Top up if the modulo collapsed any duplicates.
        j = 0
        while len(idxs) < per_bucket and j < len(items):
            if j not in idxs:
                idxs.append(j)
            j += 1
        picked.extend(items[i] for i in sorted(idxs)[:per_bucket])
    return picked


def sample_shrines_stratified(
    per_bucket: int = 40,
    target_pids: Iterable[str] = tuple(DEFAULT_TARGET_PROPERTIES),
    getter: Callable[..., dict] = _get_json,
    seed: int = 0,
    sleep_s: float = 0.2,
) -> list[dict[str, Any]]:
    """Sample ``per_bucket`` shrines from each popularity bucket, with statements."""
    pop_json = run_sparql(SHRINE_POPULARITY_SPARQL, getter=getter)
    rows = parse_popularity_rows(pop_json)
    chosen = stratified_sample(rows, per_bucket=per_bucket, seed=seed)
    entities: list[dict[str, Any]] = []
    for row in chosen:
        ej = fetch_entity_json(row["qid"], getter=getter)
        entity = parse_entity(ej, row["qid"], target_pids=target_pids)
        entity["sitelinks"] = row["sitelinks"]
        entity["popularity_bucket"] = row["bucket"]
        entities.append(entity)
        if sleep_s:
            time.sleep(sleep_s)
    return entities


# Upward-hierarchy property path per target property, for hierarchy-lenient
# scoring: admin location climbs P131; class/religion climb P279 (subclass-of).
ANCESTOR_PROPERTY_PATH: dict[str, str] = {
    "P131": "wdt:P131*",
    "P140": "wdt:P279*",
    "P31": "wdt:P279*",
    "P17": "wdt:P131*",
    "P1435": "wdt:P279*",
}

_ANCESTORS_SPARQL = "SELECT ?a WHERE {{ wd:{qid} {path} ?a . }}"


def fetch_ancestors(
    qid: str,
    target_pid: str,
    getter: Callable[..., dict] = _get_json,
    retries: int = 2,
) -> set[str]:
    """Upward-closure QIDs for ``qid`` along the property hierarchy for ``target_pid``.

    Includes ``qid`` itself (the property paths use ``*``). Returns an empty set
    for properties without a defined hierarchy.

    **Resilient:** the public SPARQL endpoint returns transient 5xx errors; on
    failure this retries with backoff and then **degrades gracefully** to
    ``{qid}`` (i.e. fall back to strict matching for that entity) rather than
    crashing the scoring stage. Callers can detect degradation: a real hierarchy
    always contains more than just ``{qid}`` for a non-root entity.
    """
    path = ANCESTOR_PROPERTY_PATH.get(target_pid)
    if not path:
        return set()
    for attempt in range(retries + 1):
        try:
            data = run_sparql(_ANCESTORS_SPARQL.format(qid=qid, path=path), getter=getter)
            out: set[str] = {qid}
            for b in data.get("results", {}).get("bindings", []):
                uri = b.get("a", {}).get("value", "")
                if uri:
                    out.add(uri.rsplit("/", 1)[-1])
            return out
        except Exception:
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
    return {qid}  # degraded: endpoint unavailable -> behave like strict match


def make_ancestor_lookup(
    target_pid: str, getter: Callable[..., dict] = _get_json
) -> Callable[[str], set[str]]:
    """A memoized ``qid -> set[qid]`` ancestor lookup for one property."""
    cache: dict[str, set[str]] = {}

    def lookup(qid: str) -> set[str]:
        if qid not in cache:
            cache[qid] = fetch_ancestors(qid, target_pid, getter=getter)
        return cache[qid]

    return lookup


def save_json(obj: Any, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
