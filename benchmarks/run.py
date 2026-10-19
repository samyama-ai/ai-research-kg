"""Run, time and check the query catalog.

    python -m benchmarks.run --url http://127.0.0.1:8090            # all queries, 3 rows each
    python -m benchmarks.run --only AR15 --rows 10                   # one query (an unknown id is an error)
    python -m benchmarks.run --coverage                              # which scope.md question each answers
    python -m benchmarks.run --no-check                              # skip the reference (no data/graph.json)

Each query's rows are compared with its plain-Python answer in benchmarks/reference.py, computed
from data/graph.json (`python -m etl.build`). Run that against the same build the engine holds.

A run fails when a query errors, when a query other than AR9x returns no rows, when an AR9x query
(the graph holds no such data) returns rows, or when an answer disagrees with its reference.
"""
from __future__ import annotations

import sys
import time

import click

from benchmarks.queries import QUERIES, TOP_AUTHOR, coverage, resolve


def run(client, graph: str, q: dict) -> tuple[list, float]:
    cypher = resolve(client, graph, q["cypher"])
    t0 = time.perf_counter()
    result = client.query(cypher, graph)
    return list(result.records or []), (time.perf_counter() - t0) * 1000


@click.command()
@click.option("--url", default="http://127.0.0.1:8090", show_default=True)
@click.option("--graph", default="default", show_default=True)
@click.option("--only", default=None, help="Run one query id, e.g. AR14.")
@click.option("--rows", default=3, show_default=True, help="Rows to print per query.")
@click.option("--coverage", "show_coverage", is_flag=True,
              help="Print which scope.md question each query answers and exit.")
@click.option("--no-check", is_flag=True, help="Do not compare with benchmarks/reference.py.")
def main(url, graph, only, rows, show_coverage, no_check):
    if show_coverage:
        for n, who in coverage().items():
            click.echo(f"Q{n:02d}  {who}")
        return
    selected = [q for q in QUERIES if only is None or q["id"] == only]
    if not selected:
        raise click.BadParameter(f"no query with id {only!r}; ids are {', '.join(q['id'] for q in QUERIES)}",
                                 param_hint="--only")
    from samyama import SamyamaClient
    client = SamyamaClient.connect(url)
    refs = None
    if not no_check:
        from benchmarks import reference
        g = reference.load()
        top = list(client.query(TOP_AUTHOR, graph).records or [])
        author = str(top[0][0]).replace("'", "") if top else None
        papers = reference.author_papers(g)
        if author and papers[author] != max(papers.values()):
            click.echo(f"TOP_AUTHOR picked {author!r}, who is not an author with the most papers")
            sys.exit(1)
        refs = reference.answers(g, author)
    failures = 0
    for q in selected:
        try:
            records, ms = run(client, graph, q)
        except Exception as exc:
            failures += 1
            click.echo(f"{q['id']}  ERROR  {q['question']}\n      {exc}")
            continue
        wrong = []
        if (not records) != bool(q.get("expect_empty")):
            wrong.append("returned rows" if q.get("expect_empty") else "returned no rows")
        if refs is not None:
            wrong += reference.check(records, refs[q["id"]])
        failures += bool(wrong)
        click.echo(f"{q['id']}  {'BAD' if wrong else 'ok '}  {len(records):4d} rows {ms:7.1f} ms  {q['question']}")
        for why in wrong:
            click.echo(f"      ! {why}")
        for r in records[:rows]:
            click.echo("      " + " | ".join(str(v)[:70] for v in r))
    checked = "" if refs is None else ", each agrees with its reference"
    click.echo(f"\n{failures} failing" if failures else f"\nall {len(selected)} queries ok{checked}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
