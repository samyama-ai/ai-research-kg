# Demo

A recorded walkthrough of the AI Research KG, as the sibling KGs have (a terminal run captured with
`asciinema`, rendered to a GIF with `agg`), is **not made yet**. It is recorded from the final graph
once PR #4 is merged, tracked under issue #6.

What it will cover, in the order of `docs/scope.md`: what the graph is made of; the topics with the
most open problems; the papers cited across the most topics; the surveys and foundational papers
behind the most problems; which labs are named on the most open problems; the problems most related
to one problem; the cheapest next experiments and the ones that fit on a single machine; and the two
questions the graph must refuse. Each question is one entry of
[`benchmarks/queries.py`](../benchmarks/queries.py), so the demo and the query catalog stay the same.

Until then, the same questions run as plain text:

```bash
python -m benchmarks.queries --url http://127.0.0.1:8090 --rows 3
```

When the recording is made, this folder gets `demo.py` (the scripted walkthrough), `record.sh`,
`ai-research-kg.cast` and `ai-research-kg.gif`, and the README links the GIF at the top.
