import json
from datetime import date

from sqlmodel import Session, select

from course_backend.database.db import ROOT, engine, init_db
from course_backend.database.models import Contract, Placement, PracticeBase, Student, Supervisor


def seed_database() -> bool:
    """Load the supplied sample dataset only into a completely empty project DB."""
    init_db()
    with Session(engine) as session:
        models = (Student, PracticeBase, Supervisor, Contract, Placement)
        counts = [len(session.exec(select(model.id)).all()) for model in models]
        if all(counts):
            return False
        if any(counts):
            raise RuntimeError(
                "Тест деректерін автоматты қосу үшін негізгі кестелер толық бос болуы керек. "
                "Бар деректерді өшірмей тұрып, резервтік көшірме жасаңыз."
            )

        seed = json.loads((ROOT / "dist" / "seed.json").read_text(encoding="utf-8"))
        # Keep the classroom database small and predictable: 3–5 examples
        # per ORM table, in dependency order.
        session.add_all(Student(**row) for row in seed["students"][:5])
        session.add_all(PracticeBase(**row) for row in seed["bases"][:3])
        session.add_all(Supervisor(**row) for row in seed["supervisors"][:3])
        session.add_all(
            Contract(**{**row, "start_date": date.fromisoformat(row["start_date"]), "end_date": date.fromisoformat(row["end_date"])})
            for row in seed["contracts"][:3]
        )
        session.add_all(
            Placement(**{**row, "start_date": date.fromisoformat(row["start_date"]), "end_date": date.fromisoformat(row["end_date"])})
            for row in seed["placements"][:3]
        )
        session.commit()
    return True


if __name__ == "__main__":
    print("Бастапқы оқу деректері қосылды." if seed_database() else "Дерекқорда деректер бар; бастапқы жазбалар өзгертілмеді.")
