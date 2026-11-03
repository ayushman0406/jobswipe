from sqlalchemy import inspect, text
from sqlmodel import SQLModel, Session, create_engine

from .config import settings

engine = create_engine(settings.db_url, connect_args={"check_same_thread": False})

# Columns added after the first sqlite file may already exist. create_all does not ALTER.
_JOB_COLUMNS = {
    "category": "VARCHAR DEFAULT ''",
    "industry": "VARCHAR DEFAULT ''",
    "education": "VARCHAR DEFAULT ''",
    "shift": "VARCHAR DEFAULT ''",
    "languages": "JSON",
    "benefits": "JSON",
    "openings": "INTEGER DEFAULT 1",
}


def init_db():
    from . import models  # noqa: F401  (register tables)
    SQLModel.metadata.create_all(engine)
    if engine.dialect.name != "sqlite":
        return
    insp = inspect(engine)
    if not insp.has_table("job"):
        return
    have = {c["name"] for c in insp.get_columns("job")}
    with engine.begin() as conn:
        for name, ddl in _JOB_COLUMNS.items():
            if name not in have:
                conn.execute(text(f"ALTER TABLE job ADD COLUMN {name} {ddl}"))


def get_session():
    with Session(engine) as s:
        yield s