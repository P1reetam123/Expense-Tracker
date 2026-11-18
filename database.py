"""
database.py - SQLite persistence for the Personal Expense Tracker.

The GUI uses these functions instead of embedding SQL queries. Connections are
opened for each operation and always closed before the function returns.
"""

import sqlite3
from pathlib import Path
from typing import Any


# Resolve the database beside this source file, not relative to the terminal's
# current working directory. This keeps one consistent database when launched
# from an IDE, Finder, or Terminal.
DB_FILENAME = str(Path(__file__).resolve().with_name("expenses.db"))


def get_connection(db_name: str = DB_FILENAME) -> sqlite3.Connection:
    """Open a SQLite connection whose rows can be accessed by column name."""
    try:
        connection = sqlite3.connect(db_name)
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error as exc:
        raise RuntimeError(f"Could not open database '{db_name}': {exc}") from exc


def init_db(db_name: str = DB_FILENAME) -> None:
    """Create required tables if missing; do not insert sample records."""
    connection = get_connection(db_name)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                month TEXT PRIMARY KEY,
                budget_amount REAL NOT NULL
            )
            """
        )
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise RuntimeError(f"Database initialization failed: {exc}") from exc
    finally:
        connection.close()


def add_expense(
    amount: float,
    category: str,
    description: str,
    expense_date: str,
    db_name: str = DB_FILENAME,
) -> int:
    """Insert an expense and return its generated ID."""
    connection = get_connection(db_name)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO expenses (amount, category, description, date)
            VALUES (?, ?, ?, ?)
            """,
            (amount, category.strip(), description.strip(), expense_date.strip()),
        )
        connection.commit()
        return int(cursor.lastrowid)
    except sqlite3.Error as exc:
        connection.rollback()
        raise RuntimeError(f"Failed to add expense: {exc}") from exc
    finally:
        connection.close()


def get_all_expenses(
    month: str | None = None,
    db_name: str = DB_FILENAME,
) -> list[dict[str, Any]]:
    """Return expenses as dictionaries, optionally filtered by YYYY-MM."""
    connection = get_connection(db_name)
    try:
        cursor = connection.cursor()
        if month and month.strip().lower() != "all":
            cursor.execute(
                """
                SELECT id, amount, category, description, date
                FROM expenses
                WHERE strftime('%Y-%m', date) = ?
                ORDER BY date DESC, id DESC
                """,
                (month.strip(),),
            )
        else:
            cursor.execute(
                """
                SELECT id, amount, category, description, date
                FROM expenses
                ORDER BY date DESC, id DESC
                """
            )
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to fetch expenses: {exc}") from exc
    finally:
        connection.close()


def get_expense_by_id(
    expense_id: int,
    db_name: str = DB_FILENAME,
) -> dict[str, Any] | None:
    """Return one expense by ID, or None when it does not exist."""
    connection = get_connection(db_name)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, amount, category, description, date
            FROM expenses
            WHERE id = ?
            """,
            (expense_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to fetch expense #{expense_id}: {exc}") from exc
    finally:
        connection.close()


def update_expense(
    expense_id: int,
    amount: float,
    category: str,
    description: str,
    expense_date: str,
    db_name: str = DB_FILENAME,
) -> bool:
    """Update an expense; return False when the ID does not exist."""
    connection = get_connection(db_name)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE expenses
            SET amount = ?, category = ?, description = ?, date = ?
            WHERE id = ?
            """,
            (
                amount,
                category.strip(),
                description.strip(),
                expense_date.strip(),
                expense_id,
            ),
        )
        connection.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        connection.rollback()
        raise RuntimeError(f"Failed to update expense #{expense_id}: {exc}") from exc
    finally:
        connection.close()


def delete_expense(expense_id: int, db_name: str = DB_FILENAME) -> bool:
    """Delete an expense; return False when the ID does not exist."""
    connection = get_connection(db_name)
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        connection.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        connection.rollback()
        raise RuntimeError(f"Failed to delete expense #{expense_id}: {exc}") from exc
    finally:
        connection.close()


def set_budget(
    month: str,
    budget_amount: float,
    db_name: str = DB_FILENAME,
) -> None:
    """Insert or replace the budget for a month represented as YYYY-MM."""
    connection = get_connection(db_name)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO budgets (month, budget_amount)
            VALUES (?, ?)
            ON CONFLICT(month)
            DO UPDATE SET budget_amount = excluded.budget_amount
            """,
            (month, budget_amount),
        )
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise RuntimeError(f"Failed to set budget for {month}: {exc}") from exc
    finally:
        connection.close()


def get_budget(month: str, db_name: str = DB_FILENAME) -> float:
    """Return a month's budget, or 0.0 when no budget has been saved."""
    connection = get_connection(db_name)
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT budget_amount FROM budgets WHERE month = ?",
            (month,),
        )
        row = cursor.fetchone()
        return float(row["budget_amount"]) if row else 0.0
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to fetch budget for {month}: {exc}") from exc
    finally:
        connection.close()


def get_available_months(db_name: str = DB_FILENAME) -> list[str]:
    """Return months found in either expenses or saved budgets, newest first."""
    connection = get_connection(db_name)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT DISTINCT strftime('%Y-%m', date) AS month
            FROM expenses
            WHERE date IS NOT NULL
            UNION
            SELECT month AS month FROM budgets
            ORDER BY month DESC
            """
        )
        return [row["month"] for row in cursor.fetchall() if row["month"]]
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to get available months: {exc}") from exc
    finally:
        connection.close()
