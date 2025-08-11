from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..deps import get_db
from .. import schemas

router = APIRouter(prefix="/schedules", tags=["schedules"])

@router.post("/prompts/{prompt_id}")
def create_schedule(prompt_id: str, payload: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    db.execute(text("""
        INSERT INTO schedules (id, tenant_id, prompt_id, cadence, timezone, run_at)
        VALUES (gen_random_uuid(), current_setting('app.tenant_id', true)::uuid, :pid, :cad, :tz, :rt::time with time zone)
    """), {"pid": prompt_id, "cad": payload.cadence, "tz": payload.timezone, "rt": payload.run_at})
    db.commit(); return {"ok": True}

@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM schedules WHERE id = :id"), {"id": schedule_id})
    db.commit(); return {"ok": True}
