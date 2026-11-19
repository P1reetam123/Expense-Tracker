"""
database.py - SQLite persistence layer using a transactional context manager.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

from models import (
    BudgetAdjustment,
    CarryforwardMode,
    DEFAULT_CATEGORIES,
    Expense,
    PersistenceError,
)


DB_FILENAME = Path(__file__).resolve().with_name("expenses.db")
SCHEMA_VERSION = 2


@contextmanager
def db_session(
    db_path: str | Path = DB_FILENAME,
    *,
    write: bool = False,
) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection, commit/rollback on writes, and always close."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as exc:
        raise PersistenceError(f"Could not open database '{db_path}': {exc}") from exc

    try:
        yield conn
        if write:
            conn.commit()
    except sqlite3.Error as exc:
        if write:
            conn.rollback()
        raise PersistenceError(f"Database operation failed: {exc}") from exc
    finally:
        conn.close()


def init_db(db_path: str | Path = DB_FILENAME) -> None:
    """Create schema v2 tables, indexes, default categories, and settings."""
    with db_session(db_path, write=True) as conn:
        cur = conn.cursor()
        version = cur.execute("PRAGMA user_version").fetchone()[0]

        if version == 0:
            # Cleanly reset any pre-v2 legacy tables if present.
            cur.execute("DROP TABLE IF EXISTS expenses")
            cur.execute("DROP TABLE IF EXISTS budgets")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_paise INTEGER NOT NULL CHECK(amount_paise > 0),
                discount_paise INTEGER NOT NULL DEFAULT 0 CHECK(discount_paise >= 0),
                category TEXT NOT NULL,
                payment_mode TEXT NOT NULL DEFAULT 'UPI',
                description TEXT NOT NULL DEFAULT '',
                date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date DESC, id DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)"
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                month TEXT PRIMARY KEY,
                base_budget_paise INTEGER NOT NULL CHECK(base_budget_paise > 0)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                amount_paise INTEGER NOT NULL CHECK(amount_paise != 0),
                reason TEXT NOT NULL,
                date TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_adjustments_month ON budget_adjustments(month)"
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                name TEXT PRIMARY KEY,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        # Seed default categories only if the table is empty.
        cat_count = cur.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if cat_count == 0:
            cur.executemany(
                "INSERT INTO categories (name, sort_order) VALUES (?, ?)",
                [(name, idx) for idx, name in enumerate(DEFAULT_CATEGORIES)],
            )

        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ("carryforward_mode", CarryforwardMode.BOTH.value),
        )
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ("default_budget_paise", "0"),
        )
        cur.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def reset_database(db_path: str | Path = DB_FILENAME) -> None:
    """Flush all user data and re-initialize a clean database."""
    path = Path(db_path)
    if path.exists():
        path.unlink()
    init_db(db_path)


def _row_to_expense(row: sqlite3.Row) -> Expense:
    return Expense(
        id=row["id"],
        amount_paise=row["amount_paise"],
        discount_paise=row["discount_paise"],
        category=row["category"],
        payment_mode=row["payment_mode"],
        description=row["description"],
        date=row["date"],
    )


# ----------------- EXPENSES CRUD -----------------

def add_expense(
    amount_paise: int,
    category: str,
    description: str,
    expense_date: str,
    *,
    discount_paise: int = 0,
    payment_mode: str = "UPI",
    db_path: str | Path = DB_FILENAME,
) -> int:
    with db_session(db_path, write=True) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO expenses (amount_paise, discount_paise, category, payment_mode, description, date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                amount_paise,
                discount_paise,
                category.strip(),
                payment_mode.strip() or "UPI",
                description.strip(),
                expense_date.strip(),
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def add_expenses_batch(
    rows: Sequence[tuple[int, int, str, str, str, str]],
    db_path: str | Path = DB_FILENAME,
) -> int:
    """
    Insert multiple expenses in a single transaction.
    Tuple order: (amount_paise, discount_paise, category, payment_mode, description, date)
    """
    if not rows:
        return 0
    with db_session(db_path, write=True) as conn:
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO expenses (amount_paise, discount_paise, category, payment_mode, description, date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)


def get_all_expenses(
    month: str | None = None,
    db_path: str | Path = DB_FILENAME,
) -> list[Expense]:
    with db_session(db_path) as conn:
        cur = conn.cursor()
        if month and month.strip().lower() != "all":
            cur.execute(
                """
                SELECT id, amount_paise, discount_paise, category, payment_mode, description, date
                FROM expenses
                WHERE date LIKE ?
                ORDER BY date DESC, id DESC
                """,
                (f"{month.strip()}-%",),
            )
        else:
            cur.execute(
                """
                SELECT id, amount_paise, discount_paise, category, payment_mode, description, date
                FROM expenses
                ORDER BY date DESC, id DESC
                """
            )
        return [_row_to_expense(row) for row in cur.fetchall()]


def get_expense_by_id(
    expense_id: int,
    db_path: str | Path = DB_FILENAME,
) -> Expense | None:
    with db_session(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, amount_paise, discount_paise, category, payment_mode, description, date
            FROM expenses
            WHERE id = ?
            """,
            (expense_id,),
        ).fetchone()
        return _row_to_expense(row) if row else None


def update_expense(
    expense_id: int,
    amount_paise: int,
    category: str,
    description: str,
    expense_date: str,
    *,
    discount_paise: int = 0,
    payment_mode: str = "UPI",
    db_path: str | Path = DB_FILENAME,
) -> bool:
    with db_session(db_path, write=True) as conn:
        cur = conn.execute(
            """
            UPDATE expenses
            SET amount_paise = ?, discount_paise = ?, category = ?,
                payment_mode = ?, description = ?, date = ?
            WHERE id = ?
            """,
            (
                amount_paise,
                discount_paise,
                category.strip(),
                payment_mode.strip() or "UPI",
                description.strip(),
                expense_date.strip(),
                expense_id,
            ),
        )
        return cur.rowcount > 0


def delete_expense(expense_id: int, db_path: str | Path = DB_FILENAME) -> bool:
    with db_session(db_path, write=True) as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return cur.rowcount > 0


def get_existing_expense_counts(
    db_path: str | Path = DB_FILENAME,
) -> Counter[tuple[str, str, str, str, int]]:
    """Return multiset of (date, category_lower, mode_lower, desc_lower, amount_paise)."""
    with db_session(db_path) as conn:
        rows = conn.execute(
            "SELECT date, category, payment_mode, description, amount_paise FROM expenses"
        ).fetchall()
        return Counter(
            (
                r["date"],
                r["category"].lower(),
                r["payment_mode"].lower(),
                r["description"].strip().lower(),
                r["amount_paise"],
            )
            for r in rows
        )

# ----------------- BUDGETS & ADJUSTMENTS -----------------

def set_budget(
    month: str,
    base_budget_paise: int,
    db_path: str | Path = DB_FILENAME,
) -> None:
    with db_session(db_path, write=True) as conn:
        conn.execute(
            """
            INSERT INTO budgets (month, base_budget_paise)
            VALUES (?, ?)
            ON CONFLICT(month)
            DO UPDATE SET base_budget_paise = excluded.base_budget_paise
            """,
            (month, base_budget_paise),
        )


def get_budget(month: str, db_path: str | Path = DB_FILENAME) -> int:
    with db_session(db_path) as conn:
        row = conn.execute(
            "SELECT base_budget_paise FROM budgets WHERE month = ?",
            (month,),
        ).fetchone()
        return row["base_budget_paise"] if row else 0


def get_all_budgets(db_path: str | Path = DB_FILENAME) -> dict[str, int]:
    with db_session(db_path) as conn:
        rows = conn.execute(
            "SELECT month, base_budget_paise FROM budgets ORDER BY month ASC"
        ).fetchall()
        return {row["month"]: row["base_budget_paise"] for row in rows}


def add_adjustment(
    month: str,
    amount_paise: int,
    reason: str,
    adj_date: str,
    db_path: str | Path = DB_FILENAME,
) -> int:
    with db_session(db_path, write=True) as conn:
        cur = conn.execute(
            """
            INSERT INTO budget_adjustments (month, amount_paise, reason, date)
            VALUES (?, ?, ?, ?)
            """,
            (month, amount_paise, reason.strip(), adj_date),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_adjustments(
    month: str | None = None,
    db_path: str | Path = DB_FILENAME,
) -> list[BudgetAdjustment]:
    with db_session(db_path) as conn:
        if month and month.strip().lower() != "all":
            rows = conn.execute(
                """
                SELECT id, month, amount_paise, reason, date
                FROM budget_adjustments
                WHERE month = ?
                ORDER BY date DESC, id DESC
                """,
                (month.strip(),),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, month, amount_paise, reason, date
                FROM budget_adjustments
                ORDER BY date DESC, id DESC
                """
            ).fetchall()
        return [
            BudgetAdjustment(
                id=r["id"],
                month=r["month"],
                amount_paise=r["amount_paise"],
                reason=r["reason"],
                date=r["date"],
            )
            for r in rows
        ]


def delete_adjustment(adjustment_id: int, db_path: str | Path = DB_FILENAME) -> bool:
    with db_session(db_path, write=True) as conn:
        cur = conn.execute(
            "DELETE FROM budget_adjustments WHERE id = ?", (adjustment_id,)
        )
        return cur.rowcount > 0


# ----------------- CATEGORIES & SETTINGS -----------------

def get_categories(db_path: str | Path = DB_FILENAME) -> list[str]:
    with db_session(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM categories ORDER BY sort_order ASC, name ASC"
        ).fetchall()
        return [r["name"] for r in rows]


def add_category(name: str, db_path: str | Path = DB_FILENAME) -> bool:
    clean = name.strip()
    if not clean:
        return False
    with db_session(db_path, write=True) as conn:
        existing = conn.execute(
            "SELECT 1 FROM categories WHERE LOWER(name) = LOWER(?)", (clean,)
        ).fetchone()
        if existing:
            return False
        next_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM categories"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO categories (name, sort_order) VALUES (?, ?)",
            (clean, next_order),
        )
        return True

def rename_category(
    old_name: str, new_name: str, db_path: str | Path = DB_FILENAME
) -> bool:
    clean_new = new_name.strip()
    if not old_name or old_name == "Other" or not clean_new:
        return False
    if old_name == clean_new:
        return False
    with db_session(db_path, write=True) as conn:
        conflict = conn.execute(
            "SELECT 1 FROM categories WHERE LOWER(name) = LOWER(?) AND name != ?",
            (clean_new, old_name),
        ).fetchone()
        if conflict:
            return False
        cur = conn.execute(
            "UPDATE categories SET name = ? WHERE name = ?",
            (clean_new, old_name),
        )
        if cur.rowcount == 0:
            return False
        conn.execute(
            "UPDATE expenses SET category = ? WHERE category = ?",
            (clean_new, old_name),
        )
        return True

def delete_category(name: str, db_path: str | Path = DB_FILENAME) -> bool:
    if name == "Other":
        return False
    with db_session(db_path, write=True) as conn:
        # Reassign existing expenses safely to 'Other' before deleting category.
        conn.execute(
            "UPDATE expenses SET category = 'Other' WHERE category = ?", (name,)
        )
        cur = conn.execute("DELETE FROM categories WHERE name = ?", (name,))
        return cur.rowcount > 0


def get_setting(
    key: str, default: str = "", db_path: str | Path = DB_FILENAME
) -> str:
    with db_session(db_path) as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default


def set_setting(
    key: str, value: str, db_path: str | Path = DB_FILENAME
) -> None:
    with db_session(db_path, write=True) as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


def get_carryforward_mode(db_path: str | Path = DB_FILENAME) -> CarryforwardMode:
    raw = get_setting("carryforward_mode", CarryforwardMode.BOTH.value, db_path)
    try:
        return CarryforwardMode(raw)
    except ValueError:
        return CarryforwardMode.BOTH


def set_carryforward_mode(
    mode: CarryforwardMode, db_path: str | Path = DB_FILENAME
) -> None:
    set_setting("carryforward_mode", mode.value, db_path)


def get_default_budget_paise(db_path: str | Path = DB_FILENAME) -> int:
    raw = get_setting("default_budget_paise", "0", db_path)
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def set_default_budget_paise(
    paise: int, db_path: str | Path = DB_FILENAME
) -> None:
    set_setting("default_budget_paise", str(max(0, paise)), db_path)


def get_available_months(db_path: str | Path = DB_FILENAME) -> list[str]:
    with db_session(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT substr(date, 1, 7) AS month FROM expenses
            UNION
            SELECT month FROM budgets
            UNION
            SELECT month FROM budget_adjustments
            ORDER BY month DESC
            """
        ).fetchall()
        return [r["month"] for r in rows if r["month"]]