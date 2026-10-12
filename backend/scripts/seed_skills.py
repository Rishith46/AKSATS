from sqlalchemy import select

from app.db import SessionLocal
from app.models.candidates import Skill, SkillAlias

SKILLS = {
    "Java": ["Java SE", "Java EE", "J2EE"],
    "Spring Boot": ["SpringBoot"],
    "Spring": ["Spring Framework"],
    "Hibernate": [],
    "Microservices": ["Micro services", "Microservice"],
    "Kafka": ["Apache Kafka"],
    "RabbitMQ": [],
    "Python": [],
    "Django": [],
    "Flask": [],
    "FastAPI": [],
    "JavaScript": ["JS", "ECMAScript"],
    "TypeScript": ["TS"],
    "React": ["React.js", "ReactJS"],
    "Angular": ["AngularJS"],
    "Vue": ["Vue.js", "VueJS"],
    "Node.js": ["NodeJS", "Node"],
    "Next.js": ["NextJS"],
    "HTML": ["HTML5"],
    "CSS": ["CSS3"],
    "C#": ["C Sharp"],
    ".NET": ["dotnet", ".NET Core", "ASP.NET"],
    "C++": ["CPP"],
    "Go": ["Golang"],
    "Ruby": [],
    "PHP": [],
    "Scala": [],
    "SQL": [],
    "PostgreSQL": ["Postgres"],
    "MySQL": [],
    "Oracle": ["Oracle DB"],
    "SQL Server": ["MSSQL", "Microsoft SQL Server"],
    "MongoDB": ["Mongo"],
    "Redis": [],
    "Elasticsearch": ["Elastic Search"],
    "Amazon Web Services": ["AWS"],
    "Microsoft Azure": ["Azure"],
    "Google Cloud Platform": ["GCP", "Google Cloud"],
    "Kubernetes": ["K8s"],
    "Docker": [],
    "Terraform": [],
    "Ansible": [],
    "Jenkins": [],
    "CI/CD": ["CICD", "CI CD"],
    "Git": [],
    "GitHub Actions": [],
    "Linux": [],
    "DevOps": [],
    "REST API": ["RESTful", "REST APIs", "RESTful API"],
    "GraphQL": [],
    "Machine Learning": ["ML"],
    "Deep Learning": [],
    "Data Science": [],
    "Pandas": [],
    "TensorFlow": [],
    "PyTorch": [],
    "Spark": ["Apache Spark", "PySpark"],
    "Hadoop": [],
    "Tableau": [],
    "Power BI": ["PowerBI"],
    "Selenium": [],
    "JUnit": [],
    "Agile": ["Scrum"],
    "AutoCAD": [],
    "SolidWorks": [],
    "PLC": ["PLCs"],
}


def main() -> None:
    added_s = added_a = 0
    with SessionLocal() as db:
        for name, aliases in SKILLS.items():
            s = db.scalar(select(Skill).where(Skill.name == name))
            if not s:
                s = Skill(name=name)
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