// AI Research Knowledge Graph -- schema
//
// Built only from github.com/samyama-ai/ai_research (pinned commit in
// etl/download_data.py). See docs/schema.md for the full description.
//
// Node labels: Problem, Topic, Paper, Person, Venue, Institution, Assumption,
//              OpenQuestion, Obstruction, FutureDirection, DataSource
//
// Edge types:  (Problem)-[:IN_TOPIC]->(Topic)
//              (Problem)-[:CITES {role, role_raw, position}]->(Paper)
//              (Paper)-[:AUTHORED_BY {position}]->(Person)
//              (Paper)-[:APPEARED_AT]->(Venue)
//              (Problem)-[:RESTS_ON {position}]->(Assumption)
//              (Problem)-[:HAS_GAP {position}]->(OpenQuestion)
//              (Problem)-[:BLOCKED_BY {detail, is_primary}]->(Obstruction)
//              (Problem)-[:HAS_NEXT_EXPERIMENT]->(FutureDirection)
//              (Institution)-[:ACTIVE_ON {direction}]->(Problem)
//              (Problem)-[:RELATED_TO {method, shared_papers, score}]->(Problem)   computed
//              (Problem)-[:FROM_SOURCE]->(DataSource)
//
// Every node carries `id`, `provenance` ("real"), `source` ("ai_research")
// and `method` ("parsed" | "keyword-classified" | "name-matched").
// Problem-derived nodes also carry `source_url` (file at the pinned commit).
//
// This engine accepts `CREATE INDEX ON :Label(prop)` but not
// `CREATE CONSTRAINT ... IS UNIQUE`; `id` uniqueness is guaranteed by the
// parser (ids are minted deterministically) and checked in tests.
//
// The `id` indexes are what make the edge load finish: every edge endpoint is
// resolved with `WHERE v.id = ...` (edge-ai-kg measured 10x without them).

CREATE INDEX ON :Problem(id);
CREATE INDEX ON :Topic(id);
CREATE INDEX ON :Paper(id);
CREATE INDEX ON :Person(id);
CREATE INDEX ON :Venue(id);
CREATE INDEX ON :Institution(id);
CREATE INDEX ON :Assumption(id);
CREATE INDEX ON :OpenQuestion(id);
CREATE INDEX ON :Obstruction(id);
CREATE INDEX ON :FutureDirection(id);
CREATE INDEX ON :DataSource(id);

// Filters used by benchmarks/queries.py
CREATE INDEX ON :Problem(status);
CREATE INDEX ON :Problem(slug);
CREATE INDEX ON :Topic(slug);
CREATE INDEX ON :OpenQuestion(kind);
