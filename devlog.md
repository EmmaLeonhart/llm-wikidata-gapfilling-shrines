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
README quickstart. **3 tests pass locally**; CI green (run 27394622997).

## 2026-06-11 — R2: Wikidata SPARQL shrine sampler

`src/o1/wikidata.py` — split into **pure parsers** (`parse_shrine_bindings`,
`extract_snak_value`, `extract_claim_values`, `parse_entity`) and **thin
network wrappers** (`run_sparql`, `fetch_entity_json`) with an injectable
`getter` so the orchestrator `sample_shrines` runs offline in tests.
`tests/test_wikidata.py` adds 5 tests (mock SPARQL + mock entity payload,
incl. a fake-getter end-to-end run). **8 tests pass locally.**

Ran a live sample of **60 shrines** → `data_lake/shrines_raw.json` (93 KB,
committed). Target-property coverage: P17 60/60, P131 60/60, P31 60/60,
P625 60/60, P571 47/60, P1435 51/60, P140 32/60. **Known limitation (carried
to R3):** `sample_shrines` orders by sitelinks DESC, so this sample is
head-only (20–68 sitelinks); the popularity gradient (H2) needs torso/tail
sampling, noted in the R3 queue item.

## 2026-06-11 — R3: target-property set + held-out eval builder

Measured the full population: **30,913** Shinto shrines; sitelink
distribution tail (0) ~76% / torso (1–5) ~23% / head (6+) ~0.7%. Set
popularity buckets head≥6 / torso 1–5 / tail 0 and added stratified
sampling to `wikidata.py` (`parse_popularity_rows`, `stratified_sample`
[deterministic, no RNG], `sample_shrines_stratified`). Built
`src/o1/dataset.py` (`build_eval_set`, `instance_context`,
`bucket_summary`). Fixed the 7-property target set and documented it +
buckets in `CLAUDE.md`.

Built the real eval set: **120 entities (40/bucket, seed=0) → 505 held-out
instances**, saved to `data_lake/shrines_stratified.json` +
`data_lake/eval_set.json`. Added `tests/test_dataset.py` (10 tests:
holdout removal, bucket assignment, deterministic stratified sample, etc.)
— **16 tests pass.**

**Finding already surfaced:** tail shrines are statement-sparse — only
`P31`/`P17`/`P131`/`P625` reach the tail; `P571`/`P1435`/`P140` are
head-concentrated. So **H2 (popularity gradient) is only measurable for
country / instance-of / admin-location / coordinates**; date/heritage/
religion get head-bucket precision only. Logged as a limitation in
`CLAUDE.md` to carry into `FINDINGS.md`.

## 2026-06-11 — R4: predict-only pipeline

`src/o1/predict.py` — per-property prompt builder (`build_prompt`),
response parser (`parse_response`: ANSWER:/ABSTAIN, lenient fallback),
typed normalizer (`normalize_answer`: year for P571, lat/lon for P625,
label→QID via injected resolver for the 5 entity properties), and the
pipeline (`predict_instance`, `predict_all`). Both the model **client** and
the QID **resolver** are injected callables, so tests run fully offline.
Real backends (`make_anthropic_client`, `wikidata_resolver`) are lazy and
only built at run time (R6). An unparseable typed answer becomes an abstain
but **keeps `raw_answer` for audit** — never silently dropped. Added
`tests/test_predict.py` (10 tests). **26 tests pass.**

## 2026-06-11 — R5: scoring + metrics

`src/o1/score.py` — type-aware matching: entities by QID (`match_entity`;
resolver-None counts as *wrong*, a documented precision-lowering choice),
dates by extracted year (`extract_year` handles Wikidata `+1879-..`, bare
years, and BCE negatives), coordinates within a 0.05° tolerance
(`match_coordinate`), strings by normalized equality. `classify` →
correct/wrong/abstain; `score` aggregates **precision (correct/answered),
recall (correct/total), abstain_rate** overall, by property, and by
property×popularity-bucket; `to_markdown` renders the by-property table.
Added `tests/test_score.py` (9 tests). **35 tests pass.** Offline wiring
check on the real `eval_set.json` (dummy all-abstain client): 505/505
predictions joined, 0 unmatched, all 7 properties + 3 buckets group
correctly — confirms the join before any live run.
