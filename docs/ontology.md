# Ontology

What kinds of thing the AI Research KG holds, how they relate, and the rules each must keep.
The machine-readable version is [`ontology/ai_research_kg.ttl`](../ontology/ai_research_kg.ttl)
(OWL/RDFS in Turtle). `etl/conformance.py` reads that file and checks the graph against it;
the result is in [conformance.md](conformance.md), checks O1–O10.

v0.2.1, 2026-10-12 (v0.2 2026-10-09). It describes the v1.1 graph as built (11 labels, 11 edge types), not the larger
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
| `Problem` | One open AI research problem (one catalog page) | 1,000 | see also ORKG `Problem` | `problem:NN-topic/slug` |
| `Topic` | One of the 35 topics of TAXONOMY.md | 35 | subclass of `skos:Concept` | `topic:NN-slug` |
| `Paper` | A cited publication | 4,932 | subclass of `fabio:ScholarlyWork`; see also `schema:ScholarlyArticle` | `paper:arxiv:…` (new or old style) / `paper:doi:…` / `paper:t:<hash>` |
| `Person` | An author, as written in the reference | 15,102 | subclass of `foaf:Agent` (19 are collectives such as "Llama Team"); see also `schema:Person` | `person:<slug, letters of any script>` |
| `Venue` | Where a paper appeared | 527 | see also `schema:Periodical`, `schema:EventSeries` (one class covers both, so neither is a superclass) | `venue:<slug>` |
| `Institution` | A lab named in Current Research | 51 | subclass of `foaf:Organization`; see also `schema:Organization` | `institution:<key>` |
| `Assumption` | An assumption one problem rests on | 3,263 | (ours) | `<problem id>#assumption-N` |
| `OpenQuestion` | One gap in what is known, with its kind | 3,790 | (ours) | `<problem id>#gap-N` |
| `Obstruction` | A type of reason a problem is hard | 6 | subclass of `skos:Concept` | `obstruction:<code>` |
| `FutureDirection` | The concrete next experiment | 1,000 | (ours) | `<problem id>#next-experiment` |
| `DataSource` | The pinned catalog | 1 | subclass of `dcat:Dataset` | `datasource:<name>` |

How the alignments are written: `rdfs:subClassOf` where the published class is genuinely
broader than ours (every Paper is a `fabio:ScholarlyWork`), `rdfs:seeAlso` where it is only
similar. `skos:closeMatch` is not used on classes: SKOS mapping properties are for SKOS concepts
(our `Topic` and `Obstruction` nodes), not for OWL classes. ORKG (the Open Research Knowledge
Graph, TIB Hannover) is the closest published model of research problems; its class `Problem`
has no formal URI, so the link is `rdfs:seeAlso https://orkg.org/class/Problem`. No published
ontology has assumptions, open questions or next experiments, so those three classes are ours.

## Relationships (11)

| Relationship | Domain → Range | Cardinality | Aligned with | Count |
|---|---|---|---|---:|
| `IN_TOPIC` | Problem → Topic | exactly 1 per problem; ≥ 1 per topic | `dcterms:subject` | 1,000 |
| `CITES {role, role_raw, position}` | Problem → Paper | ≥ 1 per paper | `cito:cites`; `role` refines it (below) | 12,615 |
| `AUTHORED_BY {position}` | Paper → Person | ≥ 1 per person | `dcterms:creator` | 28,757 |
| `APPEARED_AT` | Paper → Venue | at most 1 per paper; ≥ 1 per venue | `dcterms:isPartOf` | 4,365 |
| `RESTS_ON {position}` | Problem → Assumption | exactly 1 problem per assumption | (ours) | 3,263 |
| `HAS_GAP {position}` | Problem → OpenQuestion | exactly 1 problem per question | (ours) | 3,790 |
| `BLOCKED_BY {detail, is_primary}` | Problem → Obstruction | ≥ 1 per problem; exactly 1 primary | (ours) | 1,448 |
| `HAS_NEXT_EXPERIMENT` | Problem → FutureDirection | at most 1 per problem; exactly 1 per direction | (ours) | 1,000 |
| `ACTIVE_ON {direction}` | Institution → Problem | ≥ 1 per institution | (ours) | 2,476 |
| `RELATED_TO {method, shared_papers, score}` | Problem → Problem | symmetric; stored once, smaller id first; **computed** | `dcterms:relation` | 3,128 |
| `FROM_SOURCE` | Problem → DataSource | exactly 1 per problem | `prov:wasDerivedFrom` | 1,000 |

### Citation roles as CiTO properties

CiTO (the Citation Typing Ontology, SPAR) names the reasons one work cites another. Each
`CITES.role` maps to the nearest CiTO property:

| `role` | CiTO | Citations |
|---|---|---:|
| `sota` | `cito:citesAsAuthority` | 3,983 |
| `foundational` | `cito:obtainsBackgroundFrom` | 2,952 |
| `context` | `cito:citesForInformation` | 1,911 |
| `evidence` | `cito:citesAsEvidence` | 1,750 |
| `survey` | `cito:citesAsRecommendedReading` | 887 |
| `method` | `cito:usesMethodIn` | 826 |
| `caution` | `cito:critiques` | 306 |
| `benchmark` *(proposed)* | `cito:usesDataFrom` | — |

These are nearest-term mappings recorded in `vocab/concepts.yaml` (`maps_to`), not formal
sub-properties: CiTO's properties hold between two works, while `role` is a string on an edge.
The catalog's own 669 free-text tags are kept in `role_raw`.

## Properties and code lists

Every node carries `id`, `source`, `provenance`, `retrieved_at` (when the pinned catalog was fetched, from `data/ai_research.lock.json`, written at fetch time; left off when no fetch is recorded), `source_date` (the date of that catalog version) and (all but `DataSource`) `method`. Nodes read
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

Two conventions the checker reads from the file, so that no rule lives only in code:
`kg:propertyName` gives a property's name in the graph where two classes share one
(`kind_institution` and `kind_gap` are both `kind`; `relatedness_method` is `method` on
`RELATED_TO`), and `kg:notRequiredOn` lists the classes a required property may be missing from
(`method` is required on every node but `DataSource`). Edge properties that a rule uses are
declared too: `is_primary` on `BLOCKED_BY` (O6) and `score` on `RELATED_TO` (C9).
`source_url` is the locator of a node's `prov:hadPrimarySource`; it is a literal, so it is linked
with `rdfs:seeAlso`, not declared a sub-property of that object property.

## Does the graph follow the ontology? (measured 2026-10-09)

| Check | Rule | Result |
|---|---|---|
| O1, O2 | Labels and edge types = classes and properties | ✅ 11 = 11, 11 = 11 |
| O3 | Every edge goes from domain to range | ✅ 62,842 edges |
| O4 | Cardinalities | ✅ (v1 failed: 87 papers had 2 venues) |
| O5 | Required properties present | ✅ |
| O6 | Exactly one primary obstruction per problem | ✅ |
| O7 | `RELATED_TO` stored once per pair | ✅ |
| O8 | No orphan nodes | ✅ |
| O9 | Assumptions are extracted where the page states them | ℹ️ 220 problems have no `Assumption`; 6 of them state assumptions only in unheaded numbered lists (v1: 405 and 190) |
| O10 | Every problem has open questions | ℹ️ 8 problems have none |

**Fixed in v1.1:**

- **O4:** one venue per paper. A named venue beats `arXiv`, then the most cited, then the first
  seen; new aliases (`NSDI`, `FAST`, `CACM`, `IJCV`, `TPAMI`). The catalog's other venues for 77
  papers (preprint servers included) are kept in `Paper.venue_variants` as a list; the ICLR/ICML contradictions should go to
  `ai_research`.
- **O9:** `parse_assumptions` reads all four forms the catalog uses: a list, a table, an inline
  `(i)`/`(ii)` list, and prose items `Name: *status* — why`.

Both changed the built graph, so they were done in the v1.1 rebuild (PR #5), with the failing checks
tracked at the top of [conformance.md](conformance.md) until then.

## Followed, not imported

| Ontology | Publisher | How we use it |
|---|---|---|
| SKOS | W3C | `Topic` and `Obstruction` are concepts; topic areas would be `skos:broader` (docs/taxonomy.md R1) |
| PROV-O | W3C | `source`, `source_url` (`hadPrimarySource`), `method` (the activity), `FROM_SOURCE` (`wasDerivedFrom`) |
| CiTO, FaBiO (SPAR) | SPAR / Univ. of Bologna, Oxford | citation roles; `Paper` |
| schema.org | schema.org | `rdfs:seeAlso` from `Paper`, `Person`, `Venue`, `Institution` |
| FOAF | FOAF project | `Person` ⊂ `foaf:Agent`, `Institution` ⊂ `foaf:Organization` |
| DCAT, Dublin Core terms | W3C, DCMI | `DataSource`; `subject`, `creator`, `isPartOf`, `relation` |
| ORKG | TIB Hannover | the `Problem` class |
