from datetime import date
from typing import Optional

from pydantic import ConfigDict, Field as PydanticField
from sqlmodel import SQLModel


class PlacementCreate(SQLModel):
    student_id: int = PydanticField(gt=0)
    base_id: int = PydanticField(gt=0)
    supervisor_id: int = PydanticField(gt=0)
    contract_id: int = PydanticField(gt=0)
    kind: str = PydanticField(min_length=1, max_length=100)
    start_date: date
    end_date: date


class PlacementUpdate(SQLModel):
    student_id: Optional[int] = PydanticField(default=None, gt=0)
    base_id: Optional[int] = PydanticField(default=None, gt=0)
    supervisor_id: Optional[int] = PydanticField(default=None, gt=0)
    contract_id: Optional[int] = PydanticField(default=None, gt=0)
    kind: Optional[str] = PydanticField(default=None, min_length=1, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class PlacementRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    student_name: str
    base_id: int
    base_name: str
    supervisor_id: int
    supervisor_name: str
    contract_id: int
    kind: str
    start_date: date
    end_date: date


class LookupRead(SQLModel):
    id: int
    name: str
