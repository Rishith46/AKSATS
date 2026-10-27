import re

# The one list of visa statuses. The API serves it, the screens use it, and every write is checked
# against it, so the dropdown and the validation cannot drift apart.
VISA_OPTIONS = [
    ("Indian Candidate", "Indian Candidate"),
    ("USC", "USC (United States Citizen)"),
    ("GC", "GC (Green Card)"),
    ("H1B", "H1B"),
    ("H4-EAD", "H4-EAD"),
    ("GC-EAD", "GC-EAD"),
    ("OPT", "OPT"),
    ("STEM-OPT", "STEM-OPT"),
    ("TN", "TN"),
    ("E3", "E3"),
]
VISA_VALUES = [v for v, _ in VISA_OPTIONS]
OUTSIDE_US = "Indian Candidate"

# Ways a job description may write each status. A status counts as listed only as a whole token,
# so OPT is not found inside STEM-OPT and GC is not found inside GC-EAD.
ALIASES = {
    "USC": ["USC", "US Citizen", "U.S. Citizen", "United States Citizen", "Citizen"],
    "GC": ["GC", "Green Card"],
    "H1B": ["H1B", "H-1B", "H1-B"],
    "H4-EAD": ["H4-EAD", "H4 EAD"],
    "GC-EAD": ["GC-EAD", "GC EAD"],
    "OPT": ["OPT"],
    "STEM-OPT": ["STEM-OPT", "STEM OPT"],
    "TN": ["TN"],
    "E3": ["E3"],
    "Indian Candidate": ["Indian Candidate"],
}


def check_visa(v):
    """None or an empty string means not mentioned. Anything else must be one of the ten values."""
    if v is None:
        return None
    v = v.strip()
    if v == "":
        return None
    if v not in VISA_VALUES:
        raise ValueError("visa_status must be one of: " + ", ".join(VISA_VALUES))
    return v


def mentions(text, status):
    for term in ALIASES.get(status, [status]):
        if re.search(r"(?<![A-Za-z0-9-])" + re.escape(term) + r"(?![A-Za-z0-9-])", text, re.I):
            return True
    return False