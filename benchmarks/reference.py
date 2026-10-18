"""Each catalog query answered a second time, in plain Python, and `check()`, which compares the two.

    python -m benchmarks.reference                 # answer every query from data/graph.json
    python -m benchmarks.reference --only AR14

The answers are written from the question and the built graph (`data/graph.json`, made by
`python -m etl.build`), not from the Cypher, so a mistake in one is not copied into the other.
Grouping follows what each query returns: AR14 counts per (title, year), as its RETURN does.
Text is compared as the loader stores it: quotes and backslashes stripped, newlines made spaces
(`etl/helpers.py: _clean`, docs/ENGINE-NOTES.md), so `$\\theta$` is `$theta$` on both sides.

`check()` tests four things, because each can fail on its own:

1. the number of rows;
2. that every row is one the reference also produced;
3. that the rows are in the promised order;
4. under a LIMIT, that they are the top rows and not just any correct ones.

Rows that sort equal may come back in either order. Ordering follows Cypher: null sorts after every
value when ascending.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import click

from benchmarks.queries import EXAMPLE_PROBLEM
from etl.helpers import _clean

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "data" / "graph.json"


def _as_loaded(props: dict) -> dict:
    return {k: _clean(v) if isinstance(v, str) else v for k, v in props.items()}


class G:
    """The built graph, indexed for the questions below, with text as the engine holds it."""

    def __init__(self, data: dict):
        data = {"nodes": {label: [_as_loaded(n) for n in rows] for label, rows in data["nodes"].items()},
                "edges": [[*e[:5], _as_loaded(e[5] or {})] for e in data["edges"]]}
        self.nodes = {n["id"]: n for rows in data["nodes"].values() for n in rows}
        self.label = {n["id"]: label for label, rows in data["nodes"].items() for n in rows}
        self.by_label = {label: rows for label, rows in data["nodes"].items()}
        self.edges = defaultdict(list)                # type -> [(from, to, props)]
        for _, src, rel, _, dst, props in data["edges"]:
            self.edges[rel].append((src, dst, props or {}))

    def out(self, rel: str) -> dict[str, list[tuple[str, dict]]]:
        res = defaultdict(list)
        for src, dst, props in self.edges[rel]:
            res[src].append((dst, props))
        return res

    def one(self, rel: str) -> dict[str, str]:
        return {src: dst for src, dst, _ in self.edges[rel]}

    def get(self, node_id: str, prop: str):
        return self.nodes[node_id].get(prop)

    def undirected(self, rel: str) -> list[tuple[str, str, dict]]:
        """Each stored edge both ways, as an undirected MATCH sees it."""
        return [x for src, dst, p in self.edges[rel] for x in ((src, dst, p), (dst, src, p))]


def load(path: Path = GRAPH) -> G:
    if not path.is_file():
        raise click.ClickException(f"{path} not found: run `python -m etl.build` first")
    return G(json.loads(path.read_text(encoding="utf-8")))


@dataclass
class Answer:
    rows: list[tuple]                 # every row, before any LIMIT, in no particular order
    order: tuple[tuple[int, bool], ...] = ()   # (column, descending), as the query's ORDER BY
    limit: int | None = None


def counted(pairs) -> list[tuple]:
    """[(group tuple, ...)] -> [(*group, count)]."""
    return [(*k, n) for k, n in Counter(pairs).items()]


def distinct_counted(pairs) -> list[tuple]:
    """[(group tuple, member)] -> [(*group, distinct members)]."""
    groups = defaultdict(set)
    for k, member in pairs:
        groups[k].add(member)
    return [(*k, len(v)) for k, v in groups.items()]


def author_papers(g: G) -> Counter:
    """Full-name author -> AUTHORED_BY edges, as TOP_AUTHOR in queries.py counts them."""
    return Counter(g.get(person, "name") for _, person, _ in g.edges["AUTHORED_BY"]
                   if g.get(person, "name_form") == "full")


def top_author(g: G) -> str:
    return author_papers(g).most_common(1)[0][0]


def answers(g: G, author: str | None = None) -> dict[str, Answer]:
    topic = g.one("IN_TOPIC")
    problems = g.by_label["Problem"]
    status = {p["id"]: p.get("status") for p in problems}
    tname = lambda pid: g.get(topic[pid], "name")
    example = next(p["id"] for p in problems if p.get("slug") == EXAMPLE_PROBLEM)
    experiment = g.one("HAS_NEXT_EXPERIMENT")
    cites = g.edges["CITES"]
    authors = g.out("AUTHORED_BY")
    venues = g.out("APPEARED_AT")
    title = lambda x: g.get(x, "title")
    full = lambda person: g.get(person, "name_form") == "full"
    labs = [(src, dst, p) for src, dst, p in g.edges["ACTIVE_ON"] if g.label[src] == "Institution"]
    related = g.undirected("RELATED_TO")
    single = [(pid, f) for pid, f in experiment.items() if g.get(f, "single_machine") is True]
    author = author or top_author(g)
    a = {}

    # A. Problems and topics
    a["AR01"] = Answer([(t.get("number"), t.get("name")) for t in g.by_label["Topic"]], ((0, False),))
    a["AR02"] = Answer(counted((status[p["id"]],) for p in problems), ((1, True),))
    a["AR03"] = Answer(counted((tname(p["id"]),) for p in problems), ((1, True),))
    a["AR04"] = Answer(counted((tname(p["id"]),) for p in problems if status[p["id"]] == "open"), ((1, True),), 10)
    a["AR05"] = Answer(counted((tname(p["id"]),) for p in problems), ((0, False),))
    a["AR06"] = Answer(counted((g.get(q, "kind"),) for _, q, _ in g.edges["HAS_GAP"]), ((1, True),))
    a["AR07"] = Answer([(tname(p["id"]), p.get("title")) for p in problems
                        if status[p["id"]] == "solved-but-impractical"], ((0, False),))
    a["AR08"] = Answer(counted((g.get(o, "name"),) for _, o, _ in g.edges["BLOCKED_BY"]), ((1, True),))
    a["AR09"] = Answer([(g.get(pid, "title"), g.get(f, "compute_budget_gpu_hours")) for pid, f in single
                        if status[pid] == "open"], ((1, False),), 10)
    a["AR33"] = Answer([(g.get(pid, "title"), status[pid], g.get(f, "compute_budget_gpu_hours"))
                        for pid, f in single], ((2, False),), 10)

    # B. One problem
    p = g.nodes[example]
    a["AR10"] = Answer([(p.get("title"), p.get("status"), tname(example), p.get("statement"))])
    a["AR11"] = Answer([(e.get("role"), title(dst), g.get(dst, "year")) for src, dst, e in cites if src == example],
                       ((0, False),))
    f = experiment[example]
    a["AR12"] = Answer([(g.get(f, "question"), g.get(f, "compute_budget_gpu_hours"), g.get(f, "deciding_number"))])
    a["AR13"] = Answer([(g.get(src, "name"), e.get("direction")) for src, dst, e in labs if dst == example])

    # C. Papers
    a["AR14"] = Answer(counted((title(dst), g.get(dst, "year")) for _, dst, _ in cites), ((2, True),), 10)
    a["AR15"] = Answer(distinct_counted(((title(dst),), topic[src]) for src, dst, _ in cites), ((1, True),), 10)
    for qid, role in (("AR16", "survey"), ("AR17", "foundational"), ("AR18", "caution")):
        a[qid] = Answer(counted((title(dst),) for _, dst, e in cites if e.get("role") == role), ((1, True),), 10)
    by_venue = defaultdict(lambda: [0, set()])
    for _, paper, _ in cites:
        for venue, _ in venues.get(paper, []):
            by_venue[g.get(venue, "name")][0] += 1
            by_venue[g.get(venue, "name")][1].add(paper)
    a["AR19"] = Answer([(v, n, len(papers)) for v, (n, papers) in by_venue.items()], ((1, True),), 10)

    # D. Researchers and labs
    a["AR20"] = Answer(distinct_counted(((g.get(per, "name"),), src) for src, paper, _ in cites
                                        for per, _ in authors.get(paper, []) if full(per)), ((1, True),), 10)
    a["AR21"] = Answer(distinct_counted(((g.get(per, "name"),), topic[src]) for src, paper, _ in cites
                                        for per, _ in authors.get(paper, []) if full(per)), ((1, True),), 10)
    a["AR22"] = Answer(distinct_counted(((g.get(src, "name"),), dst) for src, dst, _ in labs
                                        if status[dst] == "open"), ((1, True),), 10)
    # Two different AUTHORED_BY edges of one paper: a MATCH never uses one edge twice.
    a["AR23"] = Answer(counted((g.get(x, "name"), g.get(y, "name"))
                               for people in authors.values()
                               for i, (x, _) in enumerate(people) for j, (y, _) in enumerate(people)
                               if i != j and g.get(x, "name") == author and full(y)), ((2, True),), 10)

    # F. Connections
    a["AR24"] = Answer(counted((g.get(x, "title"),) for x, _, _ in related), ((1, True),), 10)
    a["AR25"] = Answer(counted((tname(x), tname(y)) for x, y, _ in related if tname(x) < tname(y)), ((2, True),), 10)
    a["AR26"] = Answer([(g.get(y, "title"), e.get("shared_papers"), e.get("score")) for x, y, e in related
                        if x == example], ((2, True),))
    a["AR27"] = Answer(counted(((g.get(x, "name") or "").lower(),) for _, x, _ in g.edges["RESTS_ON"]),
                       ((1, True),), 10)
    a["AR31"] = Answer([(g.get(x, "title"), g.get(y, "title"), e.get("shared_papers"), e.get("score"))
                        for x, y, e in g.edges["RELATED_TO"]], ((2, True),), 10)
    a["AR32"] = Answer(distinct_counted(((g.get(x, "title"), tname(x)), topic[y]) for x, y, _ in related
                                        if topic[y] != topic[x]), ((2, True),), 10)

    # G. Opportunities
    budget = lambda f: g.get(f, "compute_budget_gpu_hours")
    a["AR28"] = Answer([(g.get(pid, "title"), budget(f)) for pid, f in experiment.items()
                        if budget(f) is not None and budget(f) > 0], ((1, False),), 10)
    a["AR29"] = Answer(counted((tname(pid),) for pid, _ in single), ((1, True),), 10)
    with_lab = {dst for _, dst, _ in labs}
    a["AR30"] = Answer([(p["title"],) for p in problems if status[p["id"]] == "open" and p["id"] not in with_lab],
                       limit=20)

    # H. Must return nothing: the graph holds no funding and no leaderboards.
    a["AR90"] = Answer([])
    a["AR91"] = Answer([])
    return a


def _norm(row) -> tuple:
    return tuple(round(v, 6) if isinstance(v, float) else v for v in row)


def _key(row: tuple, order) -> tuple:
    """A sort key that follows Cypher: null after every value ascending, before every value descending."""
    key = []
    for col, desc in order:
        v = row[col]
        missing = v is None
        if desc:
            key.append((not missing, _neg(v)) if not missing else (False, 0))
        else:
            key.append((missing, v if not missing else 0))
    return tuple(key)


def _neg(v):
    return -v if isinstance(v, (int, float)) and not isinstance(v, bool) else _Desc(v)


class _Desc:
    """Reverses the order of a non-numeric value."""

    def __init__(self, v):
        self.v = v

    def __lt__(self, other):
        return self.v > other.v

    def __eq__(self, other):
        return self.v == other.v


def check(engine_rows: list, ref: Answer) -> list[str]:
    """What is wrong with the engine's rows, or [] when they agree with the reference."""
    rows = [_norm(r) for r in engine_rows]
    full = [_norm(r) for r in ref.rows]
    want = len(full) if ref.limit is None else min(ref.limit, len(full))
    problems = []
    if len(rows) != want:
        problems.append(f"{len(rows)} rows, the reference has {want}")
    extra = Counter(rows) - Counter(full)
    if extra:
        problems.append(f"{sum(extra.values())} rows the reference does not have, e.g. {next(iter(extra))}")
    if ref.order:
        keys = [_key(r, ref.order) for r in rows]
        if keys != sorted(keys):
            problems.append("rows are not in the promised order")
        if ref.limit is not None:
            top = sorted(_key(r, ref.order) for r in full)[:want]
            if sorted(keys) != top:
                problems.append("under the LIMIT these are not the top rows")
    return problems


@click.command()
@click.option("--only", default=None, help="Answer one query id, e.g. AR14.")
@click.option("--rows", default=3, show_default=True)
def main(only, rows):
    found = answers(load())
    for qid, ans in sorted(found.items()):
        if only and qid != only:
            continue
        shown = sorted(ans.rows, key=lambda r: _key(_norm(r), ans.order)) if ans.order else ans.rows
        shown = shown[:ans.limit] if ans.limit else shown
        click.echo(f"{qid}  {len(shown):4d} rows")
        for r in shown[:rows]:
            click.echo("      " + " | ".join(str(v)[:70] for v in r))
    sys.exit(0)


if __name__ == "__main__":
    main()
