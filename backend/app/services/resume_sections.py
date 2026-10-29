import re

HEADING_SECTIONS = {
    "academic background": "education",
    "academic qualifications": "education",
    "education": "education",
    "education and training": "education",
    "education & training": "education",
    "technical skills": "skills",
    "technical profile": "skills",
    "programming languages": "skills",
    "skills and technologies": "skills",
    "key skills": "skills",
    "proficiencies": "skills",
    "core competencies": "skills",
    "areas of expertise": "skills",
    "skills": "skills",
    "technologies": "skills",
    "tools and technologies": "skills",
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses": "certifications",
    "licenses and certifications": "certifications",
    "professional certifications": "certifications",
}

_HEADING = re.compile(
    r"^\s*(?P<heading>academic background|academic qualifications|education(?: and training| & training)?|"
    r"technical skills|technical profile|programming languages|skills and technologies|key skills|"
    r"proficiencies|core competencies|areas of expertise|skills|technologies|tools and technologies|"
    r"certifications|certificates|licenses(?: and certifications)?|professional certifications)"
    r"\s*:?\s*(?P<inline>.*)$",
    re.I,
)
_OTHER_HEADING = re.compile(
    r"^\s*(?:professional summary|summary|profile|objective|work experience|professional experience|"
    r"experience|employment|employment history|career history|work history|projects|publications|"
    r"awards|languages|volunteer experience|interests|references|contact(?: information)?|"
    r"personal details|key achievements|accomplishments|activities)\s*:?\s*$",
    re.I,
)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_DEGREE = re.compile(
    r"\b(?:ph\.?d|doctor(?:ate)?|mba|m\.?s\.?|m\.?sc|master(?:'s)?|b\.?s\.?|b\.?sc|"
    r"bachelor(?:'s)?|b\.?a\.?|associate(?:'s)?|a\.?a\.?|a\.?s\.?|diploma|ged)\b",
    re.I,
)
_INSTITUTION = re.compile(r"\b(?:university|college|institute|school|academy)\b", re.I)
_CERT = re.compile(r"\b(?:certified|certification|certificate|license|licensed|credential)\b", re.I)


def extract_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = _HEADING.match(line)
        if match:
            current = HEADING_SECTIONS[match.group("heading").lower()]
            sections.setdefault(current, [])
            inline = match.group("inline").strip()
            if inline:
                sections[current].append(inline)
        elif _OTHER_HEADING.match(line):
            current = None
        elif current is not None:
            sections[current].append(line)
    return sections


def extract_resume_skills(text: str) -> list[str]:
    sections = extract_sections(text)
    skills: list[str] = []
    seen: set[str] = set()
    for line in sections.get("skills", []):
        line = re.sub(r"^[\W_]+", "", line)
        if ":" in line:
            label, rest = line.split(":", 1)
            if len(label) < 50 and rest.strip():
                line = rest.strip()
        for item in re.split(r"[,;|•●▪◦\t]+", line):
            skill = re.sub(r"\s+", " ", item).strip(" .:-")
            key = skill.casefold()
            if not skill or len(skill) > 150 or key in seen:
                continue
            seen.add(key)
            skills.append(skill)
    return skills


def _years(line: str) -> tuple[int | None, int | None]:
    years = [int(value) for value in _YEAR.findall(line)]
    return (years[0], years[-1]) if len(years) > 1 else (
        (None, years[0]) if years else (None, None)
    )


def extract_education(text: str) -> list[dict[str, str | int | None]]:
    records: list[dict[str, str | int | None]] = []
    seen: set[str] = set()
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in extract_sections(text).get("education", []):
        clean = re.sub(r"^[\W_]+", "", line).strip()
        if not clean:
            continue
        if current and _INSTITUTION.search(clean) and any(_INSTITUTION.search(part) for part in current):
            chunks.append(current)
            current = []
        if current and _DEGREE.search(clean) and any(_DEGREE.search(part) for part in current):
            chunks.append(current)
            current = []
        current.append(clean)
        if _YEAR.search(clean) and (_DEGREE.search("\n".join(current)) or _INSTITUTION.search("\n".join(current))):
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)

    for chunk in chunks:
        clean = " | ".join(chunk)
        if not (_DEGREE.search(clean) or _INSTITUTION.search(clean)):
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)

        parts = [
            part.strip()
            for part in re.split(r"\s*[|;,\n]\s*|\s+[—–]\s+", clean)
            if part.strip()
        ]
        degree_part = next((part for part in parts if _DEGREE.search(part)), None)
        institution = next((part for part in parts if _INSTITUTION.search(part)), None)
        if institution is None:
            institution = next(
                (part for part in reversed(parts) if part != degree_part and not _YEAR.search(part)),
                None,
            )
        degree = degree_part
        field = None
        if degree:
            degree = _YEAR.sub("", degree).strip(" ,-")
            field_match = re.search(r"\b(?:in|major(?:ed)? in|field of study:)\s+([^,|;]+)", degree, re.I)
            if field_match:
                field = field_match.group(1).strip(" .")
            else:
                abbreviation = re.match(
                    r"^((?:B\.?S\.?|B\.?A\.?|B\.?Sc\.?|M\.?S\.?|M\.?Sc\.?|M\.?A\.?|"
                    r"A\.?A\.?|A\.?S\.?|MBA|Ph\.?D\.?))\s+(.+)$",
                    degree,
                    re.I,
                )
                if abbreviation:
                    degree, field = abbreviation.group(1), abbreviation.group(2).strip(" ,-")

        start_year, end_year = _years(clean)
        records.append({
            "institution": institution[:200] if institution else None,
            "degree": degree[:200] if degree else None,
            "field_of_study": field[:200] if field else None,
            "start_year": start_year,
            "end_year": end_year,
        })
    return records


def extract_certifications(text: str) -> list[dict[str, str | int | None]]:
    records: list[dict[str, str | int | None]] = []
    seen: set[str] = set()
    for line in extract_sections(text).get("certifications", []):
        clean = re.sub(r"^[\W_]+", "", line).strip()
        if not clean or not re.search(r"[A-Za-z]", clean) or clean.casefold().startswith("issued by "):
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        issuer_match = re.search(r"\b(?:issued by|from|by)\s+(.+?)(?:[,;|]|\s+\b(?:19|20)\d{2}\b|$)", clean, re.I)
        issuer = issuer_match.group(1).strip(" .") if issuer_match else None
        year_values = _YEAR.findall(clean)
        name = (
            clean[:issuer_match.start()].strip(" ,-")
            if issuer_match
            else re.split(r"\s*[|;,]\s*|\s+[—–]\s+", clean, maxsplit=1)[0].strip(" ,-")
        )
        name = re.sub(r"\b(?:19|20)\d{2}\b", "", name).strip(" ,-")
        records.append({
            "name": name[:300],
            "issuer": issuer[:200] if issuer else None,
            "year": int(year_values[-1]) if year_values else None,
        })
    return records
