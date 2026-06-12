# o1 — Long-horizon plan (todo)

**This file is the project's *abstract* horizon, not a step list.** Each item is
a destination. When work begins, an item is pulled here, decomposed into concrete
ordered steps in `queue.md`, mirrored to the task tool, and executed. As
`queue.md` drains, refill it from the next item here. Done work does **not** stay
here — it flows to `devlog.md` + `git log`. See `CLAUDE.md` § "Queue and
longer-horizon work".

Grounded in `literature/REVIEW.md`. The headline deliverable: a **decision table**
that says which Shinto-shrine property types an LLM can safely auto-suggest, and
how much a self-verification pass moves that line.

---

## Hypotheses to test (the spine of the study)

- **H1 — Property type dominates.** Precision of LLM-proposed statements varies
  sharply by property type; relational/categorical properties (country `P17`,
  administrative location `P131`, religion `P140`, instance-of `P31`) land high,
  while specific-value properties (inception date `P571`, coordinates `P625`,
  named founder/deity) land low. *(Prior: FACT-Bench country ~90% vs date ~40%.)*
- **H2 — Popularity gradient.** For a fixed property, precision degrades from head
  to tail shrines (by sitelinks / statement count as a popularity proxy).
  *(Prior: Head-to-Tail; knowledge-boundary perception degrades on the tail.)*
- **H3 — Verification lifts precision, unevenly.** A predict-then-verify pass
  (CoVe-style independent re-check) raises precision versus predict-only, at some
  recall cost — but the lift is property-type-dependent and may be **null or
  negative** for some properties. *(Prior: CoVe helps; naive self-correction can
  backfire.)*
- **H4 — Confidence thresholding is useful despite miscalibration.** Self-reported
  per-statement confidence is miscalibrated (over-confident), yet thresholding on
  it still improves the precision/recall trade-off and yields a usable
  auto-suggest cutoff. *(Prior: fact-level calibration / ConFact.)*

## Things to build / experiments to run (abstract destinations)

1. **The evaluation dataset (held-out gap-filling from a curated KG).** A
   reproducible builder that samples Shinto-shrine entities from Wikidata via
   SPARQL, captures each entity's context (label, description, other statements),
   and for each target property *holds out* the true value as ground truth.
   Stratify by property type and by a popularity proxy. This turns the curated KG
   into a self-labeling benchmark.

2. **The prediction pipeline (single-pass baseline).** Given an entity's context
   minus the held-out property, prompt the model to either propose a value (with a
   normalized/QID-resolvable form) **or abstain**. Per-property prompt templates.
   This is the predict-only condition.

3. **The verification pipeline (predict-then-verify + confidence).** Wrap the
   prediction in a CoVe-style pass: generate verification questions, answer them
   independently, and emit a revised value + a per-statement confidence. This is
   the predict+verify condition.

4. **Scoring & analysis.** Match proposed values to held-out truth (with
   QID/string/date normalization), compute **precision, recall, and abstention
   rate per property type** for both conditions, stratified by popularity. Produce
   the verify-pass lift table and confidence-threshold precision/recall curves.

5. **Honesty controls.** Probe the two review-flagged risks: **contamination**
   (does precision track popularity in a way that smells of memorization?) and
   **ground-truth incompleteness** (spot-check a sample of "wrong" answers against
   sources — some are correct facts Wikidata lacks, making precision a lower
   bound). Report both explicitly rather than papering over them.

## The eventual report (shape of the deliverable)

- **`FINDINGS.md`** — question, method, the decision table (per-property
  precision/recall, predict-only vs predict+verify, popularity-stratified),
  confidence-threshold curves, the honesty controls, limitations, and a plain
  answer to the research question.
- **`docs/` site + `report.pdf`** — the themed published report: lede, the
  decision table as the centerpiece figure, and the headline ("which shrine
  properties are safe to auto-suggest, and what verification buys you").
- **Reproducibility** — `scripts/run.py` reproduces dataset → predictions →
  scoring → figures; results land in `results/`; tests cover the scoring and
  normalization logic.

## Stretch / later horizons

- Generalize beyond Shinto shrines to a second curated domain to test whether the
  per-property pattern transfers.
- Compare model tiers (Haiku vs Sonnet vs Opus) on the precision/cost frontier.
- A small "maintainer-facing" export: for each high-precision property, the list
  of concrete proposed statements (as QuickStatements) a human could review —
  connecting the study back to the user's existing Wikidata workflow.
