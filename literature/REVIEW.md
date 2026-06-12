# Literature review — LLM gap-filling for Wikidata, and whether self-verification makes it trustworthy

*Synthesized survey. Per-source notes (claim / method / contribution / citation)
are in [`sources.md`](./sources.md). This review establishes what is already
known, where the gap is, and what **o1** adds.*

## The question this grounds

> How reliably can an LLM fill missing factual statements in Wikidata for a
> bounded, curated domain — Shinto shrines — and does an explicit
> self-verification pass reduce the rate of wrong / hallucinated values?

Two bodies of work bear on it: **(A)** how good LLMs are at recalling structured
facts, and **(B)** whether self-verification / self-critique converts those
recalls into trustworthy outputs.

## What is already known

**1. LLM factual recall is real but strongly uneven — and the unevenness is
predictable.** The "LLM-as-knowledge-base" line (Head-to-Tail [A1]; FACT-Bench
[A2]) establishes two first-order axes:

- **Entity popularity.** Recall is high on head entities and **collapses on the
  torso/tail**. FACT-Bench reports GPT-4 at **77% EM on the most-popular quartile
  vs 51% on the least-popular** [A2]; Head-to-Tail's headline is that 16 LLMs are
  "poor… especially for torso-to-tail entities" [A1].
- **Property type.** Recall is high for some relations and low for others —
  FACT-Bench finds **90%+ on country-type properties but ~40% on date
  properties** [A2]. Different relations are not equally learnable.

Both axes matter directly to o1: Shinto shrines are a **torso/tail-heavy**
domain, and the per-property split [A2] says the answer to "can the model fill
this gap?" will depend heavily on *which* property.

**2. Recall ≠ reliability.** Knowing a fact is not the same as being a usable
knowledge base. A reliable KB must answer accurately, **abstain on what it does
not know**, and be **consistent** across paraphrases [A3]. Models are frequently
**overconfident** [B3], and popularity predicts not just whether a model knows a
fact but whether it **knows that it knows** [A4] — boundary perception itself
degrades on the tail. So a naive "always fill the gap" policy will confidently
emit wrong values exactly where the domain is thinnest.

**3. Self-verification can help — conditionally.** Train-free self-verification
reduces hallucination when the verification step is structured so the model
**re-checks claims independently** rather than re-affirming its first answer.
Chain-of-Verification (plan verification questions → answer them independently →
revise) reports F1 gains on closed-book QA [B1]; self-evaluation alignment [B2]
and fact-level confidence-guided correction [B3] point the same way.

**4. But self-critique is not a free lunch.** Naive self-correction can *increase*
apparent hallucinations (1.55 → 2.13 in one summary study) [B4], and verifiers
suffer false negatives, surface-cue dependence, and "verifier collapse" [B4].
Calibration work shows self-reported confidence is **miscalibrated** [B3]. So the
verify-pass benefit must be *measured*, per property type, against ground truth —
not assumed.

**5. On aggregation, single-pass + verify is the sensible budget.** Expensive
N-sample majority voting (self-consistency) has **lost most of its edge** on
current models — large token cost for sub-2% gains [B5]. For a maintainer on a
token budget, a single prediction plus a verification pass is the defensible
design, which is the one o1 evaluates.

## The gap

Prior work leaves three things open at exactly the intersection o1 occupies:

1. **QA, not actionable gap-filling.** The KB-eval benchmarks [A1, A2] measure
   closed-book *QA accuracy* over generic Wikidata. A KG maintainer's real
   question is different: *of the statements an LLM proposes for known-missing
   slots, what fraction are correct (precision), and how many real gaps get
   filled (recall)?* That framing — proposed-statement precision/recall against
   held-out truth — is not what the QA benchmarks report.

2. **Self-verification is evaluated on prose, not structured KG statements.** CoVe
   and friends [B1–B3] are tested on biographies, lists, and free-text QA. Whether
   independent verification lifts precision on **structured (subject, property,
   value) prediction**, and whether that lift differs **by property type**, is not
   established.

3. **No single curated real-world domain ties the two axes together.** Nobody (in
   what we surveyed) reports, for one domain a maintainer actually cares about,
   the joint picture: precision/recall **per property type**, **with vs without a
   verify pass**, while controlling **entity popularity** — i.e. the practical
   decision table "which gaps can I trust the model to fill, and does asking it to
   double-check help?"

## What o1 adds

o1 produces exactly that decision table for **Shinto shrines** — a bounded,
well-curated, torso/tail-heavy slice of Wikidata for which ground truth already
exists (the maintainer's own data and SPARQL patterns):

- **Held-out evaluation as gap-filling.** Take shrine entities, *hold out* a known
  property value, ask the model to predict it, and score against the held-out
  truth — turning the curated KG into its own benchmark, no manual labeling.
- **Precision/recall by property type**, testing the FACT-Bench prior [A2] (e.g.
  `P17` country easy, `P571` inception date hard) on a new domain.
- **Predict-only vs predict-then-verify**, applying CoVe's independence principle
  [B1] to structured statements and **measuring** the lift per property type —
  including the honest possibility, flagged by [B4], that verification helps for
  some properties and not others.
- **Popularity as a controlled covariate** [A1, A4], so the table says *where* on
  the head→tail axis each property becomes untrustworthy.

The headline deliverable is a defensible answer to: **which Shinto-shrine
property types can an LLM safely auto-suggest, and how much does a
self-verification pass move that line?**

## Open risks the review surfaces (to carry into `todo.md`)

- **Contamination / leakage.** Wikidata and Wikipedia are in pretraining, so the
  model may "recall" the held-out value from training rather than infer it. This
  inflates apparent precision and must be acknowledged — popularity stratification
  [A1, A4] partly probes it (tail = less likely memorized).
- **Ground-truth incompleteness.** A model answer scored "wrong" may be a *correct
  fact Wikidata is missing*, not a hallucination — the precision metric is a lower
  bound. Spot-checking against sources is needed for the headline claim.
- **Verifier miscalibration** [B3] and **self-correction backfire** [B4] mean the
  verify pass must be evaluated, never assumed beneficial.
