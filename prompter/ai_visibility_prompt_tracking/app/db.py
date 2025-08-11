from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

class Base(DeclarativeBase):
    pass

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

@contextmanager
def db_session(tenant_id: str | None):
    s = SessionLocal()
    try:
        if tenant_id:
            s.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
