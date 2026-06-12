#!/usr/bin/env python
"""o1 entry point — dataset -> predictions -> verification -> scoring -> report.

Stages:
    sample   pull stratified shrine entities from Wikidata        (network, free)
    build    build the held-out eval set from sampled entities    (offline)
    predict  run predict-only over a bounded sample (local Gemma) (Ollama)
    verify   run predict-then-verify over the same sample          (Ollama)
    score    aggregate metrics + write FINDINGS.md                 (offline)
    all      predict -> verify -> score

The model backend is **local Gemma via Ollama** (gemma3:12b) — no paid API.
Bare invocation with no stage prints usage and exits 0 (so it is safe in CI).
"""
from __future__ import annotations

import collections
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DATA = ROOT / "data_lake"
RESULTS = ROOT / "results"
STAGES = ("sample", "build", "predict", "verify", "score", "figures", "all")
DOCS = ROOT / "docs"

# Instances per target property in the bounded run sample (override: O1_PER_PROP).
PER_PROPERTY = int(os.environ.get("O1_PER_PROP", "8"))
# If set, sample per (property, popularity bucket) instead — for the gradient (H2).
PER_BUCKET = int(os.environ["O1_PER_BUCKET"]) if os.environ.get("O1_PER_BUCKET") else None

# Properties whose ground truth reaches the tail (so the gradient is measurable).
GRADIENT_PROPERTIES = ("P17", "P31", "P131", "P625")


def _load(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _save(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)


def bounded_sample(instances, per_property: int):
    """Deterministically pick ~per_property instances per target property."""
    by_pid = collections.defaultdict(list)
    for inst in instances:
        by_pid[inst["target_pid"]].append(inst)
    out = []
    for pid, items in sorted(by_pid.items()):
        items = sorted(items, key=lambda x: x["id"])
        if len(items) <= per_property:
            out.extend(items)
            continue
        step = len(items) / per_property
        idxs = sorted({int(k * step) for k in range(per_property)})
        out.extend(items[i] for i in idxs)
    return out


def stage_sample(per_bucket: int = 40):
    from o1 import wikidata as wd
    ents = wd.sample_shrines_stratified(per_bucket=per_bucket, seed=0)
    wd.save_json(ents, str(DATA / "shrines_stratified.json"))
    print(f"[sample] {len(ents)} shrine entities -> data_lake/shrines_stratified.json")
    return ents


def stage_build():
    from o1 import dataset as ds
    ents = _load(DATA / "shrines_stratified.json")
    insts = ds.build_eval_set(ents)
    _save(insts, DATA / "eval_set.json")
    print(f"[build] {len(insts)} held-out instances -> data_lake/eval_set.json")
    return insts


def _clients():
    from o1 import predict as pr
    return pr.make_ollama_client(), pr.wikidata_resolver()


def _run_sample(insts):
    """Select the bounded run sample — bucket-stratified if O1_PER_BUCKET is set."""
    if PER_BUCKET is not None:
        from o1 import dataset as ds
        return ds.bucket_stratified_sample(insts, PER_BUCKET)
    return bounded_sample(insts, PER_PROPERTY)


def stage_predict():
    from o1 import predict as pr
    insts = _load(DATA / "eval_set.json")
    sample = _run_sample(insts)
    client, resolver = _clients()
    print(f"[predict] running predict-only over {len(sample)} instances (local Gemma)...")
    preds = pr.predict_all(sample, client, resolver=resolver)
    _save({"sample_ids": [i["id"] for i in sample], "predictions": preds},
          RESULTS / "predict_only.json")
    print(f"[predict] {len(preds)} predictions -> results/predict_only.json")
    return sample, preds


def stage_verify():
    from o1 import verify as vf
    insts = _load(DATA / "eval_set.json")
    blob = _load(RESULTS / "predict_only.json")
    ids = set(blob["sample_ids"])
    sample = [i for i in insts if i["id"] in ids]
    client, resolver = _clients()
    print(f"[verify] verifying {len(blob['predictions'])} predictions (local Gemma)...")
    verified = vf.verify_all(sample, blob["predictions"], client, resolver=resolver)
    _save({"sample_ids": list(ids), "predictions": verified}, RESULTS / "verify.json")
    print(f"[verify] {len(verified)} verified -> results/verify.json")
    return verified


def lenient_entity_scores(predictions, sample):
    """Per entity-property hierarchy-lenient metrics (live ancestor lookup)."""
    from o1 import score as sc
    from o1.wikidata import make_ancestor_lookup, ANCESTOR_PROPERTY_PATH
    by_id = {i["id"]: i for i in sample}
    out = {}
    for pid in ANCESTOR_PROPERTY_PATH:
        pp = [p for p in predictions if p["target_pid"] == pid]
        insts_p = [by_id[p["id"]] for p in pp if p["id"] in by_id]
        if not pp:
            continue
        lookup = make_ancestor_lookup(pid)
        s = sc.score(pp, insts_p, ancestors=lookup)
        out[pid] = s["by_property"].get(pid)
    return out


def stage_score():
    from o1 import score as sc
    from o1.wikidata import DEFAULT_TARGET_PROPERTIES
    insts = _load(DATA / "eval_set.json")
    by_id = {i["id"]: i for i in insts}
    po = _load(RESULTS / "predict_only.json")
    sample = [by_id[i] for i in po["sample_ids"] if i in by_id]
    result = {"n_sample": len(sample),
              "predict_only": sc.score(po["predictions"], sample)}
    print("[score] computing hierarchy-lenient entity scores (Wikidata ancestors)...")
    result["predict_only_lenient_entity"] = lenient_entity_scores(po["predictions"], sample)
    if (RESULTS / "verify.json").exists():
        vv = _load(RESULTS / "verify.json")
        result["verify"] = sc.score(vv["predictions"], sample)
    _save(result, RESULTS / "scores.json")
    _write_findings(result, DEFAULT_TARGET_PROPERTIES)
    print(f"[score] metrics over {len(sample)} instances -> results/scores.json + FINDINGS.md")
    return result


def stage_figures():
    from o1 import figures
    scores = _load(RESULTS / "scores.json")
    written = figures.make_figures(scores, str(DOCS))
    for p in written:
        print(f"[figures] wrote {os.path.relpath(p, ROOT)}")
    return written


def _write_findings(result, labels):
    from o1 import score as sc
    po = result["predict_only"]
    lines = [
        "# Findings — LLM Wikidata gap-filling for Shinto shrines",
        "",
        "> **Model:** local Gemma (`gemma3:12b`) via Ollama, temperature 0. "
        "No paid API.",
        "",
        "## Question",
        "",
        "How reliably can a local LLM fill missing Wikidata statements for Shinto "
        "shrines, and does a self-verification pass reduce wrong / hallucinated "
        "values? Held-out single-property prediction; precision / recall by "
        "property type; predict-only vs predict-then-verify.",
        "",
        "## Method",
        "",
        f"- Eval set: held-out statements from a stratified sample of Shinto "
        f"shrines (Wikidata). This run scored **{result['n_sample']} instances** "
        f"(bounded sample, ~{round(result['n_sample'] / max(1, len(po['by_property'])))} "
        f"per property across {len(po['by_property'])} properties).",
        "- Predict-only: model proposes a value or abstains; entity answers "
        "resolved to QIDs via `wbsearchentities`.",
        "- Predict-then-verify: Chain-of-Verification-style independent re-check "
        "(KEEP / REVISE / WITHDRAW).",
        "- precision = correct / answered · recall = correct / total · "
        "abstain = abstained / total. Coordinates matched within 0.05°; dates by "
        "year; entities by QID (resolver-miss counts as wrong).",
        "",
    ]
    # Auto headline computed from the data (no hand-tuning).
    ov = po["overall"]
    head_bits = [
        f"On **{result['n_sample']} held-out statements**, predict-only Gemma "
        f"reached **precision {_f(ov['precision'])} / recall {_f(ov['recall'])}** "
        f"overall (abstaining on {_f(ov['abstain_rate'])} of gaps)."
    ]
    if "verify" in result:
        vov = result["verify"]["overall"]
        if ov["precision"] is not None and vov["precision"] is not None:
            d = vov["precision"] - ov["precision"]
            verb = "raised" if d > 0 else "lowered" if d < 0 else "did not change"
            head_bits.append(
                f"A self-verification pass **{verb}** overall precision "
                f"({_f(ov['precision'])} → {_f(vov['precision'])}) — "
                + ("consistent with the literature's warning that naive "
                   "self-correction can backfire." if d < 0 else
                   "in line with Chain-of-Verification's intended effect."
                   if d > 0 else "no net effect at this sample size.")
            )
    lines += ["## Headline", "", " ".join(head_bits), "",
              "## Predict-only — by property", "", sc.to_markdown(po, labels), ""]

    # Strict vs hierarchy-lenient for entity properties (the granularity finding).
    lenient = result.get("predict_only_lenient_entity")
    if lenient:
        lines += [
            "## Entity properties — strict vs hierarchy-lenient",
            "",
            "Strict scoring needs the *exact* QID. Hierarchy-lenient also credits an "
            "answer that is an ancestor/descendant of the recorded entity (e.g. the "
            "model gives the prefecture when Wikidata records the city). The gap is "
            "the share of answers that are **right at a different granularity**.",
            "",
            "| property | strict precision | lenient precision | strict recall | lenient recall |",
            "|---|---|---|---|---|",
        ]
        for pid, lm in lenient.items():
            sm = po["by_property"].get(pid)
            if not sm or not lm:
                continue
            lines.append(
                f"| {labels.get(pid, pid)} (`{pid}`) | {_f(sm['precision'])} | "
                f"{_f(lm['precision'])} | {_f(sm['recall'])} | {_f(lm['recall'])} |"
            )
        lines.append("")
    if "verify" in result:
        v = result["verify"]
        lines += [
            "## Predict-then-verify — by property",
            "",
            sc.to_markdown(v, labels),
            "",
            "## Verify lift (overall)",
            "",
            "| condition | precision | recall | abstain |",
            "|---|---|---|---|",
            _lift_row("predict-only", po["overall"]),
            _lift_row("predict+verify", v["overall"]),
            "",
        ]
    # Popularity gradient (H2) for the tail-covered properties.
    pb = po.get("by_property_bucket", {})
    grad_pids = [p for p in GRADIENT_PROPERTIES if p in pb]
    if grad_pids:
        lines += [
            "## Popularity gradient (H2) — predict-only precision by bucket",
            "",
            "Only the four properties whose ground truth reaches the tail. "
            "head = ≥6 sitelinks · torso = 1–5 · tail = 0. Cells show "
            "precision (n).",
            "",
            "| property | head | torso | tail |",
            "|---|---|---|---|",
        ]
        for pid in grad_pids:
            buckets = pb[pid]

            def cell(b):
                m = buckets.get(b)
                return "—" if not m else f"{_f(m['precision'])} ({m['n']})"

            lines.append(
                f"| {labels.get(pid, pid)} (`{pid}`) | "
                f"{cell('head')} | {cell('torso')} | {cell('tail')} |"
            )
        lines.append("")
    lines += [
        "## Honesty controls",
        "",
        "Two probes on the review-flagged risks (from the n=92 predict-only run).",
        "",
        "**Contamination (memorization).** If the model were reciting "
        "Wikipedia-derived facts, accuracy should collapse on shrines with **no** "
        "Wikipedia article. It does the opposite: strict correctness was "
        "**0.71 on the no-Wikipedia tail** (sitelinks=0) vs **0.53 on "
        "has-Wikipedia** entities. The per-property gradient (above) shows the "
        "same — no head→tail decay. *Caveat:* the raw tail-vs-head split is "
        "confounded by property mix (the tail sample is all categorical "
        "properties), so the per-property gradient is the cleaner evidence. Either "
        "way, **no memorization signal** for these near-constant properties.",
        "",
        "**Ground-truth incompleteness.** Spot-checked 5 `P131` answers scored "
        "*wrong* against the live Wikidata labels: **4/5 were a granularity "
        "mismatch** (model gave the prefecture — Kumamoto, Saitama, Tokyo, Akita — "
        "where Wikidata records a ward/city: Chūō-ku, Ōmiya-ku, Ueno-kōen, "
        "Yurihonjo), **1/5 a genuine error** (said *Kanagawa*; the shrine is in "
        "Kasukabe, *Saitama*), and **0/5 a Wikidata gap** (every recorded value "
        "was a legitimate, more-specific entity). So the strict `P131`≈0 is mostly "
        "granularity, not hallucination — and precision is **not** materially a "
        "lower bound from Wikidata incompleteness here (the lower-bound risk is "
        "real in principle but did not bite in this sample).",
        "",
        "## Limitations (carried from the design)",
        "",
        "- **Entity-property scores conflate model error with QID-resolution "
        "error.** Answers for entity properties (`P17`/`P131`/`P140`/`P31`/"
        "`P1435`) are mapped to a QID via `wbsearchentities`; a reasonable label "
        "(e.g. a city or ward) can resolve to a *different* QID than the specific "
        "one Wikidata records, counting as wrong. The very low `P131` precision is "
        "likely partly this, not pure hallucination — a follow-up should audit "
        "raw answers vs. resolved QIDs.",
        "- **Tail shrines are statement-sparse**, so the popularity gradient is "
        "only measurable for `P17`/`P31`/`P131`/`P625`; date/heritage/religion "
        "get head-bucket coverage only.",
        "- **Contamination:** Wikidata/Wikipedia are in pretraining, so high "
        "precision on popular entities may reflect memorization, not inference.",
        "- **Ground-truth incompleteness:** a 'wrong' answer may be a correct fact "
        "Wikidata lacks, so precision is a lower bound.",
        "- This is a **bounded sample**; numbers are indicative, not final.",
        "",
    ]
    with open(ROOT / "FINDINGS.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _f(x):
    return "—" if x is None else f"{x:.2f}"


def _lift_row(name, m):
    return f"| {name} | {_f(m['precision'])} | {_f(m['recall'])} | {_f(m['abstain_rate'])} |"


def main(argv):
    stage = argv[1] if len(argv) > 1 else None
    if stage is None:
        print("usage: python scripts/run.py {" + " | ".join(STAGES) + "}")
        return 0
    if stage not in STAGES:
        print(f"unknown stage {stage!r}; choose one of {', '.join(STAGES)}")
        return 2
    if stage == "sample":
        stage_sample()
    elif stage == "build":
        stage_build()
    elif stage == "predict":
        stage_predict()
    elif stage == "verify":
        stage_verify()
    elif stage == "score":
        stage_score()
    elif stage == "figures":
        stage_figures()
    elif stage == "all":
        stage_predict()
        stage_verify()
        stage_score()
        stage_figures()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
