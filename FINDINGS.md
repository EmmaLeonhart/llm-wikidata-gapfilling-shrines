# Findings — LLM Wikidata gap-filling for Shinto shrines

> **Model:** local Gemma (`gemma3:12b`) via Ollama, temperature 0. No paid API.

## Question

How reliably can a local LLM fill missing Wikidata statements for Shinto shrines, and does a self-verification pass reduce wrong / hallucinated values? Held-out single-property prediction; precision / recall by property type; predict-only vs predict-then-verify.

## Method

- Eval set: held-out statements from a stratified sample of Shinto shrines (Wikidata). This run scored **42 instances** (bounded sample, ~6 per property across 7 properties).
- Predict-only: model proposes a value or abstains; entity answers resolved to QIDs via `wbsearchentities`.
- Predict-then-verify: Chain-of-Verification-style independent re-check (KEEP / REVISE / WITHDRAW).
- precision = correct / answered · recall = correct / total · abstain = abstained / total. Coordinates matched within 0.05°; dates by year; entities by QID (resolver-miss counts as wrong).

## Headline

On **42 held-out statements**, predict-only Gemma reached **precision 0.50 / recall 0.33** overall (abstaining on 0.33 of gaps). A self-verification pass **lowered** overall precision (0.50 → 0.43) — consistent with the literature's warning that naive self-correction can backfire.

## Predict-only — by property

| property | n | precision | recall | abstain |
|---|---|---|---|---|
| located in admin territorial entity (`P131`) | 6 | 0.00 | 0.00 | 0.00 |
| religion or worldview (`P140`) | 6 | 0.50 | 0.50 | 0.00 |
| heritage designation (`P1435`) | 6 | 0.00 | 0.00 | 0.50 |
| country (`P17`) | 6 | 1.00 | 1.00 | 0.00 |
| instance of (`P31`) | 6 | 0.67 | 0.67 | 0.00 |
| inception (`P571`) | 6 | 1.00 | 0.17 | 0.83 |
| coordinate location (`P625`) | 6 | — | 0.00 | 1.00 |
| **overall** | 42 | 0.50 | 0.33 | 0.33 |

## Entity properties — strict vs hierarchy-lenient

Strict scoring needs the *exact* QID. Hierarchy-lenient also credits an answer that is an ancestor/descendant of the recorded entity (e.g. the model gives the prefecture when Wikidata records the city). The gap is the share of answers that are **right at a different granularity**.

| property | strict precision | lenient precision | strict recall | lenient recall |
|---|---|---|---|---|
| located in admin territorial entity (`P131`) | 0.00 | 0.33 | 0.00 | 0.33 |
| religion or worldview (`P140`) | 0.50 | 1.00 | 0.50 | 1.00 |
| instance of (`P31`) | 0.67 | 1.00 | 0.67 | 1.00 |
| country (`P17`) | 1.00 | 1.00 | 1.00 | 1.00 |
| heritage designation (`P1435`) | 0.00 | 0.00 | 0.00 | 0.00 |

## Predict-then-verify — by property

| property | n | precision | recall | abstain |
|---|---|---|---|---|
| located in admin territorial entity (`P131`) | 6 | 0.00 | 0.00 | 0.00 |
| religion or worldview (`P140`) | 6 | 0.33 | 0.33 | 0.00 |
| heritage designation (`P1435`) | 6 | 0.00 | 0.00 | 0.50 |
| country (`P17`) | 6 | 1.00 | 1.00 | 0.00 |
| instance of (`P31`) | 6 | 0.67 | 0.67 | 0.00 |
| inception (`P571`) | 6 | 0.00 | 0.00 | 0.83 |
| coordinate location (`P625`) | 6 | — | 0.00 | 1.00 |
| **overall** | 42 | 0.43 | 0.29 | 0.33 |

## Verify lift (overall)

| condition | precision | recall | abstain |
|---|---|---|---|
| predict-only | 0.50 | 0.33 | 0.33 |
| predict+verify | 0.43 | 0.29 | 0.33 |

## Limitations (carried from the design)

- **Entity-property scores conflate model error with QID-resolution error.** Answers for entity properties (`P17`/`P131`/`P140`/`P31`/`P1435`) are mapped to a QID via `wbsearchentities`; a reasonable label (e.g. a city or ward) can resolve to a *different* QID than the specific one Wikidata records, counting as wrong. The very low `P131` precision is likely partly this, not pure hallucination — a follow-up should audit raw answers vs. resolved QIDs.
- **Tail shrines are statement-sparse**, so the popularity gradient is only measurable for `P17`/`P31`/`P131`/`P625`; date/heritage/religion get head-bucket coverage only.
- **Contamination:** Wikidata/Wikipedia are in pretraining, so high precision on popular entities may reflect memorization, not inference.
- **Ground-truth incompleteness:** a 'wrong' answer may be a correct fact Wikidata lacks, so precision is a lower bound.
- This is a **bounded sample**; numbers are indicative, not final.
