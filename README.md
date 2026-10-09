# AI Research Knowledge Graph

**28,960 nodes. 62,178 edges.** 1,000 open problems in AI and machine learning, with the papers, people, labs, assumptions, gaps and next experiments around them, from 1 source.

> Part of the **Samyama** ecosystem: loaded into and queried with [samyama-graph](https://github.com/samyama-ai/samyama-graph). Sibling of the **DBMS Research KG** (`samyama-graph/case_studies/dbms-research`), built the same way from the sibling catalog.

<a href="LICENSE"><img src="https://img.shields.io/badge/code-Apache_2.0-blue" alt="Code licence"></a>
Content licence: **to be decided before publishing** (see [`docs/standards.md`](docs/standards.md), CC BY 4.0 proposed).

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

All numbers were measured on engine 1.11.0 on 2026-10-07, from catalog commit `a02e87b3`. `benchmarks/queries.py` reproduces them.

---

## Schema

**Node labels** (11): Problem 1,000 · Topic 35 · Paper 4,932 · Person 15,097 · Venue 550 · Institution 50 · Assumption 2,499 · OpenQuestion 3,790 · Obstruction 6 · FutureDirection 1,000 · DataSource 1

**Edge types** (11): `IN_TOPIC` · `CITES {role}` · `AUTHORED_BY` · `APPEARED_AT` · `RESTS_ON` · `HAS_GAP {kind on target}` · `BLOCKED_BY` · `HAS_NEXT_EXPERIMENT` · `ACTIVE_ON` · `RELATED_TO` (computed from shared papers) · `FROM_SOURCE`

**Data source**: `github.com/samyama-ai/ai_research` only, pinned at commit `a02e87b3`. There are no external lookups and no LLM extraction; every node is parsed from the catalog's Markdown.

See [`schema/ai_research_kg.cypher`](schema/ai_research_kg.cypher), [`docs/schema.md`](docs/schema.md) and [`DATASET_CARD.md`](DATASET_CARD.md).

Standards, coding systems, taxonomies and ontologies in full: **[docs/standards.md](docs/standards.md)**. The ontology as a file: [`ontology/ai_research_kg.ttl`](ontology/ai_research_kg.ttl) ([docs/ontology.md](docs/ontology.md)); the code lists: [`vocab/concepts.yaml`](vocab/concepts.yaml); the taxonomy check and refinements: [docs/taxonomy.md](docs/taxonomy.md). Whether the graph keeps all of them is measured by `python -m etl.conformance --url http://127.0.0.1:8090` (report: [docs/conformance.md](docs/conformance.md)).

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# an empty engine (CORS flag lets Samyama Insight connect; see docs/ENGINE-NOTES.md)
docker run -d --name samyama-ai_research -p 8090:8080 ghcr.io/samyama-ai/samyama-graph:latest \
  samyama --host 0.0.0.0 --cors-origin https://graph.samyama.cloud

python -m etl.download_data                         # catalog -> data/ai_research (pinned commit)
python -m etl.loader --url http://127.0.0.1:8090    # parse + load + verify counts (~30 s)
python -m benchmarks.queries                        # the scope.md questions, 32 queries
python -m etl.conformance --url http://127.0.0.1:8090   # taxonomy/ontology/coding/standards checks
pytest                                              # parser, invariant, count and standards tests

# optional: portable snapshot, same format as dbms-research.sgsnap
curl -X POST -o snapshots/ai-research.sgsnap http://127.0.0.1:8090/api/snapshot/export
```

`python -m etl.parse` builds the graph without an engine and writes `data/graph.json`.

## Structure
```
etl/download_data.py   # clone ai_research at the pinned commit
etl/parse.py           # Markdown -> nodes and edges (all extraction rules live here)
etl/loader.py          # schema + batched load + count verification
etl/conformance.py     # checks the graph against taxonomy, ontology, code lists, standards
etl/count_kg.py        # Phase 1 size estimate (kept for reference)
schema/                # Cypher schema (indexes)
ontology/              # the ontology in OWL/Turtle (ai_research_kg.ttl)
vocab/                 # controlled vocabularies (concepts.yaml)
benchmarks/queries.py  # query catalog AR01-AR30, AR90-AR91
docs/                  # scope, schema, standards, ontology, taxonomy, conformance, engine notes, logs
tests/                 # parser tests on fixtures + full-graph invariants
```

## Known limits (v1)

- **No Method nodes.** The bold text in "State of the Art" is evidence labels ("Established", "Claimed but unablated"), not method names, so methods can't be extracted without an LLM or an outside source.
- **People are not resolved.** The catalog writes authors three ways (`Wortsman`, `T. Moerland`, `Rico Sennrich`). As in the DBMS KG, bare surnames are never merged into full names; filter on `name_form = 'full'` for people queries.
- **Institutions** are matched by name against a fixed list of 50 labs and universities in "Current Research".
- **No embeddings / vector search.** The DBMS KG used OpenAI embeddings; this build uses nothing outside the catalog.
