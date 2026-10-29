from app.skill_catalog import ALIASES
from app.services.reset_ats import ATS_DATA_TABLES
from scripts.seed_skills_catalog import catalog_entries


entries = catalog_entries()
names = {entry["name"].casefold() for entry in entries}
assert len(entries) >= 500, len(entries)
assert {name.casefold() for name in ALIASES}.issubset(names)
assert "skills" not in ATS_DATA_TABLES
assert "skill_aliases" not in ATS_DATA_TABLES

for expected in (
    "Python", "TypeScript", "Snowflake", "Redis", "Kubernetes",
    "Lean Manufacturing", "Accounts Payable", "Construction Management",
    "Legal Research", "Contract Drafting", "Litigation", "Electronic Discovery",
):
    assert expected.casefold() in names, expected

print(f"skill catalog checks passed ({len(entries)} canonical skills)")
