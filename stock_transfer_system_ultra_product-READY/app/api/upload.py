from fastapi import APIRouter, Request, UploadFile, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
import io, pandas as pd

from app.api.deps import get_db, current_user, require_role
from app.models.inventory import Sale, Stock, Item, Store

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(
    request: Request,
    user=Depends(require_role(["Admin", "Planner"]))
):
    """
    ✅ Render upload page for Excel or CSV uploads.
    """
    return templates.TemplateResponse("upload.html", {"request": request, "year": 2025})


# ========================================================
# ✅ EXCEL UPLOAD ROUTE (engine fix + UPSERT logic)
# ========================================================

@router.post("/upload/excel")
async def upload_excel(
    request: Request,
    excel: UploadFile = None,
    db: Session = Depends(get_db),
    user=Depends(require_role(["Admin", "Planner"]))
):
    """
    ✅ Handles Excel uploads for 3 sheets: Stores, Items, Sales.
    ✅ Fixes:
        1. Added engine="openpyxl" for Excel parsing.
        2. Added UPSERT logic to avoid duplicate key errors.
    """

    if not excel:
        return RedirectResponse("/upload", status_code=302)

    try:
        excel_data = await excel.read()
        xl_file = pd.ExcelFile(io.BytesIO(excel_data), engine="openpyxl")

        # --------------- STORES SHEET ---------------
        if "Stores" in xl_file.sheet_names:
            df = pd.read_excel(xl_file, sheet_name="Stores", engine="openpyxl")
            for _, r in df.iterrows():
                existing = db.query(Store).filter_by(
                    org_id=user.org_id, store_id=str(r["store_id"])
                ).first()

                if not existing:
                    db.add(Store(
                        org_id=user.org_id,
                        store_id=str(r["store_id"]),
                        store_name=str(r["store_name"]),
                        priority=int(r.get("priority", 1))
                    ))
                else:
                    existing.store_name = str(r["store_name"])
                    existing.priority = int(r.get("priority", 1))

        # --------------- ITEMS SHEET ---------------
        if "Items" in xl_file.sheet_names:
            df = pd.read_excel(xl_file, sheet_name="Items", engine="openpyxl")
            for _, r in df.iterrows():
                existing = db.query(Item).filter_by(
                    org_id=user.org_id, item_id=str(r["item_id"])
                ).first()

                if not existing:
                    db.add(Item(
                        org_id=user.org_id,
                        item_id=str(r["item_id"]),
                        item_name=str(r["item_name"]),
                        price=float(r.get("price", 0.0))
                    ))
                else:
                    existing.item_name = str(r["item_name"])
                    existing.price = float(r.get("price", 0.0))

        # --------------- SALES SHEET ---------------
        if "Sales" in xl_file.sheet_names:
            df = pd.read_excel(xl_file, sheet_name="Sales", engine="openpyxl")

            if "date" not in df.columns:
                raise ValueError("Missing required 'date' column in Sales sheet")

            for _, r in df.iterrows():
                db.add(Sale(
                    org_id=user.org_id,
                    store_id=str(r["store_id"]),
                    item_id=str(r["item_id"]),
                    quantity=int(r["quantity"]),
                    date=pd.to_datetime(r["date"]).date()
                ))

        db.commit()
        return RedirectResponse("/upload", status_code=302)

    except Exception as e:
        db.rollback()
        print(f"Excel Upload Error: {e}")
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "year": 2025,
            "error": f"Excel upload failed: {str(e)}"
        })


# ========================================================
# ✅ CSV UPLOAD ROUTE (UPSERT logic + validation)
# ========================================================

@router.post("/upload/csv")
async def upload_csv(
    request: Request,
    csv: UploadFile = None,
    db: Session = Depends(get_db),
    user=Depends(require_role(["Admin", "Planner"]))
):
    """
    ✅ Handles CSV uploads (Sales, Stores, Items).
    ✅ Fixes:
        1. UPSERT logic (no duplicate key crash)
        2. Validations for missing columns
    """

    if not csv:
        return RedirectResponse("/upload", status_code=302)

    try:
        content = await csv.read()
        decoded = content.decode("utf-8")
        df = pd.read_csv(io.StringIO(decoded))
        cols = set(df.columns)

        # --------------- STORES CSV ---------------
        if {"store_id", "store_name"}.issubset(cols):
            for _, r in df.iterrows():
                existing = db.query(Store).filter_by(
                    org_id=user.org_id, store_id=str(r["store_id"])
                ).first()

                if not existing:
                    db.add(Store(
                        org_id=user.org_id,
                        store_id=str(r["store_id"]),
                        store_name=str(r["store_name"]),
                        priority=int(r.get("priority", 1))
                    ))
                else:
                    existing.store_name = str(r["store_name"])
                    existing.priority = int(r.get("priority", 1))

        # --------------- ITEMS CSV ---------------
        elif {"item_id", "item_name"}.issubset(cols):
            for _, r in df.iterrows():
                existing = db.query(Item).filter_by(
                    org_id=user.org_id, item_id=str(r["item_id"])
                ).first()

                if not existing:
                    db.add(Item(
                        org_id=user.org_id,
                        item_id=str(r["item_id"]),
                        item_name=str(r["item_name"]),
                        price=float(r.get("price", 0.0))
                    ))
                else:
                    existing.item_name = str(r["item_name"])
                    existing.price = float(r.get("price", 0.0))

        # --------------- SALES CSV ---------------
        elif {"store_id", "item_id", "quantity", "date"}.issubset(cols):
            for _, r in df.iterrows():
                db.add(Sale(
                    org_id=user.org_id,
                    store_id=str(r["store_id"]),
                    item_id=str(r["item_id"]),
                    quantity=int(r["quantity"]),
                    date=pd.to_datetime(r["date"]).date()
                ))

        else:
            raise ValueError("Unsupported CSV format or missing required columns")

        db.commit()
        return RedirectResponse("/upload", status_code=302)

    except Exception as e:
        db.rollback()
        print(f"CSV Upload Error: {e}")
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "year": 2025,
            "error": f"CSV upload failed: {str(e)}"
        })
