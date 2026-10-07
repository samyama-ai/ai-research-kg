---
id: 22-safety-robustness/fixture-swapped-sections
title: "Fixture Problem With Swapped Sections"
topic: 22-safety-robustness
status: empirically-open
first_added: 2026-09
last_reviewed: 2026-09
last_substantive_update: 2026-09
stale_since: ""
provenance: synthesized
---

# Fixture Problem With Swapped Sections

> Test fixture, not part of the catalog. Sections 9 and 10 are swapped on purpose,
> as in one real catalog file.

## 1. Problem Statement

Can a certified refusal bound be computed for a small model?

## 2. Formal Setting

**Assumptions, and which are violated.**
1. *Linear representation:* features are directions. Violated: circular features exist.
2. *Finite input region:* the input set is enumerable. Holds for the toy task.

## 3. State of the Art

**Established.** Bound propagation is sound on small networks.

## 4. What Is Known

Verification of ReLU networks is NP-complete.

## 5. What Is Not Known

- **Theoretically open.** Whether structure buys an exponential.
- **Empirically open.** Whether the pipeline survives scale-up.
- **Methodologically blocked (primary).** No formal specification of the property.

## 6. Why It Is Hard

The specific obstruction is **absent ground truth compounded by non-identifiability**.

## 7. Current Research (as of 2026)

- **Compact proofs** — Anthropic and MIT groups extend proofs to two layers.
- **Auditing games** — Google DeepMind runs auditing games.

## 8. Concrete Next Experiment

**Question.** Does the bound stay tight at 10x scale?

- **Scale.** Two model sizes, ~40 A100-hours total on a single node.
- **Control arm.** Off-the-shelf bound propagation.
- **Deciding number.** The certified bound at the larger size.

## 10. Worked Example

A two-layer model on a 64-token vocabulary.

## 9. Key References

- **[Foundational]** Katz, Barrett, Dill, Julian, Kochenderfer. *Reluplex: An Efficient SMT Solver for Verifying Deep Neural Networks.* CAV, 2017. — arXiv:1702.01135
- **[SOTA]** Gross, Chughtai, et al. *Compact Proofs of Model Performance via Mechanistic Interpretability.* 2024. — arXiv:2406.11779
- **[Survey]** Moerland, T., Broekens, J., Plaat, A. *Model-based Reinforcement Learning: A Survey.* Foundations and Trends in ML, 2023.
- **[Caution]** Neel Nanda (Google DeepMind) & Arthur Conmy. *A Made-Up Caution Paper.* Findings of EMNLP, 2024.
