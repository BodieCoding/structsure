from contextlib import contextmanager
from typing import Iterator, Optional

try:  # optional dependency
    from sqlalchemy import create_engine, text  # type: ignore[import-not-found]
    from sqlalchemy.engine import Engine  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    create_engine = None  # type: ignore[assignment]
    text = None  # type: ignore[assignment]

    class Engine:  # type: ignore[no-redef]
        pass

_engine: Optional[Engine] = None

def get_engine(dsn: str) -> Engine:
    global _engine
    if _engine is None:
        if create_engine is None:  # pragma: no cover
            raise RuntimeError("SQLAlchemy not installed. Install with `pip install -e .[server]`.")
        _engine = create_engine(dsn, future=True)  # type: ignore[call-arg]
    return _engine

@contextmanager
def db_conn(dsn: str) -> Iterator[Engine]:
    eng = get_engine(dsn)
    try:
        yield eng
    finally:
        pass

SCHEMAS_DDL = """
CREATE TABLE IF NOT EXISTS schemas (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  schema_json TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS runs (
  id SERIAL PRIMARY KEY,
  schema_id INTEGER NOT NULL REFERENCES schemas(id) ON DELETE CASCADE,
  prompt TEXT NOT NULL,
  output_json TEXT,
  provider TEXT,
  model TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

def init_db(dsn: str) -> None:
    if text is None:  # pragma: no cover
        raise RuntimeError("SQLAlchemy not installed. Install with `pip install -e .[server]`.")
    with db_conn(dsn) as eng:
        with eng.begin() as conn:  # type: ignore[attr-defined]
            conn.execute(text(SCHEMAS_DDL))  # type: ignore[call-arg]
