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
    "photo_url": "VARCHAR DEFAULT ''",
    "company_logo": "VARCHAR DEFAULT ''",
    "hiring_quote": "VARCHAR DEFAULT ''",
}

_USER_COLUMNS = {
    "ats_score": "JSON",
    "resume_latex": "TEXT",
}


def init_db():
    from . import models  # noqa: F401  (register tables)
    SQLModel.metadata.create_all(engine)
    if engine.dialect.name != "sqlite":
        return
    insp = inspect(engine)

    # Migrate job columns
    if insp.has_table("job"):
        have_job = {c["name"] for c in insp.get_columns("job")}
        with engine.begin() as conn:
            for name, ddl in _JOB_COLUMNS.items():
                if name not in have_job:
                    conn.execute(text(f"ALTER TABLE job ADD COLUMN {name} {ddl}"))

    # Migrate user columns
    if insp.has_table("user"):
        have_user = {c["name"] for c in insp.get_columns("user")}
        with engine.begin() as conn:
            for name, ddl in _USER_COLUMNS.items():
                if name not in have_user:
                    conn.execute(text(f"ALTER TABLE user ADD COLUMN {name} {ddl}"))


def get_session():
    with Session(engine) as s:
        yield s