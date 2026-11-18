"""
seed_data.py - Populates sample everyday student expenses and monthly budget for testing and demonstration.
"""

from datetime import date
import database as db

SAMPLE_EXPENSES = [
    (150.00, "Food & Dining", "College cafeteria lunch", "2026-11-02"),
    (850.00, "Books & Stationery", "Data Structures & Algorithms textbook", "2026-11-04"),
    (60.00, "Travel & Commute", "Metro ticket to campus", "2026-11-05"),
    (450.00, "Food & Dining", "Dinner with project group", "2026-11-08"),
    (1200.00, "Gadgets & Tech", "Scientific calculator and USB drive", "2026-11-10"),
    (4500.00, "Hostel / Rent", "Hostel accommodation monthly share", "2026-11-11"),
    (300.00, "Entertainment", "Movie ticket with friends", "2026-11-12"),
    (180.00, "Food & Dining", "Snacks and coffee at library", "2026-11-14"),
    (500.00, "Tuition & Courses", "Online Python certification course fee", "2026-11-15"),
    (250.00, "Health & Medical", "Vitamins & pharmacy medicines", "2026-11-16"),
]


def seed():
    db.init_db()
    existing = db.get_all_expenses()
    if len(existing) == 0:
        print("Seeding initial student expenses...")
        for amount, category, desc, dt in SAMPLE_EXPENSES:
            db.add_expense(amount, category, desc, dt)
        
        # Set a reasonable monthly budget for demonstration
        curr_month = "2026-11"
        db.set_budget(curr_month, 8000.00)
        print(f"Added {len(SAMPLE_EXPENSES)} sample expenses and set budget of Rs. 8,000 for {curr_month}.")
    else:
        print(f"Database already contains {len(existing)} records. Skipping duplicate seeding.")


if __name__ == "__main__":
    seed()
