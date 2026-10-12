# AI Research KG — Schema (v1.1, as built)

The graph as `etl/build.py` builds it and `etl/loader.py` loads it: 11 node labels, 11 edge
types, 29,696 nodes and 62,845 edges from the `ai_research` catalog at commit `a02e87b3`
(v1.1, 2026-10-09; counts re-measured 2026-10-12; `tests/test_invariants.py` pins them).
The Phase 1 design this grew out of is kept in [schema-v0.1-plan.md](schema-v0.1-plan.md);
§7 lists what was planned and not built. The standards, code lists and ontology file are in
[standards.md](standards.md).

| | |
|---|---|
| Version | v1.1 (2026-10-09; v1 was 2026-10-07 with 28,960 nodes / 62,178 edges) |
| Graph model | labelled property graph, openCypher (Samyama Graph 1.11.0) |
| Node labels | 11 |
| Edge types | 11, one computed (`RELATED_TO`) and one bookkeeping (`FROM_SOURCE`) |
| Source | `github.com/samyama-ai/ai_research` only, pinned at `a02e87b3` (`etl/download_data.py`); no external lookups, no LLM extraction |
| Provenance | `provenance`, `source`, `method`, `retrieved_at`, `source_date` on every node; `source_url` on every node read from one page (§4) |
| Loaded schema | [`schema/ai_research_kg.cypher`](../schema/ai_research_kg.cypher): `id` index per label plus the filter indexes the queries use |
| Sibling KG | DBMS Research KG (`samyama-graph/case_studies/dbms-research`): same edge names where the meaning is the same |

## 1. Picture

```
                      (Topic)◄──IN_TOPIC──┐
                                          │
 (Venue)◄──APPEARED_AT──(Paper)◄──CITES {role, role_raw, position}──(PROBLEM)──RESTS_ON {position}──►(Assumption)
                          │                                           │  │
                   AUTHORED_BY {position}                             │  ├──HAS_GAP {position}──►(OpenQuestion)
                          ▼                                           │  ├──BLOCKED_BY {detail, is_primary}──►(Obstruction)
                       (Person)                                       │  ├──HAS_NEXT_EXPERIMENT──►(FutureDirection)
                                                                      │  ├──RELATED_TO {method, shared_papers, score}──►(Problem)  [computed]
 (Institution)──ACTIVE_ON {direction}─────────────────────────────────┘  └──FROM_SOURCE──►(DataSource)
```

Problem is the centre. Topic says where it sits; Paper, Person, Venue and Institution say who has
worked on it; Assumption, OpenQuestion and Obstruction say why it is still open; FutureDirection
says what to run next. Properties in `{braces}` after an edge name sit on the edge.

## 2. Node labels (11)

Every node also carries the provenance fields of §4. Counts are for the v1 graph.

| Label | Count | One node per | Properties (beyond §4) | Read from |
|---|---:|---|---|---|
| `Problem` | 1,000 | catalog page | `title`, `slug`, `status`, `topic`, `first_added`, `last_reviewed`, `last_substantive_update`, `stale_since`, `catalog_provenance`, `statement` (opening paragraphs) | frontmatter + "Problem Statement" |
| `Topic` | 35 | TAXONOMY.md row | `number` (1–35, stable), `name`, `slug`, `scope` | `TAXONOMY.md` |
| `Paper` | 4,932 | cited work, deduplicated | `title`, `year`, `arxiv_id`, `doi`, `venue` (one per paper: a named venue beats a preprint server, then the most frequent), `venue_raw`, `venue_variants` (the catalog's other venues, `; `-separated), `authors_raw` | "Key References" |
| `Person` | 15,097 | author string as written | `name`, `name_form` (full / initials / surname / collective) | author lists in "Key References" |
| `Venue` | 522 | normalised venue name | `name` | venue text of each reference, through the alias list in `etl/rules.py` |
| `Institution` | 50 | lab on the fixed list that occurs | `name`, `kind` (industry / academic / non-profit / government) | "Current Research", matched against 51 names (`etl/rules.py: INSTITUTIONS`; MIRI never occurs) |
| `Assumption` | 3,263 | one assumption of one problem (list, table, inline (i)/(ii) or prose form) | `name`, `text`, `violated` (violated / partly / holds / unstated) | "Formal Setting" |
| `OpenQuestion` | 3,790 | labelled item of one problem's "What Is Not Known" | `kind` (theoretically_open / empirically_open / methodologically_blocked / unclassified), `kind_raw`, `is_primary`, `text` | "What Is Not Known" |
| `Obstruction` | 6 | obstruction type | `name` | "Why It Is Hard", keyword-mapped to the 5 types in the catalog's TEMPLATE.md + `other` |
| `FutureDirection` | 1,000 | problem's "Concrete Next Experiment" | `text`, `question`, `scale`, `control_arm`, `deciding_number`, `compute_budget_gpu_hours`, `single_machine` | "Concrete Next Experiment" |
| `DataSource` | 1 | source | `name`, `url`, `version` (the pinned commit), `licence` ("none stated") | — |

**Ids** are minted deterministically (`etl/build.py`), so a rebuild gives the same ids:
`problem:<NN-topic>/<slug>`, `topic:<NN-slug>`, `paper:arxiv:<id>` → `paper:doi:<doi>` → `paper:t:<12-hex title hash>`,
`person:<slug of the name as written>`, `venue:<slug>`, `institution:<key>`, `obstruction:<code>`,
`<problem id>#assumption-N`, `<problem id>#gap-N`, `<problem id>#next-experiment`, `datasource:ai_research`.
Uniqueness across the whole graph is checked in `tests/test_invariants.py`; the engine has no unique constraints.

## 3. Edge types (11)

| Edge | From → To | Count | Properties | Meaning |
|---|---|---:|---|---|
| `IN_TOPIC` | Problem → Topic | 1,000 | — | exactly one per problem |
| `CITES` | Problem → Paper | 12,615 | `role` (7 buckets, §5), `role_raw` (the catalog's tag), `position` | the problem cites the paper as evidence |
| `AUTHORED_BY` | Paper → Person | 28,753 | `position` (1 = first author) | authorship as written |
| `APPEARED_AT` | Paper → Venue | 4,365 | — | where the paper appeared: exactly one per paper that names a venue |
| `RESTS_ON` | Problem → Assumption | 3,263 | `position` | the problem depends on the assumption |
| `HAS_GAP` | Problem → OpenQuestion | 3,790 | `position` | a classified unknown of the problem |
| `BLOCKED_BY` | Problem → Obstruction | 1,448 | `detail` (the problem's own bold phrase), `is_primary` (exactly one true per problem) | why the problem is hard |
| `HAS_NEXT_EXPERIMENT` | Problem → FutureDirection | 1,000 | — | what to run next |
| `ACTIVE_ON` | Institution → Problem | 2,483 | `direction` (the "Current Research" bullet) | the page names the lab in "Current Research" (naming, not verified activity) |
| `RELATED_TO` | Problem → Problem | 3,128 | `method` = `shared_papers`, `shared_papers` (count), `score` (Jaccard, 3 decimals) | **computed**: ≥ 2 shared cited papers, top 5 per problem by Jaccard, stored once per pair from the smaller id to the larger |
| `FROM_SOURCE` | Problem → DataSource | 1,000 | — | bookkeeping: the pinned catalog version the page was read from |

`STATE_OF_ART` and `ACTIVE_ON` keep the DBMS KG's directions, so the same queries work on both graphs.

## 4. Provenance

| Field | Values in v1 | On |
|---|---|---|
| `provenance` | `real` (the Samyama build-guide flag: parsed from a real source, not synthetic) | every node |
| `source` | `ai_research` | every node |
| `method` | `parsed` (29,639 nodes), `keyword-classified` (the 6 Obstruction nodes), `name-matched` (the 50 Institution nodes) | every node except DataSource |
| `retrieved_at` | `2026-10-07`: the date the pinned catalog was fetched (git's reflog of the checkout) | every node |
| `source_date` | `2026-09-10`: the date of the pinned commit | every node |
| `source_url` | `https://github.com/samyama-ai/ai_research/blob/<commit>/<file>` | every node read from one page (not Institution, Obstruction, DataSource, which are shared) |
| `catalog_provenance` | the catalog's own frontmatter flag on its prose: `synthesized` for all 1,000 | Problem |
| `DataSource.version` | the pinned commit, 40 hex | DataSource |

Edges carry no provenance of their own: an edge's provenance is the problem page at its source
end (listed as a known limit in [standards.md](standards.md)).

## 5. Code lists

| Property | Values | How |
|---|---|---|
| `Problem.status` | open 401 · empirically-open 295 · partially-solved 189 · methodologically-blocked 96 · solved-but-impractical 19 | frontmatter, as written |
| `CITES.role` | sota 3,983 · foundational 2,952 · context 1,906 · evidence 1,750 · survey 889 · method 829 · caution 306 | the catalog's ~670 free-text tags grouped by `ROLE_RULES` (`etl/rules.py`), checked caution → survey → sota → foundational → method → evidence → context |
| `OpenQuestion.kind` | empirically_open 1,509 · theoretically_open 1,152 · methodologically_blocked 1,088 · unclassified 41 | from the item's bold label; anything else stays `unclassified` |
| `Obstruction` | confounded_measurement 521 · non_identifiability 460 · absent_ground_truth 208 · compute_cost 131 · invalid_evaluation 104 · other 24 (`BLOCKED_BY` edges) | keyword match on the bold phrase of "Why It Is Hard", then its opening text |
| `Assumption.violated` | violated · partly · holds · unstated | keyword match on the item text |
| `Person.name_form` | full · initials · surname · collective | shape of the name string |
| `Institution.kind` | industry · academic · non-profit · government | from the fixed list |
| `FutureDirection.single_machine` | true when the text says single GPU/node/machine or the budget is ≤ 192 GPU-hours (8 GPUs × 24 h); null when nothing is stated | `etl/parse.py: parse_experiment` |

## 6. Example path (from the real graph)

```
(:Problem {id: "problem:20-interpretability/internals-based-safety-verification",
           title: "Scalable Verification of Safety Properties From Internals",
           status: "solved-but-impractical", topic: "20-interpretability",
           catalog_provenance: "synthesized", provenance: "real", source: "ai_research", method: "parsed"})
  -[:IN_TOPIC]->              (:Topic {id: "topic:20-interpretability", number: 20, name: "Interpretability"})
  -[:CITES {role: "foundational", role_raw: "Foundational", position: 1}]->
                              (:Paper {id: "paper:arxiv:1702.01135", title: "Reluplex: …", year: 2017})
                                 -[:AUTHORED_BY {position: 1}]-> (:Person {id: "person:katz", name: "Katz", name_form: "surname"})
                                 -[:APPEARED_AT]->               (:Venue {id: "venue:cav", name: "CAV"})
  -[:RESTS_ON {position: 1}]-> (:Assumption {id: "…#assumption-1", name: "Linear representation", violated: "violated"})
  -[:HAS_GAP {position: 1}]->  (:OpenQuestion {id: "…#gap-1", kind: "theoretically_open"})
  -[:BLOCKED_BY {detail: "Exponential in unstable neurons, not in parameters", is_primary: true}]->
                              (:Obstruction {id: "obstruction:compute_cost", name: "Compute cost"})
  -[:HAS_NEXT_EXPERIMENT]->   (:FutureDirection {id: "…#next-experiment", compute_budget_gpu_hours: 200.0, single_machine: false})
  (every node also: retrieved_at: "2026-10-07", source_date: "2026-09-10")
  <-[:ACTIVE_ON {direction: "Anthropic / GDM interpretability teams"}]- (:Institution {id: "institution:anthropic", name: "Anthropic", kind: "industry"})
  -[:RELATED_TO {method: "shared_papers", shared_papers: 5, score: 0.278}]-> (:Problem …)
  -[:FROM_SOURCE]->           (:DataSource {id: "datasource:ai_research", version: "a02e87b3…"})
```

## 7. Planned in v0.1, not built in v1

| v0.1 plan ([schema-v0.1-plan.md](schema-v0.1-plan.md)) | v1 | Why |
|---|---|---|
| `Method` node, `STATE_OF_ART`, `MENTIONS`, `INTRODUCED_IN` | not built | the bold text in "State of the Art" is evidence labels ("Established", "Claimed but unablated"), not method names; needs an LLM or an outside source |
| `AssumptionClass` + `INSTANCE_OF` | not built | needs curation; Q34 is answered approximately by grouping `Assumption.name` (query AR27) |
| `Person -AFFILIATED_WITH-> Institution` | not built | affiliations need DBLP or OpenAlex, outside the catalog |
| Person resolution via arXiv | names kept as written, with `name_form` | no external lookups in v1 |
| 9-type obstruction list | the catalog's own 5 types + `other` | the catalog already uses that vocabulary |
| `Problem.embedding`, vector indexes | not built | needs an embedding model |
| provenance on edges | not built | an edge's provenance is its source problem page; `retrieved_at` and `source_date` were added to nodes in v1.1 |
| `method` values `parsed / resolved / llm-extracted / computed` | `parsed / keyword-classified / name-matched` | these name what the parser actually does; `RELATED_TO` carries its own `method` |
| 16 edge types, 12 node types | 11 and 11 | the rows above |

## 8. Question coverage

`benchmarks/queries.py` maps every `docs/scope.md` question to a query or to a reason it cannot be
answered (`python -m benchmarks.queries --coverage`; `tests/test_queries.py` checks the mapping is
complete). Not answerable in v1: Q12 and Q25–28 (methods), Q33 (needs an "enables" link the catalog
never states), Q35 (needs community detection over `RELATED_TO`).
