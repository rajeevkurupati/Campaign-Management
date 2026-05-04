"""
Database setup — SQLite via SQLModel.
The .db file sits next to main.py and is excluded from git via .gitignore.
"""
from sqlmodel import create_engine, Session, SQLModel

DATABASE_URL = "sqlite:///./herkey.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI threads
    echo=False,
)


def create_db_and_tables():
    """Create all tables. Called once on app startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields a DB session per request."""
    with Session(engine) as session:
        yield session
