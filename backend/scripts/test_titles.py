from app.services.matching import norm_title, title_score

m = {frozenset(("backend developer", "software engineer")): 0.7}
assert norm_title("Senior Software Engineer") == "software engineer"
assert title_score("TEST Backend Developer", ["Senior Software Engineer"], m)[0] == 0.7
assert "Related title" in title_score("TEST Backend Developer", ["Senior Software Engineer"], m)[1]
assert title_score("TEST Backend Developer", ["Senior Software Engineer"])[0] == 0.0
assert title_score("TEST Backend Developer", ["Senior Software Engineer"], {})[0] == 0.0
assert title_score("Backend Developer", ["Backend Developer"], m)[0] == 1.0
low = {frozenset(("platform engineer", "software engineer")): 0.2}
assert title_score("Platform Engineer", ["Software Engineer"], low)[0] == 0.5
assert title_score("Backend Developer", ["Software Engineer"], m)[0] < 1.0
print("title mapping checks passed")