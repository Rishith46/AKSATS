from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidates import Skill, SkillAlias


def find_skill(db: Session, name: str):
    """A skill by its name or by an alias, ignoring case. None if it is not in the skills list."""
    t = name.strip().lower()
    s = db.scalar(select(Skill).where(func.lower(Skill.name) == t))
    if s is None:
        s = db.scalar(select(Skill).join(SkillAlias, SkillAlias.skill_id == Skill.id)
                      .where(func.lower(SkillAlias.alias) == t))
    return s