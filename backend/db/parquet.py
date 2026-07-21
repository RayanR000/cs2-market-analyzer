"""DuckDB-backed Parquet store for operational data.

Each table in the system gets a single Parquet file under
``price-archive/ops/{table_name}.parquet``.  The store uses DuckDB for
columnar reads and supports:

* ``append()`` — concat-and-dedup (the file is fully rewritten, which is
  fine since every ops table is <100 MiB).
* ``query()`` — read + filter via a DuckDB connection returned as a context
  manager so callers can run SQL directly against ``read_parquet(...)``.

Denormalised tables (e.g. *event_impacts* which joins 3 tables on the
read side) are written as a single pre-joined file so that API read
paths are single-file queries with no runtime join overhead.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

ARCHIVE_ROOT = Path(__file__).resolve().parent.parent.parent / "price-archive"
OPS_DIR = ARCHIVE_ROOT / "ops"


def ensure_ops_dir() -> Path:
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    return OPS_DIR


def _table_path(table: str) -> Path:
    ensure_ops_dir()
    return OPS_DIR / f"{table}.parquet"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _coerce_dates(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == object:
            non_null = df[col].dropna()
            if len(non_null) > 0 and hasattr(non_null.iloc[0], "isoformat"):
                try:
                    df[col] = pd.to_datetime(df[col])
                except (ValueError, TypeError):
                    pass
    return df


def _append_parquet(path: Path, new_data: pd.DataFrame, dedup_keys: list[str]):
    """Append new_data to an existing Parquet file, deduplicating on dedup_keys.

    Uses DuckDB-native operations to avoid loading the full file into Python
    memory. The dedup is performed within DuckDB's engine via anti-join.
    """
    new_data = _coerce_dates(new_data)
    if not path.exists():
        new_data.to_parquet(path, index=False)
        return

    con = duckdb.connect()
    try:
        con.register("_new", new_data)
        dedup_conditions = " AND ".join(
            f"_existing.{k} = _new.{k}" for k in dedup_keys
        )
        con.execute(f"""
            COPY (
                SELECT * FROM _new
                UNION ALL
                SELECT * FROM read_parquet('{path}') _existing
                WHERE NOT EXISTS (
                    SELECT 1 FROM _new
                    WHERE {dedup_conditions}
                )
            ) TO '{path}' (FORMAT PARQUET)
        """)
    finally:
        con.close()


def read_table(table: str, columns: Optional[list[str]] = None) -> pd.DataFrame:
    """Return all rows from *table* as a DataFrame."""
    path = _table_path(table)
    if not path.exists():
        return pd.DataFrame()
    con = duckdb.connect()
    try:
        col_spec = ", ".join(columns) if columns else "*"
        return con.sql(f"SELECT {col_spec} FROM read_parquet('{path}')").fetchdf()
    finally:
        con.close()


def table_exists(table: str) -> bool:
    return _table_path(table).exists()


def append_table(table: str, rows: list[dict] | pd.DataFrame, dedup_keys: list[str]):
    """Append rows, deduplicating on *dedup_keys*."""
    if isinstance(rows, list):
        rows = pd.DataFrame(rows)
    if rows.empty:
        return
    path = _table_path(table)
    _append_parquet(path, rows, dedup_keys)


# ---------------------------------------------------------------------------
# DuckDB connection context — for ad-hoc queries in API routes
# ---------------------------------------------------------------------------

class ParquetQuery:
    """Wraps a DuckDB connection that reads from an ops table.

    Usage::

        with ParquetQuery("events") as con:
            df = con.sql("SELECT * FROM events WHERE type = 'major'").fetchdf()
    """

    def __init__(self, table: str):
        self._table = table
        self._con: Optional[duckdb.DuckDBPyConnection] = None
        self._path: Optional[Path] = None

    def __enter__(self):
        path = _table_path(self._table)
        if not path.exists():
            self._path = None
            return self
        self._path = path
        self._con = duckdb.connect()
        self._con.sql(f"CREATE VIEW {self._table} AS SELECT * FROM read_parquet('{path}')")
        return self

    def __exit__(self, *args):
        if self._con:
            self._con.close()

    @property
    def con(self):
        if self._con is None:
            msg = f"Table '{self._table}' not found at {self._path}"
            raise FileNotFoundError(msg)
        return self._con

    def df(self) -> pd.DataFrame:
        if self._con is None:
            return pd.DataFrame()
        return self._con.sql(f"SELECT * FROM {self._table}").fetchdf()

    def query(self, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
        if self._con is None:
            return pd.DataFrame()
        return self._con.sql(sql, params=params if params else {}).fetchdf()

    def scalar(self, sql: str, params: Optional[dict] = None):
        if self._con is None:
            return None
        r = self._con.sql(sql, params=params if params else {}).fetchone()
        return r[0] if r else None


def query_table(table: str, sql: str) -> pd.DataFrame:
    """Run a raw SQL query against *table*'s Parquet file."""
    with ParquetQuery(table) as q:
        return q.query(sql)


def delete_table(table: str, key_filters: dict[str, Any]):
    """Delete rows matching *key_filters* and rewrite the file."""
    path = _table_path(table)
    if not path.exists():
        return
    df = read_table(table)
    if df.empty:
        return
    mask = pd.Series(True, index=df.index)
    for col, val in key_filters.items():
        if col in df.columns:
            mask &= df[col] == val
    df = df[~mask]
    df.to_parquet(path, index=False)


@lru_cache(maxsize=1)
def _get_ops_schema(table: str) -> Optional[dict]:
    path = _table_path(table)
    if not path.exists():
        return None
    con = duckdb.connect()
    try:
        cols = con.sql(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
        return {r[0]: r[1] for r in cols}
    finally:
        con.close()
