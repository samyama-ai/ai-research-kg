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
    INSTITUTION_BY_ID,
    INSTITUTIONS,
    OBSTRUCTIONS,
    PREPRINT_VENUES,
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
    raw = raw.strip(" .,;:—–-/(")
    low = raw.lower()
    for canonical, pat in VENUE_ALIASES:      # aliases first, so "S&P" is a venue although it has no two letters in a row
        if re.search(pat, low):
            return canonical
    if not re.search(r"[A-Za-z]{2}", raw) or re.match(r"identifier omitted", raw, re.I):
        return None  # parser residue such as "(" is not a venue
    raw = re.sub(r"\s*\((?:[^)]*)\)\s*$", "", raw).strip(" .,")
    raw = re.sub(r"\s+\d+(?:\s*\(\d+\))?$", "", raw).strip(" .,")  # "CACM 52" -> "CACM"
    return raw or None


def split_authors(text: str) -> list[str]:
    text = re.sub(r"\([^)]*\)", "", text)            # "(Llama Team)", "(METR)" affiliations
    text = text.replace("(", "").replace(")", "")   # a stray, unbalanced parenthesis
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
    # drop fragments: one character, over-long, "the …" lead-ins and a bare "team" (a collective
    # such as "Llama Team" is kept and classified by name_form)
    return [n for n in names if 1 < len(n) <= 60 and not n.lower().startswith("the ") and n.lower() != "team"]


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
    # the year is read with the identifiers removed, so "arXiv:2010.11929" never yields 2010
    years = YEAR_RE.findall(DOI_RE.sub("", ARXIV_RE.sub("", rest)))
    venue_part = re.split(r"—|\s-\s|arxiv[:\s]", rest, flags=re.I)[0]
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


# Verdict words. Negation is respected ("not violated" is not a violation, "no longer holds" and
# "rarely holds" are not confirmations), and "false" is a verdict but "false positives",
# "false-positive rate", "false alarms" and "false discovery" are not.
_NEG = r"(?<!\bnot )(?<!\bnever )(?<!\brarely )(?<!\bseldom )(?<!longer )"
_NOT_A_VERDICT = r"(?![\s-]+(?:positives?|alarms?|discover\w*|negatives?)\b)"
VIOLATED_RE = re.compile(
    _NEG + r"\bviolated\b|" + _NEG + r"\bfails?\b|\bdoes not hold\b|\bno longer holds\b|\brarely holds\b|\bnever holds\b|"
    + _NEG + r"\bbroken\b"
    + r"|(?:—|–|:)\s*false\b" + _NOT_A_VERDICT
    + r"|(?:^|[.;]\s+)false\b" + _NOT_A_VERDICT
    + r"|\bfalse in practice", re.I)
PARTLY_RE = re.compile(r"\bpartly\b|\bpartially\b|\bapproximately\b|\bweakly\b|\bsometimes\b|\bmostly\b", re.I)
HOLDS_RE = re.compile(_NEG + r"\bholds\b|\bnot violated\b|\bnever violated\b|\breasonable\b|\bsafe\b", re.I)
MIXED_RE = re.compile(r"\btrue (?:for|when|in|under)\b", re.I)   # "true for X ...; false for Y"


def assumption_status(text: str) -> str:
    if (PARTLY_RE.search(text) or MIXED_RE.search(text)) and VIOLATED_RE.search(text):
        return "partly"
    if VIOLATED_RE.search(text):
        return "violated"
    if HOLDS_RE.search(text):
        return "holds"
    return "unstated"


# Two shapes count as a heading: bold starting with "Assumption(s)" that ends in ":" or "."
# (inside or right after the bold; it may sit mid-paragraph, as on many pages), or such bold
# alone on its line (optionally as a list item). A bold *sentence* about assumptions is not a
# heading: headings are short (the longest in the catalog has 8 words, "Assumptions, with the
# ones known to be violated flagged"), so a match with more than HEADING_MAX_WORDS is skipped.
ASSUMPTION_HEAD_RE = re.compile(
    r"\*\*(?:(?:further|other|key|the)\s+)?assumptions?\b[^*\n]{0,80}?(?:[:.]\*\*|\*\*[:.])"
    r"|^[ \t]*(?:[-*]\s+)?\*\*(?:(?:further|other|key|the)\s+)?assumptions?\b[^*\n]{0,80}?\*\*[ \t]*$",
    re.I | re.M)
HEADING_MAX_WORDS = 10
INLINE_ENUM_RE = re.compile(r"(?:^|\s)\((?:i{1,3}|iv|vi{0,3}|ix|x|\d{1,2}|[a-h])\)\s+")
PROSE_ITEM_RE = re.compile(r"(?<=[.;])\s+(?=[A-Z$*][^.:;]{2,100}:\s*\*)")
LIST_START_RE = re.compile(r"^\s*(?:(?:-|\*|\d+\.)\s+\S|\|\s*\S)")   # a list item (marker, space, text) or table row; "**bold**" is not a bullet


def _assumption(item: str, split_name: bool = False) -> dict:
    """One assumption. The name is the italic or bold lead-in; with `split_name` (table rows and
    prose items, which are written "Name: status — why") the text before the first colon or dash;
    otherwise (plain list items, as in v1) the first eight words."""
    nm = re.match(r"\*([^*]{2,120}?)[:.]\*\s*[:.]?\s*(.*)", item) or \
        re.match(r"\*\*([^*]{2,120}?)[:.]?\*\*\s*[:.]?\s*(.*)", item) or \
        (split_name and re.match(r"([^:—]{2,100}?)\s*(?::|—|–| - )\s*(.*)", item))
    name = strip_md(nm.group(1)) if nm else " ".join(strip_md(item).split()[:8])
    text = strip_md(item)
    return {"name": name[:160], "text": text[:1200], "violated": assumption_status(text)}


def _first_block(text: str) -> str:
    """The lines under a heading up to its first real break: a blank line is skipped when the next
    non-empty line is a list item or table row (LIST_START_RE) or starts with whitespace; any other
    blank line ends the block."""
    lines = text.lstrip("\n").splitlines()
    out = []
    for i, line in enumerate(lines):
        if not line.strip():
            nxt = next((l for l in lines[i + 1:] if l.strip()), "")
            if not (LIST_START_RE.match(nxt) or nxt.startswith((" ", "\t"))):
                break
        out.append(line)
    return "\n".join(out)


def parse_assumptions(formal: str) -> list[dict]:
    """The "Assumptions" part of Formal Setting, in the four forms the catalog uses:
    a list under the heading, a table under it, an inline (i)/(ii) list on the
    heading line, or prose items "Name: *status* — why."."""
    m = next((m for m in ASSUMPTION_HEAD_RE.finditer(formal)
              if len(re.findall(r"[A-Za-z0-9$\\]+", m.group(0))) <= HEADING_MAX_WORDS), None)
    if not m:
        return []
    line_end = formal.find("\n", m.end())
    inline = formal[m.end(): line_end if line_end != -1 else None].strip()
    below = _first_block(formal[line_end:] if line_end != -1 else "")
    out: list[dict] = []
    stripped = below.lstrip()
    markers = INLINE_ENUM_RE.findall(inline) if inline else []
    # A table or list under the heading is the content; anything on the heading line is then an
    # introduction (no page in the catalog has both, so nothing is read twice).
    if stripped.startswith("|"):
        rows = [r.strip() for r in stripped.splitlines() if r.strip().startswith("|")][2:]
        out += [_assumption(" — ".join(c.strip() for c in r.strip("|").split("|")), True) for r in rows]
    elif LIST_START_RE.match(below):
        out += [_assumption(i, False) for i in list_items("\n".join(l.lstrip() for l in below.splitlines()))]
    # Otherwise an enumeration on the heading line, "(i) ... (ii) ...": either the line starts with
    # a marker, or at least two markers follow a short introduction. A lone "(1)" in prose
    # ("see Eq. (1)") is a reference, not an enumeration.
    elif markers and (INLINE_ENUM_RE.match(inline) or len(markers) >= 2):
        out += [_assumption(p.strip(), True) for p in INLINE_ENUM_RE.split(inline)[1:] if p.strip()]
    elif inline:   # prose items "Name: *status* — why."
        out += [_assumption(p.strip(), True) for p in PROSE_ITEM_RE.split(inline) if p.strip()]
    return [a for a in out if len(a["text"]) > 3]


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
_BUILD_NAMES = ("Graph", "build_graph", "main", "catalog_dates", "choose_venues")


def __getattr__(name: str):
    if name in _BUILD_NAMES:
        from etl import build
        return getattr(build, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    from etl.build import main
    main()
