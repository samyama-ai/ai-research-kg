"""The demo's ten steps are entries of the query catalog, and the cypher file is generated from them."""
from pathlib import Path

from benchmarks.queries import QUERIES
from demo.demo import BASIS, STORY, write_cypher

IDS = {q["id"] for q in QUERIES}


def test_story_steps_are_catalog_queries_with_a_known_basis():
    assert len(STORY) == 10
    for query_id, title, lead, basis, rows in STORY:
        assert query_id in IDS, query_id
        assert basis in BASIS and title and lead and rows > 0
    assert [s[0] for s in STORY if s[3] == "none"] == ["AR90"]


def test_queries_cypher_matches_the_story(tmp_path):
    written = write_cypher(tmp_path / "queries.cypher").read_text(encoding="utf-8")
    committed = (Path(__file__).resolve().parent.parent / "demo" / "queries.cypher").read_text(encoding="utf-8")
    assert written == committed, "run `python -m demo.demo --write-cypher` after changing the story or the catalog"
