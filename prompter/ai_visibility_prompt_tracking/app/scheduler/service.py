from __future__ import annotations
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
from apscheduler.schedulers.blocking import BlockingScheduler

from app.db import SessionLocal
from app.workers.queue import rq_default

def _combine_local(d: datetime, t: time, tz: ZoneInfo) -> datetime:
    return datetime(d.year,d.month,d.day,t.hour,t.minute,getattr(t,"second",0), tzinfo=tz)

def _increment_local(dt_local: datetime, cadence: str) -> datetime:
    if cadence == "daily": return dt_local + timedelta(days=1)
    if cadence == "weekly": return dt_local + timedelta(weeks=1)
    if cadence == "monthly": return dt_local + relativedelta(months=+1)
    raise ValueError(f"Unknown cadence: {cadence}")

def _initial_next_run_at(cadence: str, tzname: str, run_at: time, now_utc: datetime) -> datetime:
    tz = ZoneInfo(tzname)
    now_local = now_utc.astimezone(tz)
    target_local = _combine_local(now_local, run_at, tz)
    if target_local <= now_local:
        target_local = _increment_local(target_local, cadence)
    return target_local.astimezone(timezone.utc)

def _advance_past(cadence: str, tzname: str, next_run_at_utc: datetime, now_utc: datetime) -> datetime:
    tz = ZoneInfo(tzname)
    cur_local = next_run_at_utc.astimezone(tz)
    now_local = now_utc.astimezone(tz)
    while cur_local <= now_local:
        cur_local = _increment_local(cur_local, cadence)
    return cur_local.astimezone(timezone.utc)

def _init_missing_next_run_at(db: Session, tenant_id: str, now_utc: datetime) -> None:
    db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
    rows = db.execute(text("SELECT id, cadence, timezone, run_at FROM schedules WHERE next_run_at IS NULL")).mappings().all()
    for r in rows:
        nr = _initial_next_run_at(r["cadence"], r["timezone"], r["run_at"], now_utc)
        db.execute(text("UPDATE schedules SET next_run_at = :nr WHERE id = :id"), {"nr": nr, "id": r["id"]})
    db.commit()

def _due_schedules(db: Session, tenant_id: str, now_utc: datetime):
    db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
    return db.execute(text("""
        SELECT id, prompt_id, cadence, timezone, run_at, next_run_at
        FROM schedules
        WHERE next_run_at <= :now
        FOR UPDATE SKIP LOCKED
    """), {"now": now_utc}).mappings().all()

def _expand_and_enqueue(db: Session, tenant_id: str, prompt_id: str, scheduled_for_ts_utc: datetime) -> int:
    db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
    combos = db.execute(text("""
        SELECT p.language, pm.model_id, pm.grounding_mode, pc.country_code
        FROM prompts p
        JOIN prompt_models pm ON pm.prompt_id = p.id AND pm.deleted_at IS NULL
        JOIN prompt_countries pc ON pc.prompt_id = p.id AND pc.deleted_at IS NULL
        WHERE p.id = :pid AND p.deleted_at IS NULL
    """), {"pid": prompt_id}).mappings().all()
    if not combos: return 0
    jobs = 0
    for row in combos:
        rq_default.enqueue("app.workers.jobs.execute_run", {
            "tenant_id": tenant_id,
            "prompt_id": prompt_id,
            "model_id": str(row["model_id"]),
            "country_code": row["country_code"],
            "language": row["language"],
            "grounding_mode": str(row["grounding_mode"]),
            "scheduled_for_ts": scheduled_for_ts_utc.isoformat(),
        })
        jobs += 1
    return jobs

def _update_next_run_at(db: Session, tenant_id: str, schedule_row: dict, now_utc: datetime) -> None:
    db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
    new_next = _advance_past(schedule_row["cadence"], schedule_row["timezone"], schedule_row["next_run_at"], now_utc)
    db.execute(text("UPDATE schedules SET next_run_at = :nr WHERE id = :id"), {"nr": new_next, "id": schedule_row["id"]})
    db.commit()

def tick():
    now_utc = datetime.now(timezone.utc)
    with SessionLocal() as db:
        tenant_ids = [str(tid) for (tid,) in db.execute(text("SELECT id FROM tenants")).all()]
    total_jobs = 0
    for tid in tenant_ids:
        with SessionLocal() as db:
            try:
                _init_missing_next_run_at(db, tid, now_utc)
                due = _due_schedules(db, tid, now_utc)
                for sch in due:
                    total_jobs += _expand_and_enqueue(db, tid, str(sch["prompt_id"]), sch["next_run_at"])
                    _update_next_run_at(db, tid, sch, now_utc)
            except Exception as e:
                print(f"[scheduler] tenant={tid} error: {e}")
    if total_jobs:
        print(f"[scheduler] enqueued {total_jobs} jobs at {now_utc.isoformat()}")

def main():
    sched = BlockingScheduler(timezone="UTC")
    sched.add_job(tick, "date", run_date=datetime.now(timezone.utc))
    sched.add_job(tick, "interval", minutes=1)
    print("[scheduler] started")
    sched.start()

if __name__ == "__main__":
    main()
