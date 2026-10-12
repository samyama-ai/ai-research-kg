# AI Research KG — Schema plan v0.1 (Phase 1 design, 2026-10-05)

> **This is the Phase 1 design, kept for the record.** What was actually built is described in
> [schema.md](schema.md) (v1, 11 node labels, 11 edge types). Where the two differ, schema.md
> is right about the graph and this file is right about the plan. The differences are listed in
> schema.md §7.

Core property-graph model for open AI research problems, their evidence, and the people, papers and methods around them.

> **Design principle:** Everything hangs off a **Problem** node. Every fact records where it came from, so each answer can be traced back to the exact problem page and reference it was read from.

| | |
|---|---|
| Scope | Baseline (v0.1 draft, 2026-10-05) |
| Graph model | Labelled property graph / openCypher (Samyama Graph) |
| Core node types | 12, plus 1 bookkeeping node (DataSource) |
| Relationship types | 16, including 1 computed (RELATED_TO) and 1 bookkeeping (FROM_SOURCE) |
| Evidence model | Provenance on every node and edge |
| Primary use | Research landscape, problem discovery, finding research opportunities |
| Source basis | `github.com/samyama-ai/ai_research` (1,000 problems, 35 topics) + `docs/scope.md` |
| Sibling KG | DBMS Research KG (`samyama-graph/case_studies/dbms-research`) — same edge names where the meaning is the same |

---

## 1. Core Graph Architecture

```
                         (Topic)◄──IN_TOPIC──┐                              (AssumptionClass)
                                             │                                      ▲
 (Venue)◄──APPEARED_AT──(Paper)◄──CITES──(PROBLEM)──RESTS_ON──►(Assumption)──INSTANCE_OF──┘
                          │      {role}      │  │  │
                     AUTHORED_BY             │  │  └──HAS_GAP──►(OpenQuestion {kind})
                          ▼                  │  │
 (Institution)◄──AFFILIATED_WITH──(Person)   │  └──BLOCKED_BY──►(Obstruction)
       │                                     │
       └────────ACTIVE_ON───────────────────►│──STATE_OF_ART {evidence}──►(Method)──INTRODUCED_IN──►(Paper)
                                             │──MENTIONS──────────────────►(Method)
                                             │──HAS_NEXT_EXPERIMENT──►(FutureDirection)
                                             │──RELATED_TO {method, score}──►(Problem)   [computed]
                                             └──FROM_SOURCE──►(DataSource)

 Every node and edge carries the Section 4 provenance fields
 (source, source_url, retrieved_at, method, confidence); the pinned commit lives in DataSource.version.
```

Properties in `{braces}` after a relationship name sit on the edge; properties after a node name sit on the node (so `kind` is an OpenQuestion property and `role` a CITES property).

**How to read the model:** Problem is the central node. Topic says *where* it sits. Paper, Person, Venue and Institution say *who* has worked on it. Method says *what has been tried*. Assumption, OpenQuestion and Obstruction say *why it is still open*. FutureDirection says *what to do next*.

### 1.1 Core design rules

1. **Stable identifiers.** Problem ids come from the catalog (`20-interpretability/internals-based-safety-verification`) and never change. Papers use the arXiv ID where one exists, so the same paper cited by 10 problems becomes one node.
2. **One node per real-world thing.** A paper cited by many problems is one Paper node with many CITES edges, not one copy per problem.
3. **Problem-specific text stays problem-specific.** Assumptions, open questions and next experiments are written for one problem, so they are one node per problem. Similar assumptions can be compared through a canonical `AssumptionClass` node; source wording remains on each Assumption.
4. **Small fixed vocabularies where possible.** Reference roles, gap kinds and obstruction types are grouped into short fixed lists, so you can count and compare them. The original wording is kept in a `_raw` property.
5. **Computed edges are labelled as computed.** RELATED_TO isn't in the source data. It carries `method` and `score`, so nobody mistakes it for a stated fact.
6. **Provenance on everything** (Section 4).

---

## 2. Node Types — 12 Core + DataSource

| # | Node | What it is | Key properties | Source in the catalog | Why the graph needs it | Est. count |
|---|---|---|---|---|---|---|
| 1 | **Problem** | One open AI research problem | `id`, `title`, `slug`, `statement`, `status`, `first_added`, `last_reviewed`, `last_substantive_update`, `stale_since`, `catalog_provenance`, `embedding` | One `.md` file: frontmatter + §1 | The centre of the graph; every question starts or ends here | 1,000 |
| 2 | **Topic** | One of the 35 research areas | `id`, `number`, `slug`, `name`, `scope` | `TAXONOMY.md` | Grouping, counting, topic-to-topic links | 35 |
| 3 | **Paper** | A cited publication | `id`, `title`, `year`, `arxiv_id`, `doi`, `venue_raw`, `authors_raw` | Key References | Evidence; links problems through shared papers | 5,004 arXiv-ID / title grouped records measured |
| 4 | **Person** | A paper author | `id`, `name`, `name_variants`, `arxiv_author_id`, `orcid`, `resolved` | author lists, resolved via arXiv | Who works on what; collaboration | 11,894 distinct raw author strings measured; identities unresolved |
| 5 | **Venue** | Where a paper appeared | `id`, `name`, `kind` (conference / journal / workshop / preprint / report), `aliases` | Key References, after cleanup | Which venues carry the research | rough estimate: ~200 after cleanup; 699 distinct normalised raw venue strings measured |
| 6 | **Institution** | A lab, company or university | `id`, `name`, `kind` (industry / academic / non-profit / government), `country` | §7 Current Research | Which labs are active on which problems | 45 canonical names / 2,057 rule-matched links measured (case-sensitive whole-word match on a fixed alias list); false matches still possible |
| 7 | **Method** | A named technique, algorithm or system | `id`, `name`, `aliases`, `kind` (algorithm / architecture / training method / evaluation / tool) | §3 State of the Art (+ mentions in other sections) | What has been tried; methods shared across topics | rough estimate: 2,000–3,000 |
| 8 | **Assumption** | A source-specific assumption | `id`, `text`, `name`, `violated` (true / false / partly), `violation_note` | §2 "Assumptions, and which are violated" | Preserve each problem's wording and violation evidence | 2,492 list items measured |
| 9 | **AssumptionClass** | A canonical category shared by similar assumptions | `id`, `name`, `description` | Curated mapping from Assumption text | Answer Q34 without merging source-specific assumptions | estimate pending curation |
| 10 | **OpenQuestion** | One specific gap in what's known | `id`, `text`, `kind` (theoretically_open / empirically_open / methodologically_blocked), `is_primary` | §5 What Is Not Known | Classifying problems by type of openness (Q5, Q7) | 3,810 §5 list items measured |
| 11 | **Obstruction** | A *type* of reason a problem is hard | `id`, `name`, `description` | §6 Why It Is Hard, grouped into a fixed list (Section 5.3) | Most common reasons problems stay hard (Q8) | rough estimate: 8–12 types |
| 12 | **FutureDirection** | The concrete next experiment | `id`, `question`, `scale`, `control_arm`, `deciding_number`, `compute_budget_text`, `gpu_count`, `wall_clock_hours`, `single_machine` | §8 Concrete Next Experiment | Cheapest and runnable experiments (Q36–38) | 1,000 |
| 13 | **DataSource** | Where the data came from (bookkeeping) | `id`, `name`, `url`, `licence`, `version` (commit hash), `fetched_at` | — | Provenance; required by the build guide. Reached from every Problem through FROM_SOURCE | 1–3 sources, depending on lookups |

*Note:* the sibling DBMS KG also has `Bound` and `ComputationModel` nodes. They're left out here: AI problems state experiments and gaps, not formal complexity bounds.

---

## 3. Relationship Types

| # | Relationship | From → To | Properties | Meaning / use | Est. count |
|---|---|---|---|---|---|
| 1 | **IN_TOPIC** | Problem → Topic | — | Each problem belongs to exactly one topic | 1,000 |
| 2 | **CITES** | Problem → Paper | `role` (fixed list, 5.2), `role_raw`, `position` | The problem uses this paper as evidence | 12,878 measured (261 of them carry no role tag in the source) |
| 3 | **AUTHORED_BY** | Paper → Person | `position` (1 = first author) | Authorship | 19,166 author entries measured; identities unresolved |
| 4 | **APPEARED_AT** | Paper → Venue | `year` | Publication venue | 4,313 grouped paper records with a parsed venue string |
| 5 | **AFFILIATED_WITH** | Person → Institution | `source` | Researcher's lab (only where a lookup confirms it) | partial, optional in v1 |
| 6 | **ACTIVE_ON** | Institution → Problem | `direction` (the §7 bullet text) | A lab named in §7 as working on the problem (the page names it; activity isn't independently verified) | 2,057 rule-matched links (measured) |
| 7 | **STATE_OF_ART** | Problem → Method | `evidence` (established / claimed / benchmark_only), `kind` (theory / empirical / systems) | Best-known method for this problem | rough estimate: ~3,000 |
| 8 | **MENTIONS** | Problem → Method | `section` (§ number) | The method appears anywhere on the page (weaker than STATE_OF_ART) | rough estimate: ~5,000+ |
| 9 | **RESTS_ON** | Problem → Assumption | `position` | The problem depends on this assumption | 2,492 list items measured |
| 10 | **HAS_GAP** | Problem → OpenQuestion | `position` | A classified unknown | 3,810 source list items measured |
| 11 | **BLOCKED_BY** | Problem → Obstruction | `detail` (the problem's own wording), `is_primary` | Why the problem is hard | rough estimate; §6 has 940 list items before mapping |
| 12 | **HAS_NEXT_EXPERIMENT** | Problem → FutureDirection | — | What to run next | 1,000 |
| 13 | **RELATED_TO** | Problem → Problem | `method` (shared_papers / shared_methods / embedding), `score` | **Computed** similarity, not stated in the source | tunable (e.g. top 5 per problem → ~5,000) |
| 14 | **INTRODUCED_IN** | Method → Paper | — | The paper that introduced the method (where clear) | optional in v1 |
| 15 | **INSTANCE_OF** | Assumption → AssumptionClass | — | Link source-specific assumptions to a curated shared class (Q34) | estimate pending curation (≤ 2,492) |
| 16 | **FROM_SOURCE** | Problem → DataSource | — | Bookkeeping: the pinned catalog version each page was read from (PROV-O `wasDerivedFrom`); page-level nodes inherit it through their Problem | 1,000 |

**Direction note:** STATE_OF_ART and ACTIVE_ON point the same way as in the DBMS KG (Problem → Method, X → Problem), so the same queries work on both graphs.

---

## 4. Provenance Model

> **Baseline rule:** every node and edge carries provenance.

| Field | Example | Purpose |
|---|---|---|
| `provenance` | `real` | Is this a sourced fact or synthetic? Always `real` here: no synthetic data is needed. |
| `catalog_provenance` | `synthesized` / `verified` | The catalog's own flag on the **prose** quality. All 1,000 are `synthesized` today. |
| `source` | `ai_research`, `arxiv-api`, `computed` | Named origin |
| `source_url` | `https://github.com/samyama-ai/ai_research/blob/<commit>/topics/...md` | Exact file it came from |
| `retrieved_at` | `2026-10-05T12:00:00Z` | When it was read |
| `method` | `parsed` / `resolved` / `llm-extracted` / `computed` | How the value was produced |
| `confidence` | `high` / `medium` / `low` | `parsed` = high; `llm-extracted` = medium; fuzzy matches = low |
| `verified` | `false` | Set where a fact could not be confirmed (guide rule) |

### 4.1 Evidence chain

```
Problem page (.md, pinned commit)
   ↓  parse frontmatter + sections
extracted record (title, status, refs, assumptions…)
   ↓  normalise (role buckets, venue names, author resolution)
graph node / edge  (with provenance fields)
   ↓  Cypher query
answer  ──►  traceable back to file + section + commit
```

---

## 5. Key Sub-models

### 5.1 Problem status and openness

Two separate things, kept separate:

- **`Problem.status`** comes from the frontmatter. It has one value per problem:

  | status | count |
  |---|---|
  | open | 401 |
  | empirically-open | 295 |
  | partially-solved | 189 |
  | methodologically-blocked | 96 |
  | solved-but-impractical | 19 |

  `methodologically-blocked` is used in the data but missing from the catalog's `TEMPLATE.md`. The schema allows it.

- **OpenQuestion.kind** comes from §5. A problem can have several gaps of different kinds. For example, the merging-safety problem has 2 empirically open, 1 theoretically open and 1 methodologically blocked. This answers Q5 properly, which `status` alone can't.

### 5.2 Citation roles (CITES.role)

The catalog uses about 500 different free-text tags (`SOTA — theory`, `Key negative result`, `Mitigation`…). They're grouped into 7 fixed roles (counts rerun 2026-10-12 with the committed keyword grouping). The original tag is kept in `role_raw`. 261 reference bullets carry no `[Tag]` at all; they are counted as `untagged` (an eighth value meaning "no tag in the source", not a role) rather than dropped.

| role | Includes tags like | Citations (measured) |
|---|---|---|
| `sota` | SOTA, SOTA — theory/empirical/systems, Theory SOTA | 3,987 |
| `foundational` | Foundational, Background, Key, Established | 2,948 |
| `evidence` | Empirical, Theory, Evidence, Analysis, Measurement, Replication | 1,661 |
| `survey` | Survey, Survey/Benchmark, Position, Roadmap | 884 |
| `method` | Method, Mechanism, Mitigation, Defense, Tooling | 753 |
| `caution` | Caution, Critique, Negative result, Counter-evidence, Limits | 245 |
| `context` | Related, Context, Adjacent, Benchmark, Dataset, everything else | 2,139 |
| `untagged` | (no tag in the source; `role_raw` empty) | 261 |
| **total** | | **12,878** |

Matching is checked in this order: caution → survey → sota → foundational → method → evidence → context. So "SOTA / negative result" counts as `caution`.

Counts are reproduced by `etl/count_kg.py` using the keyword rules in `ROLE_RULES`; the seven buckets remain a draft classification and retain the raw tag in `role_raw`.

### 5.3 Obstruction vocabulary (draft)

§6 is free text, but it names the obstruction in bold. Each problem is mapped to one or more of these:

| Obstruction | Meaning |
|---|---|
| `compute_cost` | The experiment is too expensive at the scale that matters |
| `confounded_measurement` | The metric mixes up several effects |
| `invalid_evaluation` | The benchmark doesn't measure what it names |
| `absent_ground_truth` | No reliable answer key exists |
| `non_identifiability` | Several explanations fit the same data |
| `theoretical_hardness` | Known complexity or impossibility results |
| `data_scarcity` | The needed data doesn't exist or isn't public |
| `scale_gap` | Results at small scale don't transfer to frontier scale |
| `other` | Doesn't fit the list (keep `detail`) |

### 5.4 FutureDirection

Each §8 contains a **question**, a **scale**, **control arms** and **the deciding number**. Store `gpu_count` and `wall_clock_hours` separately when the source states them. Set `single_machine = true` only when both are known and `gpu_count ≤ 8` and `wall_clock_hours ≤ 24`; aggregate GPU-hours alone cannot establish this. Leave unknown fields empty rather than guessing.

---

## 6. Standards, Taxonomies and Identifiers

| Kind | Standard / identifier | Used for |
|---|---|---|
| Taxonomy | ai_research `TAXONOMY.md` (35 topics, stable numbers) | Topic |
| Taxonomy (crosswalk, optional) | arXiv categories (cs.AI, cs.LG, cs.CL, cs.CV, stat.ML…) | `Topic.arxiv_categories` |
| Classification (optional) | ACM Computing Classification System 2012 | `Topic.acm_ccs` |
| Paper identifier | arXiv ID (71.5% of references have one in the count run), DOI (rare here) | `Paper.id` |
| Person identifier | arXiv author list, ORCID, OpenAlex author ID | `Person.id` |
| Institution identifier (optional) | ROR (Research Organization Registry) | `Institution.ror_id` |
| Dates | ISO 8601 (`2026-09`) | all dates |
| Provenance | PROV-O pattern (as in the Valuation KG) | Section 4 |
| Semantics (optional) | SKOS for topic hierarchy if it gains levels later | Topic |
| Later: Responsible AI | NIST AI RMF, EU AI Act, ISO/IEC 42001, OECD AI Principles | Optional extension (Section 7) |

---

## 7. Optional / Deeper Extensions (not in v1)

| Node | Purpose | Example relationship |
|---|---|---|
| **RAIFramework** | Responsible AI framework or guideline (from the survey of RAI frameworks a UC Berkeley student working with the team is preparing; unpublished internal work as of 2026-10, so no citation yet — add one when it's delivered) | Problem → ADDRESSED_BY → RAIFramework |
| **RAIPrinciple** | Fairness, transparency, privacy, safety… | RAIFramework → COVERS → RAIPrinciple |
| **XAITechnique** | SHAP, LIME, SAEs, probing… (could reuse Method with `kind: xai`) | Problem → MENTIONS → XAITechnique |
| **ResearchDirection** | Each §7 bullet as its own node (~4,600) | Problem → HAS_DIRECTION → ResearchDirection ← PURSUES ← Institution |
| **CandidateProblem** | Proposed future problems from `topics/*/candidates.json` | CandidateProblem → IN_TOPIC → Topic |
| **Benchmark / Dataset** | HarmBench, MMLU… named in experiments | FutureDirection → USES → Benchmark |
| **Bridge to DBMS / Maths KGs** | Shared papers, people, methods across sibling catalogs | Paper → SAME_AS → Paper (cross-KG) |

> **Guardrail:** add a node only when it answers a question in `scope.md`.

---

## 8. Data Quality and Modelling Rules

| Rule | Implementation guidance |
|---|---|
| **Paper resolution** | Match by arXiv ID first, then by normalised title. Never merge by surname alone. |
| **Person resolution** | Authors are written 3 ways: surname only (`Wortsman`), initials (`Moerland, T.`), full name. Use the arXiv API for full author lists. If a name can't be resolved, keep it as its own node with `resolved: false`. Don't merge a bare surname into a full name (the DBMS KG learned this the hard way). |
| **"et al."** | Never create a Person called "et al.". Get the full list from arXiv or leave it partial. |
| **Venue cleanup** | "EMNLP", "Findings of EMNLP" and "EMNLP (industry track)" map to one Venue, with the variant kept on the edge. |
| **Roles and obstructions** | Always keep the original text (`role_raw`, `detail`) next to the grouped value. |
| **Computed links** | RELATED_TO must carry `method` + `score`. Never present it as a stated fact. |
| **Missing values** | Leave empty or set `verified: false`. Never invent. The counter parses references from all 1,000 pages; this is not a semantic validation. |
| **Skip files** | `README.md` and `candidates.json` in topic folders aren't problems. |
| **Pin the source** | Record the ai_research commit hash in provenance properties on each source-derived node/edge, so a rebuild gives the same graph. |

---

## 9. Example Evidence Path

An interpretability problem, as a path through the graph:

```
Problem "Scalable Verification of Safety Properties From Internals"
  {status: solved-but-impractical}
  ├─ IN_TOPIC → Topic "Interpretability" (20)
  ├─ CITES {role: foundational} → Paper "Reluplex…" (arXiv:1702.01135)
  │     └─ APPEARED_AT → Venue "CAV"
  ├─ CITES {role: sota} → Paper "Compact Proofs of Model Performance…" (arXiv:2406.11779)
  │     └─ AUTHORED_BY → Person "Jason Gross" {resolved: true, name_variants: ["Gross"]}
  │            (the page says "Gross et al."; the full name comes from the arXiv author list,
  │             so the bare surname is a variant on the resolved node, not a merge by surname)
  ├─ CITES {role: caution} → Paper "Is This the Subspace You Are Looking For?…"
  ├─ STATE_OF_ART {evidence: established} → Method "α,β-CROWN"
  ├─ STATE_OF_ART {evidence: claimed} → Method "Sparse autoencoders"
  ├─ RESTS_ON → Assumption {violated: partly} "Features are linear directions"
  │     └─ INSTANCE_OF → AssumptionClass "linear feature representation"
  ├─ HAS_GAP → OpenQuestion {kind: methodologically_blocked} "No formal spec for 'no hidden goal'"
  ├─ BLOCKED_BY → Obstruction "theoretical_hardness"   (NP-complete verification)
  ├─ BLOCKED_BY → Obstruction "absent_ground_truth"
  ├─ HAS_NEXT_EXPERIMENT → FutureDirection {compute_budget_text: "~200 A100-hours"}
  ├─ ← ACTIVE_ON ← Institution "Anthropic", "Google DeepMind", "Apollo Research"
  ├─ RELATED_TO {method: shared_papers} → other interpretability / safety problems
  └─ FROM_SOURCE → DataSource "ai_research" {version: a02e87b3…}
```

---

## 10. Question Coverage (from scope.md)

| Questions | Path through the graph |
|---|---|
| A 1–4 | Topic ← IN_TOPIC ← Problem, `status` |
| A 5 | Problem → HAS_GAP → OpenQuestion `{kind}` |
| A 7 | `Problem.status = 'open'` + HAS_NEXT_EXPERIMENT → FutureDirection `{single_machine}` (as reworded in scope.md; the catalog doesn't say who has tried what) |
| A 6 | `Problem.status = 'solved-but-impractical'` |
| A 8 | Problem → BLOCKED_BY → Obstruction |
| B 9–13 | one Problem and its direct neighbours |
| C 14–19 | Problem → CITES `{role}` → Paper (→ Topic for Q15) |
| D 20–24 | Paper → AUTHORED_BY → Person; Institution → ACTIVE_ON → Problem |
| E 25–28 | Problem → STATE_OF_ART / MENTIONS → Method `{evidence}` |
| F 29–32, 35 | RELATED_TO, Topic–Topic via shared problems/papers, `embedding` |
| Stretch 33 | ❌ needs a directional "enables" link the data doesn't contain; moved out of the core list in scope.md |
| F 34 | Problem → RESTS_ON → Assumption → INSTANCE_OF → AssumptionClass |
| G 36–39 | FutureDirection `{gpu_count, wall_clock_hours, single_machine}`; count ACTIVE_ON + CITES |
| H 40–41 | no Funding or Leaderboard nodes → returns "no data" ✓ |

---

## 11. Estimated Size

| | DBMS Research KG | AI Research KG (estimate) |
|---|---|---|
| Problems | 1,053 | 1,000 |
| Nodes | 18,751 | ~28,000–29,000 = 25,979 measured + 2,100–3,300 estimated |
| Edges | 38,539 | ~64,000–65,000 = 46,716 measured + 17,500–18,500 estimated |
| Vector indexes | 2 (Problem, Topic) | 2 (Problem, Topic) |

How the totals are built (measured figures are `nodes_measured` / `edges_measured` from `etl/count_kg.py`, run 2026-10-12 on commit `a02e87b3`):

| | Measured by `count_kg.py` | Estimated (not produced by the counter) |
|---|---|---|
| Nodes | Problem 1,000 · Topic 35 · Paper 5,004 · Person 11,894 (raw author strings) · Venue 699 (raw strings) · Institution 45 · Assumption 2,492 · OpenQuestion 3,810 · FutureDirection 1,000 = **25,979** | Method 2,000–3,000 · AssumptionClass 100–300 · Obstruction ~10 · DataSource 1–3 = **2,100–3,300** |
| Edges | IN_TOPIC 1,000 · CITES 12,878 · AUTHORED_BY 19,166 · APPEARED_AT 4,313 · ACTIVE_ON 2,057 · RESTS_ON 2,492 · HAS_GAP 3,810 · HAS_NEXT_EXPERIMENT 1,000 = **46,716** | STATE_OF_ART ~3,000 · MENTIONS ~5,000 · BLOCKED_BY 1,000–2,000 (from 940 §6 items) · RELATED_TO ~5,000 (top 5 per problem) · INSTANCE_OF ~2,500 · FROM_SOURCE 1,000 · AFFILIATED_WITH and INTRODUCED_IN optional = **17,500–18,500** |

Venue and person resolution will lower the node total by a few hundred (699 raw venue strings → ~200 venues; author variants merge) without changing the edge counts. The estimated column is a planning range, not a measurement.

---

## 12. Implementation Checklist

1. Get this schema reviewed **before** loading any data.
2. Once approved, rename `schema/template_kg.cypher` to `schema/ai_research_kg.cypher` and fill it with node labels, relationships, indexes and constraints.
3. Parse frontmatter + sections → Problem, Topic, Assumption, OpenQuestion, FutureDirection (easy, exact).
4. Parse the **Key References** section → Paper, CITES `{role}`, Venue (medium).
5. Resolve authors via arXiv IDs → Person, AUTHORED_BY (medium; rate-limit and cache).
6. Extract Methods, Institutions and Obstructions (hardest; review samples by hand).
7. Compute RELATED_TO and embeddings last.
8. Loader verifies counts per label and edge type, and fails on any mismatch.
9. Do not publish a source snapshot until the `ai_research` licence is confirmed.
10. Only then add the Section 7 extensions (Responsible AI first).

---

## 13. Sources Used

- `github.com/samyama-ai/ai_research`: README, TAXONOMY.md, TEMPLATE.md, all 1,000 problem files (parsed 2026-10-05, re-counted 2026-10-12 on commit `a02e87b3` with `count_kg.py`)
- DBMS Research KG: `samyama-graph/case_studies/dbms-research` and `dbms_research/USING_WITH_SAMYAMA_GRAPH.md`
- *How to Build a Samyama Knowledge Graph — Step by Step* (Phases 4–5)
- *Enterprise Valuation KG — Detailed Schema* (used as the layout model)
- `docs/scope.md` (core question and 41 example questions)
