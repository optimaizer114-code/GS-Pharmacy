"""
صيدلية الحلول العالمية — الخادم الرئيسي
FastAPI + PostgreSQL
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from core.database import init_db
from routers import auth, products, sales, purchases, customers, companies, employees, expenses, reports, settings_router, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Pharmacy System...")
    init_db()
    print("✅ Database ready")
    yield
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title="صيدلية الحلول العالمية API",
    description="نظام إدارة الصيدلية المتكامل",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── CORS ─────────────────────────────────────────────────
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static files (uploads) ────────────────────────────────
os.makedirs("/app/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="/app/uploads"), name="uploads")

# ─── Routers ──────────────────────────────────────────────
app.include_router(auth.router,             prefix="/api/auth",       tags=["المصادقة"])
app.include_router(users.router,            prefix="/api/users",      tags=["المستخدمون"])
app.include_router(products.router,         prefix="/api/products",   tags=["المنتجات"])
app.include_router(sales.router,            prefix="/api/sales",      tags=["المبيعات"])
app.include_router(purchases.router,        prefix="/api/purchases",  tags=["المشتريات"])
app.include_router(customers.router,        prefix="/api/customers",  tags=["العملاء"])
app.include_router(companies.router,        prefix="/api/companies",  tags=["الشركات"])
app.include_router(employees.router,        prefix="/api/employees",  tags=["الموظفون"])
app.include_router(expenses.router,         prefix="/api/expenses",   tags=["المصروفات"])
app.include_router(reports.router,          prefix="/api/reports",    tags=["التقارير"])
app.include_router(settings_router.router,  prefix="/api/settings",   tags=["الإعدادات"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "صيدلية الحلول العالمية تعمل بنجاح ✅"}
