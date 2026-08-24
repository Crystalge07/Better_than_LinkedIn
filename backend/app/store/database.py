from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.store.models import Base

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_schema()


def _ensure_schema() -> None:
    """Repair leftover Step 1 constraints and widen columns create_all will not alter."""
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE jobs ALTER COLUMN source_job_id TYPE text"))
        leftover_unique = conn.execute(
            text(
                """
                SELECT 1
                FROM pg_index ix
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_class t ON t.oid = ix.indrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE t.relname = 'jobs'
                  AND n.nspname = 'public'
                  AND i.relname = 'ix_jobs_fingerprint'
                  AND ix.indisunique
                """
            )
        ).scalar()
        if leftover_unique:
            conn.execute(text("DROP INDEX IF EXISTS ix_jobs_fingerprint"))

        conn.execute(text("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_fingerprint_key"))
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_jobs_fingerprint ON jobs (fingerprint)")
        )

        has_composite = conn.execute(
            text(
                """
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_jobs_fingerprint_apply_url'
                """
            )
        ).scalar()
        if not has_composite:
            conn.execute(
                text(
                    "ALTER TABLE jobs ADD CONSTRAINT uq_jobs_fingerprint_apply_url "
                    "UNIQUE (fingerprint, apply_url)"
                )
            )


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
