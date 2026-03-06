"""الموظفون"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from pydantic import BaseModel
from core.database import get_db
from core.security import get_current_user, require_roles
from models.models import Employee, EmployeeStatus, User, UserRole

router = APIRouter()

class EmployeeCreate(BaseModel):
    name: str
    role: Optional[str] = None
    phone: Optional[str] = None
    hire_date: Optional[date] = None
    base_salary: float = 0
    housing_allowance: float = 0
    transport_allowance: float = 0
    other_allowances: float = 0
    nationality: Optional[str] = None
    status: EmployeeStatus = EmployeeStatus.active
    notes: Optional[str] = None

def emp_dict(e):
    total = e.base_salary + e.housing_allowance + e.transport_allowance + e.other_allowances
    return {"id": e.id, "name": e.name, "role": e.role, "phone": e.phone,
            "hire_date": str(e.hire_date) if e.hire_date else None,
            "base_salary": e.base_salary, "housing_allowance": e.housing_allowance,
            "transport_allowance": e.transport_allowance, "other_allowances": e.other_allowances,
            "total_salary": total, "nationality": e.nationality, "status": e.status}

@router.get("/")
async def get_employees(db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    return [emp_dict(e) for e in db.query(Employee).all()]

@router.post("/", status_code=201)
async def create_employee(data: EmployeeCreate, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    e = Employee(**data.dict()); db.add(e); db.commit(); db.refresh(e); return emp_dict(e)

@router.put("/{eid}")
async def update_employee(eid: int, data: EmployeeCreate, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    e = db.query(Employee).filter(Employee.id == eid).first()
    if not e: raise HTTPException(404, "الموظف غير موجود")
    for k, v in data.dict(exclude_unset=True).items(): setattr(e, k, v)
    db.commit(); return emp_dict(e)

@router.delete("/{eid}")
async def delete_employee(eid: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))):
    e = db.query(Employee).filter(Employee.id == eid).first()
    if not e: raise HTTPException(404, "غير موجود")
    db.delete(e); db.commit(); return {"message": "تم الحذف"}
