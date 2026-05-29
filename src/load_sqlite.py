"""
load_sqlite.py
==============
Import the provided MySQL dump (`diet.sql`) into a local SQLite database
(`diet.sqlite`) so the rest of the project can `query everything from the
database` (handout rule) with zero external services to install.

The same standard SQL queries used here run unchanged against a real MySQL
server -- see `db.py` for the optional MySQL backend. We only import the seven
tables the project actually needs.

A character-level tokenizer is used for the INSERT value tuples because food
names are Turkish strings that contain commas, apostrophes and backslash
escapes (e.g. 'ARMUT RECELI'), which a naive split would corrupt.
"""
from __future__ import annotations

import os
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DUMP_PATH = os.path.join(ROOT, "diet.sql")
SQLITE_PATH = os.path.join(ROOT, "diet.sqlite")

# Tables we need + the SQLite schema we create for each (clean, MySQL syntax stripped).
# Column order MUST match the column order in the dump's CREATE TABLE.
TABLE_SCHEMAS = {
    "foods": """
        CREATE TABLE foods (
            id INTEGER PRIMARY KEY, name TEXT, foodGroupId INTEGER, caseStudy INTEGER,
            portion INTEGER, cost REAL, preference REAL, preference2 REAL,
            preparingTime REAL, cookingTime REAL, rating REAL, co2 REAL,
            availability INTEGER, picUrl TEXT, nameRoots TEXT
        )""",
    "food_group": "CREATE TABLE food_group (id INTEGER PRIMARY KEY, name TEXT)",
    "food_nutrients": """
        CREATE TABLE food_nutrients (
            id INTEGER PRIMARY KEY, foodId INTEGER, nutrientId INTEGER, quantity REAL
        )""",
    "nutrients": """
        CREATE TABLE nutrients (
            id INTEGER PRIMARY KEY, name TEXT, nGroupId INTEGER, unitId INTEGER
        )""",
    "dri": """
        CREATE TABLE dri (
            id INTEGER PRIMARY KEY, nutrient_id INTEGER, low_age INTEGER, up_age INTEGER,
            gender TEXT, RLL REAL, RUL REAL
        )""",
    "user": """
        CREATE TABLE user (
            id INTEGER PRIMARY KEY, name TEXT, surname TEXT, username TEXT, password TEXT,
            type INTEGER, date TEXT, age INTEGER, gender TEXT, height INTEGER, weight INTEGER
        )""",
    "user_foods": """
        CREATE TABLE user_foods (
            id INTEGER PRIMARY KEY, userId INTEGER, userName TEXT, foodId INTEGER,
            foodName TEXT, preference REAL
        )""",
}


def _extract_values_blobs(sql_text: str, table: str):
    r"""Yield every VALUES blob for a table. phpMyAdmin splits large tables into
    several `INSERT INTO \`t\` (...) VALUES (...);` statements, so there can be many."""
    marker = "INSERT INTO `%s`" % table
    n = len(sql_text)
    search = 0
    while True:
        start = sql_text.find(marker, search)
        if start == -1:
            return
        values_kw = sql_text.find("VALUES", start)
        if values_kw == -1:
            return
        # Find the terminating ";" that is not inside a quoted string.
        i = values_kw + len("VALUES")
        in_str = False
        end = n
        while i < n:
            ch = sql_text[i]
            if in_str:
                if ch == "\\":
                    i += 2
                    continue
                if ch == "'":
                    in_str = False
            else:
                if ch == "'":
                    in_str = True
                elif ch == ";":
                    end = i
                    break
            i += 1
        yield sql_text[values_kw + len("VALUES"): end]
        search = end + 1


def _parse_tuples(blob: str):
    """Yield lists of Python values from a `(...),(...),...` VALUES blob."""
    i, n = 0, len(blob)
    while i < n:
        # advance to the next opening "("
        while i < n and blob[i] != "(":
            i += 1
        if i >= n:
            break
        i += 1  # skip "("
        row, i = _parse_row(blob, i)
        yield row


def _parse_row(blob: str, i: int):
    """Parse a single tuple starting just after '(' up to its matching ')'."""
    values = []
    n = len(blob)
    while i < n:
        # skip leading whitespace
        while i < n and blob[i] in " \t\r\n":
            i += 1
        if blob[i] == ")":
            return values, i + 1
        if blob[i] == "'":  # quoted string
            i += 1
            chars = []
            while i < n:
                ch = blob[i]
                if ch == "\\":  # backslash escape
                    nxt = blob[i + 1] if i + 1 < n else ""
                    chars.append({"n": "\n", "t": "\t", "r": "\r", "0": "\0"}.get(nxt, nxt))
                    i += 2
                    continue
                if ch == "'":
                    if i + 1 < n and blob[i + 1] == "'":  # '' escaped quote
                        chars.append("'")
                        i += 2
                        continue
                    i += 1
                    break
                chars.append(ch)
                i += 1
            values.append("".join(chars))
        else:  # number or NULL, read until , or )
            j = i
            while j < n and blob[j] not in ",)":
                j += 1
            token = blob[i:j].strip()
            if token.upper() == "NULL" or token == "":
                values.append(None)
            else:
                try:
                    values.append(int(token))
                except ValueError:
                    try:
                        values.append(float(token))
                    except ValueError:
                        values.append(token)
            i = j
        # skip a trailing comma between values
        while i < n and blob[i] in " \t\r\n":
            i += 1
        if i < n and blob[i] == ",":
            i += 1
    return values, i


def build(force: bool = False) -> str:
    """(Re)build diet.sqlite from diet.sql. Returns the sqlite path."""
    if os.path.exists(SQLITE_PATH) and not force:
        return SQLITE_PATH
    if os.path.exists(SQLITE_PATH):
        os.remove(SQLITE_PATH)

    with open(DUMP_PATH, "r", encoding="utf-8", errors="replace") as f:
        sql_text = f.read()

    con = sqlite3.connect(SQLITE_PATH)
    cur = con.cursor()
    for table, schema in TABLE_SCHEMAS.items():
        cur.execute(schema)
        rows = []
        for blob in _extract_values_blobs(sql_text, table):
            rows.extend(_parse_tuples(blob))
        if not rows:
            print("  WARNING: no data found for table %s" % table)
            continue
        ph = ",".join("?" * len(rows[0]))
        try:
            cur.executemany("INSERT INTO %s VALUES (%s)" % (table, ph), rows)
        except sqlite3.ProgrammingError:
            # column count mismatch on some rows -> insert individually, skip bad ones
            good = 0
            for r in rows:
                try:
                    cur.execute("INSERT INTO %s VALUES (%s)" % (table, ",".join("?" * len(r))), r)
                    good += 1
                except sqlite3.Error:
                    pass
            print("  %s: inserted %d/%d rows (variable width)" % (table, good, len(rows)))
            con.commit()
            continue
        print("  %s: %d rows" % (table, len(rows)))
    con.commit()
    con.close()
    return SQLITE_PATH


if __name__ == "__main__":
    print("Building SQLite database from diet.sql ...")
    path = build(force=True)
    con = sqlite3.connect(path)
    cur = con.cursor()
    for t in TABLE_SCHEMAS:
        cur.execute("SELECT COUNT(*) FROM %s" % t)
        print("  %-15s %d rows" % (t, cur.fetchone()[0]))
    con.close()
    print("Done -> %s" % path)
