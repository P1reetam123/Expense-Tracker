"""
database.py - Database operations for Personal Expense Tracker
Demonstrates: SQLite integration, table creation, CRUD operations, dictionaries, and exception handling.
"""

import sqlite3
import os

DB_FILENAME = "expenses.db"


def get_connection(db_name=DB_FILENAME):
    """Establish and return a connection to the SQLite database.
    Configured to return rows as dictionaries for easy manipulation.
    """
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row  # Enables accessing columns by name like a dictionary
    return conn


def init_db(db_name=DB_FILENAME):
    """Initialize database tables for expenses and monthly budgets."""
    conn = get_connection(db_name)
    try:
        cursor = conn.cursor()
        # 1. Expenses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL
            )
        """)
        
        # 2. Budgets table: stores budget per month (format: YYYY-MM)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                month TEXT PRIMARY KEY,
                budget_amount REAL NOT NULL
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Database initialization failed: {e}")
    finally:
        conn.close()


def add_expense(amount: float, category: str, description: str, date: str, db_name=DB_FILENAME) -> int:
    """Insert a new expense record into SQLite database.
    Returns the newly generated record ID.
    """
    conn = get_connection(db_name)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO expenses (amount, category, description, date)
            VALUES (?, ?, ?, ?)
        """, (amount, category.strip(), description.strip(), date.strip()))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to add expense: {e}")
    finally:
        conn.close()


def get_all_expenses(month: str = None, db_name=DB_FILENAME) -> list[dict]:
    """Retrieve expenses. If month (YYYY-MM) is provided, filter by month.
    Returns a list of dictionaries.
    """
    conn = get_connection(db_name)
    try:
        cursor = conn.cursor()
        if month and month.lower() != "all":
            cursor.execute("""
                SELECT id, amount, category, description, date
                FROM expenses
                WHERE strftime('%Y-%m', date) = ?
                ORDER BY date DESC, id DESC
            """, (month,))
        else:
            cursor.execute("""
                SELECT id, amount, category, description, date
                FROM expenses
                ORDER BY date DESC, id DESC
            """)
        rows = cursor.fetchall()
        # Convert sqlite3.Row objects to standard Python dictionaries
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to fetch expenses: {e}")
    finally:
        conn.close()


def get_expense_by_id(expense_id: int, db_name=DB_FILENAME) -> dict | None:
    """Fetch a single expense by ID."""
    conn = get_connection(db_name)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, amount, category, description, date FROM expenses WHERE id = ?", (expense_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to fetch expense #{expense_id}: {e}")
    finally:
        conn.close()


def update_expense(expense_id: int, amount: float, category: str, description: str, date: str, db_name=DB_FILENAME) -> bool:
    """Update an existing expense entry.
    Returns True if an entry was updated, False otherwise.
    """
    conn = get_connection(db_name)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE expenses
            SET amount = ?, category = ?, description = ?, date = ?
            WHERE id = ?
        """, (amount, category.strip(), description.strip(), date.strip(), expense_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to update expense #{expense_id}: {e}")
    finally:
        conn.close()


def delete_expense(expense_id: int, db_name=DB_FILENAME) -> bool:
    """Delete an expense entry by its ID.
    Returns True if successfully deleted, False otherwise.
    """
    conn = get_connection(db_name)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to delete expense #{expense_id}: {e}")
    finally:
        conn.close()


def set_budget(month: str, budget_amount: float, db_name=DB_FILENAME) -> None:
    """Insert or update the budget for a specific month (YYYY-MM)."""
    conn = get_connection(db_name)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO budgets (month, budget_amount)
            VALUES (?, ?)
            ON CONFLICT(month) DO UPDATE SET budget_amount = excluded.budget_amount
        """, (month, budget_amount))
        conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to set budget for {month}: {e}")
    finally:
        conn.close()


def get_budget(month: str, db_name=DB_FILENAME) -> float:
    """Retrieve monthly budget. Returns 0.0 if not set."""
    conn = get_connection(db_name)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT budget_amount FROM budgets WHERE month = ?", (month,))
        row = cursor.fetchone()
        return float(row["budget_amount"]) if row else 0.0
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to fetch budget for {month}: {e}")
    finally:
        conn.close()


def get_available_months(db_name=DB_FILENAME) -> list[str]:
    """Retrieve a sorted list of unique months (YYYY-MM) present in expenses or budgets."""
    conn = get_connection(db_name)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT strftime('%Y-%m', date) as m FROM expenses WHERE date IS NOT NULL
            UNION
            SELECT month as m FROM budgets
            ORDER BY m DESC
        """)
        rows = cursor.fetchall()
        return [row["m"] for row in rows if row["m"]]
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to get available months: {e}")
    finally:
        conn.close()
