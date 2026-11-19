"""
seed_data.py - Exhaustive multi-month dataset exercising all application features:
- 4 chronological months (Healthy, Over Budget, Caution >=90%, Current Month)
- Surplus & deficit carryforward chains
- Both positive allowances and negative deductions
- All 8 default categories, all 4 payment modes, and coupon discounts

Usage:
    python seed_data.py          # Seed only if database is empty
    python seed_data.py --reset  # Flush database and seed fresh data
"""

from __future__ import annotations

import sys
from datetime import date

import database as db
from models import parse_rupees_to_paise


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


def _ym(delta_months: int) -> str:
    today = date.today()
    y, m = _shift_month(today.year, today.month, delta_months)
    return f"{y:04d}-{m:02d}"


def _d(delta_months: int, day: int) -> str:
    today = date.today()
    y, m = _shift_month(today.year, today.month, delta_months)
    return date(y, m, day).isoformat()


def seed(db_path=db.DB_FILENAME, *, reset: bool = False) -> None:
    if reset:
        db.reset_database(db_path)
    else:
        db.init_db(db_path)

    if db.get_all_expenses(db_path=db_path):
        print("Database already contains expenses. Run with --reset to overwrite.")
        return

    m3, m2, m1, m0 = _ym(-3), _ym(-2), _ym(-1), _ym(0)

    # M-3: Base ₹6,000, Spent ₹5,200 -> +₹800 surplus carries into M-2 (Healthy)
    db.set_budget(m3, parse_rupees_to_paise("6000"), db_path)

    # M-2: Base ₹6,500 + ₹800 carry - ₹500 deduction = ₹6,800 effective; Spent ₹7,450 -> -₹650 deficit (Over Budget)
    db.set_budget(m2, parse_rupees_to_paise("6500"), db_path)
    db.add_adjustment(m2, -parse_rupees_to_paise("500"), "Moved to emergency savings", _d(-2, 5), db_path)

    # M-1: Base ₹8,000 - ₹650 carry + ₹1,000 allowance = ₹8,350 effective; Spent ₹7,600 (91.0% -> Caution >=90%) -> +₹750 surplus
    db.set_budget(m1, parse_rupees_to_paise("8000"), db_path)
    db.add_adjustment(m1, parse_rupees_to_paise("1000"), "Lab TA stipend", _d(-1, 6), db_path)

    # M-0 (Current): Base ₹9,000 + ₹750 carry + ₹1,500 allowance = ₹11,250 effective
    db.set_budget(m0, parse_rupees_to_paise("9000"), db_path)
    db.add_adjustment(m0, parse_rupees_to_paise("1500"), "Freelance automation script", _d(0, 4), db_path)

    samples = [
        # M-3 (Total: ₹5,200.00)
        ("3800.00", "0", "Hostel & Rent", "Bank", "Monthly hostel room fee", _d(-3, 2)),
        ("1100.00", "100", "Food & Canteen", "UPI", "Mess card + canteen snacks", _d(-3, 12)),
        ("300.00", "0", "Travel & Bus", "Cash", "Local bus & auto fares", _d(-3, 21)),

        # M-2 (Total: ₹7,450.00 -> Over Budget)
        ("3800.00", "0", "Hostel & Rent", "Bank", "Monthly hostel room fee", _d(-2, 2)),
        ("1850.00", "150", "Food & Canteen", "UPI", "Mess + project team dinner", _d(-2, 10)),
        ("1200.00", "200", "Books & Stationery", "Card", "Operating Systems textbook", _d(-2, 16)),
        ("600.00", "0", "Personal & Medical", "Cash", "Clinic consultation & meds", _d(-2, 23)),

        # M-1 (Total: ₹7,600.00 -> 91.0% Caution)
        ("4200.00", "0", "Hostel & Rent", "Bank", "Hostel fee + laundry", _d(-1, 2)),
        ("1550.00", "120", "Food & Canteen", "UPI", "Cafeteria meals", _d(-1, 9)),
        ("950.00", "50", "Course Fees", "Card", "Cloud certification mock test", _d(-1, 15)),
        ("550.00", "0", "Entertainment", "UPI", "Concert & snacks", _d(-1, 20)),
        ("350.00", "0", "Travel & Bus", "Cash", "Metro smart card recharge", _d(-1, 25)),

        # M-0 Current Month (Total: ₹6,989.50 across all 8 categories & 4 modes)
        ("4200.00", "0", "Hostel & Rent", "Bank", "Monthly hostel rent", _d(0, 1)),
        ("340.50", "60", "Food & Canteen", "UPI", "Canteen lunch combo (coupon)", _d(0, 3)),
        ("780.00", "120", "Books & Stationery", "Card", "Algorithms & lab notebooks", _d(0, 5)),
        ("190.00", "0", "Travel & Bus", "Cash", "Bus pass + metro fare", _d(0, 7)),
        ("499.00", "100", "Course Fees", "UPI", "Python architecture workshop", _d(0, 9)),
        ("280.00", "40", "Entertainment", "UPI", "Weekend movie ticket", _d(0, 11)),
        ("220.00", "0", "Personal & Medical", "Cash", "Pharmacy essentials", _d(0, 13)),
        ("480.00", "50", "Other", "Card", "USB-C hub for laptop", _d(0, 15)),
    ]

    batch = [
        (
            parse_rupees_to_paise(amt),
            parse_rupees_to_paise(disc, allow_zero=True),
            cat,
            mode,
            desc,
            dt,
        )
        for amt, disc, cat, mode, desc, dt in samples
    ]
    db.add_expenses_batch(batch, db_path)
    print(f"Seeded {len(batch)} expenses & 4 months ({m3} -> {m0}) into {db_path}.")


if __name__ == "__main__":
    seed(reset=("--reset" in sys.argv))