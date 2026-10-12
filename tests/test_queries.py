"""The query catalog is consistent with docs/scope.md: unique ids, valid scope numbers,
every question answered or listed as unanswered, and no placeholder left unresolved."""
import re

from benchmarks.queries import QUERIES, SCOPE_QUESTIONS, UNANSWERED, coverage, resolve


def test_ids_unique_and_well_formed():
    ids = [q["id"] for q in QUERIES]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"AR\d{2}", i) for i in ids)


def test_scope_numbers_are_valid_and_not_claimed_twice():
    seen = {}
    for q in QUERIES:
        for n in q["scope"] or ():
            assert n in SCOPE_QUESTIONS, f"{q['id']} names scope question {n}, which does not exist"
            assert n not in seen, f"scope question {n} claimed by both {seen[n]} and {q['id']}"
            seen[n] = q["id"]
    assert not set(seen) & set(UNANSWERED), "a question cannot be both answered and unanswered"


def test_every_scope_question_is_answered_or_explained():
    cov = coverage()
    missing = [n for n in SCOPE_QUESTIONS if n not in cov]
    assert missing == [], f"scope questions with no query and no reason: {missing}"


def test_expect_empty_only_for_the_no_data_questions():
    assert {q["id"] for q in QUERIES if q.get("expect_empty")} == {"AR90", "AR91"}


def test_author_placeholder_is_resolved_from_the_graph():
    class Records:
        records = [["Neel Nanda", 7]]

    class Client:
        def query(self, cypher, graph):
            assert "name_form = 'full'" in cypher
            return Records()

    cypher = next(q["cypher"] for q in QUERIES if q["id"] == "AR23")
    assert "{AUTHOR}" in cypher
    assert "'Neel Nanda'" in resolve(Client(), "default", cypher)
