"""Estimate AI Research KG counts from an ai_research catalog checkout.

Usage: python etl/count_kg.py /path/to/ai_research
The estimate is deterministic and does not load data. Only counts supported by
this parser are reported as measured; unparsed schema entities remain estimates.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

COUNTER = collections.Counter
SECTION_RE = re.compile(r"^## (\d+)\.([^\n]*)\n(.*?)(?=^## |\Z)", re.M | re.S)
REF_RE = re.compile(r"^\s*-\s+\*\*\[([^]]+)\]\*\*\s*(.*?)\s*$")
ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)
LABS = [
    "Google DeepMind", "Allen Institute for AI", "Allen Institute", "Together AI",
    "University of Washington", "ETH Zurich", "UK AI Safety Institute",
    "US AI Safety Institute", "Character.AI", "Hugging Face", "Carnegie Mellon",
    "Apollo Research", "Anthropic", "OpenAI", "DeepMind", "Microsoft Research",
    "Meta AI", "FAIR", "NVIDIA", "Apple", "Mistral", "DeepSeek", "Alibaba",
    "Qwen", "Redwood Research", "METR", "MIRI", "Stanford", "Berkeley", "MIT",
    "CMU", "Princeton", "Oxford", "Cambridge", "Mila", "Toronto", "Tsinghua",
    "Peking", "NYU", "Harvard", "Cohere", "xAI", "Databricks", "MosaicML",
    "IBM", "Amazon", "Samsung", "Baidu", "ByteDance", "Tencent", "Salesforce",
    "Epoch",
]
ROLE_RULES = (
    ("caution", ("caution", "critique", "negative", "counter", "limitation", "critical")),
    ("survey", ("survey", "roadmap", "position")),
    ("sota", ("sota", "state of the art")),
    ("foundational", ("foundational", "background", "key", "established")),
    ("method", ("method", "mechanism", "mitigation", "defense", "tooling")),
    ("evidence", ("empirical", "theory", "evidence", "analysis", "measurement", "replication")),
)


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def split_authors(authors: str) -> list[str]:
    """Split separators without breaking catalog-style `Surname, Initial` names."""
    text = re.sub(r",?\s*et al\.?\s*$", "", authors, flags=re.I).strip(" .")
    text = re.sub(r"\s+(?:and|&)\s+", "\n", text, flags=re.I)
    # Commas separate authors except when the next token is an initial (e.g. Moerland, T.).
    text = re.sub(r",\s+(?![A-Z]\.\s*,|[A-Z]\.\s*$)", "\n", text)
    return [part.strip(" .,\n") for part in text.splitlines() if part.strip(" .,\n")]


def parse_reference(line: str) -> dict[str, str] | None:
    match = REF_RE.match(line)
    if not match:
        return None
    role, body = match.groups()
    italic = list(re.finditer(r"\*([^*]+)\*", body))
    if len(italic) >= 2:
        authors = body[: italic[0].start()].strip(" .")
        title = italic[0].group(1).strip(" .")
    elif italic:
        authors = body[: italic[0].start()].strip(" .")
        title = italic[0].group(1).strip(" .")
    else:
        # Keep an unformatted reference visible in the estimate rather than silently dropping it.
        authors = ""
        title = body.strip(" .")
    rest_start = italic[0].end() if italic else 0
    rest = body[rest_start:]
    year = re.search(r"\b(?:19|20)\d{2}\b", rest)
    venue = ""
    if year and italic:
        venue = rest[:year.start()].strip(" .,;—–-")
    arxiv = ARXIV_RE.search(body)
    return {"role": role, "authors": authors, "title": title,
            "venue": venue, "arxiv_id": arxiv.group(1) if arxiv else ""}


def count_list_items(section: str) -> int:
    return len(re.findall(r"^\s*(?:\d+[.)]|[-*])\s+\S", section, re.M))


def assumption_items(section: str) -> int:
    # Limit the count to the subsection whose heading starts with “Assumptions”.
    heading = re.search(r"^\s*\*\*Assumptions\b[^\n]*\*\*\s*$", section, re.I | re.M)
    if not heading:
        return 0
    tail = section[heading.end():]
    next_subsection = re.search(r"^\s*\*\*[^\n]+\*\*\s*$", tail, re.M)
    if next_subsection:
        tail = tail[:next_subsection.start()]
    return count_list_items(tail)


def classify_role(raw: str) -> str:
    value = raw.lower()
    for bucket, keywords in ROLE_RULES:
        if any(re.search(r"\b" + re.escape(keyword) + r"\b", value) for keyword in keywords):
            return bucket
    return "context"


def matched_labs(text: str) -> set[str]:
    remaining = text
    found = set()
    for name in sorted(LABS, key=len, reverse=True):
        pattern = re.compile(r"(?<![\w])" + re.escape(name) + r"(?![\w])", re.I)
        if pattern.search(remaining):
            found.add(name)
            remaining = pattern.sub(" ", remaining)
    return found


def build_counts(root: Path) -> dict:
    files = sorted(path for path in root.glob("topics/*/*.md") if path.name != "README.md")
    if not files:
        raise ValueError(f"no topic Markdown files found under {root / 'topics'}")
    status, provenance, roles, gaps, labs = COUNTER(), COUNTER(), COUNTER(), COUNTER(), COUNTER()
    topics, papers, people, venues = set(), {}, set(), set()
    paper_by_title, paper_by_arxiv = {}, {}
    assumptions = future_experiments = arxiv_references = reference_count = 0
    section_6_items = 0
    edges = COUNTER()
    per_problem_refs = []
    no_reference_paths = []
    unparsed_reference_lines = []

    for path in files:
        with path.open(encoding="utf-8") as handle:
            source = handle.read()
        frontmatter = re.match(r"^---\s*\n(.*?)\n---", source, re.S)
        metadata = frontmatter.group(1) if frontmatter else ""
        for field, counter in (("status", status), ("provenance", provenance)):
            match = re.search(rf"^{field}:\s*['\"]?([^\s'\"]+)", metadata, re.M)
            counter[match.group(1) if match else "MISSING"] += 1
        topic = path.parent.name
        topics.add(topic)
        edges["IN_TOPIC"] += 1
        section_matches = list(SECTION_RE.finditer(source))
        sections = {match.group(1): match.group(3) for match in section_matches}
        references_section = next(
            (match.group(3) for match in section_matches if "key references" in match.group(2).lower()),
            "",
        )

        page_papers = set()
        for line_number, line in enumerate(references_section.splitlines(), 1):
            if not re.match(r"^\s*-\s+\*\*\[", line):
                continue
            reference = parse_reference(line)
            if not reference or not reference["title"]:
                unparsed_reference_lines.append(f"{path}:{line_number}")
                continue
            title_key = normalise(reference["title"])
            arxiv_key = reference["arxiv_id"]
            key = paper_by_arxiv.get(arxiv_key) if arxiv_key else None
            title_match = paper_by_title.get(title_key)
            if key is None and title_match is not None:
                prior_arxiv = papers[title_match]["arxiv_id"]
                key = arxiv_key if arxiv_key and prior_arxiv and arxiv_key != prior_arxiv else title_match
            key = key or arxiv_key or title_key
            paper_by_title[title_key] = key
            if arxiv_key:
                paper_by_arxiv[arxiv_key] = key
            if key in page_papers:
                continue
            page_papers.add(key)
            reference_count += 1
            roles[classify_role(reference["role"])] += 1
            arxiv_references += bool(reference["arxiv_id"])
            if key not in papers or (arxiv_key and not papers[key]["arxiv_id"]):
                papers[key] = reference
        per_problem_refs.append(len(page_papers))
        edges["CITES"] += len(page_papers)
        if not page_papers:
            no_reference_paths.append(str(path))

        a_count = assumption_items(sections.get("2", ""))
        assumptions += a_count
        edges["RESTS_ON"] += a_count
        gap_count = count_list_items(sections.get("5", ""))
        gaps["items"] += gap_count
        if sections.get("8", "").strip():
            future_experiments += 1
            edges["HAS_NEXT_EXPERIMENT"] += 1
        edges["HAS_GAP"] += gap_count
        section_6_items += count_list_items(sections.get("6", ""))
        for lab in matched_labs(sections.get("7", "")):
            labs[lab] += 1

    for paper in papers.values():
        names = split_authors(paper["authors"])
        people.update(normalise(name) for name in names)
        edges["AUTHORED_BY"] += len(names)
        if paper["venue"]:
            venues.add(normalise(paper["venue"]))
            edges["APPEARED_AT"] += 1

    return {
        "problems": len(files), "topics": len(topics), "status": status,
        "provenance": provenance, "papers": len(papers), "persons_listed": len(people),
        "venues_raw_normalised": len(venues), "assumptions": assumptions,
        "open_question_list_items": gaps["items"], "future_experiments": future_experiments,
        "section_6_list_items": section_6_items,
        "references": reference_count, "references_with_arxiv_id": arxiv_references,
        "reference_arxiv_share_percent": round(100 * arxiv_references / reference_count, 1) if reference_count else None,
        "ref_roles": roles, "refs_per_problem": {
            "min": min(per_problem_refs), "max": max(per_problem_refs),
            "avg": round(sum(per_problem_refs) / len(per_problem_refs), 1)},
        "problems_without_parsed_refs": no_reference_paths,
        "unparsed_reference_lines": unparsed_reference_lines,
        "lab_names_matched": len(labs), "lab_problem_links": sum(labs.values()),
        "top_labs": labs.most_common(8), "edges_measured": edges,
        "estimates_only": ["Method nodes and links", "canonical Obstruction nodes and BLOCKED_BY links",
                            "venue entity resolution", "normalised person entity resolution",
                            "full schema node and edge totals"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path, help="path to ai_research checkout")
    args = parser.parse_args(argv)
    if not args.catalog.is_dir():
        parser.error(f"catalog directory does not exist: {args.catalog}")
    try:
        print(json.dumps(build_counts(args.catalog), indent=2, default=dict))
    except ValueError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    sys.exit(main())
