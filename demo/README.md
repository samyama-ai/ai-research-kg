# Demo

![AI Research KG demo](ai-research-kg.gif)

Ten questions a researcher starts from, in one walk through the graph: how open the field is, which
topics are most open, the papers and surveys the problems share, which labs are named on open
problems, why problems stay hard, which problems are close to one problem, the cheapest next
experiments and the ones that fit on a single machine, and a question the graph must refuse.

| # | Query | Rests on | Question |
|---:|---|---|---|
| 1 | AR02 | parsed from the page | How open is the field? Problems per status |
| 2 | AR04 | parsed from the page | Which topics have the most open problems? |
| 3 | AR15 | parsed from the page | Which papers are cited across the most topics? |
| 4 | AR17 | our fixed rule | Which foundational papers underpin the most problems? |
| 5 | AR22 | our fixed rule | Which labs are named on the most open problems? |
| 6 | AR08 | our fixed rule | Why do problems stay hard? |
| 7 | AR26 | computed link | Which problems are closest to one problem? |
| 8 | AR28 | parsed from the page | Which next experiments are cheapest to run? |
| 9 | AR09 | parsed from the page | Which open problems fit on a single machine? |
| 10 | AR90 | no such data | How much funding has each problem received? (must return nothing) |

"Rests on" says how far an answer is from the catalog's own words: *parsed from the page* is read
as written; *our fixed rule* is a keyword or name-list classification (citation roles, obstruction
types, institutions; the lists are in `etl/rules.py`); *computed link* is `RELATED_TO`, built from
shared cited papers with a score; *no such data* is a question the graph must refuse.

The ten queries in full are in [`queries.cypher`](queries.cypher), ready to paste into Samyama
Insight. They are entries of [`benchmarks/queries.py`](../benchmarks/queries.py); `queries.cypher` is
generated from it (`python -m demo.demo --write-cypher`), so edit the catalog, not the file.

## Run it

The demo needs a server that holds the graph. Build it (about two minutes) or import the snapshot
shared inside the team (see the main README):

```bash
docker run -d --name samyama-ai_research -p 8090:8080 \
  ghcr.io/samyama-ai/samyama-graph@sha256:fc9a74053554f0be76fdc3973bbc2e5ff05cbb767aa27953ce184e9503206bd4 \
  samyama --host 0.0.0.0
python -m etl.loader --url http://127.0.0.1:8090
python -m demo.demo --url http://127.0.0.1:8090            # paced, one query at a time
python -m demo.demo --long --url http://127.0.0.1:8090     # the one-screen report of the GIF
python -m demo.demo --long --no-pause --url ...            # unpaced, for a log or a check
```

A step that returns rows when it must not (or none when it must) makes the demo exit non-zero, so
`python -m demo.demo --long --no-pause` doubles as a check that the graph still answers.

## Record the GIF

```bash
pip install asciinema                                    # 2.x; agg from github.com/asciinema/agg
AGG=/path/to/agg demo/record.sh http://127.0.0.1:8090    # -> ai-research-kg.cast, ai-research-kg.gif
```

`record.sh` measures the report's height from an unpaced run, records the paced run with asciinema at
that height (100 columns), renders it with agg at font size 18 with a 14-second hold on the final
frame, and regenerates `queries.cypher`. The GIF in this folder and `ai-research-kg.cast`, the
asciinema recording it was rendered from, were made on 2026-10-13 from the v1.1 graph (29,707 nodes,
62,842 edges); re-record both when the graph changes.

## Connect Samyama Insight

`insight_proxy.py` is a small local CORS proxy, so the Insight console can reach the engine while
you are signed in (docs/ENGINE-NOTES.md explains why it is needed):

```bash
python demo/insight_proxy.py          # 127.0.0.1:8091 -> http://127.0.0.1:8090; connect Insight to http://localhost:8091
```
