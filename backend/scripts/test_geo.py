from app.geo import (UNSET, US_STATES, compose_location, is_us, normalize_country, normalize_state,
                     resolve_location, split_location, state_code)

assert len(US_STATES) == 51 and len(set(US_STATES.values())) == 51
assert state_code("TX") == "TX" and state_code("tx") == "TX" and state_code("Texas") == "TX"
assert state_code("new  york") == "NY" and state_code("District of Columbia") == "DC"
assert state_code("ZZ") is None and state_code("") is None and state_code(None) is None

assert normalize_country("usa") == "United States" and normalize_country("U.S.") == "United States"
assert normalize_country("United States of America") == "United States"
assert normalize_country("india") == "India" and normalize_country("India") == "India"
assert normalize_country("") is None and normalize_country(None) is None and normalize_country("  ") is None
assert is_us(None) and is_us("United States") and not is_us("India")

assert split_location("Austin, TX") == ("Austin", "TX")
assert split_location("San Antonio, TX") == ("San Antonio", "TX")
assert split_location("TX") == (None, "TX") and split_location("Plano") == ("Plano", None)
assert split_location(None) == (None, None) and split_location("") == (None, None)
assert compose_location("Austin", "TX") == "Austin, TX"
assert compose_location("Austin", None) == "Austin" and compose_location(None, "TX") == "TX"
assert compose_location(None, None) is None and compose_location("  ", "") is None

assert normalize_state("Texas", None) == "TX" and normalize_state("tx", "United States") == "TX"
for args in [("Karnataka", None), ("ZZ", "United States")]:
    try:
        normalize_state(*args)
        raise SystemExit("accepted a bad state: " + repr(args))
    except ValueError:
        pass
assert normalize_state("Telangana", "India") == "Telangana"
assert normalize_state("", None) is None

assert resolve_location("Austin, TX", None, city="Dallas") == {"location": "Dallas, TX"}
assert resolve_location("Austin, TX", None, state="Oklahoma", city="Tulsa") == {"location": "Tulsa, OK"}
assert resolve_location("Austin, TX", None, state="florida") == {"location": "Austin, FL"}
assert resolve_location(None, None, city="Plano") == {"location": "Plano"}
assert resolve_location("Austin, TX", None, city="", state="") == {"location": None}
assert resolve_location("Austin, TX", None, country="usa") == {"country": "United States", "location": "Austin, TX"}
assert resolve_location("Austin, TX", None, country="India", city="Hyderabad", state="Telangana") == \
    {"country": "India", "location": "Hyderabad, Telangana"}
assert resolve_location("Hyderabad, India", None, country="India") == {"country": "India", "location": "Hyderabad, India"}
for kwargs in [dict(state="Karnataka"), dict(state="ZZ"), dict(country="usa", state="Karnataka")]:
    try:
        resolve_location("Austin, TX", None, **kwargs)
        raise SystemExit("accepted a bad edit: " + repr(kwargs))
    except ValueError:
        pass
try:
    resolve_location("Hyderabad, India", None, city="Pune")
    raise SystemExit("accepted a non-US location without a country")
except ValueError:
    pass
assert resolve_location("Hyderabad, India", "India", city="Pune") == {"location": "Pune, India"}
print("geo checks passed")