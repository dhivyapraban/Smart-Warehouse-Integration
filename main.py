from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import uvicorn

from models.models import OrderRequest, TaskResponse, Task
from schema.schema import TaskStatusUpdate
from services.erp import get_item, get_item_stock
from services.loader import load_rack_map
from services.task_service import create_task as db_create_task, update_task_status
from config.database import SessionLocal, engine, Base

# Create database tables if not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Warehouse Management System (WMS)",
    description="Lightweight WMS for ERPNext + AGV / ROS2 Fleet Adapter integration",
    version="1.0.0"
)

CURRENT_TASK = None

try:
    RACK_MAP = load_rack_map()
except RuntimeError as e:
    raise Exception(f"WMS startup failed: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "status": "online",
        "message": "WMS Service is running!",
        "docs_url": "/docs"
    }


@app.get("/wms/health")
def health_check():
    return {
        "status": "WMS is running",
        "rack_map_loaded": len(RACK_MAP),
        "pending_task": CURRENT_TASK is not None
    }


@app.get("/robot/get-task")
def get_task_for_robot():
    """Endpoint polled by ROS2 Fleet Adapter on TheConstruct.ai / Robot"""
    global CURRENT_TASK

    if CURRENT_TASK is None:
        return {"status": "NO_TASK"}

    task = CURRENT_TASK
    CURRENT_TASK = None
    return task


@app.post("/robot/update-status")
def update_robot_status(update: TaskStatusUpdate, task_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Endpoint for robot to report back status (e.g., PICKUP_REACHED, MOVING_TO_DROP, COMPLETED)"""
    if task_id:
        try:
            uuid_obj = uuid.UUID(task_id)
            updated = update_task_status(db, uuid_obj, update.status)
            if updated:
                return {"status": "updated", "task_id": task_id, "new_status": update.status}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    return {"status": "received", "new_status": update.status}


@app.get("/wms/tasks")
def list_tasks(db: Session = Depends(get_db)):
    """List all tasks stored in the database"""
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(20).all()
    return [
        {
            "id": str(t.id),
            "item_code": t.item_code,
            "quantity": t.quantity,
            "pickup_location": t.pickup_location,
            "drop_location": t.drop_location,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "pickup_reached_at": t.pickup_reached_at.isoformat() if t.pickup_reached_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in tasks
    ]


@app.get("/wms/test-erp/{item_code}")
def test_erp_connection(item_code: str):
    import requests
    from config.config import ERP_URL, HEADERS
    
    url = f"{ERP_URL}/api/resource/Item/{item_code}"
    try:
        response = requests.get(url, headers=HEADERS, verify=False, timeout=5)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "url": url,
            "response_text": response.text[:500]
        }
    except Exception as e:
        return {
            "error": str(e),
            "url": url
        }


@app.get("/wms/item/{item_code}")
def fetch_item(item_code: str):
    try:
        item = get_item(item_code)
        stock = get_item_stock(item_code)

        return {
            "item": item.get("data", item),
            "stock": stock.get("data", stock)
        }

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"ERP error: {str(e)}"
        )


def resolve_item_location(item_code: str) -> dict:
    """Finds rack/bin mapping with case/format tolerance and dynamic fallback"""
    clean_code = item_code.strip()
    normalized = clean_code.upper().replace("_", "-")

    # 1. Exact match
    if clean_code in RACK_MAP:
        return RACK_MAP[clean_code]

    # 2. Normalized match (e.g. item_002 -> ITEM-002)
    for key, val in RACK_MAP.items():
        if key.upper().replace("_", "-") == normalized:
            return val

    # 3. Dynamic fallback for any custom item from ERP
    rack_num = 50 + (abs(hash(normalized)) % 30)
    bin_num = (abs(hash(normalized)) % 6) + 1
    return {
        "warehouse": "WH-01 - CIT",
        "rack": f"RACK-{rack_num}",
        "bin": f"BIN-{bin_num}"
    }


@app.get("/wms/rack-map")
def get_rack_map():
    """Get all registered rack mappings"""
    return RACK_MAP


def extract_item_and_qty(order: OrderRequest) -> tuple[str, int]:
    """Extract item_code and quantity from any Frappe webhook payload shape"""
    # 1. Direct item_code
    if order.item_code:
        return str(order.item_code), int(order.qty or order.quantity or 1)

    # 2. Frappe 'name' field
    if order.name:
        return str(order.name), int(order.qty or order.quantity or 1)

    # 3. Frappe 'items' list from Stock Entry / Sales Order
    if order.items and len(order.items) > 0:
        first = order.items[0]
        if isinstance(first, dict):
            code = first.get("item_code") or first.get("item") or first.get("name")
            qty = int(first.get("qty") or first.get("quantity") or 1)
            if code:
                return str(code), qty
        elif isinstance(first, str):
            return first, int(order.qty or order.quantity or 1)

    # 4. Nested 'doc' dictionary
    if isinstance(order.doc, dict):
        if "item_code" in order.doc:
            return str(order.doc["item_code"]), int(order.doc.get("qty", 1))
        if "name" in order.doc:
            return str(order.doc["name"]), 1
        if "items" in order.doc and isinstance(order.doc["items"], list) and len(order.doc["items"]) > 0:
            first = order.doc["items"][0]
            if isinstance(first, dict):
                return str(first.get("item_code", "ITEM-001")), int(first.get("qty", 1))

    # Default fallback if empty
    return "ITEM-001", 1


@app.post("/wms/create-task", response_model=TaskResponse)
def create_task_endpoint(order: OrderRequest, db: Session = Depends(get_db)):
    global CURRENT_TASK
    item_code, qty = extract_item_and_qty(order)

    try:
        get_item(item_code)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Item not found in ERP: {str(e)}"
        )

    location = resolve_item_location(item_code)
    pickup_loc = location.get("rack", "Dock-A")
    drop_loc = "Assembly-Line"

    # Persist in DB
    db_task = db_create_task(
        db=db,
        item_code=item_code,
        quantity=qty,
        pickup=pickup_loc,
        drop=drop_loc
    )

    task = TaskResponse(
        task_id=str(db_task.id),
        item_code=item_code,
        warehouse=location.get("warehouse", "Default-WH"),
        rack=location.get("rack", ""),
        bin=location.get("bin", ""),
        pickup=pickup_loc,
        drop=drop_loc,
        quantity=qty,
        status="CREATED"
    )

    CURRENT_TASK = task.model_dump() if hasattr(task, "model_dump") else task.dict()
    return task




if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
