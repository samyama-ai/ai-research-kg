from pathlib import Path

from etl.count_kg import build_counts, split_authors


FIXTURE = Path(__file__).parent / "fixtures" / "count_kg"


def test_counter_handles_authors_subsections_labs_and_unformatted_titles():
    counts = build_counts(FIXTURE)

    assert split_authors("Moerland, T., Alex Smith") == ["Moerland, T", "Alex Smith"]
    assert counts["references"] == 2
    assert counts["persons_listed"] == 2
    assert counts["assumptions"] == 2
    assert counts["open_question_list_items"] == 2
    assert counts["lab_problem_links"] == 5
    assert counts["problems_without_parsed_refs"] == []
    assert counts["edges_measured"]["HAS_GAP"] == 2
    assert counts["section_6_list_items"] == 1
