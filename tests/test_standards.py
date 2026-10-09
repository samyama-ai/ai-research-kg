"""The vocabularies, the ontology file and the parser agree; the graph keeps the rules.

The last test runs etl.conformance on the full graph (skipped without the catalog).
"""
import re
from pathlib import Path

import pytest

from etl import parse
from etl.conformance import (
    Report,
    check_coding,
    check_ontology,
    check_standards,
    check_taxonomy,
    codes,
    load_ontology,
    load_vocab,
)
from etl.download_data import CATALOG_DIR, PINNED_COMMIT

SCHEMA = Path(__file__).resolve().parent.parent / "schema" / "ai_research_kg.cypher"

# Rules the graph breaks today (docs/conformance.md); v1.1 fixed the three v1 failures
# (two venues per paper, the empty id "venue:", no retrieved_at). A new one must be listed here.
KNOWN_FAILURES: set[str] = set()


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
