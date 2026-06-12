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
cd o1
claude
```

Then work `queue.md` top to bottom. The bootstrap sequence pins down the
research question with you, runs the literature review, plans the experiments,
takes the repo public, and keeps the report current as results land.

## Published report

Once the repo is public with Pages set to **Source: GitHub Actions**,
`.github/workflows/pages.yml` deploys `docs/` (the report site) and builds
`docs/report.pdf`. Site-shape inspiration: http://latent-space.emmaleonhart.com/
