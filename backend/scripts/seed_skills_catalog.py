from sqlalchemy import select

from app.db import SessionLocal
from app.models.candidates import Skill, SkillAlias
from app.skill_catalog import ALIASES, SKILLS_BY_CATEGORY
from scripts.seed_skills import SKILLS as IT_SKILLS
from scripts.seed_skills_nonit import NONIT as NONIT_SKILLS


def catalog_entries():
    entries = {}

    def add(name, category, aliases):
        key = name.casefold()
        if key not in entries:
            entries[key] = {"name": name, "category": category, "aliases": set()}
        entry = entries[key]
        entry["aliases"].update(aliases)
        if entry["category"] is None:
            entry["category"] = category

    for category, names in SKILLS_BY_CATEGORY.items():
        for name in names:
            add(name, category, ALIASES.get(name, []))
    for name, aliases in IT_SKILLS.items():
        add(name, "IT and Technology", aliases)
    for name, (category, aliases) in NONIT_SKILLS.items():
        add(name, category, aliases)
    return list(entries.values())


def main() -> None:
    added_skills = added_aliases = categorized = 0
    conflicts = []
    with SessionLocal() as db:
        skills = db.scalars(select(Skill)).all()
        by_name = {skill.name.casefold(): skill for skill in skills}
        canonical_names = set(by_name)
        aliases_by_name = {
            alias.casefold(): skill_id
            for alias, skill_id in db.execute(select(SkillAlias.alias, SkillAlias.skill_id)).all()
        }

        for entry in catalog_entries():
            name, category = entry["name"], entry["category"]
            skill = by_name.get(name.casefold())
            if skill is None:
                existing_alias_id = aliases_by_name.get(name.casefold())
                if existing_alias_id is not None:
                    skill = db.get(Skill, existing_alias_id)
                else:
                    skill = Skill(name=name, category=category, needs_review=False)
                    db.add(skill)
                    db.flush()
                    added_skills += 1
                by_name[name.casefold()] = skill
                if skill.name.casefold() == name.casefold():
                    canonical_names.add(name.casefold())
            elif skill.category is None and category:
                skill.category = category
                categorized += 1

        for entry in catalog_entries():
            skill = by_name[entry["name"].casefold()]
            for alias in sorted(entry["aliases"]):
                key = alias.casefold()
                if key == skill.name.casefold() or key in canonical_names:
                    continue
                existing_skill_id = aliases_by_name.get(key)
                if existing_skill_id == skill.id:
                    continue
                if existing_skill_id is not None:
                    conflicts.append(f"{alias} already belongs to another skill")
                    continue
                db.add(SkillAlias(skill_id=skill.id, alias=alias))
                aliases_by_name[key] = skill.id
                added_aliases += 1
        db.commit()

    print(
        f"Catalog seeded: {added_skills} skills added, {added_aliases} aliases added, "
        f"{categorized} existing skills categorized."
    )
    if conflicts:
        print(f"Skipped {len(conflicts)} conflicting aliases:")
        for conflict in conflicts:
            print(f"- {conflict}")


if __name__ == "__main__":
    main()
