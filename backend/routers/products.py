"""إدارة المنتجات والمخزون"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from datetime import date, timedelta
from pydantic import BaseModel

from core.database import get_db
from core.security import get_current_user, require_roles
from models.models import Product, ProductCategory, User, UserRole

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────
class ProductCreate(BaseModel):
    code: Optional[str] = None
    name: str
    name_en: Optional[str] = None
    category: ProductCategory
    description: Optional[str] = None
    quantity: int = 0
    min_quantity: int = 10
    unit: str = "علبة"
    location: Optional[str] = None
    cost_price: float = 0
    selling_price: float
    ingredient: Optional[str] = None
    dosage: Optional[str] = None
    form: Optional[str] = None
    med_category: Optional[str] = None
    requires_prescription: bool = False
    brand: Optional[str] = None
    cosmetic_category: Optional[str] = None
    skin_type: Optional[str] = None
    device_type: Optional[str] = None
    manufacturer: Optional[str] = None
    warranty: Optional[str] = None
    expiry_date: Optional[date] = None
    company_id: Optional[int] = None

class ProductUpdate(ProductCreate):
    pass

class StockAdjust(BaseModel):
    quantity: int
    reason: str


# ─── Helpers ──────────────────────────────────────────────
def product_to_dict(p: Product) -> dict:
    return {
        "id": p.id, "code": p.code, "name": p.name, "name_en": p.name_en,
        "category": p.category, "description": p.description,
        "quantity": p.quantity, "min_quantity": p.min_quantity,
        "unit": p.unit, "location": p.location,
        "cost_price": p.cost_price, "selling_price": p.selling_price,
        "ingredient": p.ingredient, "dosage": p.dosage, "form": p.form,
        "med_category": p.med_category, "requires_prescription": p.requires_prescription,
        "brand": p.brand, "cosmetic_category": p.cosmetic_category, "skin_type": p.skin_type,
        "device_type": p.device_type, "manufacturer": p.manufacturer, "warranty": p.warranty,
        "expiry_date": str(p.expiry_date) if p.expiry_date else None,
        "company_id": p.company_id,
        "company_name": p.company.name if p.company else None,
        "is_low_stock": p.quantity <= p.min_quantity,
        "days_to_expiry": (p.expiry_date - date.today()).days if p.expiry_date else None,
    }


# ─── Endpoints ────────────────────────────────────────────
@router.get("/")
async def get_products(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    low_stock: bool = Query(False),
    expiring_days: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Product).filter(Product.is_active == True)

    if search:
        query = query.filter(or_(
            Product.name.ilike(f"%{search}%"),
            Product.code.ilike(f"%{search}%"),
            Product.ingredient.ilike(f"%{search}%"),
            Product.brand.ilike(f"%{search}%"),
        ))
    if category:
        query = query.filter(Product.category == category)
    if low_stock:
        query = query.filter(Product.quantity <= Product.min_quantity)
    if expiring_days:
        threshold = date.today() + timedelta(days=expiring_days)
        query = query.filter(
            and_(Product.expiry_date != None, Product.expiry_date <= threshold)
        )
    if company_id:
        query = query.filter(Product.company_id == company_id)

    total = query.count()
    products = query.offset((page-1)*limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [product_to_dict(p) for p in products]
    }


@router.get("/low-stock")
async def get_low_stock(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity <= Product.min_quantity
    ).all()
    return [product_to_dict(p) for p in items]


@router.get("/expiring")
async def get_expiring(
    days: int = Query(90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    threshold = date.today() + timedelta(days=days)
    items = db.query(Product).filter(
        Product.is_active == True,
        Product.expiry_date != None,
        Product.expiry_date <= threshold
    ).order_by(Product.expiry_date).all()
    return [product_to_dict(p) for p in items]


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    return product_to_dict(p)


@router.post("/", status_code=201)
async def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.warehouse))
):
    # Auto-generate code if not provided
    if not data.code:
        prefix = {"medicine": "MED", "cosmetic": "COS", "device": "DEV"}.get(data.category, "PRD")
        count = db.query(Product).filter(Product.category == data.category).count()
        data.code = f"{prefix}-{count+1:04d}"

    p = Product(**data.dict())
    db.add(p)
    db.commit()
    db.refresh(p)
    return product_to_dict(p)


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.warehouse))
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    for key, value in data.dict(exclude_unset=True).items():
        setattr(p, key, value)
    db.commit()
    db.refresh(p)
    return product_to_dict(p)


@router.patch("/{product_id}/stock")
async def adjust_stock(
    product_id: int,
    adj: StockAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.warehouse))
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    p.quantity += adj.quantity
    if p.quantity < 0:
        raise HTTPException(status_code=400, detail="الكمية لا يمكن أن تكون سالبة")
    db.commit()
    return {"id": p.id, "name": p.name, "new_quantity": p.quantity}


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    p.is_active = False   # Soft delete
    db.commit()
    return {"message": "تم حذف المنتج"}
