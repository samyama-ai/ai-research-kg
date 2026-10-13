"""Narrated terminal demo: the AI Research knowledge graph on Samyama.

    python -m demo.demo                                   # the server on http://127.0.0.1:8090
    python -m demo.demo --url http://127.0.0.1:8092
    python -m demo.demo --no-pause                        # no pacing, for a log or a test
    python -m demo.demo --long                            # long form: one tall report, for the GIF
    python -m demo.demo --write-cypher                    # write the ten queries to demo/queries.cypher

Ten questions a researcher starts from, in one walk: how open the field is, which topics are most
open, the papers and surveys the problems share, which labs are named on open problems, why
problems stay hard, which problems are close to one problem, the cheapest next experiments and the
ones that fit on a single machine, and a question the graph must refuse.

EVERY NUMBER HERE IS READ FROM THE GRAPH AT RUN TIME. Nothing is typed in, so the demo cannot claim
something the graph no longer contains. Each step is tagged with what its answer rests on: text
parsed from the catalog page, one of our fixed rules (keyword or name matching), a computed link,
or nothing (the graph holds no such data), because a viewer must be able to tell a stated fact from
a classification we made.

The demo needs a server that holds the graph. Build it (about two minutes) or load the snapshot
shared inside the team:

    docker run -d --name samyama-ai_research -p 8090:8080 ghcr.io/samyama-ai/samyama-graph:1.11.0
    python -m etl.loader --url http://127.0.0.1:8090           # or: python -m etl.snapshot import --url ...

The ten queries are entries of benchmarks/queries.py, so the demo and the query catalog never
disagree; `--write-cypher` regenerates demo/queries.cypher from them.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from benchmarks.queries import EXAMPLE_PROBLEM, QUERIES, resolve

DEFAULT_URL = "http://127.0.0.1:8090"
GRAPH = "default"                       # engine 1.11.0 serves exactly one graph, named "default"
CYPHER_PATH = Path(__file__).resolve().parent / "queries.cypher"
BY_ID = {q["id"]: q for q in QUERIES}

# What an answer rests on. The catalog is the only source; the tag says how far the answer is from
# the page text.
BASIS = {
    "parsed": ("PARSED FROM THE PAGE", "green", "read as written from the problem page"),
    "rule": ("OUR FIXED RULE", "magenta", "a keyword or name-list classification; read the rule in etl/rules.py"),
    "computed": ("COMPUTED LINK", "yellow", "RELATED_TO: problems that cite the same papers, with a score"),
    "none": ("NO SUCH DATA", "red", "the graph must return nothing"),
}
LONG_TAG = {k: f"[{colour}]{label.lower()}[/{colour}]" for k, (label, colour, _) in BASIS.items()}

# (query id, title, what to say before it, rests on, rows to show)
STORY = [
    ("AR02", "How open is the field?", "1,000 problems, one catalog page each. Their status, as the catalog states it.", "parsed", 5),
    ("AR04", "Which topics have the most open problems?", "The 35 topics of TAXONOMY.md; every problem sits in exactly one.", "parsed", 6),
    ("AR15", "Which papers are cited across the most topics?", "A paper cited by problems in many topics is a bridge between fields.", "parsed", 5),
    ("AR17", "Which foundational papers underpin the most problems?", "The catalog tags each reference; we group ~670 tags into 7 roles.", "rule", 5),
    ("AR22", "Which labs are named on the most open problems?", "Labs named in 'Current Research', matched against a list of 52 names.", "rule", 6),
    ("AR08", "Why do problems stay hard?", "'Why It Is Hard', mapped to the five obstruction types the catalog itself names.", "rule", 6),
    ("AR26", f"Which problems are closest to '{EXAMPLE_PROBLEM}'?", "Not stated anywhere: computed from shared cited papers, with a Jaccard score.", "computed", 5),
    ("AR28", "Which next experiments are cheapest to run?", "GPU-hours parsed from 'Concrete Next Experiment', never guessed.", "parsed", 6),
    ("AR09", "Which open problems fit on a single machine?", "Open status plus an experiment at or under 8 GPUs for a day.", "parsed", 6),
    ("AR90", "How much funding has each problem received?", "The catalog says nothing about funding, so the graph says nothing.", "none", 3),
]

TAKEAWAY = ("Status, topics, shared papers, named labs, obstructions, related problems and runnable\n"
            "experiments, all answered as graph traversals over one pinned catalog commit.\n"
            "Every row leads back to the page it was read from.")


def cell(value, column: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        text = f"{value:,.3f}".rstrip("0")
        return text + "0" if text.endswith(".") else text
    if isinstance(value, int):
        return str(value) if column.endswith("year") else f"{value:,}"
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    text = str(value)
    return text if len(text) <= 70 else text[:67] + "…"


def long_pause(seconds: float, enabled: bool) -> None:
    """DEMO_PACE tunes the recording's cadence without an edit, as in the sibling KGs."""
    if enabled:
        time.sleep(seconds * float(os.environ.get("DEMO_PACE", "1.0")))


def count(client, graph_name: str, pattern: str) -> int:
    return client.query(f"MATCH {pattern} RETURN count(*)", graph_name).records[0][0]


def statement_for(client, graph_name: str, query_id: str) -> str:
    return resolve(client, graph_name, BY_ID[query_id]["cypher"])


# --------------------------------------------------------------------------
# Long form: the layout of samyama-graph/case_studies/_lib/demo_lib.py, shared by the sibling KGs.
# A title card, a numbered rule per step, the query on one line, a plain table, a closing panel.
# The whole report stays on one tall screen; demo/record.sh measures its height before recording.
# --------------------------------------------------------------------------
def run_long(console: Console, client, graph_name: str, paced: bool) -> list[str]:
    nodes = count(client, graph_name, "(n)")
    edges = count(client, graph_name, "()-[r]->()")
    problems = count(client, graph_name, "(n:Problem)")
    papers = count(client, graph_name, "(n:Paper)")
    people = count(client, graph_name, "(n:Person)")
    commit = client.query("MATCH (d:DataSource) RETURN d.version", graph_name).records[0][0]

    console.print(Panel.fit(
        "[bold]Samyama · AI Research Knowledge Graph[/bold]\n"
        f"{problems:,} open problems · {papers:,} cited papers · {people:,} author names · 35 topics\n"
        f"[dim]source: github.com/samyama-ai/ai_research at {str(commit)[:8]} · no external lookups, no LLM extraction[/dim]",
        border_style="cyan"))
    long_pause(1.4, paced)

    console.print()
    console.rule("[bold cyan]1 · Graph loaded into Samyama")
    long_pause(0.5, paced)
    console.print(f"  [green]loaded[/green] [bold]{nodes:,}[/bold] nodes · [bold]{edges:,}[/bold] edges")
    long_pause(1.3, paced)

    wrong = []
    for index, (query_id, title, lead, basis, rows) in enumerate(STORY, start=1):
        console.print()
        console.rule(f"[bold cyan]{index + 1} · {title}")
        long_pause(0.5, paced)
        console.print(f"  [dim]Q{index}.[/dim] [bold white]{title}[/bold white]  [dim]·[/dim] {LONG_TAG[basis]}")
        console.print(f"       [italic dim]{lead}[/italic dim]")
        statement = statement_for(client, graph_name, query_id)
        console.print(f"  [dim]cypher>[/dim] [yellow]{escape(' '.join(statement.split()))}[/yellow]")

        began = time.perf_counter()
        result = client.query(statement, graph_name)
        took = 1000 * (time.perf_counter() - began)

        if result.records:
            table = Table(show_edge=False, pad_edge=False, box=None, header_style="bold magenta")
            for column in result.columns:
                table.add_column(str(column))
            for row in result.records[:rows]:
                table.add_row(*(cell(v, c) for v, c in zip(row, result.columns)))
            console.print(table)
        more = len(result.records) - rows
        note = f" (showing {rows})" if more > 0 else ""
        console.print(f"  [green]→[/green] {len(result.records)} row(s){note} in [bold]{took:.1f} ms[/bold]"
                      + ("  [red]as it must: no such data[/red]" if basis == "none" else ""))
        long_pause(3.2, paced)
        if bool(result.records) == (basis == "none"):
            wrong.append(query_id)

    console.print()
    console.print(Panel.fit(f"[bold green]{TAKEAWAY}[/bold green]", border_style="green"))
    console.print("  [dim]Roles, obstructions and labs are our classifications of the catalog's words;\n"
                  "  RELATED_TO is computed. Authors are kept as written, not resolved to people.[/dim]")
    long_pause(1.6, paced)
    return wrong


def show(console: Console, client, graph_name: str, step: int, query_id: str, title: str, lead: str,
         basis: str, rows: int, pause) -> bool:
    tag, colour, meaning = BASIS[basis]
    console.rule(f"[bold]{step}/{len(STORY)}  {title}[/bold]")
    console.print(lead)
    console.print(f"[{colour}]\\[{tag}][/{colour}] [dim]{meaning}[/dim]\n")
    statement = statement_for(client, graph_name, query_id)
    console.print(statement + "\n", style="dim", highlight=False, markup=False)
    pause(1.5)

    began = time.perf_counter()
    result = client.query(statement, graph_name)
    took = 1000 * (time.perf_counter() - began)

    if result.records:
        table = Table(show_edge=False, header_style="bold")
        for column, sample in zip(result.columns, result.records[0]):
            numeric = isinstance(sample, (int, float)) and not isinstance(sample, bool)
            table.add_column(column, justify="right" if numeric else "left")
        for row in result.records[:rows]:
            table.add_row(*(cell(v, c) for v, c in zip(row, result.columns)))
        console.print(table)
    more = len(result.records) - rows
    note = f"  and {more} more" if more > 0 else ""
    console.print(f"[dim]{len(result.records)} rows in {took:.0f} ms{note}[/dim]\n")
    pause(4.0)
    return bool(result.records) != (basis == "none")


def write_cypher(path: Path = CYPHER_PATH) -> Path:
    """The ten queries in full, in the order the demo runs them, ready to paste into Insight."""
    lines = ["// The ten queries of the demo, in the order it runs them.",
             "// Written by `python -m demo.demo --write-cypher`. Do not edit: edit",
             "// benchmarks/queries.py and regenerate.", ""]
    for step, (query_id, title, _lead, basis, _rows) in enumerate(STORY, start=1):
        entry = BY_ID[query_id]
        lines += [f"// {step}. {title}  ({query_id}, rests on: {basis})",
                  f"// {entry['question']}", entry["cypher"] + ";", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def connect(url: str):
    from samyama import SamyamaClient
    client = SamyamaClient.connect(url)
    try:
        nodes = client.query("MATCH (n) RETURN count(n)", GRAPH).records[0][0]
    except Exception as exc:  # noqa: BLE001 - any failure here means "no usable server"
        raise click.ClickException(
            f"cannot query {url} ({exc}). Start a server and load the graph:\n"
            "  docker run -d --name samyama-ai_research -p 8090:8080 ghcr.io/samyama-ai/samyama-graph:1.11.0\n"
            "  python -m etl.loader --url http://127.0.0.1:8090") from exc
    if not nodes:
        raise click.ClickException(f"{url} holds an empty graph: python -m etl.loader --url {url}")
    return client


@click.command()
@click.option("--url", default=DEFAULT_URL, show_default=True, help="Samyama server holding the graph.")
@click.option("--graph", "graph_name", default=GRAPH, show_default=True, help="Graph to query.")
@click.option("--no-pause", is_flag=True, help="Do not pace the output.")
@click.option("--long", "long_form", is_flag=True, help="Long form: one tall report, in the case-study layout.")
@click.option("--write-cypher", "only_write", is_flag=True, help="Write the ten queries to demo/queries.cypher and exit.")
def main(url, graph_name, no_pause, long_form, only_write):
    if only_write:
        click.echo(f"wrote {write_cypher()}")
        return
    console = Console(width=100)
    client = connect(url)

    if long_form:
        wrong = run_long(console, client, graph_name, not no_pause)
        if wrong:
            console.print(f"[red]these steps did not return what they must: {', '.join(wrong)}[/red]")
            sys.exit(1)
        return

    def pause(seconds: float) -> None:
        if not no_pause:
            time.sleep(seconds)

    console.print(Panel.fit(
        "[bold]AI Research Knowledge Graph[/bold]\n"
        "1,000 open problems in AI research, with the papers, people, labs, assumptions, gaps and\n"
        "next experiments around them, from one pinned catalog commit.",
        border_style="cyan"))
    console.print(f"[dim]connected to {url}, graph {graph_name}[/dim]\n")
    pause(2.0)
    wrong = [query_id for step, (query_id, title, lead, basis, rows) in enumerate(STORY, start=1)
             if not show(console, client, graph_name, step, query_id, title, lead, basis, rows, pause)]

    console.print(Panel.fit(
        "[green]Parsed from the page[/green]  status, topics, papers, experiments: as the catalog writes them\n"
        "[magenta]Our fixed rule[/magenta]        citation roles, obstructions, labs: keyword and name lists in etl/rules.py\n"
        "[yellow]Computed link[/yellow]         RELATED_TO: shared cited papers, with a score\n"
        "[red]No such data[/red]          funding, leaderboards: the graph refuses\n\n"
        "Source: github.com/samyama-ai/ai_research (one commit, no external lookups, no LLM extraction).\n"
        "[dim]Authors are kept as written, not resolved; venues and roles are normalised by our lists.[/dim]",
        title="What you just saw", border_style="cyan"))
    pause(5.0)

    if wrong:
        console.print(f"[red]these steps did not return what they must: {', '.join(wrong)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
