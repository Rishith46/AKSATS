from datetime import date

from app.services.skill_history import _merge, skill_history
from app.services.skill_match import _pattern

terms = [(n, t, _pattern(t)) for n, t in
         [("Kubernetes", "Kubernetes"), ("Kubernetes", "K8s"), ("Python", "Python"), ("Docker", "Docker")]]
roles = [
    {"title": "Dev", "description": "Built Python services on K8s.", "start": date(2024, 1, 1), "end": None, "is_current": True},
    {"title": "Dev", "description": "Wrote Python scripts.", "start": date(2020, 1, 1), "end": date(2022, 1, 1), "is_current": False},
    {"title": "Dev", "description": "Maintained Docker images.", "start": date(2015, 1, 1), "end": date(2017, 1, 1), "is_current": False},
    {"title": "Dev", "description": "Used Docker.", "start": None, "end": None, "is_current": False},
]
h = skill_history(roles, terms, today=date(2026, 10, 1))
assert abs(float(h["Python"]["years"]) - 4.75) < 0.06, h["Python"]
assert h["Python"]["last_year"] == 2026 and h["Python"]["first_year"] == 2020
assert "Built Python" in h["Python"]["evidence"]
assert abs(float(h["Kubernetes"]["years"]) - 2.75) < 0.06 and h["Kubernetes"]["last_year"] == 2026
assert float(h["Docker"]["years"]) == 2.0 and h["Docker"]["last_year"] == 2017
assert sum((e - s).days for s, e in _merge([(date(2020, 1, 1), date(2022, 1, 1)), (date(2021, 1, 1), date(2023, 1, 1))])) == 1096
print("skill history checks passed")