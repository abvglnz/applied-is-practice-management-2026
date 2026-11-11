from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from course_backend.database.db import get_session
from course_backend.database.models import Contract, Placement, PracticeBase, Student, Supervisor
from course_backend.database.schemas import LookupRead, PlacementCreate, PlacementRead, PlacementUpdate

router = APIRouter(tags=["Практикаға бөлу"])


def to_read(item: Placement) -> PlacementRead:
    return PlacementRead(
        id=item.id,
        student_id=item.student_id,
        student_name=item.student.name if item.student else "",
        base_id=item.base_id,
        base_name=item.practice_base.name if item.practice_base else "",
        supervisor_id=item.supervisor_id,
        supervisor_name=item.supervisor.name if item.supervisor else "",
        contract_id=item.contract_id,
        kind=item.kind,
        start_date=item.start_date,
        end_date=item.end_date,
    )


def validate_rules(session: Session, item: Placement, exclude_id: Optional[int] = None) -> None:
    if item.start_date > item.end_date:
        raise HTTPException(status_code=422, detail="Басталу күні аяқталу күнінен кеш болмауы керек.")
    contract = session.get(Contract, item.contract_id)
    if not contract or contract.base_id != item.base_id:
        raise HTTPException(status_code=422, detail="Келісімшарт таңдалған практика базасына тиесілі емес.")
    if item.start_date < contract.start_date or item.end_date > contract.end_date:
        raise HTTPException(status_code=422, detail="Практика мерзімі келісімшарт шегінен шықты.")
    if not session.get(Student, item.student_id) or not session.get(PracticeBase, item.base_id) or not session.get(Supervisor, item.supervisor_id):
        raise HTTPException(status_code=422, detail="Студентті, базаны немесе жетекшіні тексеріңіз.")

    student_overlap = select(Placement).where(
        Placement.student_id == item.student_id,
        Placement.start_date <= item.end_date,
        Placement.end_date >= item.start_date,
    )
    if exclude_id is not None:
        student_overlap = student_overlap.where(Placement.id != exclude_id)
    if session.exec(student_overlap).first():
        raise HTTPException(status_code=409, detail="Студентте осы мерзімде басқа практика бар.")

    overlap_query = select(Placement).where(
        Placement.base_id == item.base_id,
        Placement.start_date <= item.end_date,
        Placement.end_date >= item.start_date,
    )
    if exclude_id is not None:
        overlap_query = overlap_query.where(Placement.id != exclude_id)
    intersecting = session.exec(overlap_query).all()
    base = session.get(PracticeBase, item.base_id)
    events = [(item.start_date, 1), (item.end_date, -1)]
    for other in intersecting:
        events.extend(
            [(max(other.start_date, item.start_date), 1), (min(other.end_date, item.end_date), -1)]
        )
    occupancy = 0
    for _day, change in sorted(events, key=lambda event: (event[0], -event[1])):
        occupancy += change
        if occupancy > base.capacity:
            raise HTTPException(status_code=409, detail="Практика базасындағы орын саны жеткіліксіз.")


@router.get("/students", response_model=List[LookupRead])
def get_students(session: Session = Depends(get_session)):
    return [LookupRead(id=row.id, name=f"{row.name} · {row.group_name}") for row in session.exec(select(Student).order_by(Student.name)).all()]


@router.get("/bases", response_model=List[LookupRead])
def get_bases(session: Session = Depends(get_session)):
    return [LookupRead(id=row.id, name=row.name) for row in session.exec(select(PracticeBase).order_by(PracticeBase.name)).all()]


@router.get("/supervisors", response_model=List[LookupRead])
def get_supervisors(session: Session = Depends(get_session)):
    return [LookupRead(id=row.id, name=row.name) for row in session.exec(select(Supervisor).order_by(Supervisor.name)).all()]


@router.get("/contracts", response_model=List[LookupRead])
def get_contracts(session: Session = Depends(get_session)):
    return [LookupRead(id=row.id, name=f"{row.number} · {row.practice_base.name}") for row in session.exec(select(Contract).order_by(Contract.number)).all()]


@router.get("/placements", response_model=List[PlacementRead])
def list_placements(
    search: Optional[str] = Query(default=None, max_length=100),
    kind: Optional[str] = Query(default=None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    session: Session = Depends(get_session),
):
    statement = select(Placement).join(Student).join(PracticeBase)
    if search and search.strip():
        query = f"%{search.strip()}%"
        statement = statement.where(or_(Student.name.ilike(query), Student.group_name.ilike(query), PracticeBase.name.ilike(query)))
    if kind:
        statement = statement.where(Placement.kind == kind)
    if date_from:
        statement = statement.where(Placement.end_date >= date_from)
    if date_to:
        statement = statement.where(Placement.start_date <= date_to)
    rows = session.exec(statement.order_by(Placement.start_date.desc(), Placement.id.desc())).all()
    return [to_read(row) for row in rows]


@router.get("/placements/{placement_id}", response_model=PlacementRead)
def get_placement(placement_id: int, session: Session = Depends(get_session)):
    item = session.get(Placement, placement_id)
    if not item:
        raise HTTPException(status_code=404, detail="Практика жазбасы табылмады.")
    return to_read(item)


@router.post("/placements", response_model=PlacementRead, status_code=status.HTTP_201_CREATED)
def create_placement(data: PlacementCreate, session: Session = Depends(get_session)):
    item = Placement.model_validate(data)
    validate_rules(session, item)
    session.add(item)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Байланысқан жазбалар дұрыс емес немесе қайталанды.") from exc
    session.refresh(item)
    return to_read(item)


@router.patch("/placements/{placement_id}", response_model=PlacementRead)
def update_placement(placement_id: int, data: PlacementUpdate, session: Session = Depends(get_session)):
    item = session.get(Placement, placement_id)
    if not item:
        raise HTTPException(status_code=404, detail="Практика жазбасы табылмады.")
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Өзгертілетін кемінде бір өріс жіберіңіз.")
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Өрістерді бос мәнмен жаңартуға болмайды.")
    item.sqlmodel_update(changes)
    validate_rules(session, item, exclude_id=placement_id)
    try:
        session.add(item)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Байланысқан жазбалар дұрыс емес.") from exc
    session.refresh(item)
    return to_read(item)


@router.delete("/placements/{placement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_placement(placement_id: int, session: Session = Depends(get_session)):
    item = session.get(Placement, placement_id)
    if not item:
        raise HTTPException(status_code=404, detail="Практика жазбасы табылмады.")
    try:
        session.delete(item)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Алдымен осы практикаға байланысқан күнделік, есеп немесе баға жазбаларын тексеріңіз.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
