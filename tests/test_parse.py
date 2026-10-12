"""Parser tests on a small fixture catalog (one real problem file + one handwritten)."""
from pathlib import Path

import pytest

from etl.parse import (
    build_graph,
    name_form,
    normalise_venue,
    parse_reference,
    role_bucket,
    split_authors,
    split_sections,
)

FIXTURE = Path(__file__).parent / "fixtures" / "catalog"
SWAPPED = FIXTURE / "topics/22-safety-robustness/fixture-swapped-sections.md"
REAL = "problem:20-interpretability/internals-based-safety-verification"
FIX = "problem:22-safety-robustness/fixture-swapped-sections"


@pytest.fixture(scope="module")
def graph():
    return build_graph(FIXTURE, commit="fixture")


# --- small pieces -------------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("Wortsman, Ilharco, Gadre, et al.", ["Wortsman", "Ilharco", "Gadre"]),
    ("Matena & Raffel", ["Matena", "Raffel"]),
    ("Moerland, T., Broekens, J., Plaat, A.", ["T. Moerland", "J. Broekens", "A. Plaat"]),
    ("Rico Sennrich, Barry Haddow, Alexandra Birch.", ["Rico Sennrich", "Barry Haddow", "Alexandra Birch"]),
    ("Neel Nanda (Google DeepMind) & Arthur Conmy", ["Neel Nanda", "Arthur Conmy"]),
])
def test_split_authors(text, expected):
    assert split_authors(text) == expected


def test_name_forms():
    assert name_form("Wortsman") == "surname"
    assert name_form("T. Moerland") == "initials"
    assert name_form("Rico Sennrich") == "full"
    assert name_form("Llama Team") == "collective"


def test_parse_reference_fields():
    r = parse_reference("- **[SOTA — theory]** Gross, Chughtai, et al. *Compact Proofs of Model "
                        "Performance via Mechanistic Interpretability.* NeurIPS, 2024. — arXiv:2406.11779v2")
    assert r["arxiv_id"] == "2406.11779"
    assert r["year"] == 2024
    assert r["venue"] == "NeurIPS"
    assert r["role"] == "sota" and r["role_raw"] == "SOTA — theory"
    assert r["title"].startswith("Compact Proofs")


def test_role_buckets_put_negative_results_in_caution():
    assert role_bucket("SOTA / negative result") == "caution"
    assert role_bucket("Survey/Benchmark") == "survey"
    assert role_bucket("Related") == "context"


def test_venue_normalisation():
    assert normalise_venue("Findings of EMNLP") == "EMNLP"
    assert normalise_venue("EMNLP (industry track)") == "EMNLP"
    assert normalise_venue("CACM 52") == "CACM"
    assert normalise_venue("") is None


def test_sections_found_by_name_not_number():
    sec = split_sections(SWAPPED.read_text(encoding="utf-8"))
    assert "Reluplex" in sec["refs"]
    assert "two-layer model" in sec["example"]


# --- the fixture graph ------------------------------------------------------------
def test_problem_nodes(graph):
    assert set(graph.nodes["Problem"]) == {REAL, FIX}
    p = graph.nodes["Problem"][REAL]
    assert p["status"] == "solved-but-impractical"
    assert p["catalog_provenance"] == "synthesized"   # the catalog's prose flag, kept separate from provenance = real
    assert p["provenance"] == "real" and p["method"] == "parsed"
    assert p["topic"] == "20-interpretability"
    assert p["statement"].startswith("Given a trained network")


def test_swapped_file_still_cites_its_references(graph):
    cited = [e for e in graph.edges if e[1] == FIX and e[2] == "CITES"]
    assert len(cited) == 4


def test_papers_deduplicated_by_arxiv_id(graph):
    reluplex = graph.nodes["Paper"]["paper:arxiv:1702.01135"]
    assert reluplex["year"] == 2017
    citing = {e[1] for e in graph.edges if e[2] == "CITES" and e[4] == "paper:arxiv:1702.01135"}
    assert citing == {REAL, FIX}


def test_related_to_is_computed_from_shared_papers(graph):
    rel = [e for e in graph.edges if e[2] == "RELATED_TO"]
    assert len(rel) == 1
    assert rel[0][5]["method"] == "shared_papers" and rel[0][5]["shared_papers"] >= 2


def test_gaps_assumptions_obstructions(graph):
    kinds = sorted(n["kind"] for i, n in graph.nodes["OpenQuestion"].items() if i.startswith(FIX))
    assert kinds == ["empirically_open", "methodologically_blocked", "theoretically_open"]
    assumptions = {n["name"]: n["violated"] for i, n in graph.nodes["Assumption"].items() if i.startswith(FIX)}
    assert assumptions == {"Linear representation": "violated", "Finite input region": "holds"}
    blocked = {e[4] for e in graph.edges if e[1] == FIX and e[2] == "BLOCKED_BY"}
    assert blocked == {"obstruction:absent_ground_truth", "obstruction:non_identifiability"}


def test_next_experiment_fields(graph):
    f = graph.nodes["FutureDirection"][f"{FIX}#next-experiment"]
    assert f["compute_budget_gpu_hours"] == 40.0
    assert f["single_machine"] is True
    assert f["deciding_number"].startswith("The certified bound")


def test_labs_active_on(graph):
    labs = {e[1] for e in graph.edges if e[4] == FIX and e[2] == "ACTIVE_ON"}
    assert labs == {"institution:anthropic", "institution:mit", "institution:google_deepmind"}
