from datetime import date

from app.services.experience_edit import check_experience, format_partial_date, parse_partial_date

assert parse_partial_date("2021-03") == (date(2021, 3, 1), "month")
assert parse_partial_date("2021") == (date(2021, 1, 1), "year")
assert parse_partial_date(" 2019 ") == (date(2019, 1, 1), "year")
assert parse_partial_date("") == (None, None) and parse_partial_date(None) == (None, None)
assert parse_partial_date("  ") == (None, None)
for bad in ["2020-13", "2020-00", "20-01", "Jan 2020", "2020/01", "2020-1", "1900", "2999", "2020-01-15"]:
    try:
        parse_partial_date(bad)
        raise SystemExit("accepted a bad date: " + bad)
    except ValueError:
        pass

assert format_partial_date(date(2021, 3, 1), "month") == "2021-03"
assert format_partial_date(date(2021, 1, 1), "year") == "2021"
assert format_partial_date(date(2021, 1, 1), None) == "2021"
assert format_partial_date(None, "month") is None
for s in ["2021-03", "2019", "2026-10"]:
    d, p = parse_partial_date(s)
    assert format_partial_date(d, p) == s

check_experience("Alpha", None, date(2020, 1, 1), date(2022, 1, 1), False)
check_experience(None, "Developer", None, None, False)
check_experience("Alpha", "Dev", date(2022, 2, 1), None, True)
check_experience("Alpha", "Dev", date(2020, 1, 1), date(2020, 1, 1), False)
for args in [(None, None, None, None, False), ("", "", None, None, False),
             ("A", "B", date(2020, 1, 1), date(2022, 1, 1), True),
             ("A", "B", date(2022, 1, 1), date(2020, 1, 1), False)]:
    try:
        check_experience(*args)
        raise SystemExit("accepted a bad experience: " + repr(args))
    except ValueError:
        pass
print("experience edit checks passed")