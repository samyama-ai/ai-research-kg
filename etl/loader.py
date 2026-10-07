"""Build and load the AI Research graph into Samyama.

    python -m etl.download_data                       # fetch the catalog (pinned commit)
    python -m etl.loader --url http://127.0.0.1:8090  # parse + load + verify

The loader verifies itself: after loading it counts nodes per label and edges
per type and exits non-zero on any difference. One bad endpoint id silently
drops a whole batch of edges, so this check is what catches it.

Load into an EMPTY engine. On this engine `MATCH (n) DETACH DELETE n` is not a
full reset (edge-ai-kg engine note 8: property columns survive), so recreate
the container rather than relying on --reset.
"""
from __future__ import annotations

import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import click

from etl.download_data import CATALOG_DIR, download_all
from etl.helpers import create_edges, create_nodes
from etl.parse import build_graph

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "ai_research_kg.cypher"
NODE_ORDER = ["DataSource", "Topic", "Problem", "Paper", "Person", "Venue", "Institution",
              "Assumption", "OpenQuestion", "Obstruction", "FutureDirection"]


def connect(url: str | None):
    from samyama import SamyamaClient
    return SamyamaClient.connect(url) if url else SamyamaClient.embedded()


def apply_schema(client, graph: str) -> int:
    applied = 0
    for raw in SCHEMA_PATH.read_text(encoding="utf-8").splitlines():
        stmt = raw.split("//", 1)[0].strip().rstrip(";")
        if not stmt:
            continue
        try:
            client.query(stmt, graph)
            applied += 1
        except Exception as exc:  # index already exists, or unsupported syntax
            click.echo(f"  ! schema stmt skipped ({exc.__class__.__name__}): {stmt[:60]}", err=True)
    return applied


def scalar(client, graph: str, cypher: str) -> int:
    result = client.query(cypher, graph)
    return result.records[0][0] if result.records else 0


def verify(client, graph: str, node_counts: dict, edges: list) -> list[str]:
    problems = []
    for label, want in node_counts.items():
        got = scalar(client, graph, f"MATCH (n:{label}) RETURN count(n.id) AS n")
        if got != want:
            problems.append(f"node {label}: intended {want}, graph has {got}")
    for rel, want in Counter(e[2] for e in edges).items():
        # count a property, not the relationship variable (edge-ai-kg engine note 9)
        got = scalar(client, graph, f"MATCH (a)-[:{rel}]->(b) RETURN count(a.id) AS n")
        if got != want:
            problems.append(f"edge {rel}: intended {want}, graph has {got}")
    return problems


@click.command()
@click.option("--url", default="http://127.0.0.1:8090", show_default=True,
              help="Samyama server URL. Pass --url '' for an embedded (in-process, discarded) load.")
@click.option("--graph", default="default", show_default=True)
@click.option("--reset/--no-reset", default=False, show_default=True,
              help="DETACH DELETE everything first. Not a full reset on this engine -- prefer a fresh container.")
@click.option("--check/--no-check", "check", default=True, show_default=True,
              help="Verify node and edge counts after loading.")
def cli(url, graph, reset, check):
    download_all()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=CATALOG_DIR, check=True,
                            capture_output=True, text=True).stdout.strip()
    t0 = time.time()
    g = build_graph(CATALOG_DIR, commit)
    node_counts, edge_counts = g.counts()
    click.echo(f"[parse] {sum(node_counts.values()):,} nodes, {sum(edge_counts.values()):,} edges "
               f"in {time.time() - t0:.1f}s (catalog {commit[:12]})")

    client = connect(url or None)
    if reset:
        client.query("MATCH (n) DETACH DELETE n", graph)
    existing = scalar(client, graph, "MATCH (n) RETURN count(n) AS n")
    if existing:
        click.echo(f"[load] target graph already holds {existing:,} nodes -- load into an empty engine.", err=True)
        sys.exit(2)

    click.echo(f"[schema] {apply_schema(client, graph)} statements applied")
    t1 = time.time()
    for label in NODE_ORDER:
        rows = list(g.nodes.get(label, {}).values())
        if rows:
            create_nodes(client, graph, label, rows)
    t_nodes = time.time() - t1
    create_edges(client, graph, g.edges)
    t_edges = time.time() - t1 - t_nodes
    click.echo(f"[load] nodes {t_nodes:.1f}s, edges {t_edges:.1f}s")

    if check:
        problems = verify(client, graph, node_counts, g.edges)
        if problems:
            for p in problems:
                click.echo(f"[verify] MISMATCH {p}", err=True)
            sys.exit(1)
        click.echo(f"[verify] OK: {len(node_counts)} labels and {len(edge_counts)} edge types match")


if __name__ == "__main__":
    cli()
