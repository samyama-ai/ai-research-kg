// AI Research Knowledge Graph -- one-page picture of the model.
// One example node per label and one example edge per type, taken from the
// real graph (problem: 20-interpretability/internals-based-safety-verification).
// Documentation only: the loader runs schema/ai_research_kg.cypher, not this.

// --- Nodes ---------------------------------------------------------------------
// (:Problem {id: "problem:20-interpretability/internals-based-safety-verification",
//            title: "Scalable Verification of Safety Properties From Internals",
//            status: "solved-but-impractical", topic: "20-interpretability",
//            catalog_provenance: "synthesized", provenance: "real", source: "ai_research"})
// (:Topic {id: "topic:20-interpretability", number: 20, name: "Interpretability"})
// (:Paper {id: "paper:arxiv:1702.01135", title: "Reluplex: ...", year: 2017, venue: "CAV"})
// (:Person {id: "person:katz", name: "Katz", name_form: "surname"})
// (:Venue {id: "venue:cav", name: "CAV"})
// (:Institution {id: "institution:anthropic", name: "Anthropic", kind: "industry"})
// (:Assumption {id: "<problem id>#assumption-1", name: "Linear representation", violated: "violated"})
// (:OpenQuestion {id: "<problem id>#gap-1", kind: "theoretically_open"})
// (:Obstruction {id: "obstruction:absent_ground_truth", name: "Absent ground truth"})
// (:FutureDirection {id: "<problem id>#next-experiment", compute_budget_gpu_hours: 200.0})
// (:DataSource {id: "datasource:ai_research", version: "a02e87b3..."})

// --- Edges ---------------------------------------------------------------------
// (:Problem)-[:IN_TOPIC]->(:Topic)
// (:Problem)-[:CITES {role: "foundational", role_raw: "Foundational", position: 1}]->(:Paper)
// (:Paper)-[:AUTHORED_BY {position: 1}]->(:Person)
// (:Paper)-[:APPEARED_AT]->(:Venue)
// (:Problem)-[:RESTS_ON {position: 1}]->(:Assumption)
// (:Problem)-[:HAS_GAP {position: 1}]->(:OpenQuestion)
// (:Problem)-[:BLOCKED_BY {detail: "...", is_primary: true}]->(:Obstruction)
// (:Problem)-[:HAS_NEXT_EXPERIMENT]->(:FutureDirection)
// (:Institution)-[:ACTIVE_ON {direction: "Anthropic / GDM interpretability teams"}]->(:Problem)
// (:Problem)-[:RELATED_TO {method: "shared_papers", shared_papers: 5, score: 0.278}]->(:Problem)
// (:Problem)-[:FROM_SOURCE]->(:DataSource)
