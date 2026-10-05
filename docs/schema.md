# AI Research KG — Detailed Schema

Core property-graph model for open AI research problems, their evidence, and the people, papers and methods around them.

> **Design principle:** Everything hangs off a **Problem** node. Every fact records where it came from, so each answer can be traced back to the exact problem page and reference it was read from.

| | |
|---|---|
| Scope | Baseline (v0.1 draft, 2026-10-05) |
| Graph model | Labelled property graph / openCypher (Samyama Graph) |
| Core node types | 12 + 1 bookkeeping node (DataSource) |
| Relationship types | 15 core, including 1 computed (RELATED_TO) |
| Evidence model | Provenance on every node and edge |
| Primary use | Research landscape, problem discovery, finding research opportunities |
| Source basis | `github.com/samyama-ai/ai_research` (1,000 problems, 35 topics) + `docs/scope.md` |
| Sibling KG | DBMS Research KG (`samyama-graph/case_studies/dbms-research`) — same edge names where the meaning is the same |

---

## 1. Core Graph Architecture

```
                         (Topic)◄──IN_TOPIC──┐
                                             │
 (Venue)◄──APPEARED_AT──(Paper)◄──CITES──(PROBLEM)──RESTS_ON──►(Assumption)
                          │      {role}      │  │  │
                     AUTHORED_BY             │  │  └──HAS_GAP──►(OpenQuestion) {kind}
                          ▼                  │  │
 (Institution)◄──AFFILIATED_WITH──(Person)   │  └──BLOCKED_BY──►(Obstruction)
       │                                     │
       └────────ACTIVE_ON───────────────────►│──STATE_OF_ART──►(Method)
                                             │──MENTIONS──────►(Method)
                                             │──HAS_NEXT_EXPERIMENT──►(FutureDirection)
                                             │──RELATED_TO──►(Problem)   [computed]
                                             └──DERIVED_FROM──►(DataSource)
```

**How to read the model:** Problem is the central node. Topic says *where* it sits. Paper, Person, Venue and Institution say *who* has worked on it. Method says *what has been tried*. Assumption, OpenQuestion and Obstruction say *why it is still open*. FutureDirection says *what to do next*.

### 1.1 Core design rules

1. **Stable identifiers.** Problem ids come from the catalog (`20-interpretability/internals-based-safety-verification`) and never change. Papers use the arXiv ID where one exists, so the same paper cited by 10 problems becomes one node.
2. **One node per real-world thing.** A paper cited by many problems is one Paper node with many CITES edges, not one copy per problem.
3. **Problem-specific text stays problem-specific.** Assumptions, open questions and next experiments are written for one problem, so they are one node per problem, not merged across problems.
4. **Small fixed vocabularies where possible.** Reference roles, gap kinds and obstruction types are grouped into short fixed lists, so you can count and compare them. The original wording is kept in a `_raw` property.
5. **Computed edges are labelled as computed.** RELATED_TO isn't in the source data. It carries `method` and `score`, so nobody mistakes it for a stated fact.
6. **Provenance on everything** (Section 4).

---

## 2. Node Types — Core 12

| # | Node | What it is | Key properties | Source in the catalog | Why the graph needs it | Est. count |
|---|---|---|---|---|---|---|
| 1 | **Problem** | One open AI research problem | `id`, `title`, `slug`, `statement`, `status`, `first_added`, `last_reviewed`, `last_substantive_update`, `stale_since`, `catalog_provenance`, `embedding` | One `.md` file: frontmatter + §1 | The centre of the graph; every question starts or ends here | 1,000 |
| 2 | **Topic** | One of the 35 research areas | `id`, `number`, `slug`, `name`, `scope` | `TAXONOMY.md` | Grouping, counting, topic-to-topic links | 35 |
| 3 | **Paper** | A cited publication | `id`, `title`, `year`, `arxiv_id`, `doi`, `venue_raw`, `authors_raw` | §9 Key References | Evidence; links problems through shared papers | ~5,000 |
| 4 | **Person** | A paper author | `id`, `name`, `name_variants`, `arxiv_author_id`, `orcid`, `resolved` | §9 author lists, resolved via arXiv | Who works on what; collaboration | ~7,000–9,000 |
| 5 | **Venue** | Where a paper appeared | `id`, `name`, `kind` (conference / journal / workshop / preprint / report), `aliases` | §9, after cleanup | Which venues carry the research | ~200 (from 656 raw spellings) |
| 6 | **Institution** | A lab, company or university | `id`, `name`, `kind` (industry / academic / non-profit / government), `country` | §7 Current Research | Which labs are active on which problems | ~50–100 |
| 7 | **Method** | A named technique, algorithm or system | `id`, `name`, `aliases`, `kind` (algorithm / architecture / training method / evaluation / tool) | §3 State of the Art (+ mentions in other sections) | What has been tried; methods shared across topics | ~2,000–3,000 |
| 8 | **Assumption** | An assumption the problem rests on | `id`, `text`, `name`, `violated` (true / false / partly), `violation_note` | §2 "Assumptions, and which are violated" | Problems that share an assumption (Q34) | ~3,160 |
| 9 | **OpenQuestion** | One specific gap in what's known | `id`, `text`, `kind` (theoretically_open / empirically_open / methodologically_blocked), `is_primary` | §5 What Is Not Known | Classifying problems by type of openness (Q5, Q7) | ~3,800 |
| 10 | **Obstruction** | A *type* of reason a problem is hard | `id`, `name`, `description` | §6 Why It Is Hard, grouped into a fixed list (Section 5.3) | Most common reasons problems stay hard (Q8) | ~8–12 |
| 11 | **FutureDirection** | The concrete next experiment | `id`, `question`, `scale`, `control_arm`, `deciding_number`, `compute_budget_text`, `compute_budget_gpu_hours`, `single_machine` | §8 Concrete Next Experiment | Cheapest and runnable experiments (Q36–38) | 1,000 |
| 12 | **DataSource** | Where the data came from (bookkeeping) | `id`, `name`, `url`, `licence`, `version` (commit hash), `fetched_at` | — | Provenance; required by the build guide | 2–3 (ai_research, arXiv API, OpenAlex) |

*Note:* the sibling DBMS KG also has `Bound` and `ComputationModel` nodes. They're left out here: AI problems state experiments and gaps, not formal complexity bounds.

---

## 3. Relationship Types

| # | Relationship | From → To | Properties | Meaning / use | Est. count |
|---|---|---|---|---|---|
| 1 | **IN_TOPIC** | Problem → Topic | — | Each problem belongs to exactly one topic | 1,000 |
| 2 | **CITES** | Problem → Paper | `role` (fixed list, 5.2), `role_raw`, `position` | The problem uses this paper as evidence | ~12,600 |
| 3 | **AUTHORED_BY** | Paper → Person | `position` (1 = first author) | Authorship | ~17,000–20,000 |
| 4 | **APPEARED_AT** | Paper → Venue | `year` | Publication venue | ~4,300 |
| 5 | **AFFILIATED_WITH** | Person → Institution | `source` | Researcher's lab (only where a lookup confirms it) | partial, optional in v1 |
| 6 | **ACTIVE_ON** | Institution → Problem | `direction` (the §7 bullet text) | A lab named as currently working on the problem | ~2,700 |
| 7 | **STATE_OF_ART** | Problem → Method | `evidence` (established / claimed / benchmark_only), `kind` (theory / empirical / systems) | Best-known method for this problem | ~3,000 |
| 8 | **MENTIONS** | Problem → Method | `section` (§ number) | The method appears anywhere on the page (weaker than STATE_OF_ART) | ~5,000+ |
| 9 | **RESTS_ON** | Problem → Assumption | `position` | The problem depends on this assumption | ~3,160 |
| 10 | **HAS_GAP** | Problem → OpenQuestion | `position` | A classified unknown | ~3,800 |
| 11 | **BLOCKED_BY** | Problem → Obstruction | `detail` (the problem's own wording), `is_primary` | Why the problem is hard | ~1,500–2,500 |
| 12 | **HAS_NEXT_EXPERIMENT** | Problem → FutureDirection | — | What to run next | 1,000 |
| 13 | **RELATED_TO** | Problem → Problem | `method` (shared_papers / shared_methods / embedding), `score` | **Computed** similarity, not stated in the source | tunable (e.g. top 5 per problem → ~5,000) |
| 14 | **INTRODUCED_IN** | Method → Paper | — | The paper that introduced the method (where clear) | optional in v1 |
| 15 | **DERIVED_FROM** | any node → DataSource | `source_path`, `commit` | Provenance link | 1 per node, or kept as properties only |

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

The catalog uses about 500 different free-text tags (`SOTA — theory`, `Key negative result`, `Mitigation`…). They're grouped into 7 fixed roles (counts measured 2026-10-05 with a keyword grouping). The original tag is kept in `role_raw`.

| role | Includes tags like | Citations (measured) |
|---|---|---|
| `sota` | SOTA, SOTA — theory/empirical/systems, Theory SOTA | 3,983 |
| `foundational` | Foundational, Background, Key, Established | 2,952 |
| `evidence` | Empirical, Theory, Evidence, Analysis, Measurement, Replication | 1,750 |
| `survey` | Survey, Survey/Benchmark, Position, Roadmap | 891 |
| `method` | Method, Mechanism, Mitigation, Defense, Tooling | 829 |
| `caution` | Caution, Critique, Negative result, Counter-evidence, Limits | 306 |
| `context` | Related, Context, Adjacent, Benchmark, Dataset, everything else | 1,906 |
| **total** | | **12,617** |

Matching is checked in this order: caution → survey → sota → foundational → method → evidence → context. So "SOTA / negative result" counts as `caution`.

This grouping is a first draft. Run it over all tags and adjust it before you fix the list.

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

Each §8 contains a **question**, a **scale**, **control arms** and **the deciding number**. `compute_budget_gpu_hours` is parsed from text like "~200 A100-hours". If it's ≤ 8 GPUs × 24 h, `single_machine = true`. Leave the field empty when no budget is stated, rather than guessing.

---

## 6. Standards, Taxonomies and Identifiers

| Kind | Standard / identifier | Used for |
|---|---|---|
| Taxonomy | ai_research `TAXONOMY.md` (35 topics, stable numbers) | Topic |
| Taxonomy (crosswalk, optional) | arXiv categories (cs.AI, cs.LG, cs.CL, cs.CV, stat.ML…) | `Topic.arxiv_categories` |
| Classification (optional) | ACM Computing Classification System 2012 | `Topic.acm_ccs` |
| Paper identifier | arXiv ID (71% of citations have one), DOI (rare here) | `Paper.id` |
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
| **RAIFramework** | Responsible AI framework or guideline (from the Berkeley student's survey) | Problem → ADDRESSED_BY → RAIFramework |
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
| **Missing values** | Leave empty or set `verified: false`. Never invent. 1 problem has no references, so let it have none. |
| **Skip files** | `README.md` and `candidates.json` in topic folders aren't problems. |
| **Pin the source** | Record the ai_research commit hash in DataSource, so a rebuild gives the same graph. |

---

## 9. Example Evidence Path

The interpretability problem you read, as a path through the graph:

```
Problem "Scalable Verification of Safety Properties From Internals"
  {status: solved-but-impractical}
  ├─ IN_TOPIC → Topic "Interpretability" (20)
  ├─ CITES {role: foundational} → Paper "Reluplex…" (arXiv:1702.01135)
  │     └─ APPEARED_AT → Venue "CAV"
  ├─ CITES {role: sota} → Paper "Compact Proofs of Model Performance…" (arXiv:2406.11779)
  │     └─ AUTHORED_BY → Person "Gross" (full name resolved via arXiv)
  ├─ CITES {role: caution} → Paper "Is This the Subspace You Are Looking For?…"
  ├─ STATE_OF_ART {evidence: established} → Method "α,β-CROWN"
  ├─ STATE_OF_ART {evidence: claimed} → Method "Sparse autoencoders"
  ├─ RESTS_ON {violated: partly} → Assumption "Features are linear directions"
  ├─ HAS_GAP {kind: methodologically_blocked} → OpenQuestion "No formal spec for 'no hidden goal'"
  ├─ BLOCKED_BY → Obstruction "theoretical_hardness"   (NP-complete verification)
  ├─ BLOCKED_BY → Obstruction "absent_ground_truth"
  ├─ HAS_NEXT_EXPERIMENT → FutureDirection {compute_budget_gpu_hours: 200, single_machine: false}
  ├─ ← ACTIVE_ON ← Institution "Anthropic", "Google DeepMind", "Apollo Research"
  └─ RELATED_TO {method: shared_papers} → other interpretability / safety problems
```

---

## 10. Question Coverage (from scope.md)

| Questions | Path through the graph |
|---|---|
| A 1–4 | Topic ← IN_TOPIC ← Problem, `status` |
| A 5, 7 | Problem → HAS_GAP → OpenQuestion `{kind}` |
| A 6 | `Problem.status = 'solved-but-impractical'` |
| A 8 | Problem → BLOCKED_BY → Obstruction |
| B 9–13 | one Problem and its direct neighbours |
| C 14–19 | Problem → CITES `{role}` → Paper (→ Topic for Q15) |
| D 20–24 | Paper → AUTHORED_BY → Person; Institution → ACTIVE_ON → Problem |
| E 25–28 | Problem → STATE_OF_ART / MENTIONS → Method `{evidence}` |
| F 29–32, 35 | RELATED_TO, Topic–Topic via shared problems/papers, `embedding` |
| F 33 | ❌ needs a directional "enables" link the data doesn't contain (stretch) |
| F 34 | Problem → RESTS_ON → Assumption (similar text grouped) |
| G 36–39 | FutureDirection `{compute_budget_gpu_hours, single_machine}`; count ACTIVE_ON + CITES |
| H 40–41 | no Funding or Leaderboard nodes → returns "no data" ✓ |

---

## 11. Estimated Size

| | DBMS Research KG | AI Research KG (estimate) |
|---|---|---|
| Problems | 1,053 | 1,000 |
| Nodes | 18,751 | ~25,000–28,000 (incl. ~3,800 OpenQuestion) |
| Edges | 38,539 | ~55,000–60,000 |
| Vector indexes | 2 (Problem, Topic) | 2 (Problem, Topic) |

The estimate is higher than the earlier ~20K / ~45K because OpenQuestion (~3,800 nodes and edges), MENTIONS and BLOCKED_BY were added in this draft.

---

## 12. Implementation Checklist

1. Get this schema reviewed **before** loading any data.
2. Write `schema/ai_research_kg.cypher`: labels, edge types, indexes on `id`, unique constraints on `id`.
3. Fill in `schema/template_kg.cypher` with one example node per label and one edge per type.
4. Parse frontmatter + sections → Problem, Topic, Assumption, OpenQuestion, FutureDirection (easy, exact).
5. Parse §9 → Paper, CITES `{role}`, Venue (medium).
6. Resolve authors via arXiv IDs → Person, AUTHORED_BY (medium; rate-limit and cache).
7. Extract Methods, Institutions and Obstructions (hardest; review samples by hand).
8. Compute RELATED_TO and embeddings last.
9. Loader verifies counts per label and edge type, and fails on any mismatch.
10. Only then add the Section 7 extensions (Responsible AI first).

---

## 13. Sources Used

- `github.com/samyama-ai/ai_research`: README, TAXONOMY.md, TEMPLATE.md, all 1,000 problem files (parsed 2026-10-05, `count_kg.py`)
- DBMS Research KG: `samyama-graph/case_studies/dbms-research` and `dbms_research/USING_WITH_SAMYAMA_GRAPH.md`
- *How to Build a Samyama Knowledge Graph — Step by Step* (Phases 4–5)
- *Enterprise Valuation KG — Detailed Schema* (used as the layout model)
- `docs/scope.md` (core question and 41 example questions)
