"""
database.py
-----------
Handles MySQL database creation, table setup, and sample data insertion.
"""

import mysql.connector
import os

# ── MySQL connection config ───────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("MYSQL_HOST",     "localhost"),
    "user":     os.getenv("MYSQL_USER",     "root"),
    "password": os.getenv("MYSQL_PASSWORD", "Chhama#09"),   # ← change this
    "database": os.getenv("MYSQL_DATABASE", "smart_query"),
}


def get_connection():
    """Create and return a connection to the MySQL database."""
    return mysql.connector.connect(**DB_CONFIG)


def setup_database():
    """
    Create tables and insert sample data if they don't already exist.
    Called once at app startup.
    """
    # Connect without specifying the DB so we can create it if needed
    base_cfg = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    conn = mysql.connector.connect(**base_cfg)
    cursor = conn.cursor()

    db_name = DB_CONFIG["database"]
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    cursor.execute(f"USE `{db_name}`")

    # ── Create 'users' table ──────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id    INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name  VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE
        )
    """)

    # ── Create 'orders' table ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id         INT     NOT NULL AUTO_INCREMENT PRIMARY KEY,
            user_id    INT     NOT NULL,
            amount     DECIMAL(10,2) NOT NULL,
            order_date DATE    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ── Insert sample users (only if the table is empty) ─────────────────────
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        sample_users = [
            ("Alice Johnson", "alice@example.com"),
            ("Bob Smith",     "bob@example.com"),
            ("Carol White",   "carol@example.com"),
            ("David Brown",   "david@example.com"),
            ("Eva Green",     "eva@example.com"),
        ]
        cursor.executemany(
            "INSERT INTO users (name, email) VALUES (%s, %s)", sample_users
        )

    # ── Insert sample orders (only if the table is empty) ────────────────────
    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] == 0:
        sample_orders = [
            (1, 250.00,  "2024-01-15"),
            (1, 480.50,  "2024-02-20"),
            (2, 120.75,  "2024-01-28"),
            (3, 980.00,  "2024-03-05"),
            (3, 350.25,  "2024-03-18"),
            (4, 75.00,   "2024-02-10"),
            (5, 620.00,  "2024-04-01"),
            (2, 210.00,  "2024-04-12"),
            (1, 999.99,  "2024-04-22"),
            (4, 430.00,  "2024-05-03"),
        ]
        cursor.executemany(
            "INSERT INTO orders (user_id, amount, order_date) VALUES (%s, %s, %s)",
            sample_orders,
        )

    conn.commit()
    cursor.close()
    conn.close()
    print("MySQL database ready with sample data.")


def get_schema_info():
    """Return a human-readable summary of the database schema."""
    return {
        "users":  ["id (INT)", "name (VARCHAR)", "email (VARCHAR)"],
        "orders": ["id (INT)", "user_id (INT)", "amount (DECIMAL)", "order_date (DATE)"],
    }