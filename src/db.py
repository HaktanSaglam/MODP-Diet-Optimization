"""
db.py
=====
Single point of database access. The handout requires that all data be queried
from the database (nothing hardcoded). We use the same standard SQL against two
interchangeable backends:

  * SQLite  (default) -- diet.sqlite, auto-built from diet.sql on first use.
                         Zero install; runs anywhere Python runs.
  * MySQL   (optional) -- set env MODP_DB=mysql plus MODP_MYSQL_* vars, and the
                         grader's `diet` database is queried directly via pymysql.

Both expose `connect()` and `query(sql, params)`. Queries use `?` placeholders
(SQLite style); for MySQL they are rewritten to `%s` automatically.
"""
from __future__ import annotations

import os
import sqlite3

from load_sqlite import build as build_sqlite, SQLITE_PATH

BACKEND = os.environ.get("MODP_DB", "sqlite").lower()


def connect():
    if BACKEND == "mysql":
        import pymysql  # only needed if the user opts into MySQL

        return pymysql.connect(
            host=os.environ.get("MODP_MYSQL_HOST", "127.0.0.1"),
            port=int(os.environ.get("MODP_MYSQL_PORT", "3306")),
            user=os.environ.get("MODP_MYSQL_USER", "root"),
            password=os.environ.get("MODP_MYSQL_PASSWORD", ""),
            database=os.environ.get("MODP_MYSQL_DB", "diet"),
            charset="utf8mb4",
        )
    # sqlite (default): build the file from diet.sql if it is missing
    if not os.path.exists(SQLITE_PATH):
        build_sqlite(force=False)
    con = sqlite3.connect(SQLITE_PATH)
    con.row_factory = sqlite3.Row
    return con


def query(sql: str, params: tuple = ()):  # -> list[dict]
    """Run a SELECT and return a list of plain dicts (backend-independent)."""
    con = connect()
    try:
        if BACKEND == "mysql":
            import pymysql.cursors

            sql = sql.replace("?", "%s")
            cur = con.cursor(pymysql.cursors.DictCursor)
            cur.execute(sql, params)
            return list(cur.fetchall())
        cur = con.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        con.close()


if __name__ == "__main__":
    print("Backend:", BACKEND)
    print("foods:", query("SELECT COUNT(*) AS c FROM foods")[0]["c"])
    print("sample:", query("SELECT id, name, foodGroupId FROM foods LIMIT 3"))
