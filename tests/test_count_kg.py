from pathlib import Path

from etl.count_kg import (
    PaperIndex,
    build_counts,
    classify_role,
    frontmatter_value,
    matched_institutions,
    parse_reference,
    split_authors,
)

FIXTURE = Path(__file__).parent / "fixtures" / "count_kg"
FIXTURE_PAGE = FIXTURE / "topics" / "01-fixture" / "fixture-problem.md"


def test_split_authors_keeps_surname_initial_pairs_together():
    assert split_authors("Moerland, T., Alex Smith") == ["Moerland, T", "Alex Smith"]
    assert split_authors("Dao, T., Gu, A") == ["Dao, T", "Gu, A"]
    assert split_authors("Li, Z., Liu, H., Zhou, D., Ma, T") == ["Li, Z", "Liu, H", "Zhou, D", "Ma, T"]
    assert split_authors("Merrill, W. C., Sabharwal, A., et al.") == ["Merrill, W. C", "Sabharwal, A"]
    assert split_authors("Lee, J.-P. and Kim, S.; Park, H. & Cho, K.") == ["Lee, J.-P", "Kim, S", "Park, H", "Cho, K"]
    assert split_authors("N. Muennighoff, A. M. Rush, B. Barak, et al") == ["N. Muennighoff", "A. M. Rush", "B. Barak"]


def test_frontmatter_value_keeps_whole_line():
    metadata = 'title: "Parser fixture with spaces in the title"\nstatus: solved-but-impractical\n'
    assert frontmatter_value(metadata, "title") == "Parser fixture with spaces in the title"
    assert frontmatter_value(metadata, "status") == "solved-but-impractical"
    assert frontmatter_value(metadata, "provenance") == "MISSING"


def test_parse_reference_handles_untagged_and_unformatted_lines():
    tagged = parse_reference("- **[Foundational]** Moerland, T., Alex Smith. *A paper.* ICML, 2024. — arXiv:2401.12345")
    assert tagged == {"role": "Foundational", "authors": "Moerland, T., Alex Smith", "title": "A paper",
                      "venue": "ICML", "year": "2024", "arxiv_id": "2401.12345"}
    untagged = parse_reference("- Dao, T., Gu, A. *An untagged reference.* NeurIPS, 2023.")
    assert untagged["role"] == "" and untagged["title"] == "An untagged reference" and untagged["venue"] == "NeurIPS"
    assert classify_role(untagged["role"]) == "untagged"
    plain = parse_reference("- **[Survey]** Alex Smith. A title without italics. 2022.")
    assert plain["title"] == "Alex Smith. A title without italics. 2022" and plain["venue"] == ""
    assert parse_reference("Not a bullet") is None


def test_institution_matching_is_whole_word_and_case_sensitive():
    text = ("Google DeepMind and DeepMind. Together, Together AI did it. Meta-learning; Meta AI. "
            "A fair comparison with FAIR after one epoch. Nvidia and NVIDIA.")
    assert matched_institutions(text) == {"Google DeepMind", "Together AI", "Meta AI", "NVIDIA"}
    assert matched_institutions("fair epoch meta together deepmind") == set()


def test_paper_index_keeps_the_first_title_mapping():
    index = PaperIndex()
    first = index.add({"role": "", "authors": "A", "title": "Shared Title", "venue": "", "year": "", "arxiv_id": "2402.00001"})
    second = index.add({"role": "", "authors": "B", "title": "Shared Title", "venue": "", "year": "", "arxiv_id": "2403.00002"})
    title_only = index.add({"role": "", "authors": "C", "title": "Shared title.", "venue": "", "year": "", "arxiv_id": ""})
    assert first != second
    assert title_only == first
    assert len(index.papers) == 2
    # A title-only record later gains its arXiv ID and stays one paper.
    plain = index.add({"role": "", "authors": "D", "title": "Other", "venue": "", "year": "", "arxiv_id": ""})
    with_id = index.add({"role": "", "authors": "D", "title": "Other", "venue": "", "year": "", "arxiv_id": "2404.00003"})
    assert plain == with_id and len(index.papers) == 3


def test_counter_on_fixture_page():
    counts = build_counts(FIXTURE)

    assert counts["status"] == {"solved-but-impractical": 1}
    assert counts["references"] == 5          # the two "A shared title" arXiv papers stay separate
    assert counts["references_without_role_tag"] == 1
    assert counts["ref_roles"] == {"foundational": 1, "survey": 1, "untagged": 1, "sota": 2}
    assert counts["papers"] == 5
    assert counts["persons_listed"] == 6      # Moerland T, Alex Smith, Dao T, Gu A, Lee J-P, Kim S
    assert counts["edges_measured"]["AUTHORED_BY"] == 6
    assert counts["assumptions"] == 2
    assert counts["open_question_list_items"] == 2
    assert counts["edges_measured"]["HAS_GAP"] == 2
    assert counts["section_6_list_items"] == 1
    assert counts["lab_problem_links"] == 6   # Google DeepMind, Together AI, Meta AI, ETH Zurich, UW, NVIDIA
    assert counts["edges_measured"]["ACTIVE_ON"] == 6
    assert counts["problems_without_parsed_refs"] == []
    # The tag-only bullet is reported with its line number in the file, not in the section.
    assert counts["unparsed_reference_lines"] == [f"{FIXTURE_PAGE}:45"]
    assert counts["nodes_measured_total"] == sum(counts["nodes_measured"].values())
