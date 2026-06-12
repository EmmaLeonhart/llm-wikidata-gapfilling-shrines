# Findings — LLM Wikidata gap-filling for Shinto shrines

> **Model:** local Gemma (`gemma3:12b`) via Ollama, temperature 0. No paid API.

## Question

How reliably can a local LLM fill missing Wikidata statements for Shinto shrines, and does a self-verification pass reduce wrong / hallucinated values? Held-out single-property prediction; precision / recall by property type; predict-only vs predict-then-verify.

## Method

- Eval set: held-out statements from a stratified sample of Shinto shrines (Wikidata). This run scored **92 instances** (bounded sample, ~13 per property across 7 properties).
- Predict-only: model proposes a value or abstains; entity answers resolved to QIDs via `wbsearchentities`.
- Predict-then-verify: Chain-of-Verification-style independent re-check (KEEP / REVISE / WITHDRAW).
- precision = correct / answered · recall = correct / total · abstain = abstained / total. Coordinates matched within 0.05°; dates by year; entities by QID (resolver-miss counts as wrong).

## Headline

On **92 held-out statements**, predict-only Gemma reached **precision 0.58 / recall 0.39** overall (abstaining on 0.33 of gaps). A self-verification pass **lowered** overall precision (0.58 → 0.55) — consistent with the literature's warning that naive self-correction can backfire.

## Conclusions — which shrine properties can a local LLM safely auto-suggest?

Granularity-aware precision is the relevant number for a maintainer (crediting a correct coarser answer). Verdicts from the n=92 run:

| property | granularity-aware precision | verdict |
|---|---|---|
| country (`P17`) | 0.94 | **SAFE** — auto-suggest |
| instance of (`P31`) | 1.00 | **SAFE** — auto-suggest (general type) |
| religion (`P140`) | 1.00 | **SAFE** — auto-suggest "Shinto"; not a specific sect |
| admin location (`P131`) | 0.62 | **PARTIAL** — prefecture-level only; human-verify the city/ward |
| inception (`P571`) | 1.00 prec / 0.14 recall | **RARE** — trust its few confident dates; expect little coverage |
| heritage (`P1435`) | 0.00 | **NO** — genuine failure |
| coordinates (`P625`) | — (100% abstain) | **NO** — the model declines |

**Answering the question:** a local LLM (Gemma `gemma3:12b`) is a useful gap-filler for **categorical / near-constant** shrine facts when credited at the right granularity, and it **appropriately abstains** on specific values (dates, coordinates) rather than hallucinating — so its *errors* are rare, but so is its *coverage* of the hard fields. Three takeaways:

1. **Self-verification did not help — it hurt** (precision 0.58→0.55 at n=92, replicating the n=42 result). Do not add a naive verify pass.
2. **Popularity didn't matter and there is no memorization signal** (flat/again-better on the no-Wikipedia tail) — the model leans on structural priors ("a shrine is in Japan, is Shinto, sits in *some* region"), not entity-specific recall.
3. **Granularity is the real story for entity properties**: strict exact-QID scoring badly understates a model that is reliably right at a coarser level.

*Scope: one curated domain, a 12B local model, n=92 — indicative, not a settled benchmark. The pipeline (`scripts/run.py`) reproduces every number.*

## Predict-only — by property

| property | n | precision | recall | abstain |
|---|---|---|---|---|
| located in admin territorial entity (`P131`) | 18 | 0.00 | 0.00 | 0.11 |
| religion or worldview (`P140`) | 6 | 0.50 | 0.50 | 0.00 |
| heritage designation (`P1435`) | 7 | 0.00 | 0.00 | 0.57 |
| country (`P17`) | 18 | 0.94 | 0.94 | 0.00 |
| instance of (`P31`) | 18 | 0.83 | 0.83 | 0.00 |
| inception (`P571`) | 7 | 1.00 | 0.14 | 0.86 |
| coordinate location (`P625`) | 18 | — | 0.00 | 1.00 |
| **overall** | 92 | 0.58 | 0.39 | 0.33 |

## Entity properties — strict vs hierarchy-lenient

Strict scoring needs the *exact* QID. Hierarchy-lenient also credits an answer that is an ancestor/descendant of the recorded entity (e.g. the model gives the prefecture when Wikidata records the city). The gap is the share of answers that are **right at a different granularity**.

| property | strict precision | lenient precision | strict recall | lenient recall |
|---|---|---|---|---|
| located in admin territorial entity (`P131`) | 0.00 | 0.62 | 0.00 | 0.56 |
| religion or worldview (`P140`) | 0.50 | 1.00 | 0.50 | 1.00 |
| instance of (`P31`) | 0.83 | 1.00 | 0.83 | 1.00 |
| country (`P17`) | 0.94 | 0.94 | 0.94 | 0.94 |
| heritage designation (`P1435`) | 0.00 | 0.00 | 0.00 | 0.00 |

## Predict-then-verify — by property

| property | n | precision | recall | abstain |
|---|---|---|---|---|
| located in admin territorial entity (`P131`) | 18 | 0.00 | 0.00 | 0.11 |
| religion or worldview (`P140`) | 6 | 0.33 | 0.33 | 0.00 |
| heritage designation (`P1435`) | 7 | 0.00 | 0.00 | 0.57 |
| country (`P17`) | 18 | 0.94 | 0.94 | 0.00 |
| instance of (`P31`) | 18 | 0.78 | 0.78 | 0.00 |
| inception (`P571`) | 7 | 1.00 | 0.14 | 0.86 |
| coordinate location (`P625`) | 18 | — | 0.00 | 1.00 |
| **overall** | 92 | 0.55 | 0.37 | 0.33 |

## Verify lift (overall)

| condition | precision | recall | abstain |
|---|---|---|---|
| predict-only | 0.58 | 0.39 | 0.33 |
| predict+verify | 0.55 | 0.37 | 0.33 |

## Popularity gradient (H2) — predict-only precision by bucket

Only the four properties whose ground truth reaches the tail. head = ≥6 sitelinks · torso = 1–5 · tail = 0. Cells show precision (n).

| property | head | torso | tail |
|---|---|---|---|
| country (`P17`) | 0.83 (6) | 1.00 (6) | 1.00 (6) |
| instance of (`P31`) | 0.83 (6) | 0.67 (6) | 1.00 (6) |
| located in admin territorial entity (`P131`) | 0.00 (6) | 0.00 (6) | 0.00 (6) |
| coordinate location (`P625`) | — (6) | — (6) | — (6) |

## Honesty controls

Two probes on the review-flagged risks (from the n=92 predict-only run).

**Contamination (memorization).** If the model were reciting Wikipedia-derived facts, accuracy should collapse on shrines with **no** Wikipedia article. It does the opposite: strict correctness was **0.71 on the no-Wikipedia tail** (sitelinks=0) vs **0.53 on has-Wikipedia** entities. The per-property gradient (above) shows the same — no head→tail decay. *Caveat:* the raw tail-vs-head split is confounded by property mix (the tail sample is all categorical properties), so the per-property gradient is the cleaner evidence. Either way, **no memorization signal** for these near-constant properties.

**Ground-truth incompleteness.** Spot-checked 5 `P131` answers scored *wrong* against the live Wikidata labels: **4/5 were a granularity mismatch** (model gave the prefecture — Kumamoto, Saitama, Tokyo, Akita — where Wikidata records a ward/city: Chūō-ku, Ōmiya-ku, Ueno-kōen, Yurihonjo), **1/5 a genuine error** (said *Kanagawa*; the shrine is in Kasukabe, *Saitama*), and **0/5 a Wikidata gap** (every recorded value was a legitimate, more-specific entity). So the strict `P131`≈0 is mostly granularity, not hallucination — and precision is **not** materially a lower bound from Wikidata incompleteness here (the lower-bound risk is real in principle but did not bite in this sample).

## Limitations (carried from the design)

- **Entity-property scores conflate model error with QID-resolution error.** Answers for entity properties (`P17`/`P131`/`P140`/`P31`/`P1435`) are mapped to a QID via `wbsearchentities`; a reasonable label (e.g. a city or ward) can resolve to a *different* QID than the specific one Wikidata records, counting as wrong. The very low `P131` precision is likely partly this, not pure hallucination — a follow-up should audit raw answers vs. resolved QIDs.
- **Tail shrines are statement-sparse**, so the popularity gradient is only measurable for `P17`/`P31`/`P131`/`P625`; date/heritage/religion get head-bucket coverage only.
- **Contamination:** Wikidata/Wikipedia are in pretraining, so high precision on popular entities may reflect memorization, not inference.
- **Ground-truth incompleteness:** a 'wrong' answer may be a correct fact Wikidata lacks, so precision is a lower bound.
- This is a **bounded sample**; numbers are indicative, not final.
