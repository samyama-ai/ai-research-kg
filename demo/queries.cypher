// The ten queries of the demo, in the order it runs them.
// Written by `python -m demo.demo --write-cypher`. Do not edit: edit
// benchmarks/queries.py and regenerate.

// 1. How open is the field?  (AR02, rests on: parsed)
// How many problems are there in total, and how many per status (open = status 'open')?
MATCH (p:Problem) RETURN p.status AS status, count(p.id) AS problems ORDER BY problems DESC;

// 2. Which topics have the most open problems?  (AR04, rests on: parsed)
// Which topics have the largest share of open problems? (open count and topic size; divide for the share)
MATCH (p:Problem)-[:IN_TOPIC]->(t:Topic) WHERE p.status = 'open' RETURN t.name AS topic, count(p.id) AS open_problems ORDER BY open_problems DESC LIMIT 10;

// 3. Which papers are cited across the most topics?  (AR15, rests on: parsed)
// Which papers are cited across the most topics?
MATCH (t:Topic)<-[:IN_TOPIC]-(p:Problem)-[:CITES]->(pa:Paper) RETURN pa.title AS paper, count(DISTINCT t.id) AS topics ORDER BY topics DESC LIMIT 10;

// 4. Which foundational papers underpin the most problems?  (AR17, rests on: rule)
// Which foundational papers underpin the most problems?
MATCH (p:Problem)-[c:CITES]->(pa:Paper) WHERE c.role = 'foundational' RETURN pa.title AS paper, count(p.id) AS problems ORDER BY problems DESC LIMIT 10;

// 5. Which labs are named on the most open problems?  (AR22, rests on: rule)
// Which labs are named as working on the most open problems?
MATCH (i:Institution)-[:ACTIVE_ON]->(p:Problem) WHERE p.status = 'open' RETURN i.name AS lab, count(DISTINCT p.id) AS open_problems ORDER BY open_problems DESC LIMIT 10;

// 6. Why do problems stay hard?  (AR08, rests on: rule)
// What are the most common reasons these problems remain hard?
MATCH (p:Problem)-[:BLOCKED_BY]->(o:Obstruction) RETURN o.name AS obstruction, count(p.id) AS problems ORDER BY problems DESC;

// 7. Which problems are closest to 'internals-based-safety-verification'?  (AR26, rests on: computed)
// Which problems are most similar to problem X?
MATCH (p:Problem)-[r:RELATED_TO]-(o:Problem) WHERE p.slug = 'internals-based-safety-verification' RETURN o.title AS problem, r.shared_papers AS shared_papers, r.score AS score ORDER BY score DESC;

// 8. Which next experiments are cheapest to run?  (AR28, rests on: parsed)
// Which next experiments are cheapest to run (GPU-hours)?
MATCH (p:Problem)-[:HAS_NEXT_EXPERIMENT]->(f:FutureDirection) WHERE f.compute_budget_gpu_hours > 0 RETURN p.title AS problem, f.compute_budget_gpu_hours AS gpu_hours ORDER BY gpu_hours ASC LIMIT 10;

// 9. Which open problems fit on a single machine?  (AR09, rests on: parsed)
// Which open problems have a next experiment that fits on a single machine?
MATCH (p:Problem)-[:HAS_NEXT_EXPERIMENT]->(f:FutureDirection) WHERE p.status = 'open' AND f.single_machine = true RETURN p.title AS problem, f.compute_budget_gpu_hours AS gpu_hours ORDER BY gpu_hours ASC LIMIT 10;

// 10. How much funding has each problem received?  (AR90, rests on: none)
// How much funding has each problem received? (no such data)
MATCH (p:Problem)-[:FUNDED_BY]->(f) RETURN p.title AS problem, f.amount AS amount;
