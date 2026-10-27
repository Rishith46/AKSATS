# US state rules shared by candidate editing and job locations.
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}
CODE_BY_NAME = {name.lower(): code for code, name in US_STATES.items()}
US_ALIASES = {"us", "u.s.", "usa", "u.s.a.", "united states", "united states of america", "america"}
UNSET = object()


def _clean(x):
    return (" ".join(x.split()) or None) if x else None


def normalize_country(c):
    """None means not mentioned. Any spelling of the US becomes 'United States'."""
    c = _clean(c)
    if c is None:
        return None
    if c.lower() in US_ALIASES:
        return "United States"
    return c.title() if c.islower() else c


def is_us(country):
    """A candidate with no country written is treated as US, so a US state is expected."""
    return country is None or country == "United States"


def state_code(s):
    """Two-letter code for a US state given as a code or a full name, or None if it is neither."""
    s = _clean(s)
    if s is None:
        return None
    if s.upper() in US_STATES:
        return s.upper()
    return CODE_BY_NAME.get(s.lower())


def normalize_state(state, country):
    state = _clean(state)
    if state is None:
        return None
    if is_us(country):
        code = state_code(state)
        if code is None:
            raise ValueError(f"'{state}' is not a US state. Use a two-letter code or the full name, "
                             "or set the country if it is outside the US.")
        return code
    return state[:50]


def split_location(loc):
    """'Austin, TX' -> ('Austin', 'TX'). A lone state code -> (None, 'TX')."""
    if not loc:
        return None, None
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    if not parts:
        return None, None
    if len(parts) == 1:
        one = parts[0]
        return (None, one.upper()) if one.upper() in US_STATES else (one, None)
    return ", ".join(parts[:-1]), parts[-1]


def compose_location(city, state):
    city, state = _clean(city) or "", _clean(state) or ""
    if city and state:
        return f"{city}, {state}"
    return city or state or None


def resolve_location(old_location, old_country, city=UNSET, state=UNSET, country=UNSET):
    """Column changes for an edit of city, state and/or country. Raises ValueError for a state
    that does not fit the country. Anything not passed is kept as it was."""
    changes = {}
    eff_country = old_country
    if country is not UNSET:
        eff_country = normalize_country(country)
        changes["country"] = eff_country
    old_city, old_state = split_location(old_location)
    new_city = old_city if city is UNSET else _clean(city)
    new_state = old_state if state is UNSET else _clean(state)
    new_state = normalize_state(new_state, eff_country)
    changes["location"] = compose_location(new_city, new_state)
    return changes