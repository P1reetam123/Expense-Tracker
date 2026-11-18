"""
seed_data.py - Optional sample data for a classroom demonstration.

Running this script populates an empty database. It never overwrites existing
expense records. Normal application startup creates an empty database instead.
"""

from datetime import date

import database as db
from calculations import EXPENSE_CATEGORIES


def _date_in_current_month(day: int) -> str:
    today = date.today()
    return date(today.year, today.month, day).isoformat()


SAMPLE_EXPENSES = [
    (150.00, "Food & Canteen", "College cafeteria lunch", _date_in_current_month(2)),
    (850.00, "Books & Stationery", "Data Structures textbook", _date_in_current_month(4)),
    (60.00, "Travel & Bus", "Bus fare to campus", _date_in_current_month(5)),
    (450.00, "Food & Canteen", "Dinner with project group", _date_in_current_month(8)),
    (1200.00, "Other", "Scientific calculator and USB drive", _date_in_current_month(10)),
    (4500.00, "Hostel & Rent", "Hostel accommodation share", _date_in_current_month(11)),
    (300.00, "Entertainment", "Movie ticket with friends", _date_in_current_month(12)),
    (180.00, "Food & Canteen", "Snacks and coffee at library", _date_in_current_month(14)),
    (500.00, "Course Fees", "Online Python course", _date_in_current_month(15)),
    (250.00, "Personal & Medical", "Pharmacy purchase", _date_in_current_month(16)),
]


def seed(db_name: str = db.DB_FILENAME) -> None:
    """Populate sample records only when the target database has no expenses."""
    db.init_db(db_name)
    if db.get_all_expenses(db_name=db_name):
        print("Database already contains expenses. Sample data was not added.")
        return

    for amount, category, description, expense_date in SAMPLE_EXPENSES:
        if category not in EXPENSE_CATEGORIES:
            raise ValueError(f"Unknown sample category: {category}")
        db.add_expense(amount, category, description, expense_date, db_name)

    current_month = date.today().strftime("%Y-%m")
    db.set_budget(current_month, 9000.00, db_name)
    print(
        f"Added {len(SAMPLE_EXPENSES)} sample expenses and a "
        f"₹9,000.00 budget for {current_month}."
    )


if __name__ == "__main__":
    seed()
