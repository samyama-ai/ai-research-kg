# Standards, coding systems, taxonomies and ontologies

Every standard, coding system, taxonomy and ontology the AI Research KG is built on: what is in
the graph from each, what is only planned, and whether the graph keeps its rules. Layout follows
[enterprise-valuation-kg docs/standards.md](https://git.samyama.ai/Samyama.ai/enterprise-valuation-kg/src/branch/main/docs/standards.md).

v0.3, 2026-10-09. v0.2 (2026-10-07) chose the sources; v0.3 adds what the graph actually
holds and checks it. Numbers are for **v1.1** (29,696 nodes, 62,845 edges), which fixed the
three rules v1 broke. Every count is measured by `python -m etl.conformance`, with the check ids
from [conformance.md](conformance.md).

**Approach: do what the DBMS Research KG did.** Its source repo `dbms_research` resolves people
with **DBLP**, checks references with **arXiv, Crossref, DataCite and DBLP**, and releases content
under **CC BY 4.0**. It uses neither ACM CCS nor Semantic Scholar. This KG copies those choices.
**v1 uses the catalog only** (no external lookups), so the outside identifiers are 🔑 planned,
not loaded.

| Kind | What it is | Example here | How many |
|---|---|---|---:|
| **Coding system** | A list of codes, each code naming one thing | `arXiv:2406.11779`; `20-interpretability/internals-based-safety-verification`; `CITES.role = sota` | **9 external + 12 own** |
| **Taxonomy** | Codes arranged as a tree, or a fixed classification | the 35 topics of TAXONOMY.md; the 5 obstruction types | **2 in use + 2 proposed levels** |
| **Ontology** | What kinds of thing exist and how they relate | `(Problem)-[:CITES {role}]->(Paper)` = `cito:cites` | **1 own + 7 followed** |
| **Standard / framework** | A rulebook we follow or reuse as a vocabulary | ISO 8601 dates; PROV-O provenance; FAIR | **6 followed + 4 later (RAI)** |

Status key: ✅ **loaded** = in the graph today · 🔑 **identifier, planned** = will be a property
once external lookups are allowed · 📐 **pattern** = we follow its structure; nothing is imported
· 🔜 **later** · ❌ **not used**.

## Coding systems

### External (9)

| Coding system | Authority | Codes | In the graph | Status | Follows it? |
|---|---|---|---|---|---|
| **arXiv identifier** (`YYMM.NNNNN`) | arXiv / Cornell | papers | `Paper.arxiv_id`, id `paper:arxiv:<id>`: **3,081** papers | ✅ | ✅ all valid (C4). 5 papers have a venue year before their arXiv month; that's normal (C5) |
| **DOI** (ISO 26324) | International DOI Foundation | papers | `Paper.doi`, id `paper:doi:<doi>`: **1** paper | ✅ | ✅ (C6). The catalog rarely gives DOIs; never guessed |
| **ISO 8601** dates | ISO | dates | `first_added`, `last_reviewed`, `last_substantive_update` as `YYYY-MM` | ✅ | ✅ 3,000 values (C7) |
| **Git commit SHA-1** | git | source version | `DataSource.version` = `a02e87b3…` (40 hex) | ✅ | ✅ equals the pinned commit (C8) |
| **DBLP person id** (`pid`) | Schloss Dagstuhl (CC0) | researchers | `Person.dblp_pid` | 🔑 | not yet: **52%** of 15,097 authors are initials or surname only (C12) |
| **ORCID iD** | ORCID | researchers | `Person.orcid`, only when DBLP gives it | 🔑 | — |
| **DBLP stream key** (`conf/nips`, `journals/jmlr`) | Schloss Dagstuhl | venues | `Venue.dblp_key` | 🔑 | needed: 522 venues, 24 still look like residue (C11); 67 papers have other venues in the catalog (C13) |
| **arXiv category** (`cs.LG`, `cs.CL`, `stat.ML`) | arXiv | subject areas | `Paper.arxiv_categories`; Topic crosswalk | 🔑 | — |
| **ROR / OpenAlex ids** | ROR; OurResearch (CC0) | institutions; works, authors | `Institution.ror_id`; fallback ids | 🔑 optional | DBMS didn't use them |

### Own (12)

The catalog's identifiers, plus the KG's controlled vocabularies, each a closed list in
[`vocab/concepts.yaml`](../vocab/concepts.yaml). Every coded value in the graph is on its list,
97,104 values in all (C9), and every listed code is used (C10).

| Coding system | Codes | Used for | Status |
|---|---|---|---|
| **Topic number** `NN` + slug | 35 (01–35, stable, never reused) | `Topic.number`, `topic:<NN-slug>` | ✅ (C3) |
| **Problem id** `NN-topic/slug` | 1,000 | `problem:<id>`; children `#assumption-N`, `#gap-N`, `#next-experiment` | ✅ (C1, C2) |
| **Node id patterns** | 11, one per label (`kg:idPattern` in the ontology) | every `id`; unique across the graph | ✅ all 29,696 (C1). v1 had one bad id, `venue:` |
| `problem_status` | 5 used + `stale` (unused) | `Problem.status` | ✅ |
| `catalog_provenance` | `synthesized` (all 1,000), `verified` | `Problem.catalog_provenance` | ✅ |
| `cites_role` | 7 (+ `benchmark` proposed), each mapped to CiTO | `CITES.role` (raw tag in `role_raw`) | ✅ |
| `gap_kind` | 3 + `unclassified` (41) | `OpenQuestion.kind` | ✅ |
| `obstruction` | 5 from TEMPLATE.md + `other` | `Obstruction` | ✅ |
| `assumption_status` | 4 | `Assumption.violated` | ✅ |
| `name_form` | 4 | `Person.name_form` | ✅ |
| `institution_kind` | 4 | `Institution.kind` | ✅ |
| `extraction_method`, `relatedness_method`, `provenance` | 3 · 1 · 1 | `method`, `RELATED_TO.method`, `provenance` | ✅ |

## Taxonomies

| Taxonomy | Levels | In the graph | Follows it? |
|---|---|---|---|
| **ai_research TAXONOMY.md** | 35 topics (flat) | `Topic` (35), `IN_TOPIC` (1,000) | ✅ exactly: all 7 checks T1–T7 pass |
| **Obstruction types** (TEMPLATE.md §6) | 5 + other | `Obstruction` (6), `BLOCKED_BY` (1,448) | ✅ keyword-classified, one primary per problem (O6) |
| Topic areas *(proposed)* | 6 areas above the 35 topics | `topic_area` in vocab, not built | 64% of `RELATED_TO` links stay inside one area (T11) |
| Subtopics *(proposed)* | the 166 scope terms below the topics | not built | 18 terms name no problem; 218 problems match no term (T8, T9) |

Conformance in detail, and the seven refinements: **[taxonomy.md](taxonomy.md)**.

**Crosswalks** (all planned; they need external lookups):

| From | To | How | Edge |
|---|---|---|---|
| 35 topics | arXiv categories | count the categories of each topic's cited arXiv papers | `(:Topic)-[:MAPS_TO {match: closeMatch}]->(:ArxivCategory)` |
| 35 topics | OpenAlex topics *(optional)* | top 1–3 OpenAlex topics of each topic's papers | `MAPS_TO {match: broadMatch / closeMatch}` |
| Authors | DBLP person | DBLP search by title or arXiv id (as DBMS `dblp_*.py`) | `Person.dblp_pid` |
| Venue names | DBLP stream key | alias table, then DBLP | `Venue.dblp_key` |

## Ontologies (1 own + 7 followed)

**Our ontology** is [`ontology/ai_research_kg.ttl`](../ontology/ai_research_kg.ttl) (OWL/RDFS:
11 classes, 11 relationships with domain, range and cardinality, id patterns, code lists),
explained in **[ontology.md](ontology.md)**. The conformance tool checks the graph against the
file. Result: all classes, relationships, domains, ranges and cardinalities match.

| Ontology | Publisher | How we use it | Status |
|---|---|---|---|
| **SKOS** | W3C | `Topic`, `Obstruction` are `skos:Concept`; `Topic.number` = `skos:notation`; topic areas would be `skos:broader` | 📐 |
| **PROV-O** | W3C | `source`, `source_url` = `prov:hadPrimarySource`, `method` = the activity, `FROM_SOURCE` = `prov:wasDerivedFrom` | 📐 |
| **CiTO** (Citation Typing Ontology) | SPAR | `CITES` = `cito:cites`; each `role` maps to a CiTO property | 📐 |
| **FaBiO** | SPAR | `Paper` ≈ `fabio:ScholarlyWork` | 📐 |
| **schema.org** | schema.org | `ScholarlyArticle`, `Person`, `Organization`, `Periodical` | 📐 |
| **DCAT + Dublin Core terms** | W3C, DCMI | `DataSource` ⊂ `dcat:Dataset`; `dcterms:subject / creator / isPartOf / relation` | 📐 |
| **ORKG** | TIB Hannover | `Problem` ≈ ORKG `Problem` | 📐 |

## Standards and frameworks

### Followed (6)

| Standard | Authority | What it requires here | Follows it? |
|---|---|---|---|
| **Naming conventions** (as the DBMS and Valuation KGs) | Samyama KG guide | labels PascalCase singular, edges UPPER_SNAKE, stable deterministic `id` | ✅ (S1, C2) |
| **PROV-O provenance** (docs/schema.md §4) | W3C | `source`, `provenance`, `method` on every node; `source_url` on page-level nodes | ✅ (S2, S3) |
| | | `retrieved_at` (when the pinned catalog was fetched, 2026-10-07) and `source_date` (the date of that version, 2026-09-10) on every node | ✅ all 29,696 nodes (S4). Both come from git, so a rebuild from the same checkout gives the same graph |
| | | provenance on every edge | ℹ️ no edge carries it; implied by the problem page at the edge's source (S5) |
| **Computed facts are labelled** (Samyama KG guide) | — | `RELATED_TO` carries `method` and `score` | ✅ (S6) |
| **Pinned source** (Samyama KG guide) | — | `DataSource.version` = the exact commit; a rebuild gives the same graph | ✅ (C8, E1: the engine holds exactly the built graph) |
| **ISO 8601** | ISO | dates | ✅ (C7) |
| **CC BY 4.0** (as `dbms_research`) | Creative Commons | licence of the graph | ⚠️ proposed; `ai_research` states no licence, so `DataSource.licence` says "none stated" (S8). Blocks publishing only |

### Later: Responsible AI extension (4)

Recorded so the schema has room for them. **Not loaded in v1.**

| Standard | Version | Publisher | Licence / access | Planned use |
|---|---|---|---|---|
| **NIST AI Risk Management Framework** | AI RMF 1.0 (2023) + Generative AI Profile (NIST AI 600-1, 2024) | NIST | US government work, public domain | `RAIFramework`; functions Govern, Map, Measure, Manage as `RAIPrinciple` |
| **EU AI Act** | Regulation (EU) 2024/1689 | European Union | free to reuse | risk categories and obligations, linked to safety and transparency problems |
| **ISO/IEC 42001** | 2023 | ISO / IEC | paywalled | name and clause titles only |
| **OECD AI Principles** | 2019, updated 2024 | OECD | free to read | principles (fairness, transparency, robustness…) as `RAIPrinciple` |

## Deliberately not used

| Standard | Why not |
|---|---|
| **ACM CCS 2012** | Not used by DBMS; free only for educational and research use |
| **Semantic Scholar** | Not used by DBMS; ODC-BY needs attribution |
| **Papers with Code** | Shut down 2025-07-24; leaderboards are out of scope (`scope.md`) |
| **Benchmark leaderboards, citation counts** | Out of scope: the graph is about problems, not rankings (question 41 returns "no data") |
| **An RDF export of the data** | The ontology is in OWL so it can be checked and aligned; the graph itself stays a property graph |

## What is in the graph (v1.1)

| Label | Count | Source in the catalog |
|---|---:|---|
| `Problem` | 1,000 | one `topics/NN-*/<slug>.md` file |
| `Topic` | 35 | `TAXONOMY.md` |
| `Paper` | 4,932 | Key References (3,081 by arXiv id, 1 by DOI, 1,850 by title hash) |
| `Person` | 15,097 | author lists, names as written |
| `Venue` | 522 | venue text, normalised by an alias list; one venue per paper |
| `Institution` | 50 | Current Research, matched against 50 known labs |
| `Assumption` | 3,263 | Formal Setting "Assumptions": lists, tables, inline (i)/(ii) and prose forms |
| `OpenQuestion` | 3,790 | What Is Not Known |
| `Obstruction` | 6 | Why It Is Hard |
| `FutureDirection` | 1,000 | Concrete Next Experiment |
| `DataSource` | 1 | the catalog, pinned at `a02e87b3` |

**62,845 edges** of 11 types; counts per type are in [ontology.md](ontology.md).

## Known limits (measured)

- **Venues:** each paper has one venue (a named venue beats arXiv, then the most cited). For 67
  papers the catalog gives another venue too, kept in `Paper.venue_variants` (C13); for some the
  catalog contradicts itself (ICLR vs ICML 8 times). 24 venue names still look like residue (C11).
- **Assumptions:** 220 problems have none; 6 of them state assumptions only in unheaded
  numbered lists the parser does not read (O9).
- **Provenance:** edges carry no provenance of their own; the problem page at the edge's source
  implies it (S5).
- **People:** names are as written; 52% are initials or surname only, and nothing is merged.
- **Topic scope text:** 18 of the 166 scope terms name no problem (T8).

**Fixed in v1.1** (2026-10-09): two venues for 87 papers (O4), the empty id `venue:` (C1),
`retrieved_at` missing on every node (S4), and assumptions missed in 184 problems (O9: 404 → 220
problems without one; 2,499 → 3,263 assumptions).

## Sources (checked 2026-10-07 and 2026-10-09)

- arXiv identifiers and licence: info.arxiv.org/help/arxiv_identifier.html, info.arxiv.org/help/license
- CiTO and FaBiO: sparontologies.github.io/cito, sparontologies.github.io/fabio
- ORKG class `Problem`: orkg.org/api/classes/Problem (no formal URI; "A situation, person, or thing that needs attention…")
- SKOS, PROV-O, DCAT: w3.org/TR/skos-reference, w3.org/TR/prov-o, w3.org/TR/vocab-dcat-3
- DBMS approach: github.com/samyama-ai/dbms_research (README licence, `tools/dblp_*.py`, `tools/verify_refs.py`)
- ACM CCS: acm.org/publications/class-2012 · Semantic Scholar licence: api.semanticscholar.org/license
- Reference layout: git.samyama.ai/Samyama.ai/enterprise-valuation-kg `docs/standards.md`
