from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS question_fts USING fts5(
    question_text,
    solution_text,
    concepts,
    content=''
);
"""

FTS_TRIGGERS = [
    """
    CREATE TRIGGER IF NOT EXISTS questions_ai AFTER INSERT ON questions BEGIN
      INSERT INTO question_fts(rowid, question_text, solution_text, concepts)
      VALUES (new.id, new.question_text, COALESCE(new.solution_text,''), COALESCE(new.concept_text,''));
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS questions_ad AFTER DELETE ON questions BEGIN
      INSERT INTO question_fts(question_fts, rowid, question_text, solution_text, concepts)
      VALUES ('delete', old.id, old.question_text, COALESCE(old.solution_text,''), COALESCE(old.concept_text,''));
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS questions_au AFTER UPDATE ON questions BEGIN
      INSERT INTO question_fts(question_fts, rowid, question_text, solution_text, concepts)
      VALUES ('delete', old.id, old.question_text, COALESCE(old.solution_text,''), COALESCE(old.concept_text,''));
      INSERT INTO question_fts(rowid, question_text, solution_text, concepts)
      VALUES (new.id, new.question_text, COALESCE(new.solution_text,''), COALESCE(new.concept_text,''));
    END;
    """,
]


def init_fts() -> None:
    """Create the FTS index. Called after migrations and in tests."""
    with engine.begin() as connection:
        connection.exec_driver_sql(FTS_SCHEMA)
        for trigger in FTS_TRIGGERS:
            connection.exec_driver_sql(trigger)


def rebuild_fts() -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO question_fts(question_fts) VALUES('rebuild')")
