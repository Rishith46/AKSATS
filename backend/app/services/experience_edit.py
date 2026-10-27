import re
from datetime import date

PARTIAL = re.compile(r"^(\d{4})(?:-(0[1-9]|1[0-2]))?$")


def parse_partial_date(s):
    """'2021-03' -> (date(2021, 3, 1), 'month'). '2021' -> (date(2021, 1, 1), 'year'). Blank -> (None, None).
    The precision is kept so a year-only date is never shown as a month."""
    if s is None:
        return None, None
    s = s.strip()
    if not s:
        return None, None
    m = PARTIAL.match(s)
    if not m:
        raise ValueError("dates must be written as YYYY-MM or YYYY")
    year = int(m.group(1))
    if not 1950 <= year <= date.today().year + 1:
        raise ValueError("the year is out of range")
    if m.group(2):
        return date(year, int(m.group(2)), 1), "month"
    return date(year, 1, 1), "year"


def format_partial_date(d, precision):
    if d is None:
        return None
    return d.strftime("%Y-%m") if precision == "month" else str(d.year)


def check_experience(company, title, start, end, is_current):
    """Raises ValueError when the combination makes no sense. Dates are real dates or None."""
    if not (company or title):
        raise ValueError("an experience needs a company or a title")
    if is_current and end is not None:
        raise ValueError("a current job cannot have an end date")
    if start is not None and end is not None and end < start:
        raise ValueError("the end date is before the start date")