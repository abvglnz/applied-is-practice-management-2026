from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from course_backend.database.db import get_session
from course_backend.database.models import Contract, Placement, PracticeBase, Student, Supervisor
from course_backend.routers.placements import router


@pytest.fixture
def client(tmp_path):
    """Each test gets its own temporary SQLite database and FastAPI client."""
    database_file = tmp_path / "test_praktika.sqlite3"
    engine = create_engine(
        f"sqlite:///{database_file}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Student(id=1, name="Әлия Нұрлан", group_name="АЖ-23-1", email="aliya@example.edu"),
                Student(id=2, name="Данияр Асқар", group_name="АЖ-23-1", email="daniyar@example.edu"),
                Student(id=3, name="Аружан Ермек", group_name="АЖ-23-2", email="aruzhan@example.edu"),
                PracticeBase(id=1, name="Qadam Digital", address="Алматы", contact="qadam@example.com", capacity=2),
                PracticeBase(id=2, name="Orda IT Lab", address="Астана", contact="orda@example.com", capacity=2),
                Supervisor(id=1, name="Айдана Сәрсенова", position="Оқытушы", email="aidana@example.edu"),
                Contract(id=1, number="TEST-001", base_id=1, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)),
                Contract(id=2, number="TEST-002", base_id=2, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)),
            ]
        )
        session.commit()
        session.add_all(
            [
                Placement(
                    id=1, student_id=1, base_id=1, supervisor_id=1, contract_id=1,
                    kind="Өндірістік практика", start_date=date(2026, 10, 5), end_date=date(2026, 10, 30),
                ),
                Placement(
                    id=2, student_id=3, base_id=1, supervisor_id=1, contract_id=1,
                    kind="Оқу практикасы", start_date=date(2026, 10, 5), end_date=date(2026, 10, 30),
                ),
            ]
        )
        session.commit()

    def get_test_session():
        with Session(engine) as session:
            yield session

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_session] = get_test_session
    with TestClient(test_app) as test_client:
        yield test_client
    test_app.dependency_overrides.clear()
    engine.dispose()


def valid_placement(**changes):
    data = {
        "student_id": 2,
        "base_id": 2,
        "supervisor_id": 1,
        "contract_id": 2,
        "kind": "Өндірістік практика",
        "start_date": "2026-11-01",
        "end_date": "2026-11-20",
    }
    return {**data, **changes}


def test_get_placements_returns_rows_and_related_names(client):
    response = client.get("/placements")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["student_name"] in {"Әлия Нұрлан", "Аружан Ермек"}
    assert response.json()[0]["base_name"] == "Qadam Digital"


def test_get_placement_filters_by_name_and_kind(client):
    response = client.get("/placements", params={"search": "Әлия", "kind": "Өндірістік практика"})

    assert response.status_code == 200
    assert [row["student_name"] for row in response.json()] == ["Әлия Нұрлан"]


def test_get_missing_placement_returns_404(client):
    response = client.get("/placements/999")

    assert response.status_code == 404


def test_post_valid_placement_returns_created_record(client):
    response = client.post("/placements", json=valid_placement())

    assert response.status_code == 201
    assert response.json()["student_name"] == "Данияр Асқар"
    assert response.json()["base_name"] == "Orda IT Lab"


def test_post_invalid_payload_returns_422(client):
    response = client.post("/placements", json=valid_placement(kind=""))

    assert response.status_code == 422


def test_post_rejects_student_date_overlap_even_at_another_base(client):
    response = client.post(
        "/placements",
        json=valid_placement(student_id=1, start_date="2026-10-10", end_date="2026-10-15"),
    )

    assert response.status_code == 409


def test_post_rejects_full_practice_base(client):
    response = client.post(
        "/placements",
        json=valid_placement(student_id=2, base_id=1, contract_id=1,
                             start_date="2026-10-10", end_date="2026-10-15"),
    )

    assert response.status_code == 409


def test_patch_changes_only_submitted_fields(client):
    response = client.patch("/placements/1", json={"kind": "Оқу практикасы"})

    assert response.status_code == 200
    assert response.json()["kind"] == "Оқу практикасы"
    assert response.json()["start_date"] == "2026-10-05"


def test_patch_missing_record_returns_404(client):
    response = client.patch("/placements/999", json={"kind": "Оқу практикасы"})

    assert response.status_code == 404


def test_delete_removes_record_and_second_read_returns_404(client):
    response = client.delete("/placements/1")

    assert response.status_code == 204
    assert client.get("/placements/1").status_code == 404
