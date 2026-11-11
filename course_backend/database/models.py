from datetime import date
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Student(SQLModel, table=True):
    __tablename__ = "students"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    group_name: str
    email: str
    placements: List["Placement"] = Relationship(back_populates="student")


class PracticeBase(SQLModel, table=True):
    __tablename__ = "bases"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: str
    contact: str
    capacity: int = Field(ge=1)
    placements: List["Placement"] = Relationship(back_populates="practice_base")
    contracts: List["Contract"] = Relationship(back_populates="practice_base")


class Supervisor(SQLModel, table=True):
    __tablename__ = "supervisors"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    position: str
    email: str
    placements: List["Placement"] = Relationship(back_populates="supervisor")


class Contract(SQLModel, table=True):
    __tablename__ = "contracts"
    id: Optional[int] = Field(default=None, primary_key=True)
    number: str
    base_id: int = Field(foreign_key="bases.id")
    start_date: date
    end_date: date
    practice_base: Optional[PracticeBase] = Relationship(back_populates="contracts")
    placements: List["Placement"] = Relationship(back_populates="contract")


class Placement(SQLModel, table=True):
    __tablename__ = "placements"
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="students.id")
    base_id: int = Field(foreign_key="bases.id")
    supervisor_id: int = Field(foreign_key="supervisors.id")
    contract_id: int = Field(foreign_key="contracts.id")
    kind: str
    start_date: date
    end_date: date
    student: Optional[Student] = Relationship(back_populates="placements")
    practice_base: Optional[PracticeBase] = Relationship(back_populates="placements")
    supervisor: Optional[Supervisor] = Relationship(back_populates="placements")
    contract: Optional[Contract] = Relationship(back_populates="placements")
