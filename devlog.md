# o1 — Devlog

**This file is where "done" lives.** `queue.md` is delete-only: when a queue
item is finished, the item is **deleted from `queue.md`** and a dated entry
is **appended here**, in the same commit as the work, then pushed. Never
tick a box in place — a checked box left in `queue.md` is the failure mode
this file exists to prevent.

Also record releases (tag + a one-line note), notable milestones, and
anything else worth a chronological trail. Newest entries at the bottom.

This is the **same convention as the cleanvibe repo's own `devlog.md`** —
every cleanvibe-scaffolded project gets one for the same reason.

See `CLAUDE.md` § "Workflow Rules" and `queue.md`'s preamble.

---

## 2026-06-11 — Project scaffolded

Scaffolded with `cleanvibe research` (cleanvibe v1.13.1). Future entries
land here as queue items get deleted.

## 2026-06-11 — Bootstrap 1: three-cron playbook started

Started the three session-local crons (`durable: false`, 7-day expiry):
work-loop `3 * * * *` (job f95ee40c), auto-flush `15 * * * *` (job
2e097cb4), status-report `42 * * * *` (job 2d3ecded). The autonomous
hourly cadence is now live for this session.

## 2026-06-11 — Bootstrap 2: data_lake triage (no-op)

No user-supplied files were dropped in — `data_lake/` holds only its
`.gitkeep`. Nothing to triage; queue item deleted.

## 2026-06-11 — Bootstrap 3: research question defined

The user had no files and was open on topic, so the question was arrived
at by proposing grounded options from a quick literature scan. Chosen:

> **How reliably can an LLM fill missing factual statements in Wikidata for
> a bounded, curated domain — Shinto shrines — and does an explicit
> self-verification pass reduce the rate of wrong / hallucinated values?**

Evaluation: hold out a known property value, prompt the model to predict
it, measure precision/recall by property type, predict-only vs
predict-then-verify. Scope, constraints, and success criteria written into
`README.md`, `CLAUDE.md` (`> Research question` block), and
`docs/index.html` (lede + question block + pillar 1). The topic fits the
user's existing Wikidata/Shinto tooling, which supplies ground truth.

## 2026-06-11 — Bootstrap 4: literature review

Surveyed prior work across two themes — (A) LLMs as knowledge bases and
(B) self-verification for factuality — via web search + WebFetch. Wrote
`literature/sources.md` (10 annotated sources, claim/method/contribution/
citation each) and synthesized `literature/REVIEW.md`. Key grounded
findings carried in: LLM recall collapses on torso/tail entities
(Head-to-Tail) and varies sharply by property type — countries ~90% vs
dates ~40% on Wikidata-derived FACT-Bench; recall ≠ reliability (models
overconfident, abstention matters); Chain-of-Verification's independent
re-checking reduces hallucination but naive self-correction can *backfire*
(1.55→2.13). **The gap o1 fills:** prior work measures generic closed-book
QA, not actionable per-property precision/recall of proposed statements
for one curated domain, with vs without a verify pass. Reflected the
one-line summary into `docs/index.html` pillar 2. literature/ committed as
its own reviewable artifact.

## 2026-06-11 — Bootstrap 5: todo.md long-horizon plan

Wrote `todo.md` from the literature gap: four hypotheses (H1 property type
dominates, H2 popularity gradient, H3 verification lifts precision
unevenly, H4 confidence thresholding useful despite miscalibration), five
build/experiment destinations (eval dataset → prediction pipeline →
verification pipeline → scoring/analysis → honesty controls for
contamination + ground-truth incompleteness), the report shape, and
stretch horizons. Committed on its own.

## 2026-06-11 — Bootstrap 6: went live (public repo)

Created the PUBLIC GitHub repo
**EmmaLeonhart/llm-wikidata-gapfilling-shrines** (descriptive name per
user; local folder stays `o1`) and pushed `main`. The `pages.yml` workflow
auto-enables Pages and deploys `docs/` + builds `report.pdf` from
`FINDINGS.md` once it exists. From here every commit pushes and CI/Pages
build. Repo: <https://github.com/EmmaLeonhart/llm-wikidata-gapfilling-shrines>

## 2026-06-11 — Bootstrap complete: real research queue installed

Replaced the bootstrap `## Active` section with the real research queue —
six concrete steps (R1 skeleton+CI, R2 Wikidata sampler, R3 held-out eval
builder, R4 predict-only pipeline, R5 scoring, R6 first end-to-end run)
decomposed from `todo.md` items 1/2/4 (the measurement spine). Mirrored to
the task tool (tasks #6–#11). The `## Always last` cron/summary tail stays
pinned. Crons were already running from bootstrap step 1, so no kill/start
front item. Bootstrap is done; the project now executes real experiment
work. Noted main risk: R6 needs `ANTHROPIC_API_KEY` — a documented blocker
if unset, never faked.

## 2026-06-11 — Pages workflow fixed (manual enablement needed)

The first `pages` run **failed**: `actions/configure-pages@v5` with
`enablement: true` errored *"Create Pages site failed — Resource not
accessible by integration"*. The template's claim that Pages auto-enables
with no manual step did **not** hold for a fresh repo — the workflow's
default `GITHUB_TOKEN` lacks permission to create the Pages site. Fixed by
enabling Pages once via the API as the authenticated user:
`gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow`, then
re-running. CI is now green; site live at
<https://emmaleonhart.github.io/llm-wikidata-gapfilling-shrines/> (HTTP
200). *(Worth feeding back to the cleanvibe `pages.yml` template.)*

## 2026-06-11 — R1: project skeleton + test/CI harness

Built the package skeleton: `src/o1/__init__.py` (src-layout),
`scripts/run.py` (stub entry point with stages sample/build/predict/score/
all), `requirements.txt` (requests, anthropic, pytest), `pyproject.toml`
(pytest `pythonpath=["src"]` so `import o1` works with no editable
install — sidesteps the known Documents/Github namespace-shadow quirk),
`tests/test_smoke.py` (3 tests: version + entry point runs + rejects bad
stage), and `.github/workflows/ci.yml` (pytest on push/PR). Updated the
README quickstart. **3 tests pass locally**; CI confirmed below.
