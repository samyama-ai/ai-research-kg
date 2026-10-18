# Standards, coding systems, taxonomies and ontologies

Every standard, coding system, taxonomy and ontology the AI Research KG is built on: what is in
the graph from each, what is only planned, and whether the graph keeps its rules. Layout follows
[enterprise-valuation-kg docs/standards.md](https://git.samyama.ai/Samyama.ai/enterprise-valuation-kg/src/branch/main/docs/standards.md).

v0.3.2, 2026-10-12. v0.2 (2026-10-07) chose the sources; v0.3 (2026-10-09) added what the graph
actually holds and checks it; v0.3.1 (2026-10-12) answered the AI review of PR #3 (counts, status
icons, sources); v0.3.2 (2026-10-12) describes v1.1: provenance dates from the fetch lock, one
venue per paper with `venue_variants`, the venue arithmetic below, and the engine check of that day.
Numbers are for **v1.1** (29,707 nodes, 62,842 edges), which fixed the three rules v1 broke.
Every count is measured by `python -m etl.conformance`, with the check ids
from [conformance.md](conformance.md).

**Approach: do what the DBMS Research KG did.** Its source repo `dbms_research` resolves people
with **DBLP**, checks references with **arXiv, Crossref, DataCite and DBLP**, and releases content
under **CC BY 4.0**. It uses neither ACM CCS nor Semantic Scholar. This KG copies those choices.
**v1 uses the catalog only** (no external lookups), so the outside identifiers are 🔑 planned,
not loaded.

| Kind | What it is | Example here | How many |
|---|---|---|---:|
| **Coding system** | A list of codes, each code naming one thing | `arXiv:2406.11779`; `20-interpretability/internals-based-safety-verification`; `CITES.role = sota` | **9 external + 14 own** (3 identifier conventions + 11 code lists) |
| **Taxonomy** | Codes arranged as a tree, or a fixed classification | the 35 topics of TAXONOMY.md; the 5 obstruction types | **2 in use + 2 proposed levels** |
| **Ontology** | What kinds of thing exist and how they relate | `(Problem)-[:CITES {role}]->(Paper)` = `cito:cites` | **1 own + 8 followed** |
| **Standard / framework** | A rulebook we follow or reuse as a vocabulary | ISO 8601 dates; PROV-O provenance; FAIR | **5 followed + 1 proposed + 4 later (RAI)** |

Status key: ✅ **loaded** = in the graph today · 🔑 **identifier, planned** = will be a property
once external lookups are allowed · 📐 **pattern** = we follow its structure; nothing is imported
· 🔜 **later**. In the "Follows it?" columns, ✅ = the graph keeps the rule, ❌ = it breaks it (the
fix is tracked at the top of [conformance.md](conformance.md)), ⚠️ = proposed, not decided yet.
Planned (🔑) rows have nothing to follow yet, so that column says "— not loaded"; what the v1
measurements say about them is written out below each table. Standards we deliberately don't
use have their own section, with no icon.

## Coding systems

### External (9)

| Coding system | Authority | Codes | In the graph | Status | Follows it? |
|---|---|---|---|---|---|
| **arXiv identifier** (`YYMM.NNNNN`) | arXiv / Cornell | papers | `Paper.arxiv_id`, id `paper:arxiv:<id>`: **3,081** papers | ✅ | ✅ all valid (C4). 5 papers have a venue year before their arXiv month; that's normal (C5) |
| **DOI** (ISO 26324) | International DOI Foundation | papers | `Paper.doi`, id `paper:doi:<doi>`: **1** paper | ✅ | ✅ (C6). The catalog rarely gives DOIs; never guessed |
| **ISO 8601** dates | ISO | dates | `first_added`, `last_reviewed`, `last_substantive_update` as `YYYY-MM` | ✅ | ✅ 3,000 values (C7) |
| **Git commit SHA-1** | git | source version | `DataSource.version` = `a02e87b3…` (40 hex) | ✅ | ✅ equals the pinned commit (C8) |
| **DBLP person id** (`pid`) | Schloss Dagstuhl (CC0) | researchers | `Person.dblp_pid` | 🔑 | — not loaded |
| **ORCID iD** (16 characters in four groups, `0000-0002-1825-0097`; the last is a checksum and can be `X`) | ORCID | researchers | `Person.orcid`, only when DBLP gives it | 🔑 | — |
| **DBLP stream key** (`conf/nips`, `journals/jmlr`) | Schloss Dagstuhl | venues | `Venue.dblp_key` | 🔑 | — not loaded |
| **arXiv category** (`cs.LG`, `cs.CL`, `stat.ML`) | arXiv | subject areas | `Paper.arxiv_categories`; Topic crosswalk | 🔑 | — |
| **ROR / OpenAlex ids** | ROR; OurResearch (CC0) | institutions; works, authors | `Institution.ror_id`; fallback ids | 🔑 optional | — not loaded |

**What v1.1 measures about the planned identifiers.** 52% of the 15,102 author names are
initials or a surname only, so people can't be told apart without DBLP (C12). There are 527 venue
names, 24 of them still look like parser residue, and 77 papers are cited with more than one
venue (the others kept in `Paper.venue_variants`) (C11, C13), so venues need a canonical key such
as the DBLP stream. ROR and OpenAlex are optional
because the DBMS KG managed without them.

### Reference-checking services (planned, as DBMS `tools/verify_refs.py` and `dblp_*.py`)

Services, not coding systems, so they are not counted above. They supply or verify the codes.

| Service | Gives | Terms to respect | Status |
|---|---|---|---|
| **arXiv API** (legacy API, Atom) | full author lists, categories, dates for an arXiv id | **max 1 request every 3 s, one connection**; batch up to ~100 ids per request (`id_list`); cache in `data/`; metadata CC0 | 🔑 |
| **Crossref REST API** | metadata for a DOI | open metadata; polite pool with a `mailto` | 🔑 |
| **DataCite REST API** | DOIs Crossref doesn't hold, e.g. arXiv DOIs `10.48550/…` | CC0 metadata | 🔑 |
| **DBLP** (XML dump or search API) | person ids, stream keys, affiliations | CC0; record the dump date | 🔑 |

### Own (14): 3 identifier conventions + 11 code lists

The catalog's identifiers, plus the KG's controlled vocabularies, each a closed list in
[`schema/concepts.yaml`](../schema/concepts.yaml). Every coded value in the graph is on its list,
97,104 values in all (C9), and every listed code is used (C10).

| Coding system | Codes | Used for | Status |
|---|---|---|---|
| **Topic number** `NN` + slug | 35 (01–35, stable, never reused) | `Topic.number`, `topic:<NN-slug>` | ✅ (C3) |
| **Problem id** `NN-topic/slug` | 1,000 | `problem:<id>`; children `#assumption-N`, `#gap-N`, `#next-experiment` | ✅ (C1, C2) |
| **Node id patterns** | 11, one per label (`kg:idPattern` in the ontology) | every `id`; unique across the graph | ✅ all 29,707 (C1). v1 had one bad id, `venue:` |
| `problem_status` | 5 used + `stale` (unused) | `Problem.status` | ✅ |
| `catalog_provenance` | `synthesized` (all 1,000), `verified` | `Problem.catalog_provenance` | ✅ |
| `cites_role` | 7 (+ `benchmark` proposed), each mapped to CiTO | `CITES.role` (raw tag in `role_raw`) | ✅ |
| `gap_kind` | 3 + `unclassified` (41) | `OpenQuestion.kind` | ✅ |
| `obstruction` | 5 from TEMPLATE.md + `other` | `Obstruction` | ✅ |
| `assumption_status` | 4 | `Assumption.violated` | ✅ |
| `name_form` | 4 | `Person.name_form` | ✅ |
| `institution_kind` | 4 | `Institution.kind` | ✅ |
| `extraction_method` | 3 | `method` on every node but `DataSource` | ✅ |
| `relatedness_method` | 1 | `RELATED_TO.method` | ✅ |
| `provenance` | 1 (`real`) | `provenance` on every node | ✅ |

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
| 35 topics | arXiv categories | count the categories of each topic's cited arXiv papers | `(:Topic)-[:MAPS_TO {match: closeMatch / broadMatch}]->(:ArxivCategory)`: `closeMatch` for the category most papers carry, `broadMatch` for a parent such as `cs.AI` |
| 35 topics | OpenAlex topics *(optional)* | top 1–3 OpenAlex topics of each topic's papers | `MAPS_TO {match: broadMatch / closeMatch}` |
| Authors | DBLP person | DBLP search by title or arXiv id (as DBMS `dblp_*.py`) | `Person.dblp_pid` |
| Venue names | DBLP stream key | alias table, then DBLP | `Venue.dblp_key` |

## Ontologies (1 own + 8 followed)

**Our ontology** is [`schema/ai_research_kg.ttl`](../schema/ai_research_kg.ttl) (OWL/RDFS:
11 classes, 11 relationships with domain, range and cardinality, id patterns, code lists,
required properties and the two edge properties rules use),
explained in **[ontology.md](ontology.md)**. The conformance tool checks the graph against the
file. Result: all classes, relationships, domains, ranges and cardinalities match.

| Ontology | Publisher | How we use it | Status |
|---|---|---|---|
| **SKOS** | W3C | `Topic`, `Obstruction` are `skos:Concept`; `Topic.number` = `skos:notation`; topic areas would be `skos:broader` | 📐 |
| **PROV-O** | W3C | `source`, `source_url` (locator of the `prov:hadPrimarySource`), `method` = the activity, `FROM_SOURCE` = `prov:wasDerivedFrom`, `retrieved_at` ≈ `prov:generatedAtTime` (a date, so linked with `rdfs:seeAlso`, not a sub-property) | 📐 |
| **CiTO** (Citation Typing Ontology) | SPAR | `CITES` = `cito:cites`; each `role` maps to a CiTO property | 📐 |
| **FaBiO** | SPAR | `Paper` ⊂ `fabio:ScholarlyWork` | 📐 |
| **schema.org** | schema.org | `rdfs:seeAlso` from `Paper`, `Person`, `Institution`, `Venue` to `ScholarlyArticle`, `Person`, `Organization`, `Periodical` / `EventSeries` | 📐 |
| **FOAF** | FOAF project | `Person` ⊂ `foaf:Agent` (19 authors are collectives), `Institution` ⊂ `foaf:Organization` | 📐 |
| **DCAT + Dublin Core terms** | W3C, DCMI | `DataSource` ⊂ `dcat:Dataset`; `dcterms:subject / creator / isPartOf / relation` | 📐 |
| **ORKG** | TIB Hannover | `Problem` `rdfs:seeAlso` ORKG `Problem` (no formal URI) | 📐 |

## Standards and frameworks

### Followed (5) and proposed (1)

| Standard | Authority | What it requires here | Follows it? |
|---|---|---|---|
| **Naming conventions** (as the DBMS and Valuation KGs) | Samyama KG guide | labels PascalCase singular, edges UPPER_SNAKE, stable deterministic `id` | ✅ (S1, C2) |
| **PROV-O provenance** (docs/schema.md §4) | W3C | `source`, `provenance`, `method` on every node; `source_url` on page-level nodes | ✅ (S2, S3) |
| | | `retrieved_at` (when the pinned catalog was fetched, 2026-10-07) and `source_date` (the date of that version, 2026-09-10) on every node | ✅ all 29,707 nodes (S4). `retrieved_at` is the fetch recorded in `data/ai_research.lock.json`, `source_date` the commit's date, so a rebuild from the same checkout gives the same graph; `unknown` fails S4 |
| | | provenance on every edge | ℹ️ no edge carries it; implied by the problem page at the edge's source (S5) |
| **Computed facts are labelled** (Samyama KG guide) | — | `RELATED_TO` carries `method` and `score` | ✅ (S6) |
| **Pinned source** (Samyama KG guide) | — | `DataSource.version` = the exact commit; a rebuild gives the same graph | ✅ (C8; E1: on 2026-10-12 the engine held exactly this build, 29,707 nodes and 62,842 edges, checked with `--url`; `etl/snapshot.py` checks the loaded counts against the snapshot's `manifest.json`) |
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
| **Papers with Code** | Sunset in late July 2025: paperswithcode.com redirects to Hugging Face's Trending Papers, announced by Hugging Face's CTO on 2025-07-25; only the static GitHub archive remains. Leaderboards are out of scope (`scope.md`) |
| **Benchmark leaderboards, citation counts** | Out of scope (`scope.md` "Out of scope"): the graph is about problems, not rankings. The two "must return no data" questions are 40 (funding) and 41 (leaderboards) |
| **An RDF export of the data** | The ontology is in OWL so it can be checked and aligned; the graph itself stays a property graph |

## What is in the graph (v1.1)

| Label | Count | Source in the catalog |
|---|---:|---|
| `Problem` | 1,000 | one `topics/NN-*/<slug>.md` file |
| `Topic` | 35 | `TAXONOMY.md` |
| `Paper` | 4,932 | Key References (3,081 by arXiv id, 1 by DOI, 1,850 by title hash) |
| `Person` | 15,102 | author lists, names as written (ids keep letters of every script) |
| `Venue` | 527 | venue text, normalised by an alias list; one venue per paper (sister journals of Nature and Science are their own venues) |
| `Institution` | 51 | Current Research, matched against 52 known labs (MIRI never occurs) |
| `Assumption` | 3,263 | Formal Setting "Assumptions": lists, tables, inline (i)/(ii) and prose forms |
| `OpenQuestion` | 3,790 | What Is Not Known |
| `Obstruction` | 6 | Why It Is Hard |
| `FutureDirection` | 1,000 | Concrete Next Experiment |
| `DataSource` | 1 | the catalog, pinned at `a02e87b3` |

**62,842 edges** of 11 types; counts per type are in [ontology.md](ontology.md).

## Known limits (measured)

- **Venues:** each paper has one venue (a named venue beats a preprint server, then the most
  cited, then the first seen). In v1, 88 papers had more than one `APPEARED_AT` edge (103 surplus
  edges; one paper had 7). Eleven of those duplicates came from residue strings or aliases that v1.1
  resolves (`NSDI` = `USENIX NSDI`, `CACM`, `IJCV`, `TPAMI`), which leaves **77 papers the catalog
  cites with more than one venue**; every venue other than the chosen one is kept in
  `Paper.venue_variants` (C13), 15 papers having two or more. For 10 of the 77 the other venue is
  only arXiv; the other 67 name two real venues. In 18 of them the catalog contradicts itself about
  the conference: ICLR vs ICML 8 times, ICML vs NeurIPS 2, ACL vs NAACL 2, ICLR vs NeurIPS 2, and
  NAACL vs NeurIPS, ACL vs EMNLP, COLM vs ICML, COLM vs NeurIPS once each (all present in v1 too).
  24 venue names still look like residue (C11).
- **Assumptions:** 220 problems have none; 6 of them state assumptions only in unheaded
  numbered lists the parser does not read (O9).
- **Provenance:** edges carry no provenance of their own; the problem page at the edge's source
  implies it (S5).
- **People:** names are as written; 52% are initials or surname only, and nothing is merged.
- **Topic scope text:** 18 of the 166 scope terms name no problem (T8).

**Fixed in v1.1** (rebuilt 2026-10-09; the numbers here are from the conformance run of
2026-10-12 on that build): two venues for 88 papers (O4), the empty id `venue:` (C1),
`retrieved_at` missing on every node (S4), and assumptions missed in 185 problems (O9: 405 → 220
problems without one; 2,496 → 3,263 assumptions). The edge arithmetic, against the v1 graph as
rebuilt on 2026-10-12: 62,178 − 103 surplus `APPEARED_AT` edges (4,468 → 4,365) + 767 `RESTS_ON`
edges (2,496 → 3,263) = 62,842. Nodes: 28,974 − 34 Venue (561 → 527) + 767 Assumption = 29,707.
The failing checks were tracked at the top of [conformance.md](conformance.md) until then; the
licence still waits on the lead (issue #6).

## Sources (checked 2026-10-07, 2026-10-09 and 2026-10-12)

Two hosts appear below on purpose: the **source-data repos** (`ai_research`, `dbms_research`)
live on GitHub under `samyama-ai`; the **KG repos** (`enterprise-valuation-kg`, this one) live on
the team's Gitea under `Samyama.ai`.

- arXiv identifiers, licence and API terms: info.arxiv.org/help/arxiv_identifier.html, info.arxiv.org/help/license, info.arxiv.org/help/api/tou.html (rate limit)
- arXiv category taxonomy: arxiv.org/category_taxonomy
- Crossref and DataCite APIs: api.crossref.org (docs: www.crossref.org/documentation/retrieve-metadata/rest-api), support.datacite.org/docs/api
- DBLP licence (CC0) and API: dblp.org/faq, dblp.org/faq/How+to+use+the+dblp+search+API.html
- ORCID: info.orcid.org · ROR data dump: ror.readme.io/docs/data-dump · OpenAlex topics: help.openalex.org/data/topics
- CiTO and FaBiO: sparontologies.github.io/cito, sparontologies.github.io/fabio
- ORKG class `Problem`: orkg.org/api/classes/Problem (no formal URI; "A situation, person, or thing that needs attention…")
- SKOS, PROV-O, DCAT, Dublin Core terms: w3.org/TR/skos-reference, w3.org/TR/prov-o, w3.org/TR/vocab-dcat-3, dublincore.org/specifications/dublin-core/dcmi-terms
- schema.org, FOAF: schema.org, xmlns.com/foaf/spec
- ISO 8601: iso.org/iso-8601-date-and-time-format.html · DOI (ISO 26324): doi.org
- Responsible AI standards (later): nist.gov/itl/ai-risk-management-framework (AI RMF 1.0 and NIST AI 600-1), eur-lex.europa.eu Regulation (EU) 2024/1689, iso.org/standard/81230.html (ISO/IEC 42001:2023), oecd.org/en/topics/ai-principles.html
- DBMS approach: github.com/samyama-ai/dbms_research (README licence, `tools/dblp_*.py`, `tools/verify_refs.py`); its KG: github.com/samyama-ai/samyama-graph `case_studies/dbms-research`
- Not used: ACM CCS acm.org/publications/class-2012 · Semantic Scholar licence api.semanticscholar.org/license · Papers with Code shutdown: paperswithcode.com (redirects to huggingface.co/papers), Hugging Face forum thread discuss.huggingface.co/t/167174, secondary report hyper.ai/en/news/42900 (no primary Meta statement found)
- Reference layout: git.samyama.ai/Samyama.ai/enterprise-valuation-kg `docs/standards.md`
