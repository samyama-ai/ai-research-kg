# AI Research Knowledge Graph

**29,696 nodes. 62,845 edges.** 1,000 open problems in AI and machine learning, with the papers, people, labs, assumptions, gaps and next experiments around them, from 1 source.

> Part of the **Samyama** ecosystem: loaded into and queried with [samyama-graph](https://github.com/samyama-ai/samyama-graph). Sibling of the **DBMS Research KG** (`samyama-graph/case_studies/dbms-research`), built the same way from the sibling catalog.

<a href="LICENSE"><img src="https://img.shields.io/badge/code-Apache_2.0-blue" alt="Code licence"></a>
Content licence: **to be decided before publishing**: the source states no licence, CC BY 4.0 is proposed (see [`docs/standards.md`](docs/standards.md)).

---

We loaded the [`ai_research`](https://github.com/samyama-ai/ai_research) catalog into one graph, then asked:

> *"Which papers are cited across the most AI research topics?"*

```cypher
MATCH (t:Topic)<-[:IN_TOPIC]-(p:Problem)-[:CITES]->(pa:Paper)
RETURN pa.title AS paper, count(DISTINCT t.id) AS topics
ORDER BY topics DESC LIMIT 5
```

| paper | topics |
|---|---|
| Training Compute-Optimal Large Language Models | 28 |
| Scaling Laws for Neural Language Models | 20 |
| Lost in the Middle: How Language Models Use Long Contexts | 15 |
| RULER: What's the Real Context Size of Your Long-Context Language Models? | 15 |
| Quantifying Memorization Across Neural Language Models | 13 |

And why problems stay open, which the catalog names in "Why It Is Hard":

| obstruction | problems |
|---|---|
| Confounded measurement | 521 |
| Non-identifiability | 460 |
| Absent ground truth | 208 |
| Compute cost | 131 |
| Evaluation does not measure what it names | 104 |

All numbers were measured on engine 1.11.0 on 2026-10-09 (v1.1), from catalog commit `a02e87b3`. `benchmarks/queries.py` reproduces them (queries AR15 and AR08).

---

## Schema

**Node labels** (11): Problem 1,000 · Topic 35 · Paper 4,932 · Person 15,097 · Venue 522 · Institution 50 · Assumption 3,263 · OpenQuestion 3,790 · Obstruction 6 · FutureDirection 1,000 · DataSource 1

**Edge types** (11): `IN_TOPIC` · `CITES {role, role_raw, position}` · `AUTHORED_BY {position}` · `APPEARED_AT` · `RESTS_ON {position}` · `HAS_GAP {position}` (`kind` is on the OpenQuestion) · `BLOCKED_BY {detail, is_primary}` · `HAS_NEXT_EXPERIMENT` · `ACTIVE_ON {direction}` · `RELATED_TO {method, shared_papers, score}` (computed from shared papers) · `FROM_SOURCE`

**Data source**: `github.com/samyama-ai/ai_research` only, pinned at commit `a02e87b3`. There are no external lookups and no LLM extraction; every node is parsed from the catalog's Markdown.

See [`schema/ai_research_kg.cypher`](schema/ai_research_kg.cypher), [`docs/schema.md`](docs/schema.md) and [`DATASET_CARD.md`](DATASET_CARD.md).

Standards, coding systems, taxonomies and ontologies in full: **[docs/standards.md](docs/standards.md)**. The ontology as a file: [`ontology/ai_research_kg.ttl`](ontology/ai_research_kg.ttl) ([docs/ontology.md](docs/ontology.md)); the code lists: [`vocab/concepts.yaml`](vocab/concepts.yaml); the taxonomy check and refinements: [docs/taxonomy.md](docs/taxonomy.md). Whether the graph keeps all of them is measured by `python -m etl.conformance --url http://127.0.0.1:8090` (report: [docs/conformance.md](docs/conformance.md)).

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# an empty engine, pinned to the image the counts were measured on (1.11.0);
# the CORS flag lets Samyama Insight connect, see docs/ENGINE-NOTES.md
docker run -d --name samyama-ai_research -p 8090:8080 \
  ghcr.io/samyama-ai/samyama-graph@sha256:fc9a74053554f0be76fdc3973bbc2e5ff05cbb767aa27953ce184e9503206bd4 \
  samyama --host 0.0.0.0 --cors-origin https://graph.samyama.cloud

python -m etl.download_data                         # catalog -> data/ai_research (pinned commit; writes data/ai_research.lock.json)
python -m etl.loader --url http://127.0.0.1:8090    # parse + load + verify counts (~30 s)
python -m benchmarks.queries                        # the scope.md questions, 34 queries
python -m etl.conformance --url http://127.0.0.1:8090   # taxonomy/ontology/coding/standards checks
pytest                                              # parser, invariant, count, query-catalog and standards tests

# snapshot: export the loaded graph + write snapshots/manifest.json (counts, SHA-256, commit)
python -m etl.snapshot export --url http://127.0.0.1:8090
```

### Or skip the build: load the snapshot

The built graph is shared **inside the team** as `ai-research.sgsnap` (3.5 MB), outside git like
the other KGs' snapshots; it is not published, because the source states no licence yet (S8 in
`docs/conformance.md`, issue #6). Ask the maintainers for it; where it will be hosted is being
decided in issue #6.
`snapshots/manifest.json` records its SHA-256 and counts. Put the file in `snapshots/` and import
it into a **fresh** server (import appends, so `etl.snapshot import` refuses a non-empty one and
checks every count against the manifest afterwards):

```bash
docker run -d --name samyama-ai_research-snap -p 8092:8080 \
  ghcr.io/samyama-ai/samyama-graph@sha256:fc9a74053554f0be76fdc3973bbc2e5ff05cbb767aa27953ce184e9503206bd4 \
  samyama --host 0.0.0.0 --cors-origin https://graph.samyama.cloud
python -m etl.snapshot import --url http://127.0.0.1:8092
```

`python -m etl.build` builds the graph without an engine and writes `data/graph.json`.

## Structure
```
etl/download_data.py   # clone ai_research at the pinned commit; checks the checkout is clean and at that commit
etl/rules.py           # the fixed lists: citation-role buckets, venue aliases, obstruction types, institutions
etl/text.py            # Markdown helpers: sections (by heading text), frontmatter, lists
etl/parse.py           # one page -> references, assumptions, gaps, experiment, labs
etl/build.py           # catalog walk -> Graph (ids, paper dedup, computed RELATED_TO)
etl/loader.py          # schema + batched load + count verification
etl/helpers.py         # Cypher literals, identifier checks, batched CREATE
etl/conformance.py     # checks the graph against taxonomy, ontology, code lists, standards (etl/conformance_lib.py: inputs, report)
etl/snapshot.py        # export/import the .sgsnap, write and check snapshots/manifest.json
etl/count_kg.py        # Phase 1 size estimate (kept for reference)
schema/                # Cypher schema (indexes)
ontology/              # the ontology in OWL/Turtle (ai_research_kg.ttl)
vocab/                 # controlled vocabularies (concepts.yaml)
benchmarks/queries.py  # query catalog AR01-AR32, AR90-AR91, with scope.md coverage
mcp_server/            # MCP server exposing the graph to Claude (from the KG template; not yet adapted)
demo/                  # recorded demo (from the KG template; not yet recorded for this graph)
tools/insight_proxy.py # local CORS proxy so Samyama Insight can reach the engine (docs/ENGINE-NOTES.md)
docs/                  # scope, schema (as built) and the v0.1 plan, standards, ontology, taxonomy, conformance, engine notes, logs
tests/                 # parser tests on fixtures, full-graph invariants, count, query-catalog and standards tests
```

## Known limits (v1)

- **No Method nodes.** The bold text in "State of the Art" is evidence labels ("Established", "Claimed but unablated"), not method names, so methods can't be extracted without an LLM or an outside source.
- **People are not resolved.** The catalog writes authors three ways (`Wortsman`, `T. Moerland`, `Rico Sennrich`). As in the DBMS KG, bare surnames are never merged into full names; filter on `name_form = 'full'` for people queries.
- **Institutions** are matched by name against a fixed list of 51 labs and universities in "Current Research" (50 occur in the catalog).
- **No embeddings / vector search.** The DBMS KG used OpenAI embeddings; this build uses nothing outside the catalog.
