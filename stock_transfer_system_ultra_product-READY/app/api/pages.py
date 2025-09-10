from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from datetime import datetime
import pandas as pd
from sqlalchemy import inspect
from app.api.deps import get_db, current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def t(lang, key):
    en = {
        "Dashboard":"Dashboard","Stores":"Stores","SKUs":"SKUs","Sales Records":"Sales Records",
        "Welcome":"Welcome","WelcomeBody":"Delightful stock transfer planning for every client."
    }
    ur = {
        "Dashboard":"ڈیش بورڈ","Stores":"اسٹورز","SKUs":"اشیاء","Sales Records":"سیلز ریکارڈز",
        "Welcome":"خوش آمدید","WelcomeBody":"ہر کلائنٹ کے لیے آسان اور شاندار اسٹاک ٹرانسفر پلاننگ۔"
    }
    d = ur if lang=="ur" else en
    return d.get(key, key)

@router.get("/", response_class=HTMLResponse)
def home(request: Request, lang: str = "en", db: Session = get_db().__next__()):
    user = current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=302)

    engine = db.get_bind(); insp = inspect(engine)
    def exists(name): 
        try: return insp.has_table(name)
        except: return False
    stores_df = pd.read_sql_table("stores", con=engine) if exists("stores") else pd.DataFrame()
    items_df  = pd.read_sql_table("items", con=engine) if exists("items") else pd.DataFrame()
    sales_df  = pd.read_sql_table("sales", con=engine) if exists("sales") else pd.DataFrame()

    stats = {"stores": len(stores_df[stores_df.get("org_id",0)==user.org_id]) if not stores_df.empty else 0,
             "skus": items_df[items_df.get("org_id",0)==user.org_id]["sku"].nunique() if not items_df.empty else 0,
             "records": len(sales_df[sales_df.get("org_id",0)==user.org_id]) if not sales_df.empty else 0}

    return templates.TemplateResponse("dashboard.html", {"request": request, "year": datetime.now().year,
        "stats": stats, "lookback": 7, "lang": lang, "t": t})
