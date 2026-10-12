"""The vocabularies, the ontology file and the parser agree; the graph keeps the rules.

The last test runs etl.conformance on the full graph (skipped without the catalog).
"""
import re
from pathlib import Path

import pytest

from etl import parse
from etl.conformance import (
    TRACKED_FAILURES,
    Report,
    arxiv_year_month,
    check_coding,
    check_ontology,
    check_standards,
    check_taxonomy,
    codes,
    load_ontology,
    load_vocab,
)
from etl.conformance_lib import inline_code
from etl.download_data import CATALOG_DIR, PINNED_COMMIT

SCHEMA = Path(__file__).resolve().parent.parent / "schema" / "ai_research_kg.cypher"

# Rules the v1 graph breaks today, each with its tracked fix (etl.conformance.TRACKED_FAILURES,
# shown at the top of docs/conformance.md). Fixing one must remove it there.
KNOWN_FAILURES = set(TRACKED_FAILURES)


@pytest.fixture(scope="module")
def vocab():
    return load_vocab()


@pytest.fixture(scope="module")
def onto():
    return load_ontology()


def test_vocabularies_are_well_formed(vocab):
    for name, scheme in vocab.items():
        assert {"label", "property", "status", "source", "concepts"} <= set(scheme), name
        assert scheme["status"] in ("in_use", "proposed"), name
        found = [c["code"] for c in scheme["concepts"]]
        assert len(found) == len(set(found)), f"duplicate code in {name}"
        for c in scheme["concepts"]:
            assert c.get("label") and c.get("definition"), f"{name}.{c['code']}"


def test_vocabularies_match_the_parser(vocab):
    assert codes(vocab, "cites_role") == {name for name, _ in parse.ROLE_RULES} | {"context"}
    assert codes(vocab, "obstruction") == set(parse.OBSTRUCTIONS) | {"other"}
    assert codes(vocab, "institution_kind") == {kind for _, _, kind, _ in parse.INSTITUTIONS}
    assert {parse.classify_gap(h) for h in ("Theoretically open", "Empirically open", "Methodologically blocked", "Open")} \
        == codes(vocab, "gap_kind")
    assert {parse.assumption_status(t) for t in ("violated", "partly violated", "holds", "")} \
        == codes(vocab, "assumption_status")
    assert {parse.name_form(n) for n in ("Rico Sennrich", "T. Moerland", "Wortsman", "Llama Team")} \
        == codes(vocab, "name_form")


def test_topic_areas_cover_each_topic_once(vocab):
    numbers = sorted(n for c in vocab["topic_area"]["concepts"] for n in c["topics"])
    assert numbers == list(range(1, 36))


def test_ontology_matches_schema_file(onto):
    text = SCHEMA.read_text(encoding="utf-8")
    labels = set(re.search(r"Node labels: (.*?)\n//\n", text, re.S).group(1).replace("//", "").replace("\n", " ").replace(",", " ").split())
    assert labels == set(onto["classes"])
    declared = set(re.findall(r"\((\w+)\)-\[:(\w+)[^\]]*\]->\((\w+)\)", text))
    assert declared == {(r["domain"], t, r["range"]) for t, r in onto["edges"].items()}
    for name, cls in onto["classes"].items():
        re.compile(cls["id_pattern"])
        assert cls["id_pattern"] != "None", name


def test_ontology_code_lists_exist(onto, vocab):
    for key, p in onto["props"].items():
        if p["code_list"]:
            assert p["code_list"] in vocab, key


def test_ontology_names_and_rules_are_data_not_labels(onto):
    props = onto["props"]
    # Two classes carry a `kind`; the graph name comes from kg:propertyName, not rdfs:label.
    assert props["kind_institution"]["name"] == "kind" and props["kind_institution"]["domain"] == "Institution"
    assert props["kind_gap"]["name"] == "kind" and props["kind_gap"]["domain"] == "OpenQuestion"
    assert props["relatedness_method"]["name"] == "method" and props["relatedness_method"]["on_edge"]
    # The "method on every node but DataSource" rule is declared, not hard-coded.
    assert props["method"]["required"] and props["method"]["not_required_on"] == {"DataSource"}
    # Edge properties used by rules are declared.
    assert props["is_primary"]["on_edge"] and props["score"]["on_edge"]


def test_arxiv_ids_old_and_new_style():
    assert arxiv_year_month("2406.11779") == (2024, 6)
    assert arxiv_year_month("1412.6980") == (2014, 12)
    assert arxiv_year_month("cs/0112017") == (2001, 12)
    assert arxiv_year_month("math.GT/0309136") == (2003, 9)
    assert arxiv_year_month("2406.1177") is None      # 4 digits after 2015
    assert arxiv_year_month("1412.69800") is None     # 5 digits before 2015
    assert arxiv_year_month("hep-th/9901001") == (1999, 1)


def test_inline_code_survives_backticks():
    assert inline_code("ICLR") == "`ICLR`"
    assert inline_code("Technical write-up / `guidance` documentation") == "``Technical write-up / `guidance` documentation``"
    assert inline_code("`(") == "`` `( ``"


@pytest.mark.skipif(not (CATALOG_DIR / "TAXONOMY.md").exists(), reason="catalog not downloaded")
def test_conformance_failures_are_the_known_ones(vocab, onto):
    g = parse.build_graph(CATALOG_DIR, PINNED_COMMIT)
    areas = {n: c["code"] for c in vocab["topic_area"]["concepts"] for n in c["topics"]}
    r = Report()
    check_taxonomy(r, g, CATALOG_DIR, vocab, areas)
    check_ontology(r, g, onto, CATALOG_DIR)
    check_coding(r, g, onto, vocab)
    check_standards(r, g)
    assert {c.cid for c in r.failures()} == KNOWN_FAILURES
    assert all(c.ok for c in r.checks if c.section.startswith("1.") and c.ok is not None), "taxonomy rules must hold"
