# Sources — annotated

One entry per source: **claim** (what it establishes), **method**, **what it
contributes to o1**, and **citation**. The synthesis lives in `REVIEW.md`.

Two themes structure the survey: **(A)** how well LLMs recall structured facts
(the "LLM-as-knowledge-base" line), and **(B)** whether self-verification /
self-critique makes those facts trustworthy.

---

## A. LLMs as knowledge bases — how good is the parametric recall?

### A1. Head-to-Tail: Will LLMs replace knowledge graphs?
- **Claim.** LLMs grasp head (popular) facts reasonably but are **poor on
  torso-to-tail facts**; existing LLMs are "far from perfect" as factual stores
  and cannot yet replace KGs.
- **Method.** Built **Head-to-Tail**, an 18K-QA benchmark bucketing facts into
  head / torso / tail by entity popularity; evaluated **16 public LLMs** in
  closed-book QA; proposed an automated way to score how many facts a model
  reliably knows.
- **Contributes to o1.** The central motivation: the *gaps* in a KG live
  disproportionately on torso/tail entities, which is exactly where LLM recall
  is weakest. Shinto shrines are a torso/tail-heavy domain, so this predicts
  gap-filling will be hard and **popularity must be a controlled variable**.
- **Cite.** Sun et al., "Head-to-Tail: How Knowledgeable are Large Language
  Models? A.K.A. Will LLMs Replace Knowledge Graphs?", arXiv:2308.10168 (2023).
  <https://arxiv.org/abs/2308.10168>

### A2. FACT-Bench: a holistic evaluation of LLM factual knowledge recall
- **Claim.** Recall varies **sharply by property type and by popularity**.
  GPT-4 scores **90%+ on country-type properties but ~40% on date properties**;
  **77% EM on the top-25% popular entities vs 51% on the bottom-25%** (10-shot).
  Larger models recall more; **instruction-tuning *hurts* recall**. Even GPT-4
  reaches only ~65.9% EM against a ~90% upper bound.
- **Method.** **FACT-Bench**: 20K closed-book QA built **from Wikidata triplets**
  (subject + object both appearing in the same Wikipedia article), spanning
  20 domains, **134 property types**, 3 answer types.
- **Contributes to o1.** The single most directly relevant prior work: it is
  Wikidata-derived, it breaks results out **by property type**, and it confirms
  the property-type axis is first-order. o1 narrows the lens from "all of
  Wikidata" to one curated domain and asks the *actionable* version (precision of
  proposed statements, not just QA EM). The country-vs-date split is a concrete
  prior we can test against on shrine properties (e.g. `P17` country should be
  easy; `P571` inception date hard).
- **Cite.** "Towards a Holistic Evaluation of LLMs on Factual Knowledge Recall"
  (FACT-Bench), arXiv:2404.16164 (2024). <https://arxiv.org/abs/2404.16164>

### A3. How reliable are LLMs as knowledge bases? Factuality and consistency
- **Claim.** Knowledge *volume* alone does not make a reliable KB: a usable KB
  must answer seen facts accurately, **abstain on unseen facts**, and be
  **consistent** across paraphrases. Many models fail the abstention/consistency
  bar even when raw recall looks adequate.
- **Method.** Re-frames KB evaluation around factuality + consistency metrics and
  re-measures several LLMs.
- **Contributes to o1.** Motivates measuring **precision** (and abstention), not
  just recall — a model that confidently fills a wrong shrine location is worse
  than one that declines. Directly supports the verify-pass hypothesis.
- **Cite.** "How Reliable are LLMs as Knowledge Bases? Re-thinking Factuality and
  Consistency", arXiv:2407.13578 (2024). <https://arxiv.org/abs/2407.13578>

### A4. Knowledge popularity and the model's knowledge boundary
- **Claim.** Popularity not only predicts whether a model *knows* a fact, it
  predicts whether the model **knows that it knows** — boundary perception is
  better for popular entities and degrades on the tail.
- **Method.** Studies the relationship between entity/knowledge popularity and
  the model's self-assessed knowledge boundary.
- **Contributes to o1.** Predicts that **self-verification will help more on
  popular entities and less on the tail** — i.e. the verify-pass benefit should
  interact with popularity. A hypothesis o1 can test directly.
- **Cite.** "How Knowledge Popularity Influences and Enhances LLM Knowledge
  Boundary Perception", arXiv:2505.17537 (2025).
  <https://arxiv.org/abs/2505.17537>

### A5. Exploring LLMs for knowledge graph completion
- **Claim.** Naive **zero-shot LLMs perform poorly at triple classification**
  (judging whether a (s, r, o) triple is true), even with strong models;
  structure-aware / few-shot framing helps substantially.
- **Method.** Treats KGC as text (triple → natural-language judgment / generation)
  and benchmarks zero- and few-shot LLMs.
- **Contributes to o1.** Warns that a raw "is this triple true?" prompt is a weak
  baseline; o1's predict-then-verify framing and per-property prompting are a
  response to exactly this. Sets a methodological floor.
- **Cite.** Yao et al., "Exploring Large Language Models for Knowledge Graph
  Completion", arXiv:2308.13916 (2023). <https://arxiv.org/abs/2308.13916>

---

## B. Self-verification / self-critique — does double-checking help?

### B1. Chain-of-Verification (CoVe)
- **Claim.** A **train-free** self-verification loop reduces hallucination on
  closed-book QA and list tasks (reported F1 gains, e.g. ~0.39 → ~0.48 on a
  closed-book QA setting). The key is that **verification questions are answered
  independently** of the baseline answer, breaking the circular "reaffirm my own
  error" failure.
- **Method.** Four steps: (1) baseline answer, (2) generate verification
  questions, (3) **answer them independently**, (4) synthesize a corrected final
  answer.
- **Contributes to o1.** The canonical design for o1's **verify pass**. o1's
  contribution is to apply this independence principle to **structured KG
  statement prediction** and measure the precision lift per property type.
- **Cite.** Dhuliawala et al., "Chain-of-Verification Reduces Hallucination in
  Large Language Models", arXiv:2309.11495 (2023).
  <https://arxiv.org/abs/2309.11495>

### B2. Self-Alignment for Factuality (self-evaluation)
- **Claim.** A model's own **self-evaluation signal** can be harnessed to reduce
  hallucination, improving factual accuracy without external retrieval.
- **Method.** Uses self-evaluation to align the model toward more factual outputs.
- **Contributes to o1.** Evidence that the verify-pass signal is real and not
  purely cosmetic; a second prompting strategy to compare against CoVe-style
  verification.
- **Cite.** Zhang et al., "Self-Alignment for Factuality: Mitigating
  Hallucinations in LLMs via Self-Evaluation", arXiv:2402.09267 (2024).
  <https://arxiv.org/abs/2402.09267>

### B3. Fact-Level Confidence Calibration and Self-Correction (ConFact)
- **Claim.** Confidence should be measured **per atomic fact**, not per whole
  response; LLMs are **overconfident** under naive self-evaluation prompting;
  using high-confidence facts to correct low-confidence ones helps.
- **Method.** Fact-level calibration framework + confidence-guided self-correction.
- **Contributes to o1.** Justifies (a) collecting a **per-statement confidence**
  signal during the verify pass and (b) using a confidence threshold as the
  auto-suggest cutoff — and warns that raw self-reported confidence is
  miscalibrated, so it must be measured against held-out ground truth (which o1
  has).
- **Cite.** "Fact-Level Confidence Calibration and Self-Correction" (ConFact),
  arXiv:2411.13343 (2024). <https://arxiv.org/abs/2411.13343>

### B4. The self-correction caveat — it can backfire
- **Claim.** Self-critique is **not a free lunch**: asking a model to find and
  fix false claims in its own output can *increase* the number of (claimed)
  hallucinations — in one summary setting, detected hallucinations rose from
  **1.55 → 2.13** under naive self-correction. Known failure modes include high
  false-negative rates, surface-cue dependence, and "verifier collapse."
- **Method.** Factored verification + analyses of when self-correction degrades
  rather than improves outputs.
- **Contributes to o1.** The crucial null/negative hypothesis: o1 must be able to
  report **"verification did not help (or hurt) for property type X,"** not
  assume a uniform benefit. Keeps the study honest against an over-optimistic
  prior.
- **Cite.** "Factored Verification: Detecting and Reducing Hallucination in
  Summaries of Academic Papers", arXiv:2310.10627 (2023); see also the
  self-correction-limits discussion in the factuality literature.
  <https://arxiv.org/abs/2310.10627>

### B5. Self-consistency is losing its edge (aggregation context)
- **Claim.** On 2025–26 models, **majority-voting / self-consistency gains have
  collapsed** — large token cost for sub-2% accuracy gains on problems models
  largely solve unaided; reserve it for genuinely hard cases.
- **Method.** Re-measures self-consistency scaling curves on current models.
- **Contributes to o1.** Bounds the design space: o1 uses a **single-pass +
  verify** design rather than expensive N-sample majority voting, and this is the
  evidence for why that is the sensible aggregation choice for a maintainer on a
  token budget.
- **Cite.** "Self-Consistency Is Losing Its Edge: Diminishing Returns and Rising
  Costs in Modern LLMs", arXiv:2511.00751 (2025).
  <https://arxiv.org/abs/2511.00751>
