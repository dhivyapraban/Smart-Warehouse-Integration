from sqlalchemy.orm import Session
from models.models import Task

def create_task(
    db: Session,
    item_code: str,
    quantity: int,
    pickup: str,
    drop: str
):
    task = Task(
        item_code=item_code,
        quantity=quantity,
        pickup_location=pickup,
        drop_location=drop,
        status="CREATED"
    )

    db.add(task)
    db.commit()        
    db.refresh(task)  

    return task


def update_task_status(
    db: Session,
    task_id,
    status: str
):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        return None

    task.status = status

    if status == "PICKUP_REACHED":
        from sqlalchemy.sql import func
        task.pickup_reached_at = func.now()

    elif status == "MOVING_TO_DROP":
        task.drop_started_at = func.now()

    elif status == "COMPLETED":
        task.completed_at = func.now()

    db.commit()       
    db.refresh(task)

    return task
    