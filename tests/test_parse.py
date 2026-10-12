"""Parser tests on a small fixture catalog (one real problem file + one handwritten)."""
from pathlib import Path

import pytest

import json
from collections import Counter

import etl.build as build
import etl.parse as parse
from etl.build import catalog_dates
from etl.download_data import CATALOG_DIR, LOCK_PATH, lock_path
from etl.parse import (
    BUILD_EXPORTS,
    assumption_status,
    build_graph,
    name_form,
    normalise_venue,
    parse_assumptions,
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


def test_assumptions_in_all_four_forms():
    inline = "**Assumptions known to be violated.** (i) $T$ is applied to whole prompts — false: templates split. (ii) Tokens are stable — violated in practice.\n"
    assert [a["violated"] for a in parse_assumptions(inline)] == ["violated", "violated"]
    prose = "**Assumptions and their status.** Smoothness with a global $L$: *violated* — sharpness grows. Bounded variance: *violated* under heavy tails.\n"
    assert [a["name"] for a in parse_assumptions(prose)] == ["Smoothness with a global $L$", "Bounded variance"]
    table = "**Assumptions, and their status:**\n\n| Assumption | Status |\n|---|---|\n| $H \\approx cI$ | **Violated.** wide spectra |\n| i.i.d. data | holds |\n"
    assert [a["violated"] for a in parse_assumptions(table)] == ["violated", "holds"]
    listed = "**Assumptions.**\n- *Linear features.* Partly violated.\n- *Fixed data.* Holds.\n"
    assert [a["name"] for a in parse_assumptions(listed)] == ["Linear features", "Fixed data"]


def test_venue_residue_and_aliases():
    assert normalise_venue("(") is None
    assert normalise_venue("USENIX NSDI") == normalise_venue("NSDI") == "NSDI"
    assert normalise_venue("Communications of the ACM") == "CACM"


def test_one_venue_per_paper(graph):
    per_paper = Counter(e[1] for e in graph.edges if e[2] == "APPEARED_AT")
    assert per_paper and max(per_paper.values()) == 1
    # the fixture has no recorded fetch, so the dates are left off every node (never a placeholder)
    assert not any("retrieved_at" in n or "source_date" in n for nodes in graph.nodes.values() for n in nodes.values())


def test_assumption_heading_rules():
    # a heading mid-paragraph still counts; bold emphasis that merely mentions assumptions does not
    mid = "Both cannot hold. **Assumptions known to be violated:** (i) Language ID is known — false. (ii) Test data is human — violated.\n"
    assert len(parse_assumptions(mid)) == 2
    emphasis = "This **assumption is load-bearing** for the bound.\n- not an assumption list\n"
    assert parse_assumptions(emphasis) == []
    # intro text on the heading line does not hide the list under it
    intro = "**Assumptions and their status:** the first matters most.\n\n- *Linear features.* Violated.\n- *Fixed data.* Holds.\n\nLater prose.\n- unrelated list\n"
    assert [a["name"] for a in parse_assumptions(intro)] == ["Linear features", "Fixed data"]


def test_assumption_verdict_words():
    assert assumption_status("Heads are independent. False — subspaces overlap.") == "violated"
    assert assumption_status("Rare: false positives are filtered out by a second pass.") == "unstated"
    assert assumption_status("True for post-LN models; false for rotated models.") == "partly"


def test_fast_alias_is_not_any_word_fast():
    assert normalise_venue("USENIX FAST") == "FAST"
    assert normalise_venue("Fast Company") == "Fast Company"


def test_venue_raw_matches_the_chosen_venue(graph):
    for p in graph.nodes["Paper"].values():
        if p.get("venue") and p.get("venue_raw"):
            assert normalise_venue(p["venue_raw"]) == p["venue"], p["id"]


def test_bare_assumptions_heading_and_plain_list_names():
    bare = "**Assumptions**\n- *Linear features.* Violated.\n- Features are directions — violated by circular features (Engels 2024).\n"
    items = parse_assumptions(bare)
    # the plain list item keeps the v1 naming: lead-in if italic/bold, else the first eight words
    assert [a["name"] for a in items] == ["Linear features", "Features are directions — violated by circular features"]
    assert [a["violated"] for a in items] == ["violated", "violated"]
    emphasis = "The **assumption** here is strong.\n- not an assumption list\n"
    assert parse_assumptions(emphasis) == []


def test_false_positive_forms_are_not_verdicts():
    assert assumption_status("Rare: false-positive rate stays below 1%.") == "unstated"
    assert assumption_status("Rare: false positives are filtered out.") == "unstated"
    assert assumption_status("Independence: false — heads share subspaces.") == "violated"


def test_catalog_dates_come_from_the_lock_file(tmp_path):
    root = tmp_path / "ai_research"
    root.mkdir()
    assert catalog_dates(root, "abc") == (None, None)
    (tmp_path / "ai_research.lock.json").write_text(json.dumps(
        {"commit": "abc", "fetched_at": "2026-10-07T09:12:00+00:00", "commit_date": "2026-09-10T03:38:11+05:30"}))
    assert catalog_dates(root, "abc") == ("2026-10-07", "2026-09-10")
    assert catalog_dates(root, "other") == (None, None)


def test_venue_with_no_two_letters_in_a_row_still_resolves():
    assert normalise_venue("S&P") == "IEEE S&P"
    assert normalise_venue("OpenReview") == "OpenReview"
    assert normalise_venue("USENIX Conference on File and Storage Technologies") == "FAST"


def test_false_positives_at_sentence_start_is_not_a_verdict():
    assert assumption_status("False positives are filtered by a second pass.") == "unstated"
    assert assumption_status("False. The heads overlap.") == "violated"


def test_inline_enumeration_rules():
    # "(1)" inside prose is a reference, not an enumeration; the item list below is what counts
    prose_ref = "**Assumptions.** See Eq. (1) for the setting.\n\n- *Smoothness.* Violated.\n- *Bounded noise.* Holds.\n"
    assert [a["name"] for a in parse_assumptions(prose_ref)] == ["Smoothness", "Bounded noise"]
    # a list below the heading is the content; an enumeration on the heading line is then an introduction
    both = "**Assumptions:** (i) linearity and (ii) stationarity, in detail:\n- *Linearity.* Violated.\n- *Stationarity.* Holds.\n"
    assert [a["name"] for a in parse_assumptions(both)] == ["Linearity", "Stationarity"]
    # a table under the heading, even indented
    table = "**Assumptions and their status.**\n\n  | Assumption | Status |\n  |---|---|\n  | i.i.d. data | holds |\n  | Bounded noise | **Violated** |\n"
    assert [(a["name"], a["violated"]) for a in parse_assumptions(table)] == [("i.i.d. data", "holds"), ("Bounded noise", "violated")]
    # an indented list under the heading is a list
    indented = "**Assumptions.**\n  - *Linear features.* Violated.\n  - *Fixed data.* Holds.\n"
    assert [a["name"] for a in parse_assumptions(indented)] == ["Linear features", "Fixed data"]


def test_lazy_reexports_are_the_build_objects():
    for name in BUILD_EXPORTS:
        assert getattr(parse, name) is getattr(build, name), name
    with pytest.raises(AttributeError):
        parse.no_such_name  # noqa: B018


def test_bold_sentence_about_assumptions_is_not_a_heading():
    # a bold sentence is longer than any real heading (the cap is HEADING_MAX_WORDS = 10 words)
    sentence = "**Assumptions in this section are often violated in practice, as the next three paragraphs show.**\n- not an assumption list\n"
    assert parse_assumptions(sentence) == []
    long_heading = "**Assumptions, with the ones known to be violated flagged:**\n- *Linear features.* Violated.\n"
    assert [a["name"] for a in parse_assumptions(long_heading)] == ["Linear features"]


def test_venue_provenance_raw_and_variants(graph):
    venues = graph.nodes["Venue"]
    # a Venue node's source_url is the page that first names that venue: CAV comes from the real
    # page (both pages cite Reluplex at CAV; the real page is read first), the invented journal
    # only from the handwritten page
    assert venues["venue:cav"]["source_url"].endswith("internals-based-safety-verification.md")
    assert venues["venue:journal_of_fixture_studies"]["source_url"].endswith("fixture-swapped-sections.md")
    # no venue chosen -> no venue_raw either (residue such as "(" is not a venue)
    assert all(p.get("venue_raw") is None for p in graph.nodes["Paper"].values() if not p.get("venue"))
    # variants, when present, are a list and never repeat the chosen venue
    for p in graph.nodes["Paper"].values():
        if p.get("venue_variants"):
            assert isinstance(p["venue_variants"], list) and p["venue"] not in p["venue_variants"]


def test_lock_path_is_defined_in_one_place(tmp_path):
    assert LOCK_PATH == lock_path(CATALOG_DIR) == CATALOG_DIR.with_name("ai_research.lock.json")
    assert lock_path(tmp_path / "x" / "catalog") == tmp_path / "x" / "catalog.lock.json"


def test_enumeration_rules_reject_equation_references_and_keep_sub_bullets():
    # "Eq. (1) and (2)" is a pair of references, not an enumeration: the line stays one prose statement
    refs = "**Assumptions.** The bound follows from Eq. (1) and (2) under smoothness.\n"
    assert [a["name"] for a in parse_assumptions(refs)] == ["The bound follows from Eq. (1) and"]
    # a sub-bullet is a continuation of its item, not an assumption of its own
    nested = "**Assumptions.**\n- *Linear features.* Violated.\n  - detail: circular features exist\n- *Fixed data.* Holds.\n"
    items = parse_assumptions(nested)
    assert [a["name"] for a in items] == ["Linear features", "Fixed data"]
    assert "circular features" in items[0]["text"]
    # a table without a header separator has no header row to drop
    headerless = "**Assumptions and their status.**\n\n| i.i.d. data | holds |\n| Bounded noise | **Violated** |\n"
    assert [a["violated"] for a in parse_assumptions(headerless)] == ["holds", "violated"]
    # a mixed verdict needs the contrast in the same sentence; "true in practice" alone is not mixed
    assert assumption_status("True for post-LN models; false for rotated models.") == "partly"
    assert assumption_status("True in practice. A later sentence says the bound is violated.") == "violated"
    # an unbalanced parenthesis is residue, a balanced one is part of the venue text
    assert normalise_venue("NeurIPS)") == "NeurIPS"
    assert normalise_venue("Findings (ACL)") == "ACL"
