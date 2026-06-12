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

1. **Audit + fix the entity-QID resolution artifact.** The first run shows
   `P131` precision 0.00 and depressed `P140` — likely a measurement artifact:
   a plausible place/label resolves via `wbsearchentities` to a *different* QID
   than the one Wikidata records, scored as wrong. Write a small audit
   (`scripts/audit_resolution.py` or a stage) over the **saved** `results/`
   predictions: for each entity-property miss, show raw answer → resolved QID →
   true QID(s) + their labels. Then make scoring fairer — e.g. resolve the true
   QID's label and **also credit a normalized label match**, or report a
   `raw-label precision` column alongside the QID precision. Offline (reuses saved
   results); add tests for the new scoring path. Commit.

2. **Scale the run + popularity gradient (H2).** Re-run with a larger bounded
   sample (e.g. `O1_PER_PROP=20`) that **includes torso/tail** instances for the
   four tail-covered properties (`P17`/`P31`/`P131`/`P625`), and report
   precision/recall **by popularity bucket** for those (the `by_property_bucket`
   data is already computed — surface it in `FINDINGS.md` + `docs/`). Local Gemma,
   no API cost; budget the wall-clock. Commit refreshed `FINDINGS.md` + `docs/`.

3. **Figures.** Generate simple precision/recall-by-property and verify-lift
   plots (matplotlib) into `docs/` (e.g. `docs/fig_precision.png`) and embed them
   in the report site. Commit.

When this section drains, refill from `todo.md` item 5 (honesty controls:
contamination probe + ground-truth-incompleteness spot-check), then the final
report polish.

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
