from fastapi import FastAPI, HTTPException
from models.models import OrderRequest, TaskResponse
from services.erp import get_item, get_item_stock
from services.loader import load_rack_map
import uuid

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


@app.get("/")
def root():
    return {
        "service is runningggggg!!!"
    }


@app.get("/wms/health")
def health_check():
    return {
        "status": "WMS is running",
        "rack_map_loaded": len(RACK_MAP)
    }


@app.get("/robot/get-task")
def get_task_for_robot():
    global CURRENT_TASK

    if CURRENT_TASK is None:
        return {}

    task = CURRENT_TASK
    CURRENT_TASK = None   
    return task

@app.get("/wms/test-erp/{item_code}")
def test_erp_connection(item_code: str):
    import requests
    from config.config import ERP_URL, HEADERS
    
    url = f"{ERP_URL}/api/resource/Item/{item_code}"
    try:
        response = requests.get(url, headers=HEADERS, verify=False)
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
            "item": item["data"],
            "stock": stock["data"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"ERP error: {str(e)}"
        )




@app.post("/wms/create-task", response_model=TaskResponse)
def create_task(order: OrderRequest):
    global CURRENT_TASK
    try:
        get_item(order.item_code)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Item not found in ERP: {str(e)}"
        )

    if order.item_code not in RACK_MAP:
        raise HTTPException(
            status_code=400,
            detail="Rack/Bin mapping not found in WMS"
        )

    location = RACK_MAP[order.item_code]

    task_id = str(uuid.uuid4())

    task = TaskResponse(
        task_id=task_id,
        item_code=order.item_code,
        warehouse=location["warehouse"],
        rack=location["rack"],
        bin=location["bin"],
        pickup="Dock-A",   
        drop="Assembly-Line"
    )

    CURRENT_TASK = task.dict()
    return task