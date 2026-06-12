# o1 — Work Queue (research)

**This file is a queue of *concrete, executable steps*, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `devlog.md` (a dated entry) and `git log`; longer-horizon, *abstract* work lives in `todo.md` and gets decomposed into items here when it's ready to execute. **When an item is done, delete it from this file AND append a dated entry to `devlog.md` in the same commit, then push.** Do not add checkmarks, "done" markers, or status indicators in place. If an item is still here, it is not done.

**This is a `cleanvibe research` project** — your own investigation, not a replication. Its distinctive move is an up-front **literature review** (agentic RAG) before any building, and a published, themed GitHub Pages **report** under `docs/`.

**Why this file exists:** when a planning step produces a plan, that plan is written here BEFORE execution starts, so an interrupted session can pick up from the queue rather than from chat context that may be gone.

See `CLAUDE.md` § "Workflow Rules" and § "Research workflow" for how this file, planning mode, and the task tool stay in sync.

**Three-cron playbook.** Research IS extensive work, so it runs under three local `CronCreate` jobs — **work-loop at :03** (the engine that drains `queue.md` and refills it from `todo.md`), **auto-flush at :15** (commit/push backstop), and **status-report at :42** (heartbeat). On a fresh session they are **started** as the opening step (bootstrap step 1 below); on a mid-session **large-scale re-fill** of this queue the FIRST item worked is instead to **kill** the already-running crons. Either way the **last two items are always pinned at the tail** (see `## Always last`). Entering planning mode also disables the crons; their restart lives at the end of the queue. (See `CLAUDE.md` § "Autonomous productivity loop — the three-cron playbook".)

---

## Active — Build the measurement spine (todo items 1, 2, 4)

Concrete, ordered steps decomposed from `todo.md`: the **evaluation dataset**,
the **predict-only baseline**, and **scoring** — the spine that produces the
first real precision/recall numbers. The verify pipeline (todo 3), full
stratified analysis/figures, honesty controls (todo 5), and report polish are
**later refills** — pull them from `todo.md` as this section drains.

**Cron status:** the three crons are **already running** (started at bootstrap
step 1 of this session and never killed). This is a continuation, not a
planning-burst re-fill, so there is no kill/start front item — the pinned
`## Always last` tail just *ensures* they are still up. Work top to bottom;
**delete each item in the same commit that completes it + append a dated
`devlog.md` entry**, push, let CI run.

1. **Project skeleton + test/CI harness.** Create the `src/o1/` package
   (`__init__.py`), a `scripts/run.py` entry stub, `requirements.txt` (`requests`,
   `anthropic`, `pytest`), a `tests/` dir with one trivial passing test, and
   `.github/workflows/ci.yml` running `pytest` on push/PR. Update the README
   quickstart. Commit, push, **confirm CI (ci.yml) goes green** before moving on.

2. **Wikidata SPARQL sampler.** `src/o1/wikidata.py`: query Shinto-shrine entities
   (`P31` → Shinto shrine `Q845945` and relevant subtypes) via the public SPARQL
   endpoint, returning label, description, **sitelink count (popularity proxy)**,
   and each entity's statements for the candidate target properties. Unit-test the
   result-parsing / normalization on a saved mock JSON payload (no live call in
   tests). Save a raw sample to `data_lake/shrines_raw.json`. Commit.

3. **Target-property set + held-out eval builder.** Fix the target property list
   (candidates: `P17` country, `P131` admin location, `P140` religion, `P31`
   instance-of, `P571` inception, `P625` coordinates, and an enshrined-deity link
   if reliably present) and **document it in `CLAUDE.md`**. `src/o1/dataset.py`:
   from the raw shrines, build eval instances = *(entity context with the target
   property held out, the true held-out value)*, stratified by property type and
   popularity bucket. Save `data_lake/eval_set.json`. Tests cover the holdout +
   stratification logic. Commit.

4. **Predict-only pipeline.** `src/o1/predict.py`: given an instance's context,
   prompt Claude to **propose a value or explicitly abstain**, with per-property
   templates; parse + normalize the answer (QID resolution / date / coordinate /
   string forms). **Inject the model client** so parsing/normalization is unit-
   tested with a fake client — no live API calls in tests. Commit.

5. **Scoring + metrics.** `src/o1/score.py`: match predicted vs held-out value
   (QID / date / coordinate / fuzzy-label normalization), compute **precision,
   recall, and abstention rate per property type and per popularity bucket**.
   Tests on hand-built cases (exact match, near-miss, abstain). Commit.

6. **First end-to-end predict-only run.** Wire `scripts/run.py` to: load
   `eval_set` → run predict-only over a modest sample → score → write
   `results/predict_only.json` + a compact markdown table. **Needs
   `ANTHROPIC_API_KEY`** — if it is not set in the environment, this is a
   **documented blocker**: record it in `devlog.md` and STOP at this item (do
   **not** fabricate numbers — hard rail). If it is set, run on a bounded sample,
   record the real per-property table, and seed `FINDINGS.md` (question + method +
   the predict-only table). Commit results + `FINDINGS.md`.

When this section drains, refill from `todo.md` item 3 (verify pipeline) next.

---

## Always last — restart the three crons and summarize

**These two items stay pinned to the tail of the queue at all times** — below every bootstrap step and below every real work item. They are the closing half of the three-cron lifecycle in `CLAUDE.md` § "Autonomous productivity loop":

A. **Ensure the three crons are running** — start them if this session never did, restart them if a planning burst / queue re-fill killed them: work-loop (`3 * * * *`), auto-flush (`15 * * * *`), status-report (`42 * * * *`).
B. **Run the status-report action once more, independently** — an end-of-session summary of everything that happened this session.

---

## Pointers

- Long-horizon backlog (abstract goals, source of future queue items): `todo.md`.
- The literature review (the project's evidentiary base): `literature/REVIEW.md`.
- Completed work (chronological, with milestones): `devlog.md`.
- Narrative history: `git log`.
