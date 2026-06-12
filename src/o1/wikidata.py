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


def save_json(obj: Any, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
