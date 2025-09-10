from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.api import auth as auth_routes, pages as pages_routes, upload as upload_routes, rules as rules_routes, plan as plan_routes, approvals as approvals_routes, admin as admin_routes
from app.api.auth import seed_admin

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

Base.metadata.create_all(bind=engine)
db = SessionLocal(); seed_admin(db); db.close()

app.include_router(auth_routes.router)
app.include_router(pages_routes.router)
app.include_router(upload_routes.router)
app.include_router(rules_routes.router)
app.include_router(plan_routes.router)
app.include_router(approvals_routes.router)
app.include_router(admin_routes.router)

@app.get("/health")
def health(): return {"ok": True}
