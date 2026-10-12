from app.services.field_extract import extract_fields

mock = """Jane Mockperson
Dallas, TX | jane.mock@example.com | (555) 010-0123
linkedin.com/in/jane-mockperson
Senior Java Developer, Acme Mock Corp, 2021 - Present
"""
print("Full mock:", extract_fields(mock))

sparse = """Experienced engineer
Worked on many systems and built software for several years across teams.
"""
print("Sparse mock:", extract_fields(sparse))