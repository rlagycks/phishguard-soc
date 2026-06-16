from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import orm  # noqa: F401 — registers models with metadata
    Base.metadata.create_all(bind=engine)


def migrate_db() -> None:
    """Apply schema migrations not handled by create_all (new columns on existing tables)."""
    migrations = [
        "ALTER TABLE email_analyses ADD COLUMN owner_email VARCHAR(255)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(_text(sql))
                conn.commit()
            except Exception:
                conn.rollback()


def _text(sql: str):
    from sqlalchemy import text
    return text(sql)
