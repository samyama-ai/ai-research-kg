# Ontology

What kinds of thing the AI Research KG holds, how they relate, and the rules each must keep.
The machine-readable version is [`ontology/ai_research_kg.ttl`](../ontology/ai_research_kg.ttl)
(OWL/RDFS in Turtle). `etl/conformance.py` reads that file and checks the graph against it;
the result is in [conformance.md](conformance.md), checks O1–O10.

v0.1, 2026-10-09. It describes the v1 graph as built (11 labels, 11 edge types), not the larger
v0.1 design in docs/schema.md.

## Why a separate ontology file

The graph is a labelled property graph, so it runs without OWL. The Valuation KG keeps its
ontology in `docs/schema.md` and `schema/template_kg.cypher`, and lists "an OWL export" under
"not yet". This KG writes the ontology down as a file for three reasons:

1. **It can be checked.** Domain, range, cardinality, id patterns and code lists are data in the
   file. The conformance tool reads them, so the documented rules and the tested rules are the
   same rules.
2. **It says what our terms mean in shared vocabularies.** `CITES` is `cito:cites`, `Paper` is
   close to `schema:ScholarlyArticle`, and so on. That's what makes the graph joinable with the
   DBMS and Maths research KGs and with outside scholarly graphs.
3. **The sibling KGs can reuse it.** The DBMS and Maths research KGs have the same shape:
   problems, topics, papers, people.

## Classes (11)

| Class | What it is | Count | Aligned with | Id pattern |
|---|---|---:|---|---|
| `Problem` | One open AI research problem (one catalog page) | 1,000 | ORKG `Problem` (closeMatch) | `problem:NN-topic/slug` |
| `Topic` | One of the 35 topics of TAXONOMY.md | 35 | subclass of `skos:Concept` | `topic:NN-slug` |
| `Paper` | A cited publication | 4,932 | `schema:ScholarlyArticle`, `fabio:ScholarlyWork` | `paper:arxiv:…` / `paper:doi:…` / `paper:t:<hash>` |
| `Person` | An author, as written in the reference | 15,097 | `schema:Person`, `foaf:Agent` | `person:<slug>` |
| `Venue` | Where a paper appeared | 550 | `schema:Periodical`, `schema:EventSeries` | `venue:<slug>` |
| `Institution` | A lab named in Current Research | 50 | `schema:Organization`, `foaf:Organization` | `institution:<key>` |
| `Assumption` | An assumption one problem rests on | 2,499 | (ours) | `<problem id>#assumption-N` |
| `OpenQuestion` | One gap in what is known, with its kind | 3,790 | (ours) | `<problem id>#gap-N` |
| `Obstruction` | A type of reason a problem is hard | 6 | subclass of `skos:Concept` | `obstruction:<code>` |
| `FutureDirection` | The concrete next experiment | 1,000 | (ours) | `<problem id>#next-experiment` |
| `DataSource` | The pinned catalog | 1 | subclass of `dcat:Dataset` | `datasource:<name>` |

ORKG (the Open Research Knowledge Graph, TIB Hannover) is the closest published model of
research problems. Its class `Problem` has no formal URI, so the link is `skos:closeMatch` to
`https://orkg.org/class/Problem`, not equivalence. No published ontology has assumptions, open
questions or next experiments, so those three classes are ours.

## Relationships (11)

| Relationship | Domain → Range | Cardinality | Aligned with | Count |
|---|---|---|---|---:|
| `IN_TOPIC` | Problem → Topic | exactly 1 per problem; ≥ 1 per topic | `dcterms:subject` | 1,000 |
| `CITES {role, role_raw, position}` | Problem → Paper | ≥ 1 per paper | `cito:cites`; `role` refines it (below) | 12,615 |
| `AUTHORED_BY {position}` | Paper → Person | ≥ 1 per person | `dcterms:creator` | 28,753 |
| `APPEARED_AT` | Paper → Venue | at most 1 per paper; ≥ 1 per venue | `dcterms:isPartOf` | 4,462 |
| `RESTS_ON {position}` | Problem → Assumption | exactly 1 problem per assumption | (ours) | 2,499 |
| `HAS_GAP {position}` | Problem → OpenQuestion | exactly 1 problem per question | (ours) | 3,790 |
| `BLOCKED_BY {detail, is_primary}` | Problem → Obstruction | ≥ 1 per problem; exactly 1 primary | (ours) | 1,448 |
| `HAS_NEXT_EXPERIMENT` | Problem → FutureDirection | at most 1 per problem; exactly 1 per direction | (ours) | 1,000 |
| `ACTIVE_ON {direction}` | Institution → Problem | ≥ 1 per institution | (ours) | 2,483 |
| `RELATED_TO {method, shared_papers, score}` | Problem → Problem | symmetric; stored once, smaller id first; **computed** | `dcterms:relation` | 3,128 |
| `FROM_SOURCE` | Problem → DataSource | exactly 1 per problem | `prov:wasDerivedFrom` | 1,000 |

### Citation roles as CiTO properties

CiTO (the Citation Typing Ontology, SPAR) names the reasons one work cites another. Each
`CITES.role` maps to the nearest CiTO property:

| `role` | CiTO | Citations |
|---|---|---:|
| `sota` | `cito:citesAsAuthority` | 3,983 |
| `foundational` | `cito:obtainsBackgroundFrom` | 2,952 |
| `context` | `cito:citesForInformation` | 1,906 |
| `evidence` | `cito:citesAsEvidence` | 1,750 |
| `survey` | `cito:citesAsRecommendedReading` | 889 |
| `method` | `cito:usesMethodIn` | 829 |
| `caution` | `cito:critiques` | 306 |
| `benchmark` *(proposed)* | `cito:usesDataFrom` | — |

These are `closeMatch` mappings. The catalog's own 669 free-text tags are kept in `role_raw`.

## Properties and code lists

Every node carries `id`, `source`, `provenance` and (all but `DataSource`) `method`. Nodes read
from one page also carry `source_url` at the pinned commit (`prov:hadPrimarySource`). Properties
whose values come from a fixed list point to their scheme in
[`vocab/concepts.yaml`](../vocab/concepts.yaml):

| Property | Code list | Values |
|---|---|---:|
| `Problem.status` | `problem_status` | 5 used (+ `stale`, unused) |
| `Problem.catalog_provenance` | `catalog_provenance` | 1 used (+ `verified`) |
| `CITES.role` | `cites_role` | 7 |
| `OpenQuestion.kind` | `gap_kind` | 4 |
| `Obstruction` id | `obstruction` | 6 |
| `Assumption.violated` | `assumption_status` | 4 |
| `Person.name_form` | `name_form` | 4 |
| `Institution.kind` | `institution_kind` | 4 |
| `<node>.method` | `extraction_method` | 3 |
| `RELATED_TO.method` | `relatedness_method` | 1 |

Dates are ISO 8601 year-months (`xsd:gYearMonth`), and `Topic.number` is a `skos:notation`.

## Does the graph follow the ontology? (measured 2026-10-09)

| Check | Rule | Result |
|---|---|---|
| O1, O2 | Labels and edge types = classes and properties | ✅ 11 = 11, 11 = 11 |
| O3 | Every edge goes from domain to range | ✅ 62,178 edges |
| O4 | Cardinalities | ❌ **87 papers have 2 venues** (`APPEARED_AT` max 1). Every other cardinality holds |
| O5 | Required properties present | ✅ |
| O6 | Exactly one primary obstruction per problem | ✅ |
| O7 | `RELATED_TO` stored once per pair | ✅ |
| O8 | No orphan nodes | ✅ |
| O9 | Assumptions are extracted where the page states them | ℹ️ **404 problems have no `Assumption`; 189 of them do state assumptions** in a bold heading the parser misses (an inline `(i) … (ii) …` list, not bullets) |
| O10 | Every problem has open questions | ℹ️ 8 problems have none |

**What fixes the two real gaps:**

- **O4:** choose one venue per paper. Prefer a real venue over `arXiv` and resolve aliases
  (`NSDI` = `USENIX NSDI`, `CACM` = `Communications of the ACM`, `IJCV`). Report the 8 ICLR/ICML
  and 2 ICML/NeurIPS disagreements to `ai_research`, since the catalog contradicts itself there.
- **O9:** teach `parse_assumptions` the inline `(i)`/`(ii)` form. That would add assumptions to
  up to 189 problems.

Both change the built graph, so they belong in a v1.1 rebuild, not in this ontology change.

## Followed, not imported

| Ontology | Publisher | How we use it |
|---|---|---|
| SKOS | W3C | `Topic` and `Obstruction` are concepts; topic areas would be `skos:broader` (docs/taxonomy.md R1) |
| PROV-O | W3C | `source`, `source_url` (`hadPrimarySource`), `method` (the activity), `FROM_SOURCE` (`wasDerivedFrom`) |
| CiTO, FaBiO (SPAR) | SPAR / Univ. of Bologna, Oxford | citation roles; `Paper` |
| schema.org | schema.org | `Paper`, `Person`, `Venue`, `Institution` |
| DCAT, Dublin Core terms | W3C, DCMI | `DataSource`; `subject`, `creator`, `isPartOf`, `relation` |
| ORKG | TIB Hannover | the `Problem` class |
