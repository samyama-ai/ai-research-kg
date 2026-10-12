# Taxonomy: does the graph follow the 35 topics, and what could be refined

Checked 2026-10-09 against `ai_research` at `a02e87b3` (the pinned commit). Every number here is
measured by `python -m etl.conformance` and listed check by check in
[conformance.md](conformance.md) (checks T1–T13, C9, C11, C13).

**Short answer:** the graph follows the taxonomy exactly. All 35 topics are present with the
same number, name, folder and scope, and every one of the 1,000 problems sits in the topic its
folder and frontmatter say. The refinements below add structure *around* the 35 topics. None of
them renumbers or moves a topic, because the catalog says topic numbers are stable identity.

---

## 1. Conformance to TAXONOMY.md

| Check | Rule | Result |
|---|---|---|
| T1 | One `Topic` node per TAXONOMY.md row | ✅ 35 rows, 35 nodes |
| T2 | `number`, `name`, `slug`, `scope` equal the row; the slug starts with the number | ✅ all 35 |
| T3 | Every `topics/` folder is a taxonomy topic, and the reverse | ✅ 35 folders |
| T4 | Every problem has exactly one `IN_TOPIC` | ✅ 1,000 of 1,000 |
| T5 | `IN_TOPIC` target = folder = frontmatter `topic` = id prefix | ✅ no mismatch |
| T6 | Problems per topic in the graph = files per folder | ✅ 26–31 per topic |
| T7 | `Problem.status` is on the status list | ✅ (see refinement R5) |

Topic ids are `topic:<NN-slug>`, and `Topic.number` (1–35) is the stable code. Topic sizes are
even: 26 (Safety & Robustness) to 31 (Tokenization).

## 2. Refinements

### R1. Add a level above the topics: 6 topic areas

The taxonomy is flat: 35 siblings with no grouping. More than half of the computed problem links
cross topics (1,735 of 3,128 `RELATED_TO` edges, 55%), so a reader needs a coarser map. The
proposal groups the topics by measured coupling: papers cited by both topics, and `RELATED_TO`
links between their problems.

| Area | Topics | Strongest couplings inside the area (papers cited by both topics, T13) |
|---|---|---|
| `architecture`: model architecture and generative families | 01, 02, 07, 08, 09, 14, 15, 16, 34 | 02–14 (72), 02–09 (64), 09–14 (49) |
| `training`: training, data and scaling | 03, 06, 10, 13, 29, 30 | 03–10 (63), 06–30 (52), 13–29 (45) |
| `systems`: systems and efficiency | 11, 12, 31, 32 | 31–32 (60), 11–32 (46), 12–32 (32) |
| `post_training`: alignment, RL and reasoning | 04, 17, 18 | 04–18 (71), 17–18 (49), 04–17 (35) |
| `trust`: trust, safety and evaluation | 19, 20, 21, 22, 23, 28, 33 | 21–33 (39), 22–33 (36), 19–33 (35) |
| `applications`: capabilities and modalities | 05, 24, 25, 26, 27, 35 | 05–26 (28), 05–27 (20), 26–27 (19) |

One unit throughout: the number of papers cited by both topics (T13). The `applications` area is
the loosest: its strongest inside pair, 05–26 (28), is weaker than its strongest pulls outward,
05–21 Factuality (40) and 07–24 (38), so it is a residual group as much as a cluster.

**Measured (T11):** 64% of `RELATED_TO` links stay inside one area. If the areas were random
groups of these sizes, 19% would. Caution: the grouping was chosen *from* this coupling data, so
the 64% shows the grouping fits the data, not that it is the right grouping. One boundary is a
judgment call: 04 Alignment couples equally with 18 RL (71 papers) and 22 Safety (72), and 04–22
is the strongest cross-area pair in the whole graph (T13).

**How to build it:** `TopicArea` nodes (or SKOS concepts in a `topic_area` scheme) with
`(Topic)-[:BROADER]->(TopicArea)`, the SKOS `broader` pattern the Valuation KG uses. The codes
are drafted in `vocab/concepts.yaml` (`topic_area`, status `proposed`). **Needs the lead's yes**,
because it adds a layer to the catalog's own taxonomy.

### R2. Add a level below the topics: the scope terms as subtopics

Each topic's scope column lists 4–6 terms (166 in all), such as *RLHF, DPO, GRPO, reward models*.
They are written as one string today. Splitting them into subtopic concepts (`skos:narrower`)
would let a query ask for "the DPO problems". A keyword test of each term against each problem's
title, statement and formal setting shows the scope column doesn't describe the problems well
yet:

- **18 of 166 terms name no problem in their topic** (T8): *multilingual fairness* (01), *GRPO*
  (04), *planning loops* (05), *cleaning*, *deterministic data execution* (06), *byte codecs*
  (07), *end-to-end sizing* (09), *QAT* (12), *memory hierarchies* (14), *MoE inference
  economics* (15), *hybrid stacks* (16), *statistical power* (19), *knowledge boundaries* (21),
  *vision-language fusion* (24), *continual learning* (28), *curriculum transfer* (29),
  *verifier-guided synthesis* (30), *parallelism strategies* (31).
- **218 of 1,000 problems match none of their topic's terms** (T9, which lists the worst
  topics): 28 Knowledge Editing (20 of 29), 06 Data Pipelines (13 of 29), 22 Safety (13 of 26),
  and 07, 14, 18, 32 (12 each).

Keyword matching is crude; a term like *parallelism strategies* may be covered under other
words. Treat both lists as a review queue: either the scope text gains the missing words, or the
term marks a gap in the catalog. The second case is useful too, since *GRPO* and *QAT* are live
research areas with no problem yet.

### R3. Give problems a secondary topic

90 problems (9%) have most of their `RELATED_TO` neighbours (at least 2/3, and at least 3 links)
in one *other* topic (T10). The five strongest, as T10 lists them:

| Problem | Filed under | Neighbours mostly in |
|---|---|---|
| `29-distillation/lora-expressivity-limits-transfer` | 29 Distillation | 13 Parameter-Efficient Adaptation (9 of 9) |
| `17-reasoning/diversity-collapse-under-reasoning-rl` | 17 Reasoning | 18 RL for LLMs (7 of 7) |
| `29-distillation/compression-method-frontier` | 29 Distillation | 12 Quantization & Compression (7 of 7) |
| `23-privacy-memorization/memorization-parameter-efficient-finetuning` | 23 Privacy & Memorization | 13 Parameter-Efficient Adaptation (6 of 6) |
| `24-multimodal/cross-modal-routing-circuits` | 24 Multimodal | 20 Interpretability (5 of 5) |

These are not misfilings: problem ids are stable and the primary topic stays. The proposal is a
computed `(Problem)-[:ALSO_IN_TOPIC {method: "related_majority", score}]->(Topic)` edge,
labelled as computed like `RELATED_TO`. Then a query for one topic also finds the problems
filed elsewhere that mostly link to it. [conformance.md](conformance.md) shows these same five
(T10); the full list of 90 is not stored anywhere, the tool prints it with
`python -m etl.conformance --examples 0`.

### R4. Mark cross-cutting topics and isolated topics

The share of a topic's cited papers that no other topic cites shows what kind of topic it is
(T12):

- **Cross-cutting lenses:** 10 Scaling Laws (8% own papers), 14 Long Context (19%), 09 Model
  Design (21%). They study *every* other area at scale. Queries should expect them to overlap.
- **Islands:** 25 Speech & Audio (84%), 35 World Models (79%), 34 Diffusion (61%). These have
  their own literature and are the least connected to the rest.

Proposal: a `Topic.kind` of `area` or `lens`. Small, but it explains query results.

### R5. Fix the status list upstream

`TEMPLATE.md` lists 5 statuses: `open`, `partially-solved`, `empirically-open`,
`solved-but-impractical` and `stale`. The data uses `methodologically-blocked` (96 problems),
which is not in the template, and never uses `stale`. The KG accepts both (`vocab/concepts.yaml`
`problem_status`). Proposal for `ai_research`: add `methodologically-blocked` to `TEMPLATE.md`.

### R6. Refine the graph's own sub-taxonomies

These are the KG's own classifications (full lists and counts in `vocab/concepts.yaml` and
conformance C9):

| Vocabulary | Finding | Proposal |
|---|---|---|
| Citation role (7) | `context` is the catch-all, with 1,911 citations (15%). Benchmark (268) and Evaluation (116) alone are 384 of them (raw tags listed under C9) | Add `benchmark` (→ CiTO `usesDataFrom`); drafted as `proposed` |
| Open-question kind (3 + unclassified) | 41 of 3,790 unclassified; 18 of those say just "Open" (raw labels under C9) | Keep `unclassified`: guessing a kind would invent data |
| Obstruction (5 + other) | Keyword-classified. `confounded_measurement` (521) and `non_identifiability` (458) dominate; `other` is 20 (`BLOCKED_BY` counts under C9) | Review a sample of 50 by hand before trusting the split |
| Venue (none) | 527 venues; 339 with one paper; 24 still look like residue. v1.1 gives each paper one venue; 77 papers keep the catalog's other venues in `venue_variants` (10 of them only arXiv; 18 conference contradictions, ICLR vs ICML 8 times) | A `venue_kind` code list (drafted) and a canonical venue list, keyed to DBLP stream ids later |

### R7. Crosswalks (later, need external lookups)

v1 uses the catalog only, so no topic is mapped to an outside taxonomy yet. When lookups are
allowed: map each topic to **arXiv categories** by counting the categories of its 3,081 arXiv
papers (`skos:closeMatch` / `broadMatch`). OpenAlex topics are optional (docs/standards.md). Also
load the **1,380 candidate problems** in `topics/*/candidates.json` as `CandidateProblem` nodes,
which shows where each topic is growing.

## 3. What to ask the lead

1. R1 topic areas: is this grouping right, especially where 04 Alignment goes?
2. R5: OK to add `methodologically-blocked` to `ai_research/TEMPLATE.md`?
3. R2: should the 18 empty scope terms be reworded, or kept as gaps for new problems?
