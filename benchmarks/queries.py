"""Query catalog for the AI Research KG -- the docs/scope.md questions as Cypher.

    python -m benchmarks.queries --url http://127.0.0.1:8090          # run all
    python -m benchmarks.queries --url http://127.0.0.1:8090 --only AR12
    python -m benchmarks.queries --coverage                           # which scope questions are covered

Each entry names the scope.md question(s) it answers (`scope`), or None for a
query that is useful but answers no numbered question. Questions the v1 graph
cannot answer are listed in UNANSWERED with the reason; tests/test_queries.py
checks that every question 1-41 is either answered or listed there.

A run fails when a query errors, when a query returns no rows, or when an
AR9x query (must return nothing: the graph holds no such data) returns rows.

Engine note (from edge-ai-kg): aggregate on a property, `count(x.id)`, not on
a relationship variable.
"""
from __future__ import annotations

import sys
import time

import click

EXAMPLE_PROBLEM = "internals-based-safety-verification"   # the page read in Phase 1
SCOPE_QUESTIONS = range(1, 42)                            # docs/scope.md numbers 1-41

# scope.md questions no query answers, and why (docs/scope.md, README "Known limits").
UNANSWERED = {
    12: "methods: not extracted in v1 (the bold text in State of the Art is evidence labels, not method names)",
    25: "methods: not extracted in v1",
    26: "methods: not extracted in v1",
    27: "methods: not extracted in v1",
    28: "methods: not extracted in v1",
    33: "stretch question: needs a directional 'enables' link between problems that the catalog never states",
    35: "topic clusters need a community-detection step over RELATED_TO; not computed in v1",
}

# {AUTHOR} is replaced at run time by the full-name author with the most papers,
# so the query does not depend on one hard-coded person being in the graph.
TOP_AUTHOR = ("MATCH (pa:Paper)-[:AUTHORED_BY]->(per:Person) WHERE per.name_form = 'full' "
              "RETURN per.name AS author, count(pa.id) AS papers ORDER BY papers DESC LIMIT 1")

QUERIES = [
    # --- A. Problems & topics -------------------------------------------------
    dict(id="AR01", scope=(1,), question="What are the 35 AI research topics?",
         cypher="MATCH (t:Topic) RETURN t.number AS number, t.name AS topic ORDER BY number"),
    dict(id="AR02", scope=(2,), question="How many problems are there in total, and how many per status (open = status 'open')?",
         cypher="MATCH (p:Problem) RETURN p.status AS status, count(p.id) AS problems ORDER BY problems DESC"),
    dict(id="AR03", scope=(3,), question="How many problems are in each topic?",
         cypher="MATCH (p:Problem)-[:IN_TOPIC]->(t:Topic) RETURN t.name AS topic, count(p.id) AS problems ORDER BY problems DESC"),
    dict(id="AR04", scope=(4,), question="Which topics have the largest share of open problems? (open count and topic size; divide for the share)",
         cypher="MATCH (p:Problem)-[:IN_TOPIC]->(t:Topic) WHERE p.status = 'open' "
                "RETURN t.name AS topic, count(p.id) AS open_problems ORDER BY open_problems DESC LIMIT 10"),
    dict(id="AR05", scope=None, question="Topic sizes, to turn AR04's open counts into shares",
         cypher="MATCH (p:Problem)-[:IN_TOPIC]->(t:Topic) RETURN t.name AS topic, count(p.id) AS problems ORDER BY topic"),
    dict(id="AR06", scope=(5,), question="How many gaps are theoretically open vs empirically open vs methodologically blocked?",
         cypher="MATCH (p:Problem)-[:HAS_GAP]->(q:OpenQuestion) RETURN q.kind AS kind, count(q.id) AS gaps ORDER BY gaps DESC"),
    dict(id="AR07", scope=(6,), question="Which problems are solved but impractical?",
         cypher="MATCH (p:Problem)-[:IN_TOPIC]->(t:Topic) WHERE p.status = 'solved-but-impractical' RETURN t.name AS topic, p.title AS problem ORDER BY topic"),
    dict(id="AR08", scope=(8,), question="What are the most common reasons these problems remain hard?",
         cypher="MATCH (p:Problem)-[:BLOCKED_BY]->(o:Obstruction) RETURN o.name AS obstruction, count(p.id) AS problems ORDER BY problems DESC"),
    dict(id="AR09", scope=(7, 37), question="Which open problems have a next experiment that fits on a single machine?",
         cypher="MATCH (p:Problem)-[:HAS_NEXT_EXPERIMENT]->(f:FutureDirection) WHERE p.status = 'open' AND f.single_machine = true "
                "RETURN p.title AS problem, f.compute_budget_gpu_hours AS gpu_hours ORDER BY gpu_hours ASC LIMIT 10"),

    # --- B. One problem ---------------------------------------------------------
    dict(id="AR10", scope=(9, 10), question="What does problem X state, and what is its status and topic?",
         cypher=f"MATCH (p:Problem)-[:IN_TOPIC]->(t:Topic) WHERE p.slug = '{EXAMPLE_PROBLEM}' RETURN p.title AS problem, p.status AS status, t.name AS topic, p.statement AS statement"),
    dict(id="AR11", scope=(11,), question="Which papers does problem X cite, and in what role?",
         cypher=f"MATCH (p:Problem)-[c:CITES]->(pa:Paper) WHERE p.slug = '{EXAMPLE_PROBLEM}' RETURN c.role AS role, pa.title AS paper, pa.year AS year ORDER BY role"),
    dict(id="AR12", scope=(13,), question="What is the proposed next experiment for problem X?",
         cypher=f"MATCH (p:Problem)-[:HAS_NEXT_EXPERIMENT]->(f:FutureDirection) WHERE p.slug = '{EXAMPLE_PROBLEM}' RETURN f.question AS question, f.compute_budget_gpu_hours AS gpu_hours, f.deciding_number AS deciding_number"),
    dict(id="AR13", scope=(23,), question="Which labs are named as working on problem X?",
         cypher=f"MATCH (i:Institution)-[a:ACTIVE_ON]->(p:Problem) WHERE p.slug = '{EXAMPLE_PROBLEM}' RETURN i.name AS lab, a.direction AS direction"),

    # --- C. Papers ----------------------------------------------------------------
    dict(id="AR14", scope=(14,), question="Which papers are cited by the most problems?",
         cypher="MATCH (p:Problem)-[:CITES]->(pa:Paper) RETURN pa.title AS paper, pa.year AS year, count(p.id) AS citing_problems ORDER BY citing_problems DESC LIMIT 10"),
    dict(id="AR15", scope=(15,), question="Which papers are cited across the most topics?",
         cypher="MATCH (t:Topic)<-[:IN_TOPIC]-(p:Problem)-[:CITES]->(pa:Paper) RETURN pa.title AS paper, count(DISTINCT t.id) AS topics ORDER BY topics DESC LIMIT 10"),
    dict(id="AR16", scope=(17,), question="Which surveys cover the most problems?",
         cypher="MATCH (p:Problem)-[c:CITES]->(pa:Paper) WHERE c.role = 'survey' RETURN pa.title AS survey, count(p.id) AS problems ORDER BY problems DESC LIMIT 10"),
    dict(id="AR17", scope=(18,), question="Which foundational papers underpin the most problems?",
         cypher="MATCH (p:Problem)-[c:CITES]->(pa:Paper) WHERE c.role = 'foundational' RETURN pa.title AS paper, count(p.id) AS problems ORDER BY problems DESC LIMIT 10"),
    dict(id="AR18", scope=(19,), question="Which papers are cited as cautions or negative results most often?",
         cypher="MATCH (p:Problem)-[c:CITES]->(pa:Paper) WHERE c.role = 'caution' RETURN pa.title AS paper, count(p.id) AS problems ORDER BY problems DESC LIMIT 10"),
    dict(id="AR19", scope=None, question="Which venues' papers are cited by the most problems?",
         cypher="MATCH (p:Problem)-[:CITES]->(pa:Paper)-[:APPEARED_AT]->(v:Venue) "
                "RETURN v.name AS venue, count(p.id) AS citations, count(DISTINCT pa.id) AS papers ORDER BY citations DESC LIMIT 10"),

    # --- D. Researchers & labs ------------------------------------------------------
    dict(id="AR20", scope=(20,), question="Which researchers (full names) appear on papers cited by the most problems?",
         cypher="MATCH (p:Problem)-[:CITES]->(pa:Paper)-[:AUTHORED_BY]->(per:Person) WHERE per.name_form = 'full' "
                "RETURN per.name AS author, count(DISTINCT p.id) AS problems ORDER BY problems DESC LIMIT 10"),
    dict(id="AR21", scope=(21,), question="Which researchers are linked to problems in the most topics?",
         cypher="MATCH (t:Topic)<-[:IN_TOPIC]-(p:Problem)-[:CITES]->(:Paper)-[:AUTHORED_BY]->(per:Person) WHERE per.name_form = 'full' RETURN per.name AS author, count(DISTINCT t.id) AS topics ORDER BY topics DESC LIMIT 10"),
    dict(id="AR22", scope=(22,), question="Which labs are named as working on the most open problems?",
         cypher="MATCH (i:Institution)-[:ACTIVE_ON]->(p:Problem) WHERE p.status = 'open' RETURN i.name AS lab, count(DISTINCT p.id) AS open_problems ORDER BY open_problems DESC LIMIT 10"),
    dict(id="AR23", scope=(24,), question="Who does the most-cited full-name author co-author with most?",
         cypher="MATCH (a:Person)<-[:AUTHORED_BY]-(pa:Paper)-[:AUTHORED_BY]->(b:Person) WHERE a.name = '{AUTHOR}' AND b.name_form = 'full' "
                "RETURN a.name AS author, b.name AS collaborator, count(pa.id) AS papers ORDER BY papers DESC LIMIT 10"),

    # --- F. Connections -----------------------------------------------------------------
    dict(id="AR24", scope=(29,), question="Which problems are related to the most other problems (shared papers)?",
         cypher="MATCH (p:Problem)-[:RELATED_TO]-(o:Problem) RETURN p.title AS problem, count(o.id) AS related ORDER BY related DESC LIMIT 10"),
    dict(id="AR25", scope=(30,), question="Which pairs of topics are most strongly connected through related problems?",
         # RELATED_TO is stored once per pair in an arbitrary direction, so match it undirected and
         # keep each topic pair once by ordering the names.
         cypher="MATCH (t1:Topic)<-[:IN_TOPIC]-(a:Problem)-[:RELATED_TO]-(b:Problem)-[:IN_TOPIC]->(t2:Topic) WHERE t1.name < t2.name "
                "RETURN t1.name AS topic_a, t2.name AS topic_b, count(a.id) AS links ORDER BY links DESC LIMIT 10"),
    dict(id="AR26", scope=(31,), question="Which problems are most similar to problem X?",
         cypher=f"MATCH (p:Problem)-[r:RELATED_TO]-(o:Problem) WHERE p.slug = '{EXAMPLE_PROBLEM}' RETURN o.title AS problem, r.shared_papers AS shared_papers, r.score AS score ORDER BY score DESC"),
    dict(id="AR27", scope=(34,), question="Which assumptions (by name) do the most problems rest on?",
         cypher="MATCH (p:Problem)-[:RESTS_ON]->(a:Assumption) RETURN toLower(a.name) AS assumption, count(p.id) AS problems ORDER BY problems DESC LIMIT 10"),
    dict(id="AR31", scope=(16,), question="Which pairs of problems share the most important papers?",
         cypher="MATCH (a:Problem)-[r:RELATED_TO]->(b:Problem) RETURN a.title AS problem_a, b.title AS problem_b, r.shared_papers AS shared_papers, r.score AS score ORDER BY shared_papers DESC LIMIT 10"),
    dict(id="AR32", scope=(32,), question="Which problems bridge the most other topics (related problems in many topics other than their own)?",
         cypher="MATCH (own:Topic)<-[:IN_TOPIC]-(p:Problem)-[:RELATED_TO]-(o:Problem)-[:IN_TOPIC]->(t:Topic) WHERE t.id <> own.id "
                "RETURN p.title AS problem, own.name AS topic, count(DISTINCT t.id) AS other_topics ORDER BY other_topics DESC LIMIT 10"),

    # --- G. Opportunities ------------------------------------------------------------
    dict(id="AR28", scope=(36,), question="Which next experiments are cheapest to run (GPU-hours)?",
         cypher="MATCH (p:Problem)-[:HAS_NEXT_EXPERIMENT]->(f:FutureDirection) WHERE f.compute_budget_gpu_hours > 0 RETURN p.title AS problem, f.compute_budget_gpu_hours AS gpu_hours ORDER BY gpu_hours ASC LIMIT 10"),
    dict(id="AR29", scope=(38,), question="Which topics have the most experiments runnable on one machine?",
         cypher="MATCH (t:Topic)<-[:IN_TOPIC]-(p:Problem)-[:HAS_NEXT_EXPERIMENT]->(f:FutureDirection) WHERE f.single_machine = true RETURN t.name AS topic, count(p.id) AS runnable ORDER BY runnable DESC LIMIT 10"),
    dict(id="AR30", scope=(39,), question="Which open problems have no lab named as working on them?",
         cypher="MATCH (p:Problem) WHERE p.status = 'open' AND NOT (p)<-[:ACTIVE_ON]-(:Institution) RETURN p.title AS problem LIMIT 20"),

    # --- H. Must return nothing --------------------------------------------------------
    dict(id="AR90", scope=(40,), question="How much funding has each problem received? (no such data)",
         cypher="MATCH (p:Problem)-[:FUNDED_BY]->(f) RETURN p.title AS problem, f.amount AS amount",
         expect_empty=True),
    dict(id="AR91", scope=(41,), question="Which model tops a given benchmark leaderboard? (no such data)",
         cypher="MATCH (m:Model)-[:TOPS]->(b:Benchmark) RETURN m.name AS model, b.name AS benchmark",
         expect_empty=True),
]


def coverage() -> dict[int, str]:
    """scope.md question number -> the query id that answers it, or 'unanswered: <why>'."""
    out: dict[int, str] = {}
    for q in QUERIES:
        for n in q["scope"] or ():
            out[n] = q["id"]
    for n, why in UNANSWERED.items():
        out[n] = f"unanswered: {why}"
    return dict(sorted(out.items()))


def resolve(client, graph: str, cypher: str) -> str:
    """Fill run-time placeholders ({AUTHOR}) from the graph itself."""
    if "{AUTHOR}" in cypher:
        records = list(client.query(TOP_AUTHOR, graph).records or [])
        author = str(records[0][0]).replace("'", "") if records else ""
        cypher = cypher.replace("{AUTHOR}", author)
    return cypher


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
@click.option("--coverage", "show_coverage", is_flag=True, help="Print which scope.md question each query answers and exit.")
def main(url, graph, only, rows, show_coverage):
    if show_coverage:
        for n, who in coverage().items():
            click.echo(f"Q{n:02d}  {who}")
        return
    selected = [q for q in QUERIES if only is None or q["id"] == only]
    if not selected:
        raise click.BadParameter(f"no query with id {only!r}; ids are {', '.join(q['id'] for q in QUERIES)}", param_hint="--only")
    from samyama import SamyamaClient
    client = SamyamaClient.connect(url)
    failures = 0
    for q in selected:
        try:
            records, ms = run(client, graph, q)
        except Exception as exc:
            failures += 1
            click.echo(f"{q['id']}  ERROR  {q['question']}\n      {exc}")
            continue
        ok = (not records) if q.get("expect_empty") else bool(records)
        failures += not ok
        click.echo(f"{q['id']}  {'ok ' if ok else 'BAD'}  {len(records):4d} rows {ms:7.1f} ms  {q['question']}")
        for r in records[:rows]:
            click.echo("      " + " | ".join(str(v)[:70] for v in r))
    click.echo(f"\n{failures} failing" if failures else f"\nall {len(selected)} queries ok")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
