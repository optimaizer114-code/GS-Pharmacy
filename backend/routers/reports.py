"""التقارير والإحصائيات"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from typing import Optional
from datetime import date, timedelta

from core.database import get_db
from core.security import get_current_user, require_roles
from models.models import (
    Sale, SaleItem, Product, Customer, Purchase,
    Employee, Expense, User, UserRole
)

router = APIRouter()


@router.get("/dashboard")
async def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    month_start = today.replace(day=1)

    today_sales_q = db.query(func.sum(Sale.total), func.count(Sale.id)).filter(
        func.date(Sale.sale_date) == today
    ).first()
    month_sales_q = db.query(func.sum(Sale.total)).filter(
        func.date(Sale.sale_date) >= month_start
    ).first()

    low_stock = db.query(func.count(Product.id)).filter(
        Product.is_active == True,
        Product.quantity <= Product.min_quantity
    ).scalar()

    expiring_30 = db.query(func.count(Product.id)).filter(
        Product.is_active == True,
        Product.expiry_date != None,
        Product.expiry_date <= today + timedelta(days=30)
    ).scalar()

    return {
        "today_sales_total": today_sales_q[0] or 0,
        "today_sales_count": today_sales_q[1] or 0,
        "month_sales_total": month_sales_q[0] or 0,
        "total_products": db.query(func.count(Product.id)).filter(Product.is_active == True).scalar(),
        "low_stock_count": low_stock,
        "expiring_30_days": expiring_30,
        "total_customers": db.query(func.count(Customer.id)).scalar(),
        "total_employees": db.query(func.count(Employee.id)).scalar(),
    }


@router.get("/sales/monthly")
async def sales_monthly_report(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sales = db.query(Sale).filter(
        extract("year", Sale.sale_date) == year,
        extract("month", Sale.sale_date) == month
    ).all()

    by_day = {}
    by_payment = {}
    for s in sales:
        d = s.sale_date.date().isoformat()
        by_day[d] = by_day.get(d, 0) + s.total
        pm = s.payment_method
        by_payment[pm] = by_payment.get(pm, 0) + s.total

    total = sum(s.total for s in sales)
    return {
        "year": year, "month": month,
        "total": total,
        "count": len(sales),
        "average": total / len(sales) if sales else 0,
        "max_invoice": max((s.total for s in sales), default=0),
        "by_day": by_day,
        "by_payment": by_payment,
        "sales": [
            {
                "id": s.id, "invoice_number": s.invoice_number,
                "date": s.sale_date.isoformat(),
                "customer": s.customer.name if s.customer else "عميل عام",
                "total": s.total, "payment_method": s.payment_method,
                "items_count": len(s.items),
            }
            for s in sorted(sales, key=lambda x: x.sale_date)
        ]
    }


@router.get("/sales/yearly")
async def sales_yearly_report(
    year: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    MONTHS = ['يناير','فبراير','مارس','أبريل','مايو','يونيو',
              'يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
    rows = []
    grand_total = 0
    for m in range(1, 13):
        result = db.query(func.sum(Sale.total), func.count(Sale.id)).filter(
            extract("year", Sale.sale_date) == year,
            extract("month", Sale.sale_date) == m
        ).first()
        total = result[0] or 0
        count = result[1] or 0
        grand_total += total
        rows.append({"month": m, "month_name": MONTHS[m-1], "total": total, "count": count})

    return {"year": year, "grand_total": grand_total, "months": rows}


@router.get("/products/{product_id}/sales")
async def product_sales_report(
    product_id: int,
    year: int = Query(...),
    month: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return {"error": "المنتج غير موجود"}

    query = db.query(SaleItem).join(Sale).filter(
        SaleItem.product_id == product_id,
        extract("year", Sale.sale_date) == year,
    )
    if month:
        query = query.filter(extract("month", Sale.sale_date) == month)

    items = query.all()
    total_qty = sum(i.quantity for i in items)
    total_rev = sum(i.total_price for i in items)
    profit = total_rev - (product.cost_price * total_qty)

    return {
        "product": {"id": product.id, "name": product.name, "category": product.category},
        "period": {"year": year, "month": month},
        "total_quantity": total_qty,
        "total_revenue": total_rev,
        "total_cost": product.cost_price * total_qty,
        "gross_profit": profit,
        "profit_margin": (profit / total_rev * 100) if total_rev else 0,
        "transactions": [
            {
                "invoice": i.sale.invoice_number,
                "date": i.sale.sale_date.isoformat(),
                "customer": i.sale.customer.name if i.sale.customer else "عميل عام",
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "total": i.total_price,
            }
            for i in sorted(items, key=lambda x: x.sale.sale_date)
        ]
    }


@router.get("/customers/purchases")
async def customer_purchases_report(
    year: int = Query(...),
    month: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Sale).filter(extract("year", Sale.sale_date) == year)
    if month:
        query = query.filter(extract("month", Sale.sale_date) == month)
    if customer_id:
        query = query.filter(Sale.customer_id == customer_id)

    sales = query.all()
    grouped = {}
    for s in sales:
        cid = s.customer_id or 0
        if cid not in grouped:
            grouped[cid] = {
                "customer_id": cid,
                "customer_name": s.customer.name if s.customer else "عميل عام",
                "count": 0, "total": 0, "products": {}
            }
        grouped[cid]["count"] += 1
        grouped[cid]["total"] += s.total
        for item in s.items:
            pname = item.product.name if item.product else "غير معروف"
            grouped[cid]["products"][pname] = grouped[cid]["products"].get(pname, 0) + item.quantity

    return {
        "year": year, "month": month,
        "customers": sorted(grouped.values(), key=lambda x: x["total"], reverse=True)
    }


@router.get("/profit/monthly")
async def profit_monthly(
    year: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))
):
    MONTHS = ['يناير','فبراير','مارس','أبريل','مايو','يونيو',
              'يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
    total_salaries = sum(
        e.base_salary + e.housing_allowance + e.transport_allowance + e.other_allowances
        for e in db.query(Employee).all()
    )
    rows = []
    for m in range(1, 13):
        rev = db.query(func.sum(Sale.total)).filter(
            extract("year", Sale.sale_date) == year,
            extract("month", Sale.sale_date) == m
        ).scalar() or 0
        pur = db.query(func.sum(Purchase.total)).filter(
            extract("year", Purchase.purchase_date) == year,
            extract("month", Purchase.purchase_date) == m
        ).scalar() or 0
        exp = db.query(func.sum(Expense.amount)).filter(
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == m
        ).scalar() or 0
        cost = pur + exp + total_salaries
        rows.append({
            "month": m, "month_name": MONTHS[m-1],
            "revenue": rev, "purchases": pur,
            "expenses": exp, "salaries": total_salaries,
            "total_cost": cost, "profit": rev - cost,
            "margin": round((rev-cost)/rev*100, 1) if rev else 0
        })

    grand_rev = sum(r["revenue"] for r in rows)
    grand_cost = sum(r["total_cost"] for r in rows)
    return {
        "year": year, "months": rows,
        "grand_revenue": grand_rev,
        "grand_cost": grand_cost,
        "grand_profit": grand_rev - grand_cost,
        "grand_margin": round((grand_rev-grand_cost)/grand_rev*100, 1) if grand_rev else 0
    }


@router.get("/expenses/monthly")
async def expenses_monthly(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin))
):
    expenses = db.query(Expense).filter(
        extract("year", Expense.expense_date) == year,
        extract("month", Expense.expense_date) == month
    ).all()
    by_cat = {}
    for e in expenses:
        by_cat[e.category] = by_cat.get(e.category, 0) + e.amount
    salaries = sum(
        e.base_salary + e.housing_allowance + e.transport_allowance + e.other_allowances
        for e in db.query(Employee).all()
    )
    return {
        "expenses": [{"id": e.id, "date": str(e.expense_date), "category": e.category,
                      "description": e.description, "amount": e.amount, "payment": e.payment_method}
                     for e in expenses],
        "by_category": by_cat,
        "total_expenses": sum(e.amount for e in expenses),
        "total_salaries": salaries,
        "grand_total": sum(e.amount for e in expenses) + salaries,
    }


@router.get("/inventory/summary")
async def inventory_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    products = db.query(Product).filter(Product.is_active == True).all()
    today = date.today()
    by_cat = {}
    for p in products:
        c = p.category
        if c not in by_cat:
            by_cat[c] = {"count": 0, "total_value_cost": 0, "total_value_selling": 0}
        by_cat[c]["count"] += 1
        by_cat[c]["total_value_cost"] += p.cost_price * p.quantity
        by_cat[c]["total_value_selling"] += p.selling_price * p.quantity

    return {
        "total_products": len(products),
        "total_value_cost": sum(p.cost_price * p.quantity for p in products),
        "total_value_selling": sum(p.selling_price * p.quantity for p in products),
        "low_stock": [{"id": p.id, "name": p.name, "quantity": p.quantity, "min": p.min_quantity}
                      for p in products if p.quantity <= p.min_quantity],
        "expired": [{"id": p.id, "name": p.name, "expiry": str(p.expiry_date)}
                    for p in products if p.expiry_date and p.expiry_date < today],
        "by_category": by_cat,
    }
