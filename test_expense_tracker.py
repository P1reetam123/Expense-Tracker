"""
test_expense_tracker.py - Automated tests for Personal Expense Tracker
Tests:
- Database CRUD (Add, Retrieve, Update, Delete)
- Date validation & formatting
- Category-wise dictionary aggregation
- Spending calculations & percentage computation
- Budget warning triggers (under budget, approaching budget, exceeded budget)
- Exception handling for invalid inputs
"""

import unittest
import os
import sqlite3
from datetime import datetime

import database as db
import calculations as calc

TEST_DB = "test_expenses.db"


class TestExpenseTracker(unittest.TestCase):
    def setUp(self):
        # Use an isolated test database
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        db.init_db(TEST_DB)

    def tearDown(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_database_crud(self):
        # 1. Add Expense
        exp_id = db.add_expense(150.50, "Food & Dining", "Lunch at canteen", "2026-11-17", TEST_DB)
        self.assertIsInstance(exp_id, int)
        self.assertGreater(exp_id, 0)

        # 2. Retrieve All Expenses
        expenses = db.get_all_expenses("2026-11", TEST_DB)
        self.assertEqual(len(expenses), 1)
        self.assertEqual(expenses[0]["amount"], 150.50)
        self.assertEqual(expenses[0]["category"], "Food & Dining")
        self.assertEqual(expenses[0]["description"], "Lunch at canteen")
        self.assertEqual(expenses[0]["date"], "2026-11-17")

        # 3. Update Expense
        updated = db.update_expense(exp_id, 200.00, "Food & Dining", "Buffet lunch", "2026-11-17", TEST_DB)
        self.assertTrue(updated)
        fetched = db.get_expense_by_id(exp_id, TEST_DB)
        self.assertEqual(fetched["amount"], 200.00)
        self.assertEqual(fetched["description"], "Buffet lunch")

        # 4. Delete Expense
        deleted = db.delete_expense(exp_id, TEST_DB)
        self.assertTrue(deleted)
        self.assertEqual(len(db.get_all_expenses("2026-11", TEST_DB)), 0)

    def test_budget_operations(self):
        db.set_budget("2026-11", 5000.0, TEST_DB)
        budget = db.get_budget("2026-11", TEST_DB)
        self.assertEqual(budget, 5000.0)

        # Update budget
        db.set_budget("2026-11", 6000.0, TEST_DB)
        budget_updated = db.get_budget("2026-11", TEST_DB)
        self.assertEqual(budget_updated, 6000.0)

    def test_input_validation_and_exceptions(self):
        # Valid input
        amt, cat, desc, dt = calc.validate_expense_inputs("450.75", "Books", "Python book", "2026-11-10")
        self.assertEqual(amt, 450.75)
        self.assertEqual(cat, "Books")
        self.assertEqual(dt, "2026-11-10")

        # Empty category should raise ValueError
        with self.assertRaises(ValueError):
            calc.validate_expense_inputs("100", "   ", "Desc", "2026-11-10")

        # Invalid amount (string) should raise ValueError
        with self.assertRaises(ValueError):
            calc.validate_expense_inputs("abc", "Books", "Desc", "2026-11-10")

        # Negative amount should raise ValueError
        with self.assertRaises(ValueError):
            calc.validate_expense_inputs("-50", "Books", "Desc", "2026-11-10")

        # Zero amount should raise ValueError
        with self.assertRaises(ValueError):
            calc.validate_expense_inputs("0", "Books", "Desc", "2026-11-10")

        # Invalid date format should raise ValueError
        with self.assertRaises(ValueError):
            calc.validate_expense_inputs("100", "Books", "Desc", "17/11/2026")

        # Non-existent date (e.g. Feb 31) should raise ValueError
        with self.assertRaises(ValueError):
            calc.validate_expense_inputs("100", "Books", "Desc", "2026-02-31")

    def test_spending_summary_and_category_breakdown(self):
        sample_expenses = [
            {"amount": 1000.0, "category": "Hostel / Rent"},
            {"amount": 500.0, "category": "Food & Dining"},
            {"amount": 500.0, "category": "Food & Dining"},
            {"amount": 200.0, "category": "Travel"},
        ]
        summary = calc.compute_spending_summary(sample_expenses, monthly_budget=2500.0)

        # Check total calculation
        self.assertEqual(summary["total_spending"], 2200.0)

        # Check dictionary category totals
        cat_totals = summary["category_totals"]
        self.assertEqual(cat_totals["Hostel / Rent"], 1000.0)
        self.assertEqual(cat_totals["Food & Dining"], 1000.0)
        self.assertEqual(cat_totals["Travel"], 200.0)

        # Check percentages
        breakdown = {b["category"]: b["percentage"] for b in summary["category_breakdown"]}
        self.assertAlmostEqual(breakdown["Hostel / Rent"], (1000.0 / 2200.0) * 100, places=1)

        # Check budget warning: total 2200 <= budget 2500 -> not over budget
        self.assertFalse(summary["is_over_budget"])

    def test_budget_warning_exceeded(self):
        sample_expenses = [
            {"amount": 3500.0, "category": "Tuition"},
            {"amount": 2000.0, "category": "Rent"},
        ]
        # Total = 5500, Budget = 5000 -> Exceeded by 500
        summary = calc.compute_spending_summary(sample_expenses, monthly_budget=5000.0)

        self.assertTrue(summary["is_over_budget"])
        self.assertIn("exceeds budget", summary["warning_message"])
        self.assertIn("₹500.00", summary["warning_message"])


if __name__ == "__main__":
    unittest.main()
