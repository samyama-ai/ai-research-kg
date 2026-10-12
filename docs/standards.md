# AI Research KG — Standards, Coding Systems, Taxonomies and Ontologies

Phase 4 of *How to Build a Samyama Knowledge Graph*. This file lists every standard, identifier scheme, taxonomy and ontology the graph **uses**, **follows**, or **deliberately leaves out**, and why.

Draft v0.2, 2026-10-07. Licences and versions were checked on that date.

**Approach: do what the DBMS Research KG did.** Its source repo `dbms_research` resolves people with **DBLP** and checks references with **arXiv, Crossref, DataCite and DBLP** (`tools/dblp_*.py`, `tools/verify_refs.py`), and releases content under **CC BY 4.0**. It uses neither ACM CCS nor Semantic Scholar. This KG copies those choices.

**Rule:** reuse the codes the field already uses instead of inventing our own. That's what makes this graph joinable with other data, such as the DBMS and Maths research KGs, OpenAlex, or a company's publication list.

---

## 1. Summary

| # | Name | Kind | Decision | Used for |
|---|---|---|---|---|
| 1 | ai_research `TAXONOMY.md` | Taxonomy | ✅ **Use** (primary) | `Topic` nodes |
| 2 | arXiv identifier | Identifier standard | ✅ **Use** | `Paper.id` |
| 3 | arXiv category taxonomy | Coding system | ✅ **Use** | `Paper.arxiv_categories`, Topic crosswalk |
| 4 | DOI | Identifier standard | ✅ **Use** where present | `Paper.doi` |
| 5 | ORCID iD | Identifier standard | ✅ **Use** where DBLP gives it | `Person.orcid` |
| 6 | **DBLP** | Identifier + bibliography | ✅ **Use** (as DBMS) | `Person.dblp_pid`, `dblp_url`, affiliation; reference checks |
| 7 | Crossref + DataCite | DOI metadata services | ✅ **Use** (as DBMS) | reference verification |
| 8 | ISO 8601 | Standard | ✅ **Follow** | all dates |
| 9 | PROV-O | Ontology (pattern) | ✅ **Follow** | provenance fields |
| 10 | SKOS | Ontology (pattern) | ✅ **Follow** | Topic hierarchy and crosswalks |
| 11 | OpenAlex IDs + Topics | Identifier + taxonomy | ⚠️ **Optional** (DBMS didn't use it) | fallback for people DBLP misses; Topic crosswalk |
| 12 | ROR ID | Identifier standard | ⚠️ **Optional** (DBMS didn't use it) | `Institution.ror_id` |
| 13 | ACM CCS 2012 | Taxonomy | ❌ **Not used** (as DBMS; licence is non-commercial) | — |
| 14 | Semantic Scholar | Identifier + graph | ❌ **Not used** (as DBMS) | — |
| 15 | Papers with Code | Taxonomy (tasks/methods) | ❌ **Not used** | — |
| 16 | NIST AI RMF 1.0 | Standard (RAI) | 🔜 **Later** | RAI extension |
| 17 | EU AI Act | Regulation (RAI) | 🔜 **Later** | RAI extension |
| 18 | ISO/IEC 42001:2023 | Standard (RAI) | 🔜 **Later**, name only | RAI extension |
| 19 | OECD AI Principles | Principles (RAI) | 🔜 **Later** | RAI extension |

---

## 2. Details

### 2.1 Used

| Name | Version | Publisher | Licence | Link | Format | Size | Notes |
|---|---|---|---|---|---|---|---|
| **ai_research TAXONOMY.md** | git commit (pin in `DataSource`) | Samyama.ai | ⚠️ **no licence file**: ask the lead | github.com/samyama-ai/ai_research | Markdown table | 35 topics | Topic numbers are stable identity, assigned once and never changed. Primary taxonomy. |
| **arXiv identifier** | `YYMM.NNNNN` (5 digits since 2015, 4 before; old-style `archive/YYMMNNN` before 2007) | arXiv / Cornell | metadata CC0 1.0 | info.arxiv.org/help/arxiv_identifier.html | string | 3,081 unique IDs in the catalog; 71% of citations have one | Best join key for papers. `Paper.id` is `paper:arxiv:2406.11779` (as `etl/build.py` mints it). Papers without one fall back to `paper:doi:<doi>`, then `paper:t:<12-hex hash of the normalised title>`. |
| **arXiv category taxonomy** | live list | arXiv | metadata CC0 1.0 | arxiv.org/category_taxonomy | web page / API | ~40 `cs.*` categories, plus `stat.ML`, `eess.*` | Fetched per paper from the arXiv API. Gives each Paper its primary and cross-list categories. |
| **arXiv API** | legacy API | arXiv | metadata CC0; API terms of use | info.arxiv.org/help/api/tou.html | Atom XML | — | **Max 1 request every 3 seconds, one connection.** Batch up to ~100 IDs per request (`id_list`) and cache in `data/`. |
| **DOI** | ISO 26324 | DOI Foundation / Crossref | identifiers free; Crossref metadata open | doi.org | string | only 8 citations carry one | Store when present. Never guess one. |
| **ORCID iD** | — | ORCID | public data file CC0 | orcid.org | 16 characters in four groups, `0000-0002-1825-0097`; the last is a checksum and can be `X` | — | Store only when a lookup returns it. Never infer from a name. |
| **DBLP** | live (dump date recorded) | Schloss Dagstuhl | CC0 1.0 | dblp.org | XML dump / search API | covers NeurIPS, ICML, ICLR, ACL, CVPR… | **Primary person resolution, as in DBMS** (which matched 1,966 researchers to a `dblp_pid` + affiliation). Never merge a bare surname into a full name. |
| **Crossref** | REST API | Crossref | metadata facts, open | api.crossref.org | JSON | — | Verify references that have a DOI (as DBMS `verify_refs.py`). |
| **DataCite** | REST API | DataCite | CC0 metadata | api.datacite.org | JSON | — | Verify DOIs that Crossref doesn't hold, e.g. arXiv DOIs `10.48550/…` (as DBMS). |

### 2.2 Followed (patterns, not data)

| Name | Publisher | Licence | Use |
|---|---|---|---|
| **ISO 8601** | ISO | standard (free to follow) | All dates as `YYYY-MM` or `YYYY-MM-DD`. The catalog already uses `YYYY-MM`. |
| **PROV-O** | W3C | W3C document licence | Followed as a naming pattern only, as in the Valuation KG: `source`, `source_url` (the primary source's locator), `method` (the activity) on every node, and `retrieved_at` planned (not in v1). No PROV-O triples are produced and nothing is validated against the ontology. |
| **SKOS** | W3C | W3C document licence | Vocabulary for crosswalk edges: `exactMatch` / `closeMatch` / `broadMatch` (see Section 3). |

### 2.3 Optional (not in DBMS; add only if needed)

| Name | Version | Publisher | Licence | Use if… |
|---|---|---|---|---|
| **OpenAlex** | live | OurResearch | CC0 | DBLP misses an author, or to crosswalk our topics to OpenAlex's ~4,516 topics (4 domains → 26 fields → 252 subfields). |
| **ROR** | v2.x dump | ROR | CC0 1.0 | We want labs joinable with other KGs (`Institution.ror_id`). DBMS kept the affiliation as text from DBLP. |

### 2.4 Not used

| Name | Why |
|---|---|
| **ACM CCS 2012** | Not used by DBMS. Free only for educational and research use; commercial use needs ACM's permission (www.acm.org/publications/class-2012). |
| **Semantic Scholar** | Not used by DBMS. Its ODC-BY licence also needs attribution in the README. |
| **Papers with Code** (tasks, methods, leaderboards) | Sunset in late July 2025: paperswithcode.com now redirects to Hugging Face's Trending Papers (huggingface.co/papers), announced by Hugging Face's CTO on 2025-07-25; only the static GitHub archive remains. Leaderboards are also **out of scope** (`scope.md`). |
| **Benchmark leaderboards** (LMArena, HELM…) | Out of scope: the graph is about problems, not model rankings. |
| **Citation counts** (Google Scholar, S2) | Out of scope (`scope.md` "Out of scope": citation counts from outside the catalog; the two "must return no data" questions are 40 funding and 41 leaderboards). Google Scholar also has no open licence. |

### 2.5 Later: Responsible AI extension

These are for the Responsible AI / Explainable AI work that gets merged in later. Record them now so the schema has room for them. **Don't load any of them in v1.**

| Name | Version | Publisher | Licence / access | Planned use |
|---|---|---|---|---|
| **NIST AI Risk Management Framework** | AI RMF 1.0 (Jan 2023) + Generative AI Profile (NIST AI 600-1, 2024) | NIST (US government) | US government work: public domain | `RAIFramework` + its functions (Govern, Map, Measure, Manage) as `RAIPrinciple` |
| **EU AI Act** | Regulation (EU) 2024/1689 | European Union | EU legal texts are free to reuse | Risk categories and obligations, linked to problems (safety, transparency) |
| **ISO/IEC 42001** | 2023 | ISO / IEC | **paywalled, copyrighted** | Name and clause titles only, never the text |
| **OECD AI Principles** | 2019, updated 2024 | OECD | free to read | High-level principles (fairness, transparency, robustness…) as `RAIPrinciple` |

---

## 3. Crosswalks (mappings between systems)

The guide says crosswalks are often the most valuable part. They become `MAPS_TO` edges carrying a SKOS match type.

| From | To | How it's made | Edge |
|---|---|---|---|
| our 35 Topics | arXiv categories | **By hand**, then checked by counting the categories of each topic's cited papers | `(:Topic)-[:MAPS_TO {match: 'closeMatch' / 'broadMatch'}]->(:ArxivCategory)`: `closeMatch` for the category most of a topic's papers carry, `broadMatch` for a parent category such as `cs.AI` (the example below uses both) |
| our 35 Topics | OpenAlex topics/subfields *(optional)* | Look up the OpenAlex topics of each topic's cited papers and keep the top 1–3 | `(:Topic)-[:MAPS_TO {match: 'broadMatch' / 'closeMatch'}]->(:ExternalTopic)` |
| Papers (arXiv ID) | OpenAlex work ID | API lookup | `Paper.openalex_id` property |
| Authors (name + paper) | DBLP person | DBLP search by title/arXiv ID, then take the author list (as DBMS `dblp_*.py`) | `Person.dblp_pid` property |
| Institutions (name) | ROR ID *(optional)* | ROR API "affiliation" matching, accepting only `chosen: true` matches | `Institution.ror_id` property |

**Example:** Topic `20-interpretability` → arXiv `cs.LG` (closeMatch), `cs.AI` (broadMatch) → OpenAlex topic "Explainable Artificial Intelligence (XAI)" (closeMatch).

That example is a **guess to check**. Confirm it by counting the categories of the papers cited by interpretability problems, as the guide says ("measure, don't assert").

---

## 4. Minimum set for v1

Answering the `scope.md` questions needs only:
1. **ai_research TAXONOMY** (topics)
2. **arXiv ID + arXiv API** (papers, full author names, categories)
3. **DBLP** (full author names, `dblp_pid`, affiliations), as DBMS did
4. **Crossref + DataCite** (verify DOIs), as DBMS did
5. **ISO 8601 + PROV-O** (dates, provenance)

Everything else is optional, on hold, or later.

---

## 5. Licence of the graph

- `dbms_research` states **"Content released under CC BY 4.0"** in its README and CLAUDE.md. The published DBMS snapshot follows from that.
- `ai_research` has **no licence statement at all**: no LICENSE file, and nothing in README or CLAUDE.md.
- **Proposal:** match DBMS. Add "Content released under CC BY 4.0" to `ai_research` (the same team owns it), and release this graph as CC BY 4.0. **Needs the lead's yes**, because only the owner of `ai_research` can choose its licence.

## 6. Open question (decide before publishing, not before building)

1. OK to add the CC BY 4.0 line to `ai_research`, as in `dbms_research`, and use CC BY 4.0 for this graph? The repo is private, and the licence only matters when the snapshot or repo is published (Phase 9).

## 7. Sources (checked 2026-10-07)

- arXiv licences and API terms: info.arxiv.org/help/license/index.html, info.arxiv.org/help/api/tou.html
- ACM CCS 2012: www.acm.org/publications/class-2012
- OpenAlex Topics: help.openalex.org/data/topics
- ROR data dump: ror.readme.io/docs/data-dump
- Semantic Scholar licence: api.semanticscholar.org/license
- DBMS approach: github.com/samyama-ai/dbms_research (README "License", CLAUDE.md, tools/dblp_*.py, tools/verify_refs.py)
- DBLP licence: dblp.org (CC0)
- Papers with Code shutdown: paperswithcode.com (redirects to huggingface.co/papers); Hugging Face forum thread "Missing dataset after PapersWithCode migration" (discuss.huggingface.co/t/167174); secondary reports hyper.ai/en/news/42900. No primary Meta statement was found; the date is from the Hugging Face announcement
