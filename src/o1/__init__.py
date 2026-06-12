"""o1 — measuring how reliably an LLM can fill missing Wikidata statements
for Shinto shrines, and whether a self-verification pass reduces wrong values.

Package layout (src-layout; tests add ``src`` to the path via pyproject):
- ``o1.wikidata`` — sample shrine entities + statements from Wikidata SPARQL.
- ``o1.dataset``  — build held-out eval instances from sampled entities.
- ``o1.predict``  — predict-only and predict-then-verify pipelines.
- ``o1.score``    — precision/recall/abstention metrics by property + popularity.
"""

__version__ = "0.0.1"
