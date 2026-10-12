"""Estimate AI Research KG counts from an ai_research catalog checkout.

Usage: python etl/count_kg.py /path/to/ai_research

The estimate is deterministic and does not load data. Only the fields this
parser reads are reported as measured (see ``nodes_measured`` and
``edges_measured`` in the output); every other node and edge type of
docs/schema.md stays an estimate and is listed under ``estimates_only``.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

SECTION_RE = re.compile(r"^## (\d+)\.([^\n]*)\n(.*?)(?=^## |\Z)", re.M | re.S)
BULLET_RE = re.compile(r"^[-*]\s+\S")                 # top level only: an indented sub-bullet is not a reference
# A reference bullet: "- **[Role]** Authors. *Title.* Venue, year. — arXiv:..."; the role tag is optional.
REFERENCE_RE = re.compile(r"^[-*]\s+(?:\*\*\[([^]]+)\]\*\*)?\s*(.*?)\s*$")
ITALIC_RE = re.compile(r"\*([^*]+)\*")
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)
LIST_ITEM_RE = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+\S", re.M)
# "T", "T.", "T. M.", "J.-P.": a token made only of initials belongs to the surname before it.
INITIALS_RE = re.compile(r"^(?:[A-Z]\.?(?:\s*-\s*[A-Z]\.?)*\s*)+$")
ET_AL_RE = re.compile(r",?\s*\bet al\.?\s*$", re.I)
AND_RE = re.compile(r"\s+(?:and|&)\s+", re.I)

# Canonical institution name -> the spellings that count as a mention of it.
# Matching is case-sensitive and whole-word, so "fair comparison", "Meta-learning"
# and "training epoch" don't count. Ambiguous short names ("Meta", "Epoch", "UW",
# "Google" on its own) are left out on purpose.
INSTITUTIONS: dict[str, tuple[str, ...]] = {
    "Google DeepMind": ("Google DeepMind", "DeepMind"),
    "Meta AI": ("Meta AI", "Meta FAIR", "FAIR"),
    "Allen Institute for AI": ("Allen Institute for AI", "Allen Institute", "AI2"),
    "Together AI": ("Together AI",),
    "University of Washington": ("University of Washington",),
    "ETH Zurich": ("ETH Zurich", "ETH Zürich"),
    "UK AI Safety Institute": ("UK AI Safety Institute", "UK AISI"),
    "US AI Safety Institute": ("US AI Safety Institute", "US AISI"),
    "Character.AI": ("Character.AI",),
    "Hugging Face": ("Hugging Face", "HuggingFace"),
    "Carnegie Mellon": ("Carnegie Mellon", "CMU"),
    "Apollo Research": ("Apollo Research",),
    "Anthropic": ("Anthropic",),
    "OpenAI": ("OpenAI",),
    "Microsoft Research": ("Microsoft Research", "Microsoft"),
    "NVIDIA": ("NVIDIA", "Nvidia"),
    "Apple": ("Apple",),
    "Mistral AI": ("Mistral AI", "Mistral"),
    "DeepSeek": ("DeepSeek",),
    "Alibaba": ("Alibaba",),
    "Redwood Research": ("Redwood Research",),
    "METR": ("METR",),
    "MIRI": ("MIRI",),
    "Stanford": ("Stanford",),
    "UC Berkeley": ("UC Berkeley", "Berkeley"),
    "MIT": ("MIT",),
    "Princeton": ("Princeton",),
    "University of Oxford": ("University of Oxford", "Oxford University"),
    "University of Cambridge": ("University of Cambridge", "Cambridge University"),
    "Mila": ("Mila",),
    "University of Toronto": ("University of Toronto", "Vector Institute"),
    "Tsinghua": ("Tsinghua",),
    "Peking University": ("Peking University",),
    "NYU": ("NYU",),
    "Harvard": ("Harvard",),
    "Cohere": ("Cohere",),
    "xAI": ("xAI",),
    "Databricks": ("Databricks",),
    "MosaicML": ("MosaicML",),
    "IBM": ("IBM",),
    "Amazon": ("Amazon",),
    "Samsung": ("Samsung",),
    "Baidu": ("Baidu",),
    "ByteDance": ("ByteDance",),
    "Tencent": ("Tencent",),
    "Salesforce": ("Salesforce",),
    "Epoch AI": ("Epoch AI",),
}
# Longest spelling first (by the alias itself, not its escaped pattern), so "Google DeepMind"
# is consumed before "DeepMind". Ambiguous bare words ("Oxford", "Cambridge", "Toronto",
# "Peking", "Qwen") are not aliases: they also name places and models.
INSTITUTION_PATTERNS = [
    (re.compile(r"(?<!\w)" + re.escape(alias) + r"(?!\w)"), canonical)
    for alias, canonical in sorted(
        ((alias, canonical) for canonical, aliases in INSTITUTIONS.items() for alias in aliases),
        key=lambda item: len(item[0]), reverse=True)
]

# Citation role buckets (docs/schema.md §5.2). Checked in this order; first hit wins.
ROLE_RULES = (
    ("caution", ("caution", "critique", "negative", "counter", "limitation", "critical")),
    ("survey", ("survey", "roadmap", "position")),
    ("sota", ("sota", "state of the art")),
    ("foundational", ("foundational", "background", "key", "established")),
    ("method", ("method", "mechanism", "mitigation", "defense", "tooling")),
    ("evidence", ("empirical", "theory", "evidence", "analysis", "measurement", "replication")),
)
UNTAGGED_ROLE = "untagged"


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def frontmatter_value(metadata: str, field: str) -> str:
    """Return the whole value of a frontmatter line, without surrounding quotes."""
    match = re.search(rf"^{re.escape(field)}:[ \t]*(.*?)[ \t]*$", metadata, re.M)
    if not match:
        return "MISSING"
    return match.group(1).strip().strip("'\"") or "MISSING"


def split_authors(authors: str) -> list[str]:
    """Split an author string into names without breaking `Surname, T.` pairs.

    Separators are `,`, `;`, `and` and `&`. A comma-separated token made only of
    initials (`T.`, `T. M.`, `J.-P.`) is glued back onto the surname before it.
    """
    text = ET_AL_RE.sub("", authors)
    text = AND_RE.sub(", ", text).replace(";", ",")
    names: list[str] = []
    for token in (part.strip() for part in text.split(",")):
        if not token:
            continue
        if names and INITIALS_RE.match(token):
            names[-1] = f"{names[-1]}, {token}"
        else:
            names.append(token)
    return [name.strip(" .") for name in names if name.strip(" .")]


def parse_reference(line: str) -> dict[str, str] | None:
    """Parse one Key References bullet. Returns None for a non-bullet line."""
    match = REFERENCE_RE.match(line)
    if not match or not BULLET_RE.match(line):
        return None
    role = (match.group(1) or "").strip()
    body = match.group(2)
    italic = ITALIC_RE.search(body)
    if italic:
        authors = body[: italic.start()].strip(" .")
        title = italic.group(1).strip(" .")
        rest = body[italic.end():]
    else:
        # No italic title: keep the line visible in the estimate instead of dropping it.
        authors = ""
        title = body.strip(" .")
        rest = ""
    arxiv = ARXIV_RE.search(body)
    year = YEAR_RE.search(ARXIV_RE.sub("", rest))    # never read "2010" out of "arXiv:2010.11929"
    venue = rest[: year.start()].strip(" .,;—–-") if year else ""
    return {
        "role": role,
        "authors": authors,
        "title": title,
        "venue": venue,
        "year": year.group(0) if year else "",
        "arxiv_id": arxiv.group(1) if arxiv else "",
    }


def count_list_items(section: str) -> int:
    return len(LIST_ITEM_RE.findall(section))


def assumption_items(section: str) -> int:
    """Count the list items of the §2 subsection whose bold heading starts with "Assumptions"."""
    heading = re.search(r"^\s*\*\*Assumptions\b[^\n]*\*\*\s*$", section, re.I | re.M)
    if not heading:
        return 0
    tail = section[heading.end():]
    next_subsection = re.search(r"^\s*\*\*[^\n]+\*\*\s*$", tail, re.M)
    if next_subsection:
        tail = tail[: next_subsection.start()]
    return count_list_items(tail)


def classify_role(raw: str) -> str:
    if not raw:
        return UNTAGGED_ROLE
    value = raw.lower()
    for bucket, keywords in ROLE_RULES:
        if any(re.search(r"\b" + re.escape(keyword) + r"\b", value) for keyword in keywords):
            return bucket
    return "context"


def matched_institutions(text: str) -> set[str]:
    """Canonical institutions named in the text, each counted once; longest spelling wins."""
    remaining = text
    found: set[str] = set()
    for pattern, canonical in INSTITUTION_PATTERNS:
        if pattern.search(remaining):
            found.add(canonical)
            remaining = pattern.sub(" ", remaining)
    return found


class PaperIndex:
    """Group references into papers: arXiv ID first, then normalised title (schema.md §8).

    A title that appears with two different arXiv IDs stays two papers, and the
    title keeps pointing at the first one, so later title-only citations are
    never silently re-pointed.
    """

    def __init__(self) -> None:
        self.papers: dict[str, dict[str, str]] = {}
        self.key_by_arxiv: dict[str, str] = {}
        self.key_by_title: dict[str, str] = {}

    def add(self, reference: dict[str, str]) -> str:
        arxiv_id = reference["arxiv_id"]
        title = normalise(reference["title"])
        if len(title) < 3:   # a blank title must not merge every untitled reference into one paper
            title = normalise(f"{reference['authors']} {reference.get('year', '')} {reference['venue']}") or "untitled"
        key = self.key_by_arxiv.get(arxiv_id) if arxiv_id else None
        if key is None and title in self.key_by_title:
            candidate = self.key_by_title[title]
            prior_arxiv = self.papers[candidate]["arxiv_id"]
            if not arxiv_id or not prior_arxiv or prior_arxiv == arxiv_id:
                key = candidate
                if arxiv_id and not prior_arxiv:
                    # A title-only record gains its arXiv ID; keep the richer reference.
                    self.key_by_arxiv[arxiv_id] = key
                    self.papers[key] = reference
        if key is None:
            key = f"arxiv:{arxiv_id}" if arxiv_id else f"title:{title}"
            self.papers[key] = reference
            if arxiv_id:
                self.key_by_arxiv[arxiv_id] = key
        self.key_by_title.setdefault(title, key)
        kept = self.papers[key]
        for field in ("authors", "venue", "year", "arxiv_id"):   # fill gaps, never overwrite
            if not kept.get(field) and reference.get(field):
                kept[field] = reference[field]
        return key


def problem_files(root: Path) -> list[Path]:
    files = sorted(path for path in root.glob("topics/*/*.md") if path.name != "README.md")
    if not files:
        raise ValueError(f"no topic Markdown files found under {root / 'topics'}")
    return files


def build_counts(root: Path) -> dict:
    files = problem_files(root)
    status_counts: collections.Counter[str] = collections.Counter()
    provenance_counts: collections.Counter[str] = collections.Counter()
    role_counts: collections.Counter[str] = collections.Counter()
    institution_links: collections.Counter[str] = collections.Counter()
    edges: collections.Counter[str] = collections.Counter()
    topics: set[str] = set()
    index = PaperIndex()
    assumption_total = gap_total = section_6_total = future_experiments = 0
    reference_total = arxiv_reference_total = untagged_reference_total = 0
    references_per_problem: list[int] = []
    problems_without_references: list[str] = []
    unparsed_reference_lines: list[str] = []

    for path in files:
        source = path.read_text(encoding="utf-8")
        frontmatter = re.match(r"^---\s*\n(.*?)\n---", source, re.S)
        metadata = frontmatter.group(1) if frontmatter else ""
        status_counts[frontmatter_value(metadata, "status")] += 1
        provenance_counts[frontmatter_value(metadata, "provenance")] += 1
        topics.add(path.parent.name)
        edges["IN_TOPIC"] += 1

        section_matches = list(SECTION_RE.finditer(source))
        sections = {match.group(1): match.group(3) for match in section_matches}
        references_match = next(
            (match for match in section_matches if "key references" in match.group(2).lower()), None,
        )

        page_papers: set[str] = set()
        if references_match is not None:
            # Line numbers are reported relative to the file, not to the section.
            first_line = source.count("\n", 0, references_match.start(3)) + 1
            for offset, line in enumerate(references_match.group(3).splitlines()):
                if not BULLET_RE.match(line):
                    continue
                reference = parse_reference(line)
                if not reference or not reference["title"]:
                    unparsed_reference_lines.append(f"{path}:{first_line + offset}")
                    continue
                key = index.add(reference)
                if key in page_papers:
                    continue
                page_papers.add(key)
                reference_total += 1
                role_counts[classify_role(reference["role"])] += 1
                arxiv_reference_total += bool(reference["arxiv_id"])
                untagged_reference_total += not reference["role"]
        references_per_problem.append(len(page_papers))
        edges["CITES"] += len(page_papers)
        if not page_papers:
            problems_without_references.append(str(path))

        assumptions = assumption_items(sections.get("2", ""))
        assumption_total += assumptions
        edges["RESTS_ON"] += assumptions
        gaps = count_list_items(sections.get("5", ""))
        gap_total += gaps
        edges["HAS_GAP"] += gaps
        section_6_total += count_list_items(sections.get("6", ""))
        if sections.get("8", "").strip():
            future_experiments += 1
            edges["HAS_NEXT_EXPERIMENT"] += 1
        for institution in matched_institutions(sections.get("7", "")):
            institution_links[institution] += 1
            edges["ACTIVE_ON"] += 1

    people: set[str] = set()
    venues: set[str] = set()
    for paper in index.papers.values():
        names = split_authors(paper["authors"])
        people.update(normalise(name) for name in names)
        edges["AUTHORED_BY"] += len(names)
        if paper["venue"]:
            venues.add(normalise(paper["venue"]))
            edges["APPEARED_AT"] += 1

    nodes = {
        "Problem": len(files),
        "Topic": len(topics),
        "Paper (arXiv-ID / title grouped)": len(index.papers),
        "Person (distinct raw author strings)": len(people),
        "Venue (distinct normalised raw strings)": len(venues),
        "Institution (names matched)": len(institution_links),
        "Assumption": assumption_total,
        "OpenQuestion (§5 list items)": gap_total,
        "FutureDirection": future_experiments,
    }
    return {
        "problems": len(files),
        "topics": len(topics),
        "status": status_counts,
        "provenance": provenance_counts,
        "papers": len(index.papers),
        "persons_listed": len(people),
        "venues_raw_normalised": len(venues),
        "assumptions": assumption_total,
        "open_question_list_items": gap_total,
        "future_experiments": future_experiments,
        "section_6_list_items": section_6_total,
        "references": reference_total,
        "references_with_arxiv_id": arxiv_reference_total,
        "reference_arxiv_share_percent": (
            round(100 * arxiv_reference_total / reference_total, 1) if reference_total else None
        ),
        "references_without_role_tag": untagged_reference_total,
        "ref_roles": role_counts,
        "refs_per_problem": {
            "min": min(references_per_problem),
            "max": max(references_per_problem),
            "avg": round(sum(references_per_problem) / len(references_per_problem), 1),
        },
        "problems_without_parsed_refs": problems_without_references,
        "unparsed_reference_lines": unparsed_reference_lines,
        "lab_names_matched": len(institution_links),
        "lab_problem_links": sum(institution_links.values()),
        "top_labs": institution_links.most_common(8),
        "nodes_measured": nodes,
        "nodes_measured_total": sum(nodes.values()),
        "edges_measured": edges,
        "edges_measured_total": sum(edges.values()),
        "estimates_only": [
            "Method nodes, STATE_OF_ART, MENTIONS and INTRODUCED_IN",
            "canonical Obstruction nodes and BLOCKED_BY links",
            "AssumptionClass nodes and INSTANCE_OF links",
            "RELATED_TO (computed)",
            "AFFILIATED_WITH (needs an external lookup)",
            "venue entity resolution",
            "person entity resolution",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("catalog", type=Path, help="path to an ai_research checkout")
    args = parser.parse_args(argv)
    if not args.catalog.is_dir():
        parser.error(f"catalog directory does not exist: {args.catalog}")
    try:
        counts = build_counts(args.catalog)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(counts, indent=2, default=dict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
