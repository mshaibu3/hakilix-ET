from __future__ import annotations
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from hakilix.config import settings

_engine = None
_SessionLocal = None

def engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(settings.database_url_app, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)
    return _engine

def session_local():
    if _SessionLocal is None:
        engine()
    return _SessionLocal

@contextmanager
def db_session(tenant_id: str | None = None) -> Generator[Session, None, None]:
    db = session_local()()
    try:
        if tenant_id:
            db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        try:
            if tenant_id:
                db.execute(text('RESET app.tenant_id'))
        except Exception:
            pass
        db.close()
