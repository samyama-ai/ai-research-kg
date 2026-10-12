"""Parse the ai_research catalog pages: references, assumptions, gaps, experiments, labs.

Everything comes from the catalog itself (data/ai_research at a pinned commit):
no external lookups, no LLM extraction. What each label is built from:

    Topic           TAXONOMY.md table
    Problem         one topics/NN-*/<slug>.md file: frontmatter + "Problem Statement"
    Paper           "Key References" lines, deduplicated by arXiv id, then by title
    Person          author lists in "Key References" (no merging of name forms)
    Venue           the venue text of each reference, normalised
    Assumption      the "Assumptions" list in "Formal Setting"
    OpenQuestion    classified items in "What Is Not Known"
    Obstruction     "Why It Is Hard", mapped to the catalog's own 5 obstruction types
    FutureDirection "Concrete Next Experiment"
    Institution     labs named in "Current Research", matched against a fixed alias list
    DataSource      the catalog itself

The module is split in four: etl/rules.py holds the fixed lists and patterns,
etl/text.py the Markdown helpers, this file the parsing of one page, and
etl/build.py the Graph container, the catalog walk and the computed RELATED_TO
edges. `from etl.parse import build_graph` still works (lazy re-export below).

Sections are found by their heading text, not their number: one file has
sections 9 and 10 swapped.
"""
from __future__ import annotations

import re
from pathlib import Path

from etl.rules import (  # noqa: F401  (re-exported: tests and vocab checks read them from here)
    BUDGET_RE,
    COLLECTIVE_RE,
    EXP_FIELDS,
    INSTITUTIONS,
    OBSTRUCTIONS,
    ROLE_RULES,
    SECTION_KEYS,
    SINGLE_MACHINE_GPU_HOURS,
    SINGLE_MACHINE_RE,
    VENUE_ALIASES,
)
from etl.text import (  # noqa: F401  (re-exported)
    first_paragraphs,
    list_items,
    norm_title,
    parse_frontmatter,
    split_sections,
    strip_md,
)

# Older names, kept so existing callers and the sibling branches keep working.
_strip_md, _first_paragraphs, _norm_title = strip_md, first_paragraphs, norm_title


# --------------------------------------------------------------------------- #
# References
# --------------------------------------------------------------------------- #
REF_RE = re.compile(r"^\s*[-*]\s+\*\*\[([^\]]+)\]\*\*\s*(.*?)\s*\*([^*]+)\*\s*(.*)$")
ARXIV_RE = re.compile(r"arXiv[:\s]*(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s,;)]+)")
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-3]\d)\b")
INITIALS_RE = re.compile(r"^(?:[A-Z][a-z]?\.\s?-?)+$")


def role_bucket(tag: str) -> str:
    t = tag.lower().strip()
    for name, pat in ROLE_RULES:
        if re.search(pat, t):
            return name
    return "context"


def normalise_venue(raw: str) -> str | None:
    raw = raw.strip(" .,;—-")
    if not raw:
        return None
    low = raw.lower()
    for canonical, pat in VENUE_ALIASES:
        if re.search(pat, low):
            return canonical
    raw = re.sub(r"\s*\((?:[^)]*)\)\s*$", "", raw).strip(" .,")
    raw = re.sub(r"\s+\d+(?:\s*\(\d+\))?$", "", raw).strip(" .,")  # "CACM 52" -> "CACM"
    return raw or None


def split_authors(text: str) -> list[str]:
    text = re.sub(r"\([^)]*\)", "", text)            # "(Llama Team)", "(METR)" affiliations
    text = re.sub(r"\([^,]*|[^,(]*\)", lambda m: m.group(0).split("(")[0].replace(")", ""), text)
    text = re.sub(r",?\s*\bet al\.?", "", text).strip()
    text = text.replace(" and ", ", ").replace(" & ", ", ")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    parts = [p if INITIALS_RE.match(p) else p.rstrip(".") for p in parts]
    names: list[str] = []
    for p in parts:
        if INITIALS_RE.match(p) and names:  # "Moerland, T." -> "T. Moerland"
            names[-1] = f"{p} {names[-1]}"
        else:
            names.append(p)
    return [n for n in names if 1 < len(n) <= 60 and not n.lower().startswith(("the ", "team"))]


def name_form(name: str) -> str:
    if COLLECTIVE_RE.search(name):
        return "collective"
    tokens = name.split()
    if len(tokens) == 1:
        return "surname"
    if all(INITIALS_RE.match(t) for t in tokens[:-1]):
        return "initials"
    return "full"


def parse_reference(line: str) -> dict | None:
    m = REF_RE.match(line)
    if not m:
        return None
    tag, authors, title, rest = m.groups()
    title = title.strip().rstrip(".")
    arxiv = ARXIV_RE.search(rest)
    doi = DOI_RE.search(rest)
    years = YEAR_RE.findall(rest)
    venue_part = re.split(r"—|\s-\s|arXiv[:\s]", rest)[0]
    venue_part = YEAR_RE.sub("", venue_part)
    return {
        "role_raw": tag.strip(),
        "role": role_bucket(tag),
        "authors_raw": authors.strip().rstrip("."),
        "authors": split_authors(authors),
        "title": title,
        "arxiv_id": arxiv.group(1) if arxiv else None,
        "doi": doi.group(1).rstrip(".") if doi else None,
        "year": int(years[0]) if years else None,
        "venue": normalise_venue(venue_part),
        "venue_raw": venue_part.strip(" .,;") or None,
    }


# --------------------------------------------------------------------------- #
# Section classifiers
# --------------------------------------------------------------------------- #
def classify_obstructions(section: str) -> tuple[list[str], str]:
    bold = re.findall(r"\*\*([^*\n]{3,200})\*\*", section)
    head = bold[0] if bold else ""
    for text in (head, first_paragraphs(section, 600)):
        found = [k for k, (_, pat) in OBSTRUCTIONS.items() if re.search(pat, text, re.I)]
        if found:
            return found, strip_md(head)[:200]
    return ["other"], strip_md(head)[:200]


def classify_gap(head: str) -> str:
    h = head.lower()
    if "theoretic" in h:
        return "theoretically_open"
    if "empiric" in h:
        return "empirically_open"
    if "method" in h:
        return "methodologically_blocked"
    return "unclassified"


VIOLATED_RE = re.compile(r"\bviolated\b|\bfails?\b|does not hold|broken", re.I)
PARTLY_RE = re.compile(r"\bpartly\b|\bpartially\b|approximately|weakly|sometimes|mostly", re.I)
HOLDS_RE = re.compile(r"\bholds\b|\breasonable\b|\bsafe\b", re.I)


def assumption_status(text: str) -> str:
    if PARTLY_RE.search(text) and VIOLATED_RE.search(text):
        return "partly"
    if VIOLATED_RE.search(text):
        return "violated"
    if HOLDS_RE.search(text):
        return "holds"
    return "unstated"


def parse_assumptions(formal: str) -> list[dict]:
    m = re.search(r"^.*\*\*Assumptions?[^\n]*\n", formal, re.M | re.I)
    if not m:
        return []
    out = []
    for item in list_items(formal[m.end():]):
        nm = re.match(r"\*([^*]{2,120}?)[:.]\*\s*[:.]?\s*(.*)", item) or \
            re.match(r"\*\*([^*]{2,120}?)[:.]?\*\*\s*[:.]?\s*(.*)", item)
        name = strip_md(nm.group(1)) if nm else " ".join(strip_md(item).split()[:8])
        text = strip_md(item)
        out.append({"name": name[:160], "text": text[:1200], "violated": assumption_status(text)})
    return out


def parse_gaps(not_known: str) -> list[dict]:
    out = []
    for item in list_items(not_known):
        m = re.match(r"\*\*([^*]{3,120})\*\*\s*[:.]?\s*(.*)", item)
        if not m:
            continue
        head = m.group(1).strip().rstrip(".:")
        out.append({"kind": classify_gap(head), "kind_raw": head[:120],
                    "is_primary": bool(re.search(r"primary|core", head, re.I)),
                    "text": strip_md(m.group(2))[:1200]})
    return out


def parse_experiment(section: str) -> dict:
    out: dict = {"text": first_paragraphs(section, 1500)}
    blocks = re.split(r"(?m)^(?=(?:[-*]\s+)?\*\*[^*\n]{2,60}\*\*)", section)
    for block in blocks:
        m = re.match(r"(?:[-*]\s+)?\*\*([^*\n]{2,60}?)[:.]?\*\*[:.]?\s*(.*)", block, re.S)
        if not m:
            continue
        label = re.sub(r"^the\s+", "", m.group(1).strip().lower())
        for key, pat in EXP_FIELDS.items():
            if key not in out and re.match(pat, label):
                out[key] = strip_md(m.group(2))[:1200]
                break
    hours = []
    for bm in BUDGET_RE.finditer(section):
        try:
            value = float(bm.group(2).replace(",", ""))
        except ValueError:
            continue
        if bm.group(3):
            value *= 1000
        if "hour" in bm.group(0).lower() and re.search(r"GPU|[AH]\d{2,3}|TPU|accelerator", bm.group(0), re.I):
            hours.append(value)
    out["compute_budget_gpu_hours"] = max(hours) if hours else None
    single = bool(SINGLE_MACHINE_RE.search(section))
    if out["compute_budget_gpu_hours"] is not None and out["compute_budget_gpu_hours"] <= SINGLE_MACHINE_GPU_HOURS:
        single = True
    out["single_machine"] = single if (single or out["compute_budget_gpu_hours"] is not None) else None
    return out


def parse_current_research(section: str) -> list[dict]:
    out = []
    for item in list_items(section):
        m = re.match(r"\*\*([^*]{2,150})\*\*", item)
        direction = strip_md(m.group(1)).rstrip(".:") if m else " ".join(strip_md(item).split()[:10])
        labs = [iid for iid, _, _, pat in INSTITUTIONS if re.search(pat, item)]
        out.append({"direction": direction[:200], "labs": labs})
    return out


# --------------------------------------------------------------------------- #
# Catalog files
# --------------------------------------------------------------------------- #
def parse_taxonomy(root: Path) -> list[dict]:
    topics = []
    for line in (root / "TAXONOMY.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(\d{2})\s*\|\s*([^|]+?)\s*\|\s*\[`([^`]+)`\][^|]*\|\s*([^|]*?)\s*\|\s*$", line)
        if m:
            topics.append({"number": int(m.group(1)), "name": m.group(2).strip(),
                           "slug": m.group(3).strip(), "scope": m.group(4).strip()})
    return topics


def problem_files(root: Path) -> list[Path]:
    return sorted(p for p in (root / "topics").glob("*/*.md") if p.name != "README.md")


# --------------------------------------------------------------------------- #
# Lazy re-exports of the graph builder (etl/build.py imports this module, so a
# plain import here would be circular).
# --------------------------------------------------------------------------- #
_BUILD_NAMES = ("Graph", "build_graph", "main")


def __getattr__(name: str):
    if name in _BUILD_NAMES:
        from etl import build
        return getattr(build, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    from etl.build import main
    main()
