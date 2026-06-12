# o1

> A **research project** scaffolded with
> [cleanvibe](https://github.com/Immanuelle/cleanvibe) `research`.

**Research question:** *How reliably can a large language model fill in missing
factual statements in Wikidata for a bounded, curated domain — Shinto shrines —
and does an explicit self-verification pass meaningfully reduce the rate of
wrong / hallucinated values?* Concretely: hold out a known property value for a
sampled shrine entity, prompt the model to predict it, and measure precision /
recall **by property type**, comparing a single predict pass against
predict-then-self-verify. A successful outcome is a precision/recall table that
says **which property types are safe to auto-suggest** and **how much a
verification pass lifts precision**.

## About

This is an original research project (not a replication). It poses a question,
surveys the prior literature, runs experiments / builds something to answer it,
and publishes the findings as a themed GitHub Pages report + a transportable PDF.

The distinctive first move is a **literature review** (agentic RAG) *before* any
building — see `literature/`.

## How it's organized

- `literature/` — the literature review (sources + `REVIEW.md`), built first.
- `data_lake/` — datasets and supplied material.
- `src/` — the research code; `scripts/run.py` — the run entry point.
- `results/` — run outputs (gitignored). `FINDINGS.md` — the write-up.
- `docs/` — the published GitHub Pages report site (themed) + built PDF.
- `queue.md` / `todo.md` / `devlog.md` — the cleanvibe work loop.

## Getting started

```
pip install -r requirements.txt
pytest -q                 # run the test suite
python scripts/run.py all # pipeline entry point (stages wired up in R2-R6)
```

The LLM backend is **local Gemma (`gemma3:12b`) via Ollama** (`localhost:11434`)
— no paid API. `predict`/`verify` stages call it; `sample`/`build`/`score` are
offline.

**Findings** (bounded, popularity-stratified run, n=92): predict-only Gemma is
reliable on categorical facts (country 0.94, instance-of 0.83 — both → 1.00 under
granularity-aware scoring; 62% of admin-location answers are right at a coarser
level), abstains appropriately on hard specifics (all coordinates, 86% of dates),
a self-verification pass *lowered* precision (0.58→0.55), and there was *no*
popularity gradient for the near-constant properties. See [`FINDINGS.md`](FINDINGS.md)
and the [report site](https://emmaleonhart.github.io/llm-wikidata-gapfilling-shrines/).

The research question is set and the literature review is in `literature/`.
Active experiment steps live in `queue.md`; longer-horizon goals in `todo.md`.

## Published report

Once the repo is public with Pages set to **Source: GitHub Actions**,
`.github/workflows/pages.yml` deploys `docs/` (the report site) and builds
`docs/report.pdf`. Site-shape inspiration: http://latent-space.emmaleonhart.com/
