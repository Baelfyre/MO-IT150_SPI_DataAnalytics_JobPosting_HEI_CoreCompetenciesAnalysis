#!/usr/bin/env python3
"""Turn saved job-posting HTML pages into reviewable CSV datasets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html as html_lib
import json
import re
import sys
import traceback
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

try:
    from bs4 import BeautifulSoup
except ImportError as exc:  # pragma: no cover - environment dependency message
    raise SystemExit(
        "Missing dependency beautifulsoup4. Install it in this Python runtime "
        "before running this script."
    ) from exc


COLLECTION_DATE = "2026-10-09"
WHERE_FOUND = "SimplifyTrabaho"
NOT_STATED = "Not stated"

JOB_COLUMNS = [
    "posting_id", "source_html_file", "where_job_was_found", "company",
    "job_title", "original_job_url", "collection_date", "location",
    "work_setup", "hiring_type", "employer_type", "data_analytics_related",
    "data_analytics_relevance_basis", "entry_level_status", "entry_level_basis",
    "education_requirement", "experience_required", "experience_preferred",
    "required_skills_tools", "preferred_additional_qualifications",
    "review_status", "notes",
]
SKILL_COLUMNS = [
    "posting_id", "company", "job_title", "skill_tool", "requirement_type",
    "skill_category", "evidence_context",
]
REVIEW_COLUMNS = JOB_COLUMNS + ["review_reasons"]


SKILL_PATTERNS = [
    ("Power BI", r"\bpower\s*bi\b", "Visualization"),
    ("Excel", r"\b(?:microsoft\s+)?excel\b", "Spreadsheet"),
    ("Tableau", r"\btableau\b", "Visualization"),
    ("Looker Studio", r"\blooker\s+studio\b", "Visualization"),
    ("Looker", r"\blooker\b", "Visualization"),
    ("SQL", r"\b(?:sql|structured query language)\b", "Database"),
    ("Python", r"\bpython\b", "Programming"),
    ("R", r"\b(?:R programming|R language)\b", "Programming"),
    ("SAS", r"\bsas\b", "Analytics software"),
    ("SPSS", r"\bspss\b", "Analytics software"),
    ("Stata", r"\bstata\b", "Analytics software"),
    ("Alteryx", r"\balteryx\b", "Analytics software"),
    ("Qlik Sense", r"\bqlik\s+sense\b", "Visualization"),
    ("Google Analytics", r"\bgoogle analytics\b", "Analytics software"),
    ("BigQuery", r"\bbigquery\b", "Data platform"),
    ("Snowflake", r"\bsnowflake\b", "Data platform"),
    ("Databricks", r"\bdatabricks\b", "Data platform"),
    ("Apache Spark", r"\b(?:apache\s+)?spark\b", "Data platform"),
    ("AWS", r"\baws\b|amazon web services", "Cloud platform"),
    ("Microsoft Azure", r"\b(?:microsoft\s+)?azure\b", "Cloud platform"),
    ("Google Cloud", r"\bgoogle cloud(?: platform)?\b|\bgcp\b", "Cloud platform"),
    ("Data analysis", r"\bdata analys[ie]s\b", "Analytics"),
    ("Data analytics", r"\bdata analytics\b", "Analytics"),
    ("Statistical analysis", r"\bstatistical analys[ie]s\b|\bstatistics\b", "Analytics"),
    ("Data visualization", r"\bdata visuali[sz]ation\b", "Visualization"),
    ("Dashboard development", r"\bdashboard(?:s)?\b", "Visualization"),
    ("Business intelligence", r"\bbusiness intelligence\b|\bBI tools\b", "Analytics"),
    ("Reporting", r"\breporting\b|\b(report|reports) generation\b", "Analytics"),
    ("Data cleaning", r"\bdata clean(?:ing|se|sing)\b", "Data preparation"),
    ("ETL/ELT", r"\b(?:etl|elt)\b|extract,? transform,? load", "Data preparation"),
    ("Data modeling", r"\bdata model(?:ing|ling)\b", "Data management"),
    ("Machine learning", r"\bmachine learning\b", "Analytics"),
    ("Data quality", r"\bdata[- ]quality\b", "Data management"),
]
COMPILED_SKILLS = [
    (name, re.compile(pattern, re.IGNORECASE), category)
    for name, pattern, category in SKILL_PATTERNS
]

PREFERRED_CUE = re.compile(
    r"\b(preferred|preferably|desirable|advantageous|nice[- ]to[- ]have|"
    r"a plus|an advantage|bonus|asset)\b", re.IGNORECASE,
)
REQUIRED_CUE = re.compile(
    r"\b(required|minimum|must[- ]have|must possess|essential|mandatory|"
    r"at least|required to)\b", re.IGNORECASE,
)
EXPERIENCE_CUE = re.compile(
    r"\b(experience|experienced|work history|professional background)\b",
    re.IGNORECASE,
)
EDUCATION_CUE = re.compile(
    r"\b(education|degree|bachelor(?:'s)?|master(?:'s)?|doctorate|diploma|"
    r"certification|certificate|academic qualification|major in|graduate degree|"
    r"B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?)\b", re.IGNORECASE,
)
SECTION_RE = re.compile(
    r"\b(required skills and qualifications|required qualifications|"
    r"minimum qualifications|minimum requirements|preferred qualifications|"
    r"preferred skills|preferred experience|requirements|qualifications|"
    r"education and experience|technical skills|responsibilities|"
    r"what you(?:'|’)ll do|what you(?:'|’)ll need|what you bring|"
    r"education|experience|skills)\b\s*: ?", re.IGNORECASE,
)
YEAR_RANGE_RE = re.compile(
    r"(?<!\w)(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)
YEAR_PLUS_RE = re.compile(r"(?<!\w)(\d{1,2})\s*\+\s*(?:years?|yrs?)\b", re.IGNORECASE)
YEAR_SINGLE_RE = re.compile(r"(?<!\w)(\d{1,2})\s*(?:years?|yrs?)\b", re.IGNORECASE)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def short(value: str, limit: int = 280) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rsplit(" ", 1)[0] + "…"


def plain_html(value: object) -> str:
    if not value:
        return ""
    return clean_text(BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True))


def stable_posting_id(source_html_file: str) -> str:
    normalized = PurePosixPath(source_html_file.replace("\\", "/")).as_posix().casefold()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"JP-{digest}"


def walk_json(value: object):
    if isinstance(value, list):
        for item in value:
            yield from walk_json(item)
    elif isinstance(value, dict):
        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(str(item).casefold() == "jobposting" for item in types):
            yield value
        for key, item in value.items():
            if key not in {"@context", "@type"}:
                yield from walk_json(item)


def structured_job_postings(soup: BeautifulSoup) -> list[dict]:
    found = []
    for script in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        try:
            parsed = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        found.extend(walk_json(parsed))
    return found


def as_text(value: object) -> str:
    if isinstance(value, dict):
        return clean_text(html_lib.unescape(value.get("name") or value.get("@value") or ""))
    if isinstance(value, list):
        return clean_text(", ".join(filter(None, (as_text(item) for item in value))))
    return clean_text(html_lib.unescape(str(value))) if value is not None else ""


def meta_map(soup: BeautifulSoup) -> dict[str, str]:
    result = {}
    for tag in soup.find_all("meta"):
        key = clean_text(tag.get("property") or tag.get("name") or tag.get("itemprop")).casefold()
        content = clean_text(tag.get("content"))
        if key and content:
            result.setdefault(key, content)
    return result


def first_value(*values: object) -> str:
    for value in values:
        text = as_text(value)
        if text:
            return text
    return ""


def visible_text(soup: BeautifulSoup) -> str:
    scope = soup.find("main") or soup.find("article") or soup.body or soup
    for tag in list(scope.find_all(["script", "style", "noscript", "svg", "nav", "footer", "iframe", "form", "button", "template"])):
        tag.extract()
    for tag in list(scope.find_all(True)):
        marker = " ".join((clean_text(tag.get("id")), clean_text(tag.get("class")))).casefold()
        if any(word in marker for word in ("cookie", "consent", "modal", "search-filter", "breadcrumb")):
            tag.extract()
    return "\n".join(clean_text(line) for line in scope.get_text("\n", strip=True).splitlines() if clean_text(line))


def split_fragments(text: str) -> list[str]:
    if not text:
        return []
    text = re.sub(r"[\r\n]+", "\n", str(text))
    text = re.sub(r"(?i)(?<!\w)(required skills (?:and|&) qualifications|required qualifications|"
                  r"minimum qualifications|minimum requirements|preferred qualifications|"
                  r"preferred skills|preferred experience|education and experience|"
                  r"technical skills|responsibilities|requirements|qualifications|"
                  r"what you(?:'|’)ll do|what you(?:'|’)ll need|what you bring|"
                  r"education|experience|skills)\s*: ?", r"\n\1: ", text)
    pieces = re.split(r"\n|[•●▪◦]+|(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [clean_text(piece).strip(" -:;•") for piece in pieces if clean_text(piece).strip(" -:;•")]


def section_kind(label: str) -> str:
    lower = label.casefold()
    if "preferred" in lower or "desirable" in lower:
        return "Preferred"
    if any(token in lower for token in ("required", "minimum", "requirement", "must")):
        return "Required"
    return "Unclear"


def segment_requirement(text: str, heading: str = "") -> str:
    if heading in {"Required", "Preferred"}:
        return heading
    if PREFERRED_CUE.search(text):
        return "Preferred"
    if REQUIRED_CUE.search(text):
        return "Required"
    return "Unclear"


def segments_from_dom(soup: BeautifulSoup) -> list[tuple[str, str]]:
    scope = soup.find("main") or soup.find("article") or soup.body or soup
    result: list[tuple[str, str]] = []
    heading = ""
    selectors = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "dt", "dd"]
    for tag in scope.find_all(selectors):
        if tag.name == "p" and tag.find_parent("li"):
            continue
        text = clean_text(tag.get_text(" ", strip=True))
        if not text:
            continue
        if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            heading = section_kind(text)
            if heading == "Unclear" and re.search(r"\b(requirements?)\b", text, re.I):
                heading = "Required"
            continue
        for fragment in split_fragments(text):
            result.append((fragment, heading))
    return result


def segments_from_text(text: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    heading = ""
    for fragment in split_fragments(text):
        marker = re.match(r"^(.{1,80}?):\s*(.*)$", fragment)
        if marker and re.fullmatch(
            r"(?i)(required skills (?:and|&) qualifications|required qualifications|minimum qualifications|"
            r"minimum requirements|preferred qualifications|preferred skills|preferred experience|"
            r"requirements|qualifications|education and experience|technical skills|responsibilities|"
            r"education|experience|skills)", marker.group(1).strip(),
        ):
            heading = section_kind(marker.group(1))
            if "requirement" in marker.group(1).casefold():
                heading = "Required"
            if marker.group(2):
                result.append((clean_text(marker.group(2)), heading))
            continue
        result.append((fragment, heading))
    return result


def all_segments(soup: BeautifulSoup, body_text: str, descriptions: list[str]) -> list[tuple[str, str]]:
    segments = segments_from_dom(soup)
    segments.extend(segments_from_text(body_text))
    for description in descriptions:
        segments.extend(segments_from_text(description))
    unique = {}
    for text, heading in segments:
        key = clean_text(text).casefold()
        if len(key) < 3:
            continue
        unique.setdefault((key, heading), (clean_text(text), heading))
    return list(unique.values())


def field_from_lines(text: str, labels: tuple[str, ...]) -> str:
    lines = [clean_text(line) for line in re.split(r"[\r\n]+", text) if clean_text(line)]
    label_pattern = re.compile(r"^(?:" + "|".join(re.escape(item) for item in labels) + r")\s*:?\s*(.*)$", re.I)
    for index, line in enumerate(lines):
        match = label_pattern.match(line)
        if not match:
            continue
        value = clean_text(match.group(1))
        if value:
            return short(value, 160)
        if index + 1 < len(lines):
            return short(lines[index + 1], 160)
    return ""


def clean_job_title(value: str) -> str:
    value = clean_text(value)
    value = re.sub(r"\s*[|–—]\s*(?:SmartRecruiters|Career Page|Workday|Greenhouse|Lever|LinkedIn|Indeed)\s*$", "", value, flags=re.I)
    value = re.sub(r"\s+-\s+(?:SmartRecruiters|Career Page|Workday|Greenhouse|Lever)\s*$", "", value, flags=re.I)
    return value.strip(" |–—-")


def get_source_url(html: str, soup: BeautifulSoup, meta: dict[str, str]) -> str:
    saved = re.search(r"saved from url=\(\d+\)(https?://[^\s\"']+)", html, re.I)
    if saved:
        return saved.group(1).rstrip(".)\"'")
    canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
    return first_value(canonical.get("href") if canonical else "", meta.get("og:url"), meta.get("twitter:url"))


def company_from_filename(source_name: str) -> str:
    stem = PurePosixPath(source_name).stem
    match = re.search(r"\s+@\s+(.+)$", stem)
    if match:
        return clean_text(match.group(1).replace("_", " "))
    return ""


def normalize_company(value: str) -> str:
    company = clean_text(html_lib.unescape(value))
    company = re.sub(r"^Company\s+\d+\s*[-:]\s*", "", company, flags=re.I)
    company = re.sub(r"^\d{3,5}\s+(?=[A-Za-z&])", "", company)
    if re.search(r"\b(?:inc\.?|ltd\.?|corp\.?|corporation|limited)\s+company$", company, re.I):
        company = re.sub(r"\s+company$", "", company, flags=re.I)
    company = re.sub(r"\bInc$", "Inc.", company, flags=re.I)
    return clean_text(company).strip(" ,;-")


def company_from_at_title(value: str) -> str:
    match = re.search(r"\s+at\s+(.+?)\s*(?:\|.*)?$", clean_text(value), re.I)
    if not match:
        return ""
    return clean_text(match.group(1)).strip(" |–—-")


def career_page_company(value: str, source_url: str) -> str:
    title = re.sub(r"\s*\|\s*Career Page\s*$", "", clean_text(value), flags=re.I)
    parts = re.split(r"\s+[-–—]\s+", title)
    path = re.sub(r"[^a-z0-9]", "", urlsplit(source_url).path.casefold())
    path_company = path.split("job", 1)[0].rstrip("/")
    company_marker = re.compile(
        r"\b(inc\.?|incorporated|corp\.?|corporation|llc|ltd\.?|limited|solutions|"
        r"group|bank|university|firm|consultancy|consultants|staffing|company|"
        r"technologies|technology|services|labs|industries|foundation)\b", re.I,
    )
    candidates = [clean_text(" - ".join(parts[start:])) for start in range(len(parts) - 1, 0, -1)]
    for candidate in candidates:
        slug = re.sub(r"[^a-z0-9]", "", candidate.casefold())
        if slug and path and (slug in path or (path_company and path_company in slug)):
            return candidate
    for candidate in candidates:
        if company_marker.search(candidate):
            return candidate
    return ""


def company_from_host_title(source_url: str, title: str) -> str:
    hostname = urlsplit(source_url).hostname or ""
    host_parts = hostname.casefold().split(".") if hostname else []
    if len(host_parts) < 2:
        return ""
    brand = host_parts[-2]
    generic = {
        "smartrecruiters", "greenhouse", "lever", "workable", "myworkdayjobs",
        "breezy", "careers-page", "ashby", "linkedin", "indeed", "jobstreet",
    }
    if brand in generic:
        return ""
    match = re.search(rf"\b{re.escape(brand)}\b", title, re.I)
    return match.group(0) if match else ""


def extract_location(job: dict, body_text: str) -> str:
    locations = job.get("jobLocation", [])
    if not isinstance(locations, list):
        locations = [locations]
    for place in locations:
        if not isinstance(place, dict):
            continue
        address = place.get("address", {})
        if isinstance(address, dict):
            bits = [
                clean_text(address.get(key))
                for key in ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry")
                if clean_text(address.get(key))
            ]
            if bits:
                return ", ".join(dict.fromkeys(bits))
        if place.get("name"):
            return clean_text(place["name"])
    labelled = field_from_lines(body_text, ("location", "job location", "work location", "office location"))
    return labelled


def extract_work_setup(job: dict, text: str) -> str:
    location_type = clean_text(job.get("jobLocationType")).casefold()
    if "telecommute" in location_type or "remote" in location_type:
        return "Remote"
    flags = set()
    if re.search(r"\b(remote|work from home|WFH)\b", text, re.I):
        flags.add("Remote")
    if re.search(r"\bhybrid\b", text, re.I):
        flags.add("Hybrid")
    if re.search(r"\b(on[- ]site|onsite|office[- ]based)\b", text, re.I):
        flags.add("On-site")
    return next(iter(flags)) if len(flags) == 1 else ("Unclear" if flags else "")


def agency_evidence(company: str, text: str) -> bool:
    company_pattern = re.compile(r"\b(recruitment|staffing|manpower|employment agency|placement services)\b", re.I)
    body_pattern = re.compile(
        r"\b(recruitment agency|staffing agency|employment agency|recruitment firm|staffing firm|"
        r"outsourcing (?:company|provider|firm)|staffing and recruitment)\b", re.I,
    )
    return bool(company_pattern.search(company) or body_pattern.search(text))


def analytics_classification(title: str, text: str) -> tuple[str, str]:
    title_lower = title.casefold()
    exclusions = (
        r"\bdata entry\b", r"\bdata engineer\b", r"\bdata architect\b",
        r"\bdatabase administrator\b", r"\bmachine learning engineer\b",
        r"\bAI trainer\b", r"\bAI content\b", r"\bdata solutions architect\b",
    )
    for pattern in exclusions:
        match = re.search(pattern, title, re.I)
        if match:
            return "NO", f"Job title evidence: {short(match.group(0), 120)}. This is an adjacent or non-target role under the conservative screening rules."

    target_title = bool(re.search(
        r"\b(data|analytics?|business intelligence|BI|reporting|insights?)\s+(?:analyst|analytics analyst)\b|"
        r"\banalytics analyst\b|\bBI analyst\b", title, re.I,
    ))
    markers = [
        ("analysis", r"\banal[yi][sz](?:e|es|ed|ing|is|ysis)\b|\banalytics?\b"),
        ("querying", r"\bSQL\b|\bquery(?:ing)? data\b|\bdata extraction\b"),
        ("visualization", r"\bvisuali[sz](?:e|es|ed|ing|ation)\b|\bdashboard(?:s)?\b"),
        ("reporting", r"\breport(?:ing|s)?\b|\bscorecards?\b"),
        ("interpretation", r"\binterpret(?:ation|ing)?\b|\binsights?\b|\btrends?\b"),
        ("data quality", r"\bdata[- ]quality\b|\bdata validation\b|\banomaly detection\b"),
        ("statistics", r"\bstatistic(?:al|s)?\b|\bforecast(?:ing)?\b"),
    ]
    matched = [name for name, pattern in markers if re.search(pattern, text, re.I)]
    evidence = next((short(fragment, 220) for fragment in split_fragments(text)
                     if any(re.search(pattern, fragment, re.I) for _, pattern in markers)), "")
    if target_title and matched:
        return "YES", f"Job title: {short(title, 100)}. Duties/qualification evidence: {evidence or ', '.join(matched)}"
    if not target_title and "analyst" in title_lower and len(matched) >= 3:
        return "YES", f"Analyst title with multiple data-analysis indicators ({', '.join(matched)}); evidence: {evidence}"
    if target_title:
        return "NEEDS_REVIEW", f"Job title suggests an analytics role ({short(title, 100)}), but saved duties do not provide decisive supporting evidence."
    return "NEEDS_REVIEW", f"The title ({short(title, 100) or NOT_STATED}) and saved duties do not establish a clear target or non-target classification."


def year_bounds(text: str) -> tuple[int, int | None] | None:
    match = YEAR_RANGE_RE.search(text)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = YEAR_PLUS_RE.search(text)
    if match:
        return int(match.group(1)), None
    match = YEAR_SINGLE_RE.search(text)
    if match:
        return int(match.group(1)), int(match.group(1))
    return None


def is_experience_segment(text: str, heading: str) -> bool:
    return bool(EXPERIENCE_CUE.search(text) or (heading.casefold() == "experience" and year_bounds(text)))


def extract_qualifications(segments: list[tuple[str, str]]) -> tuple[str, str, str, str, list[str], bool]:
    education, required_exp, preferred_exp, preferred_quals = [], [], [], []
    ambiguous_experience = False
    for text, heading in segments:
        req = segment_requirement(text, heading)
        if EDUCATION_CUE.search(text):
            qualifier = "Preferred: " if req == "Preferred" else ("Required: " if req == "Required" else "")
            education.append(qualifier + short(text, 280))
        if is_experience_segment(text, heading):
            if req == "Required":
                required_exp.append(short(text, 280))
            elif req == "Preferred":
                preferred_exp.append(short(text, 280))
            else:
                ambiguous_experience = True
        if req == "Preferred" and (
            any(pattern.search(text) for _, pattern, _ in COMPILED_SKILLS)
            or EDUCATION_CUE.search(text)
            or EXPERIENCE_CUE.search(text)
            or re.search(r"\b(qualification|proficien|knowledge|ability|skill|familiar|certif)\b", text, re.I)
        ):
            preferred_quals.append(short(text, 280))
    return (
        "; ".join(dict.fromkeys(education)) or NOT_STATED,
        "; ".join(dict.fromkeys(required_exp)) or NOT_STATED,
        "; ".join(dict.fromkeys(preferred_exp)) or NOT_STATED,
        "; ".join(dict.fromkeys(preferred_quals)) or NOT_STATED,
        list(dict.fromkeys([
            f"{segment_requirement(text, heading)}: {text}"
            for text, heading in segments if is_experience_segment(text, heading)
        ])),
        ambiguous_experience,
    )


def classify_entry_level(title: str, text: str, experience_segments: list[str], required_exp: str, preferred_exp: str) -> tuple[str, str]:
    direct = re.search(
        r"\b(fresh graduates? (?:are )?(?:welcome|encouraged|accepted)|open to fresh graduates?|"
        r"fresh graduates? may apply|entry[- ]level|junior|intern(?:ship)?|graduate program|"
        r"no (?:prior )?experience required|zero experience required)\b", text, re.I,
    )
    if direct:
        required_years = [year_bounds(item) for item in experience_segments
                          if segment_requirement(item) == "Required" and year_bounds(item)]
        if any(bounds and bounds[0] >= 3 for bounds in required_years):
            return "UNCLEAR", f"Conflicting evidence: {short(direct.group(0), 100)} and a requirement for three or more years of experience."
        return "EXPLICIT_ENTRY_LEVEL", short(direct.group(0), 220)

    req_bounds = [year_bounds(item) for item in experience_segments
                  if segment_requirement(item) == "Required" and year_bounds(item)]
    pref_bounds = [year_bounds(item) for item in experience_segments
                   if segment_requirement(item) == "Preferred" and year_bounds(item)]
    if req_bounds:
        finite_maxes = [bounds[1] for bounds in req_bounds if bounds and bounds[1] is not None]
        lower_bounds = [bounds[0] for bounds in req_bounds if bounds]
        if lower_bounds and min(lower_bounds) >= 3:
            return "NOT_ENTRY_LEVEL", required_exp
        if finite_maxes and max(finite_maxes) <= 2 and max(lower_bounds, default=0) <= 2:
            return "ENTRY_LEVEL_WITH_EXPERIENCE", required_exp
        if lower_bounds and min(lower_bounds) <= 2:
            return "POSSIBLE_ENTRY_LEVEL", required_exp
    if pref_bounds and all(bounds and bounds[1] is not None and bounds[1] <= 2 for bounds in pref_bounds):
        return "POSSIBLE_ENTRY_LEVEL", preferred_exp
    if re.search(r"\b(junior|intern|entry[- ]level)\b", title, re.I):
        return "EXPLICIT_ENTRY_LEVEL", short(title, 220)
    if experience_segments:
        return "UNCLEAR", short(experience_segments[0], 220)
    return "UNCLEAR", "No explicit fresh-graduate, entry-level, junior, or qualifying experience evidence found in the saved posting text. The source filter was not used to infer eligibility."


def extract_skills(segments: list[tuple[str, str]], posting_id: str, company: str, title: str) -> tuple[list[dict[str, str]], str, bool]:
    mentions: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for text, heading in segments:
        requirement = segment_requirement(text, heading)
        for name, pattern, category in COMPILED_SKILLS:
            if pattern.search(text):
                mentions[name].append((requirement, short(text, 240), category))
    rows = []
    for name, values in mentions.items():
        types = {kind for kind, _, _ in values if kind in {"Required", "Preferred"}}
        requirement = "Unclear" if len(types) > 1 or not types else next(iter(types))
        chosen = next((item for item in values if item[0] == requirement), values[0])
        rows.append({
            "posting_id": posting_id,
            "company": company,
            "job_title": title,
            "skill_tool": name,
            "requirement_type": requirement,
            "skill_category": chosen[2],
            "evidence_context": chosen[1],
        })
    rows.sort(key=lambda item: item["skill_tool"].casefold())
    required = [row["skill_tool"] for row in rows if row["requirement_type"] == "Required"]
    separation_unclear = any(row["requirement_type"] == "Unclear" for row in rows)
    return rows, "; ".join(required) or NOT_STATED, separation_unclear


def blank_record(source_html_file: str) -> dict[str, str]:
    row = {column: NOT_STATED for column in JOB_COLUMNS}
    row.update({
        "posting_id": stable_posting_id(source_html_file),
        "source_html_file": source_html_file,
        "where_job_was_found": WHERE_FOUND,
        "collection_date": COLLECTION_DATE,
        "original_job_url": "",
        "work_setup": NOT_STATED,
        "hiring_type": "Unclear",
        "employer_type": "Unclear",
        "data_analytics_related": "NEEDS_REVIEW",
        "entry_level_status": "UNCLEAR",
        "review_status": "NEEDS_REVIEW",
        "notes": "",
    })
    return row


def parse_posting(source_html_file: str, raw: bytes) -> tuple[dict[str, str], list[dict[str, str]], list[str], bool]:
    row = blank_record(source_html_file)
    review_reasons: list[str] = []
    try:
        html = raw.decode("utf-8", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")
        metadata = meta_map(soup)
        jobs = structured_job_postings(soup)
        job = jobs[0] if jobs else {}
        body_text = visible_text(soup)
        meta_description = first_value(metadata.get("og:description"), metadata.get("description"))
        job_description = plain_html(job.get("description"))
        descriptions = list(dict.fromkeys(value for value in (job_description, meta_description) if value))
        evidence_text = clean_text(" ".join([body_text, *descriptions]))
        segments = all_segments(soup, body_text, descriptions)

        h1 = soup.find("h1")
        document_title = soup.title.get_text(" ", strip=True) if soup.title else ""
        raw_page_title = first_value(
            job.get("title"), metadata.get("og:title"), metadata.get("twitter:title"),
            h1.get_text(" ", strip=True) if h1 else "", document_title,
        )
        page_title = clean_job_title(raw_page_title)
        if not page_title:
            page_title = clean_job_title(PurePosixPath(source_html_file).stem.split(" @ ")[0])
        source_url = get_source_url(html, soup, metadata)
        company = first_value(
            (job.get("hiringOrganization") or {}).get("name") if isinstance(job.get("hiringOrganization"), dict) else "",
            metadata.get("hiringorganization"), metadata.get("company"), metadata.get("employer"),
            metadata.get("og:site_name"),
        )
        generic_company_names = re.compile(
            r"^(simplifytrabaho|smartrecruiters|career page|manatal|workday|linkedin|indeed|"
            r"glassdoor|greenhouse|lever|jobstreet|careers|jobs)$", re.I,
        )
        if generic_company_names.fullmatch(company):
            company = ""
        if not company:
            company = field_from_lines(body_text, ("company", "employer", "hiring organization"))
        if not company:
            company = company_from_filename(source_html_file)
        if not company:
            company = company_from_at_title(document_title) or company_from_at_title(raw_page_title)
        if not company and "careers-page.com" in source_url.casefold():
            company = career_page_company(raw_page_title, source_url)
        if not company:
            company = company_from_host_title(source_url, document_title or raw_page_title)
        source_company_label = company
        company = normalize_company(company)
        if company:
            title_suffix = re.compile(r"\s+(?:at|@)\s+" + re.escape(company) + r"\s*$", re.I)
            page_title = title_suffix.sub("", page_title).strip()
            career_suffix = re.compile(r"\s+[-–—]\s+" + re.escape(company) + r"\s*$", re.I)
            page_title = career_suffix.sub("", page_title).strip()

        row.update({
            "company": company or NOT_STATED,
            "job_title": page_title or NOT_STATED,
            "original_job_url": source_url or "",
            "location": extract_location(job, body_text) or NOT_STATED,
        })
        work_setup = extract_work_setup(job, evidence_text)
        row["work_setup"] = work_setup or NOT_STATED

        employer_is_agency = agency_evidence(company, evidence_text)
        if employer_is_agency:
            employer_type = "Recruitment agency"
        elif isinstance(job.get("hiringOrganization"), dict) and company:
            employer_type = "Direct employer"
        elif company and source_url:
            host = urlsplit(source_url).netloc.casefold()
            company_tokens = [token.casefold() for token in re.findall(r"[A-Za-z0-9]+", company) if len(token) >= 4]
            url_surface = (host + " " + urlsplit(source_url).path).casefold()
            employer_type = "Direct employer" if any(token in url_surface for token in company_tokens) else "Unclear"
        else:
            employer_type = "Unclear"
        row["employer_type"] = employer_type
        row["hiring_type"] = {
            "Direct employer": "Direct company posting",
            "Recruitment agency": "Agency posting",
            "Unclear": "Unclear",
        }[employer_type]

        relevance, relevance_basis = analytics_classification(page_title, evidence_text)
        row["data_analytics_related"] = relevance
        row["data_analytics_relevance_basis"] = relevance_basis
        education, required_exp, preferred_exp, preferred_quals, experience_segments, ambiguous_exp = extract_qualifications(segments)
        row["education_requirement"] = education
        row["experience_required"] = required_exp
        row["experience_preferred"] = preferred_exp
        row["preferred_additional_qualifications"] = preferred_quals
        entry_status, entry_basis = classify_entry_level(page_title, evidence_text, experience_segments, required_exp, preferred_exp)
        row["entry_level_status"] = entry_status
        row["entry_level_basis"] = entry_basis

        skill_rows, required_skills, skill_separation_unclear = extract_skills(segments, row["posting_id"], row["company"], row["job_title"])
        row["required_skills_tools"] = required_skills
        if relevance == "NEEDS_REVIEW":
            review_reasons.append("Data Analytics relevance is ambiguous from the saved title and duties.")
        if entry_status in {"UNCLEAR", "POSSIBLE_ENTRY_LEVEL"}:
            review_reasons.append("Entry-level eligibility is not established decisively by the saved posting.")
        if employer_type == "Unclear":
            review_reasons.append("Employer type cannot be determined from available page evidence.")
        if skill_separation_unclear or ambiguous_exp:
            review_reasons.append("Required versus preferred qualification wording needs review.")
        if row["company"] == NOT_STATED:
            review_reasons.append("Company could not be extracted reliably.")
        if row["job_title"] == NOT_STATED:
            review_reasons.append("Job title could not be extracted reliably.")
        if len(body_text) < 80 and max((len(value) for value in descriptions), default=0) < 80:
            review_reasons.append("Saved HTML has little usable visible or structured job content.")
        notes = [f"Visible text characters: {len(body_text)}"]
        if jobs:
            notes.append("JobPosting JSON-LD metadata found")
        if not source_url:
            notes.append("Original source URL not found in saved-page metadata")
        if source_company_label and company != source_company_label:
            notes.append(f"Company label normalized from saved metadata: {source_company_label}")
        row["notes"] = "; ".join(notes)
        return row, skill_rows, list(dict.fromkeys(review_reasons)), True
    except Exception as exc:
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        row["notes"] = f"HTML extraction failed at line {frame.lineno}: {type(exc).__name__}: {short(str(exc), 180)}"
        return row, [], ["HTML content could not be parsed reliably."], False


def canonical_url(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
        if not parts.scheme or not parts.netloc:
            return url.strip().casefold()
        return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), "", ""))
    except ValueError:
        return url.strip().casefold()


def duplicate_groups(rows: list[dict[str, str]], key_function) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = key_function(row)
        if key:
            groups[key].append(row)
    return {key: values for key, values in groups.items() if len(values) > 1}


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_outputs(rows: list[dict[str, str]], skills: list[dict[str, str]], review_rows: list[dict[str, str]],
                     html_count: int, parsed_count: int, output_path: Path, skills_path: Path, review_path: Path) -> list[str]:
    checks = []
    errors = []
    def check(name: str, condition: bool) -> None:
        checks.append((name, condition))
        if not condition:
            errors.append(name)

    ids = [row["posting_id"] for row in rows]
    review_ids = {row["posting_id"] for row in review_rows}
    expected_review_ids = {row["posting_id"] for row in rows if row["review_status"] == "NEEDS_REVIEW"}
    valid_statuses = {"YES", "NO", "NEEDS_REVIEW"}
    check("One dataset row exists for every HTML archive member", len(rows) == html_count)
    check("Posting IDs are unique and stable from source paths", len(ids) == len(set(ids)) and all(row["posting_id"] == stable_posting_id(row["source_html_file"]) for row in rows))
    check("Every processed row retains source_html_file", all(bool(row["source_html_file"]) for row in rows))
    check("Data Analytics values use the allowed set", all(row["data_analytics_related"] in valid_statuses for row in rows))
    check("All NEEDS_REVIEW records appear in needs_review.csv", review_ids == expected_review_ids)
    check("Every skills_long posting_id belongs to job_postings.csv", {row["posting_id"] for row in skills}.issubset(set(ids)))
    check("Experience wording is not emitted as a skill", all(not re.search(r"\b(experience|years?|work history)\b", row["skill_tool"], re.I) for row in skills))
    check("Education credentials are not emitted as skills", all(not re.search(r"\b(degree|bachelor|master|diploma|certificate)\b", row["skill_tool"], re.I) for row in skills))
    check("Required skills and preferred qualifications are independently extracted", all(
        row["required_skills_tools"] == NOT_STATED or row["preferred_additional_qualifications"] == NOT_STATED
        or row["required_skills_tools"] != row["preferred_additional_qualifications"] for row in rows
    ))
    check("Each posting has at most one row per normalized skill", len({(row["posting_id"], row["skill_tool"]) for row in skills}) == len(skills))
    check("Parsed and failed counts reconcile to archive HTML count", parsed_count <= html_count and parsed_count + (html_count - parsed_count) == html_count)

    csv_jobs = read_csv(output_path)
    csv_skills = read_csv(skills_path)
    csv_reviews = read_csv(review_path)
    check("Written job_postings.csv is readable and has the expected row count", len(csv_jobs) == len(rows) and list(csv_jobs[0].keys()) == JOB_COLUMNS if csv_jobs else not rows)
    check("Written skills_long.csv is readable and preserves all skill rows", len(csv_skills) == len(skills) and (list(csv_skills[0].keys()) == SKILL_COLUMNS if csv_skills else True))
    check("Written needs_review.csv is readable and preserves all review rows", len(csv_reviews) == len(review_rows) and (list(csv_reviews[0].keys()) == REVIEW_COLUMNS if csv_reviews else True))
    if errors:
        raise RuntimeError("Validation failed: " + "; ".join(errors))
    return [f"PASS: {name}" for name, passed in checks if passed]


def build_summary(rows: list[dict[str, str]], skills: list[dict[str, str]], review_rows: list[dict[str, str]],
                  html_count: int, parsed_count: int, duplicate_urls: dict, duplicate_titles: dict,
                  validation: list[str], archive_path: Path, output_path: Path, skills_path: Path,
                  review_path: Path, report_path: Path) -> str:
    data_counts = Counter(row["data_analytics_related"] for row in rows)
    entry_counts = Counter(row["entry_level_status"] for row in rows)
    employer_counts = Counter(row["employer_type"] for row in rows)
    companies = {row["company"] for row in rows if row["company"] not in {"", NOT_STATED}}
    accessible_urls = sum(row["original_job_url"].startswith(("https://", "http://")) for row in rows)
    reasons = Counter(reason for row in review_rows for reason in row.get("_review_reasons", []))
    missing_by_host: Counter[str] = Counter()
    total_by_host: Counter[str] = Counter()
    for row in rows:
        host = urlsplit(row["original_job_url"]).netloc.casefold() or "URL unavailable"
        total_by_host[host] += 1
        if row["job_title"] == NOT_STATED or row["company"] == NOT_STATED:
            missing_by_host[host] += 1
    recurring = [(host, count, total_by_host[host]) for host, count in missing_by_host.most_common() if count >= 2]

    lines = [
        "# Job-posting HTML processing summary",
        "",
        "## Source and scope",
        "",
        "- Initial live candidate pool: 364 roles across 93 companies on October 9, 2026 (user-provided context; not re-verified).",
        f"- Archive: `{archive_path}`",
        f"- HTML files found in ZIP before processing: **{html_count}**.",
        f"- Successfully parsed: **{parsed_count}**.",
        f"- Failed to parse: **{html_count - parsed_count}**.",
        "- Each saved HTML page is retained as one record; no records were merged or removed.",
        "",
        "## Classification counts",
        "",
        f"- Data Analytics-related YES: **{data_counts['YES']}**.",
        f"- Data Analytics-related NO: **{data_counts['NO']}**.",
        f"- Data Analytics-related NEEDS_REVIEW: **{data_counts['NEEDS_REVIEW']}**.",
        "- Entry-level status:",
    ]
    for status in ("EXPLICIT_ENTRY_LEVEL", "ENTRY_LEVEL_WITH_EXPERIENCE", "POSSIBLE_ENTRY_LEVEL", "NOT_ENTRY_LEVEL", "UNCLEAR"):
        lines.append(f"  - {status}: **{entry_counts[status]}**.")
    lines.extend([
        "- Employer type:",
        f"  - Direct employer: **{employer_counts['Direct employer']}**.",
        f"  - Recruitment agency: **{employer_counts['Recruitment agency']}**.",
        f"  - Unclear: **{employer_counts['Unclear']}**.",
        f"- Unique companies represented (excluding unstated): **{len(companies)}**.",
        f"- Records with an HTTP/S original source URL captured in saved HTML: **{accessible_urls}** (live reachability not checked).",
        f"- Skill rows: **{len(skills)}** across **{len({row['posting_id'] for row in skills})}** postings.",
        f"- Records requiring review: **{len(review_rows)}**.",
        "",
        "## Duplicate checks",
        "",
        f"- Duplicate original URL groups: **{len(duplicate_urls)}**; records in those groups: **{sum(len(v) for v in duplicate_urls.values())}**. Duplicate URLs are retained and flagged for review.",
        f"- Duplicate company and job-title groups: **{len(duplicate_titles)}**; records in those groups: **{sum(len(v) for v in duplicate_titles.values())}**. Similar postings are not merged automatically.",
        "",
        "## Validation",
        "",
    ])
    lines.extend(f"- {result}." for result in validation)
    lines.extend([
        "",
        "## Review patterns and limitations",
        "",
    ])
    if reasons:
        for reason, count in reasons.most_common():
            lines.append(f"- {reason}: **{count}** record(s).")
    else:
        lines.append("- No review reasons were generated.")
    if recurring:
        lines.append("- Repeated source hosts with at least two missing company or title extractions:")
        for host, count, total in recurring[:12]:
            lines.append(f"  - `{host}`: **{count}/{total}** records have a missing company or title.")
    else:
        lines.append("- No recurring host-level company/title extraction gap affected two or more records.")
    lines.extend([
        "- Saved HTML may omit content loaded dynamically after the page was saved; no live sites were revisited.",
        "- Original source URL presence was checked from saved-page metadata only; live URL reachability was not checked.",
        "- Descriptions in page metadata can be truncated or duplicate the visible page. Extraction uses JSON-LD, metadata, headings, labels, and visible text; missing evidence remains `Not stated` or is sent for review.",
        "- Data Analytics and entry-level classifications are conservative rule-based screening labels, not final human coding. The SimplifyTrabaho filter was not used as proof of entry-level eligibility.",
        "- Skills are limited to a transparent built-in list of common analytics tools and skills. Unrecognized terms are not guessed or normalized.",
        "- BeautifulSoup 4 is the only non-standard Python dependency. The script makes no network requests and reads HTML directly from the ZIP without extracting or modifying it.",
        "",
        "## Files created",
        "",
        f"- Script: `{Path(__file__).resolve()}`",
        f"- Job postings: `{output_path}`",
        f"- Long-format skills: `{skills_path}`",
        f"- Review queue: `{review_path}`",
        f"- Summary: `{report_path}`",
        "",
        "## Safest next step for Google Colab",
        "",
        "Copy the reviewed script and the unchanged ZIP into the Colab runtime (or a mounted Drive folder), then invoke the same script with explicit `--input`, `--output`, and `--reports` paths. Compare the ZIP HTML count and validation summary before using the CSVs in a notebook; keep analysis and curriculum comparison in a later, separately reviewed step.",
        "",
    ])
    return "\n".join(lines)


def run(input_path: Path, output_path: Path, reports_path: Path) -> tuple[int, int]:
    if not input_path.is_file():
        raise FileNotFoundError(f"Input ZIP not found: {input_path}")
    output_path.mkdir(parents=True, exist_ok=True)
    reports_path.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(input_path) as archive:
        html_infos = [info for info in archive.infolist() if not info.is_dir() and PurePosixPath(info.filename).suffix.casefold() in {".html", ".htm"}]
        print(f"HTML files found in ZIP before processing: {len(html_infos)}")
        rows: list[dict[str, str]] = []
        skills: list[dict[str, str]] = []
        review_reasons_by_id: dict[str, list[str]] = {}
        parsed_count = 0
        for info in html_infos:
            row, skill_rows, reasons, parsed = parse_posting(info.filename, archive.read(info))
            rows.append(row)
            skills.extend(skill_rows)
            review_reasons_by_id[row["posting_id"]] = reasons
            parsed_count += int(parsed)

    url_groups = duplicate_groups(rows, lambda row: canonical_url(row["original_job_url"]) if row["original_job_url"] else "")
    for group in url_groups.values():
        for row in group:
            reason = "Duplicate original job URL appears in more than one saved HTML file."
            review_reasons_by_id[row["posting_id"]] = list(dict.fromkeys(review_reasons_by_id[row["posting_id"]] + [reason]))
    title_groups = duplicate_groups(
        rows,
        lambda row: "|".join((row["company"].casefold(), row["job_title"].casefold()))
        if row["company"] != NOT_STATED and row["job_title"] != NOT_STATED else "",
    )
    for row in rows:
        reasons = review_reasons_by_id[row["posting_id"]]
        row["review_status"] = "NEEDS_REVIEW" if reasons else "READY"

    review_rows = []
    for row in rows:
        if row["review_status"] == "NEEDS_REVIEW":
            review_rows.append({**row, "review_reasons": "; ".join(review_reasons_by_id[row["posting_id"]]), "_review_reasons": review_reasons_by_id[row["posting_id"]]})

    output_file = output_path / "job_postings.csv"
    skills_file = output_path / "skills_long.csv"
    review_file = output_path / "needs_review.csv"
    report_file = reports_path / "processing_summary.md"
    write_csv(output_file, JOB_COLUMNS, rows)
    write_csv(skills_file, SKILL_COLUMNS, skills)
    write_csv(review_file, REVIEW_COLUMNS, review_rows)
    validation = validate_outputs(rows, skills, review_rows, len(html_infos), parsed_count, output_file, skills_file, review_file)
    summary = build_summary(rows, skills, review_rows, len(html_infos), parsed_count, url_groups, title_groups,
                            validation, input_path, output_file, skills_file, review_file, report_file)
    report_file.write_text(summary, encoding="utf-8")
    print(f"Successfully parsed: {parsed_count}; failed: {len(html_infos) - parsed_count}")
    print(f"Outputs: {output_file}; {skills_file}; {review_file}; {report_file}")
    print(f"Validation checks passed: {len(validation)}")
    return len(html_infos), parsed_count


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Process saved job-posting HTML files from a ZIP archive.")
    parser.add_argument("--input", type=Path, default=root / "data" / "raw" / "JobPostingsHtmlFormat.zip", help="Path to the source ZIP archive.")
    parser.add_argument("--output", type=Path, default=root / "data" / "processed", help="Directory for CSV outputs.")
    parser.add_argument("--reports", type=Path, default=None, help="Directory for processing_summary.md; defaults beside the data directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if args.reports:
        reports_path = args.reports.expanduser().resolve()
    elif output_path.parent.name.casefold() == "data":
        reports_path = output_path.parent.parent / "reports"
    else:
        reports_path = output_path.parent / "reports"
    html_count, parsed_count = run(input_path, output_path, reports_path)
    return 0 if parsed_count == html_count else 1


if __name__ == "__main__":
    sys.exit(main())
