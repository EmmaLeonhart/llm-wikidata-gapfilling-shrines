"""Predict-only pipeline: ask the model to fill a held-out property, or abstain.

Design for testability: the model **client** and the label->QID **resolver** are
both injected callables, so the whole pipeline runs offline against fakes in
tests. The real client (Anthropic) and resolver (Wikidata ``wbsearchentities``)
are constructed only when actually running (R6), behind ``make_anthropic_client``
and ``wikidata_resolver``.

A prediction::

    {
      "id": "Q191763__P571",
      "qid": "Q191763", "target_pid": "P571", "popularity_bucket": "head",
      "abstain": False,
      "raw_answer": "593",
      "predicted": {"type": "time", "value": "593"},   # None if abstain
    }
"""
from __future__ import annotations

import re
from typing import Any, Callable, Iterable, Optional

from o1.wikidata import DEFAULT_TARGET_PROPERTIES

# (clause used in the question, expected answer format) per target property.
PROPERTY_PROMPTS: dict[str, tuple[str, str]] = {
    "P17": ("the country it is in", "the country name"),
    "P131": ("the administrative territory (prefecture / city / town) it is located in",
             "the administrative territory name"),
    "P140": ("the religion or worldview associated with it", "the religion name"),
    "P31": ("what kind of thing it is (its type / class)", "the type or class name"),
    "P1435": ("its heritage designation, if any", "the heritage designation name"),
    "P571": ("the year it was founded / established", "a year such as 1879"),
    "P625": ("its geographic coordinates", "latitude and longitude as 'lat, lon'"),
}

# Properties whose value is a Wikidata entity (resolve label -> QID for scoring).
ENTITY_PROPERTIES = {"P17", "P131", "P140", "P31", "P1435"}

ClientFn = Callable[[str], str]
ResolverFn = Callable[[str], Optional[str]]


# --------------------------------------------------------------------------
# Prompt construction + response parsing (pure)
# --------------------------------------------------------------------------

def render_value(v: dict[str, Any]) -> str:
    """Render a stored statement value for inclusion in the context block."""
    t = v.get("type")
    val = v.get("value")
    if t == "coordinate" and isinstance(val, (list, tuple)):
        return f"{val[0]}, {val[1]}"
    if t == "time":
        return str(val)
    return str(val)


def build_prompt(
    instance: dict[str, Any],
    property_labels: dict[str, str] = DEFAULT_TARGET_PROPERTIES,
) -> str:
    ctx = instance["context"]
    lines: list[str] = []
    lines.append(f"Shrine: {ctx.get('label_en') or instance['qid']}")
    if ctx.get("label_ja"):
        lines.append(f"Japanese name: {ctx['label_ja']}")
    if ctx.get("description_en"):
        lines.append(f"Description: {ctx['description_en']}")
    statements = ctx.get("statements") or {}
    if statements:
        lines.append("Known facts (from Wikidata):")
        for pid, vals in statements.items():
            label = property_labels.get(pid, pid)
            rendered = ", ".join(render_value(v) for v in vals)
            lines.append(f"  - {label}: {rendered}")
    ask, fmt = PROPERTY_PROMPTS[instance["target_pid"]]
    lines.append("")
    lines.append(f"Question: For this Shinto shrine, what is {ask}?")
    lines.append(
        f'Answer with {fmt}. If you are not confident, respond exactly "ABSTAIN".'
    )
    lines.append('Respond on a single line as `ANSWER: <value>` or `ABSTAIN`.')
    return "\n".join(lines)


_ANSWER_RE = re.compile(r"ANSWER\s*:\s*(.+)", re.IGNORECASE)
_YEAR_RE = re.compile(r"-?\b(\d{1,4})\b")
_COORD_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*[,/]\s*(-?\d+(?:\.\d+)?)")


def parse_response(text: str) -> tuple[bool, Optional[str]]:
    """Return ``(abstain, raw_answer)``. raw_answer is None when abstaining."""
    t = (text or "").strip()
    m = _ANSWER_RE.search(t)
    if m:
        ans = m.group(1).strip().strip("`\"'").strip()
        if not ans or ans.upper() == "ABSTAIN":
            return True, None
        return False, ans
    if "ABSTAIN" in t.upper():
        return True, None
    # No explicit marker: treat a short non-empty reply as the answer, else abstain.
    return (False, t) if t else (True, None)


def normalize_answer(
    raw: str, target_pid: str, resolver: Optional[ResolverFn] = None
) -> Optional[dict[str, Any]]:
    """Turn a raw answer string into a typed value comparable to ``true_values``."""
    if target_pid == "P571":
        m = _YEAR_RE.search(raw)
        return {"type": "time", "value": m.group(1)} if m else None
    if target_pid == "P625":
        m = _COORD_RE.search(raw)
        if not m:
            return None
        return {"type": "coordinate", "value": [float(m.group(1)), float(m.group(2))]}
    if target_pid in ENTITY_PROPERTIES:
        qid = resolver(raw) if resolver else None
        return {"type": "entity", "value": qid, "label": raw}
    return {"type": "string", "value": raw}


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

def predict_instance(
    instance: dict[str, Any],
    client: ClientFn,
    resolver: Optional[ResolverFn] = None,
) -> dict[str, Any]:
    prompt = build_prompt(instance)
    response = client(prompt)
    abstain, raw = parse_response(response)
    predicted = None
    if not abstain and raw is not None:
        predicted = normalize_answer(raw, instance["target_pid"], resolver=resolver)
        if predicted is None:
            # Unparseable answer for a typed property -> treat as abstain, but
            # keep the raw text so it is auditable (never silently dropped).
            abstain = True
    return {
        "id": instance["id"],
        "qid": instance["qid"],
        "target_pid": instance["target_pid"],
        "popularity_bucket": instance.get("popularity_bucket"),
        "abstain": abstain,
        "raw_answer": raw,
        "predicted": predicted,
    }


def predict_all(
    instances: Iterable[dict[str, Any]],
    client: ClientFn,
    resolver: Optional[ResolverFn] = None,
) -> list[dict[str, Any]]:
    return [predict_instance(i, client, resolver=resolver) for i in instances]


# --------------------------------------------------------------------------
# Real client / resolver (constructed only at run time; not used in tests)
# --------------------------------------------------------------------------

def model_tag(model: str) -> str:
    """Filename-safe tag for a model id, e.g. 'llama3.1:8b' -> 'llama3_1_8b'."""
    return model.replace(":", "_").replace(".", "_").replace("/", "_")


def make_ollama_client(
    model: str = "gemma3:12b",
    host: str = "http://localhost:11434",
    num_predict: int = 200,
    temperature: float = 0.0,
) -> ClientFn:
    """Build a ``client(prompt) -> str`` backed by **local Gemma via Ollama**.

    The project runs entirely on a local model (no paid API). Requires Ollama
    serving at ``host`` with ``model`` pulled (``ollama list``). ``requests`` is
    imported lazily so offline tests need no network. ``temperature=0`` keeps
    runs reproducible.
    """
    import requests

    def client(prompt: str) -> str:
        r = requests.post(
            f"{host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": num_predict, "temperature": temperature},
            },
            timeout=300,
        )
        r.raise_for_status()
        return r.json().get("response", "")

    return client


def pick_resolver_hit(hits: list[dict[str, Any]], query: str) -> Optional[str]:
    """Choose the best QID from wbsearchentities hits.

    Prefer a hit whose label or alias **exactly** matches the query (case-fold),
    which avoids grabbing an unrelated sense that merely ranks first (e.g. a
    "Shinto"-named item that isn't the religion). Fall back to the top hit.
    """
    if not hits:
        return None
    q = query.strip().casefold()
    for h in hits:
        if (h.get("label") or "").strip().casefold() == q:
            return h.get("id")
        if (h.get("match", {}).get("text") or "").strip().casefold() == q:
            return h.get("id")
    return hits[0].get("id")


def wikidata_resolver(getter: Optional[Callable[..., dict]] = None) -> ResolverFn:
    """Build a ``resolve(label) -> QID|None`` via Wikidata ``wbsearchentities``."""
    from o1.wikidata import USER_AGENT

    def resolve(label: str) -> Optional[str]:
        import requests

        g = getter
        if g is None:
            def g(url, params=None):  # noqa: E306
                r = requests.get(
                    url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30
                )
                r.raise_for_status()
                return r.json()
        data = g(
            "https://www.wikidata.org/w/api.php",
            {"action": "wbsearchentities", "search": label, "language": "en",
             "format": "json", "limit": "5"},
        )
        return pick_resolver_hit(data.get("search", []), label)

    return resolve
