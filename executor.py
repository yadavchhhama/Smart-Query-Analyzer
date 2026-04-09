"""
executor.py
-----------
Executes SQL queries against the MySQL database, measures execution time,
and provides basic query-optimization suggestions.
"""

import time
import re
import mysql.connector
from database import get_connection


# ─────────────────────────────────────────────────────────────────────────────
# Query Execution
# ─────────────────────────────────────────────────────────────────────────────

def execute_query(sql: str) -> dict:
    """
    Run a SQL query and return results plus timing info.

    Returns a dict with keys:
        success       : bool
        rows          : list[dict]  – each row as a column→value dict
        columns       : list[str]
        row_count     : int
        execution_ms  : float       – wall-clock time in milliseconds
        error         : str | None
    """
    result = {
        "success":      False,
        "rows":         [],
        "columns":      [],
        "row_count":    0,
        "execution_ms": 0.0,
        "error":        None,
    }
    try:
        conn   = get_connection()
        # dictionary=True makes every row come back as a dict automatically
        cursor = conn.cursor(dictionary=True)

        # ── Time the actual query execution ───────────────────────────────────
        start = time.perf_counter()
        cursor.execute(sql)
        raw_rows = cursor.fetchall()          # ← fetchall AFTER execute (bug fix)
        end   = time.perf_counter()

        result["execution_ms"] = round((end - start) * 1000, 4)

        if raw_rows:
            result["columns"] = list(raw_rows[0].keys())
            result["rows"]    = raw_rows
        else:
            result["columns"] = [desc[0] for desc in (cursor.description or [])]

        result["row_count"] = len(result["rows"])
        result["success"]   = True

        cursor.close()
        conn.close()

    except mysql.connector.Error as e:
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Query Optimization Analyzer
# ─────────────────────────────────────────────────────────────────────────────

def analyze_query(sql: str) -> list[dict]:
    """
    Inspect a SQL query and return a list of optimization suggestions.

    Each suggestion is a dict:
        level   : "warning" | "info" | "tip"
        message : str
    """
    suggestions = []
    sql_upper = sql.upper().strip()

    # ── 1. SELECT * check ─────────────────────────────────────────────────────
    if re.search(r"SELECT\s+\*", sql_upper):
        suggestions.append({
            "level":   "warning",
            "message": "**Avoid SELECT *** – Fetching all columns is wasteful. "
                       "List only the columns you actually need (e.g., `SELECT name, email`)."
        })

    # ── 2. Missing WHERE clause ───────────────────────────────────────────────
    if "WHERE" not in sql_upper and "GROUP BY" not in sql_upper:
        suggestions.append({
            "level":   "warning",
            "message": "**No WHERE clause** – The query scans every row in the table. "
                       "Add a WHERE condition to narrow results and improve speed."
        })

    # ── 3. Missing LIMIT on potentially large result sets ────────────────────
    if "LIMIT" not in sql_upper and "COUNT" not in sql_upper \
            and "SUM" not in sql_upper and "AVG" not in sql_upper:
        suggestions.append({
            "level":   "tip",
            "message": "**Consider LIMIT** – If you only need the first N rows, "
                       "add `LIMIT N` to avoid fetching unnecessary data."
        })

    # ── 4. LIKE with leading wildcard ─────────────────────────────────────────
    if re.search(r"LIKE\s+'%[^%]", sql_upper):
        suggestions.append({
            "level":   "warning",
            "message": "**Leading wildcard in LIKE** – `LIKE '%value'` cannot use an index "
                       "and forces a full scan. Prefer `LIKE 'value%'` where possible."
        })

    # ── 5. ORDER BY without LIMIT ─────────────────────────────────────────────
    if "ORDER BY" in sql_upper and "LIMIT" not in sql_upper:
        suggestions.append({
            "level":   "tip",
            "message": "**ORDER BY without LIMIT** – Sorting a large result set is expensive. "
                       "Combine with `LIMIT N` if you only need the top/bottom rows."
        })

    # ── 6. JOIN present — index reminder ─────────────────────────────────────
    if "JOIN" in sql_upper:
        suggestions.append({
            "level":   "info",
            "message": "**JOIN detected** – Make sure the join column (`user_id`) "
                       "is indexed on the child table for fast lookups."
        })

    # ── 7. Cartesian join guard ───────────────────────────────────────────────
    if sql_upper.count("FROM") == 1 and sql_upper.count(",") > 0 \
            and "JOIN" not in sql_upper:
        suggestions.append({
            "level":   "warning",
            "message": "**Possible Cartesian join** – Multiple tables in FROM without "
                       "an explicit JOIN condition can produce huge result sets. Use explicit JOINs."
        })

    # ── 8. All good ───────────────────────────────────────────────────────────
    if not suggestions:
        suggestions.append({
            "level":   "info",
            "message": "**Query looks good!** No obvious issues detected."
        })

    return suggestions