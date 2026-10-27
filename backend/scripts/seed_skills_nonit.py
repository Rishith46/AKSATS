from sqlalchemy import select

from app.db import SessionLocal
from app.models.candidates import Skill, SkillAlias

# Draft list written from five real Caterpillar job descriptions. Names and aliases are the
# developer's drafts for the client to confirm, not client rules. Edit freely.
NONIT = {
 "Supplier Management": ("Supply Chain", ["Vendor Management"]),
 "Supplier Evaluation": ("Supply Chain", ["Supplier Evaluations", "Vendor Evaluation"]),
 "Supplier Certification": ("Supply Chain", ["Vendor Certification"]),
 "Procurement": ("Supply Chain", []),
 "Supply Chain": ("Supply Chain", ["Supply Chain Management"]),
 "Inventory Management": ("Supply Chain", ["Inventory Control"]),
 "Rough Cut Capacity Planning": ("Supply Chain", ["RCCP"]),
 "Data Analytics": ("Data and Tools", ["Data Analysis"]),
 "Dashboards": ("Data and Tools", ["Dashboard Development"]),
 "Microsoft Excel": ("Data and Tools", ["Excel"]),
 "Microsoft Office 365": ("Data and Tools", ["Office 365", "Microsoft 365", "O365"]),
 "SharePoint": ("Data and Tools", ["Microsoft SharePoint"]),
 "Microsoft Lists": ("Data and Tools", []),
 "EtQ": ("Quality", ["EtQ Reliance"]),
 "PPAP": ("Quality", ["Production Part Approval Process"]),
 "APQP": ("Quality", ["Advanced Product Quality Planning"]),
 "SPC": ("Quality", ["Statistical Process Control", "Statistical SPC"]),
 "Root Cause Analysis": ("Quality", ["RCA"]),
 "RCCA": ("Quality", ["Root Cause Corrective Action"]),
 "8D": ("Quality", ["8D Problem Solving", "Eight Disciplines"]),
 "Six Sigma": ("Quality", ["6 Sigma", "Six-Sigma"]),
 "Lean Manufacturing": ("Quality", ["Lean", "Lean Production"]),
 "Continuous Improvement": ("Quality", []),
 "Corrective Action": ("Quality", ["Corrective Actions"]),
 "Quality Standards": ("Quality", []),
 "Manufacturing Operations": ("Manufacturing", []),
 "Machining": ("Manufacturing", ["Machining Processes"]),
 "CNC Programming": ("Manufacturing", ["CNC Programing"]),
 "Process Development": ("Manufacturing", []),
 "Process Improvement": ("Manufacturing", []),
 "Honing": ("Manufacturing", []),
 "OD/ID Grinding": ("Manufacturing", ["OD Grinding", "ID Grinding"]),
 "Centerless Grinding": ("Manufacturing", []),
 "Automated Cells": ("Manufacturing", ["Automated Cell"]),
 "Print Reading": ("Engineering", ["Blueprint Reading", "Reading Blueprints", "Blueprint Interpretation", "Blueprints", "Blueprint"]),
 "Engineering Drawings": ("Engineering", ["Technical Drawings"]),
 "Mechanical Design": ("Engineering", []),
 "Creo": ("Engineering", ["PTC Creo"]),
 "3D CAD": ("Engineering", ["3-D CAD"]),
 "Teamcenter Visualization": ("Engineering", []),
 "Teamcenter": ("Engineering", []),
}


def main() -> None:
    added_s = added_a = 0
    with SessionLocal() as db:
        for name, (category, aliases) in NONIT.items():
            s = db.scalar(select(Skill).where(Skill.name == name))
            if not s:
                s = Skill(name=name, category=category)
                db.add(s)
                db.flush()
                added_s += 1
            for a in aliases:
                if not db.scalar(select(SkillAlias).where(SkillAlias.alias == a)):
                    db.add(SkillAlias(skill_id=s.id, alias=a))
                    added_a += 1
        db.commit()
    print(f"Skills added: {added_s}, aliases added: {added_a}")


if __name__ == "__main__":
    main()