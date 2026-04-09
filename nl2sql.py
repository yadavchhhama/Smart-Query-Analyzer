"""
nl2sql.py
---------
Converts natural language questions into MySQL-compatible SQL queries
using a rule-based pattern-matching approach.
"""

import re



AGGREGATES = {
    "total":    "SUM",
    "sum":      "SUM",
    "average":  "AVG",
    "avg":      "AVG",
    "count":    "COUNT",
    "how many": "COUNT",
    "maximum":  "MAX",
    "max":      "MAX",
    "highest":  "MAX",
    "minimum":  "MIN",
    "min":      "MIN",
    "lowest":   "MIN",
}

ORDER_KEYWORDS = {
    "highest":  "DESC",
    "most":     "DESC",
    "top":      "DESC",
    "largest":  "DESC",
    "lowest":   "ASC",
    "least":    "ASC",
    "smallest": "ASC",
    "cheapest": "ASC",
    "oldest":   "ASC",
    "newest":   "DESC",
    "latest":   "DESC",
    "recent":   "DESC",
}

MONTHS = {
    "january": "01", "february": "02", "march":     "03",
    "april":   "04", "may":      "05", "june":      "06",
    "july":    "07", "august":   "08", "september": "09",
    "october": "10", "november": "11", "december":  "12",
}


def natural_to_sql(query: str) -> tuple[str, str]:
    """
    Convert a natural language query into a MySQL SQL statement.

    Returns
    -------
    sql         : str – The generated SQL query
    explanation : str – Human-readable explanation of what it does
    """
    q = query.lower().strip()

    # ── 1. Determine which table(s) to query 
    use_users  = any(w in q for w in ("user", "name", "email", "people", "customer"))
    use_orders = any(w in q for w in ("order", "amount", "purchase", "bought",
                                       "spend", "spent", "payment", "sale"))

    if not use_users and not use_orders:
        use_users = True

    need_join = use_users and use_orders

    # ── 2. Detect aggregate function 
    agg_func   = None
    agg_column = None
    for phrase, func in AGGREGATES.items():
        if phrase in q:
            agg_func = func
            if func in ("SUM", "AVG", "MAX", "MIN") and use_orders:
                agg_column = "orders.amount" if need_join else "amount"
            else:
                agg_column = "*"
            break

    # ── 3. Build SELECT clause 
    per_user = any(p in q for p in ("per user", "each user", "by user", "by name"))

    if agg_func and agg_column:
        if per_user:
            select_clause = f"users.name, {agg_func}(orders.amount) AS total_amount"
        else:
            select_clause = f"{agg_func}({agg_column}) AS result"
    elif need_join:
        select_clause = "users.name, users.email, orders.amount, orders.order_date"
    elif use_orders:
        select_clause = "orders.*"
    else:
        select_clause = "users.*"

    # ── 4. Build FROM + JOIN clause ─
    if need_join:
        from_clause = "FROM users JOIN orders ON users.id = orders.user_id"
    elif use_orders:
        from_clause = "FROM orders"
    else:
        from_clause = "FROM users"
    # ── 5. Build WHERE clause 
    where_parts = []

    # Filter by name
    name_match = re.search(
        r"(?:by|for|named?|called|user(?:'s)?)\s+['\"]?([A-Za-z]+)['\"]?", query, re.I
    )
    if name_match:
        name = name_match.group(1).capitalize()
        if need_join or use_users:
            where_parts.append(f"users.name LIKE '%{name}%'")

    # Filter by amount – greater than
    amount_match = re.search(
        r"(?:more than|greater than|above|over|>)\s*\$?(\d+(?:\.\d+)?)", q
    )
    if amount_match:
        val = amount_match.group(1)
        col = "orders.amount" if need_join else "amount"
        where_parts.append(f"{col} > {val}")

    # Filter by amount – less than
    amount_less = re.search(
        r"(?:less than|below|under|cheaper than|<)\s*\$?(\d+(?:\.\d+)?)", q
    )
    if amount_less:
        val = amount_less.group(1)
        col = "orders.amount" if need_join else "amount"
        where_parts.append(f"{col} < {val}")

    # Filter by year  ── MySQL: YEAR(order_date) = 2024
    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match and use_orders:
        year = year_match.group(1)
        col  = "orders.order_date" if need_join else "order_date"
        where_parts.append(f"YEAR({col}) = {year}")

    # Filter by month name  ── MySQL: MONTH(order_date) = 4
    for month_name, month_num in MONTHS.items():
        if month_name in q and use_orders:
            col = "orders.order_date" if need_join else "order_date"
            where_parts.append(f"MONTH({col}) = {int(month_num)}")
            break

    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    # ── 6. GROUP BY 
    group_clause = ""
    if agg_func and per_user:
        group_clause = "GROUP BY users.id, users.name"

    # ── 7. ORDER BY 
    order_clause = ""
    for phrase, direction in ORDER_KEYWORDS.items():
        if phrase in q:
            if use_orders and not agg_func:
                col = "orders.amount" if need_join else "amount"
                order_clause = f"ORDER BY {col} {direction}"
            elif agg_func and group_clause:
                order_clause = f"ORDER BY total_amount {direction}"
            break

    # ── 8. LIMIT 
    limit_clause = ""
    limit_match = re.search(r"\b(?:top|first|last)\s+(\d+)\b", q)
    if limit_match:
        limit_clause = f"LIMIT {limit_match.group(1)}"
    elif "top" in q and not limit_match:
        limit_clause = "LIMIT 5"

    # ── 9. Assemble final SQL 
    parts = [
        f"SELECT {select_clause}",
        from_clause,
        where_clause,
        group_clause,
        order_clause,
        limit_clause,
    ]
    sql = "\n".join(p for p in parts if p).strip()

    # ── 10. Plain-English explanation 
    explanation = _build_explanation(
        select_clause, from_clause, where_clause,
        group_clause, order_clause, limit_clause,
        agg_func, need_join
    )

    return sql, explanation


def _build_explanation(select, frm, where, group, order, limit,
                       agg_func, need_join) -> str:
    """Build a friendly explanation of what the SQL query does."""
    parts = []

    if agg_func:
        parts.append(f"Calculates the **{agg_func}** aggregate")
    else:
        parts.append("Retrieves records")

    if "orders" in frm and "users" in frm:
        parts.append("by joining the **users** and **orders** tables")
    elif "orders" in frm:
        parts.append("from the **orders** table")
    else:
        parts.append("from the **users** table")

    if where:
        condition = where.replace("WHERE ", "").replace(" AND ", " **and** ")
        parts.append(f"filtered by: {condition}")

    if group:
        parts.append("grouped by each user")

    if order:
        direction = "descending" if "DESC" in order else "ascending"
        parts.append(f"sorted in {direction} order")

    if limit:
        n = limit.replace("LIMIT ", "")
        parts.append(f"limited to {n} result(s)")

    return ", ".join(parts) + "."