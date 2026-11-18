"""Unit tests for the expense tracker's database and business logic."""

import tempfile
import unittest
from pathlib import Path

import calculations as calc
import database as db
from seed_data import SAMPLE_EXPENSES


class ExpenseTrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = str(Path(self.temp_dir.name) / "test_expenses.db")
        db.init_db(self.test_db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_run_creates_empty_tables_without_demo_data(self):
        self.assertEqual(db.get_all_expenses(db_name=self.test_db), [])
        self.assertEqual(db.get_available_months(self.test_db), [])
        self.assertEqual(db.get_budget("2026-11", self.test_db), 0.0)

    def test_database_crud_and_month_filtering(self):
        expense_id = db.add_expense(
            150.50, "Food & Canteen", "Lunch at canteen", "2026-11-17", self.test_db
        )
        self.assertGreater(expense_id, 0)

        db.add_expense(
            75.00, "Travel & Bus", "Bus fare", "2026-10-30", self.test_db
        )

        november = db.get_all_expenses("2026-11", self.test_db)
        self.assertEqual(len(november), 1)
        self.assertEqual(november[0]["amount"], 150.5)
        self.assertEqual(november[0]["category"], "Food & Canteen")
        self.assertEqual(november[0]["description"], "Lunch at canteen")

        all_expenses = db.get_all_expenses("All", self.test_db)
        self.assertEqual(len(all_expenses), 2)
        self.assertEqual(all_expenses[0]["date"], "2026-11-17")

        updated = db.update_expense(
            expense_id,
            200.00,
            "Food & Canteen",
            "Updated lunch",
            "2026-11-18",
            self.test_db,
        )
        self.assertTrue(updated)
        fetched = db.get_expense_by_id(expense_id, self.test_db)
        self.assertEqual(fetched["amount"], 200.0)
        self.assertEqual(fetched["description"], "Updated lunch")

        self.assertFalse(
            db.update_expense(99999, 1, "Other", "Missing", "2026-11-18", self.test_db)
        )
        self.assertTrue(db.delete_expense(expense_id, self.test_db))
        self.assertFalse(db.delete_expense(expense_id, self.test_db))
        self.assertIsNone(db.get_expense_by_id(expense_id, self.test_db))
        self.assertEqual(len(db.get_all_expenses("2026-11", self.test_db)), 0)

    def test_budget_operations_and_available_months(self):
        db.set_budget("2026-11", 5000.0, self.test_db)
        self.assertEqual(db.get_budget("2026-11", self.test_db), 5000.0)

        db.set_budget("2026-11", 6000.0, self.test_db)
        self.assertEqual(db.get_budget("2026-11", self.test_db), 6000.0)
        self.assertEqual(db.get_available_months(self.test_db), ["2026-11"])

    def test_expense_validation(self):
        amount, category, description, expense_date = calc.validate_expense_inputs(
            "450.75", "  Books & Stationery ", " Python book ", "2026-11-10"
        )
        self.assertEqual(amount, 450.75)
        self.assertEqual(category, "Books & Stationery")
        self.assertEqual(description, "Python book")
        self.assertEqual(expense_date, "2026-11-10")

        invalid_inputs = [
            ("", "Books", "Description", "2026-11-10"),
            ("abc", "Books", "Description", "2026-11-10"),
            ("-50", "Books", "Description", "2026-11-10"),
            ("0", "Books", "Description", "2026-11-10"),
            ("nan", "Books", "Description", "2026-11-10"),
            ("inf", "Books", "Description", "2026-11-10"),
            ("100", "   ", "Description", "2026-11-10"),
            ("100", "Books", "Description", "17/11/2026"),
            ("100", "Books", "Description", "2026-02-31"),
            ("100", "Books", "Description", "2026-1-2"),
        ]
        for values in invalid_inputs:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    calc.validate_expense_inputs(*values)

    def test_budget_validation(self):
        self.assertEqual(calc.validate_budget_input("5000.50"), 5000.50)
        for invalid_budget in ("", "abc", "-1", "0", "nan", "inf"):
            with self.subTest(invalid_budget=invalid_budget):
                with self.assertRaises(ValueError):
                    calc.validate_budget_input(invalid_budget)

    def test_spending_summary_and_category_percentages(self):
        expenses = [
            {"amount": 1000.0, "category": "Hostel & Rent"},
            {"amount": 500.0, "category": "Food & Canteen"},
            {"amount": 500.0, "category": "Food & Canteen"},
            {"amount": 200.0, "category": "Travel & Bus"},
        ]
        summary = calc.compute_spending_summary(expenses, monthly_budget=2500.0)

        self.assertEqual(summary["total_spending"], 2200.0)
        self.assertEqual(summary["category_totals"]["Hostel & Rent"], 1000.0)
        self.assertEqual(summary["category_totals"]["Food & Canteen"], 1000.0)
        self.assertEqual(summary["category_totals"]["Travel & Bus"], 200.0)

        percentages = {
            row["category"]: row["percentage"]
            for row in summary["category_breakdown"]
        }
        self.assertAlmostEqual(percentages["Hostel & Rent"], 45.5, places=1)
        self.assertEqual(summary["budget_status"], "healthy")
        self.assertFalse(summary["is_over_budget"])
        self.assertEqual(summary["difference"], 300.0)

    def test_budget_warning_at_ninety_percent_and_above_budget(self):
        caution = calc.compute_spending_summary(
            [{"amount": 4500.0, "category": "Food"}],
            monthly_budget=5000.0,
        )
        self.assertEqual(caution["budget_status"], "caution")
        self.assertIn("90.0%", caution["warning_message"])

        exceeded = calc.compute_spending_summary(
            [
                {"amount": 3500.0, "category": "Course Fees"},
                {"amount": 2000.0, "category": "Hostel & Rent"},
            ],
            monthly_budget=5000.0,
        )
        self.assertEqual(exceeded["budget_status"], "exceeded")
        self.assertTrue(exceeded["is_over_budget"])
        self.assertEqual(exceeded["exceeded_by"], 500.0)
        self.assertIn("₹500.00", exceeded["warning_message"])

    def test_empty_summary_and_missing_budget(self):
        summary = calc.compute_spending_summary([], monthly_budget=0.0)
        self.assertEqual(summary["total_spending"], 0.0)
        self.assertEqual(summary["category_totals"], {})
        self.assertEqual(summary["budget_status"], "no_budget")
        self.assertFalse(summary["is_over_budget"])

    def test_seed_categories_match_gui_categories(self):
        for _amount, category, _description, _expense_date in SAMPLE_EXPENSES:
            self.assertIn(category, calc.EXPENSE_CATEGORIES)

    def test_optional_seed_populates_empty_database_once(self):
        import seed_data

        seed_data.seed(self.test_db)
        seeded_expenses = db.get_all_expenses(db_name=self.test_db)
        self.assertEqual(len(seeded_expenses), len(SAMPLE_EXPENSES))
        self.assertEqual(
            db.get_budget(
                seeded_expenses[0]["date"][:7],
                self.test_db,
            ),
            9000.0,
        )

        # Running it again must not duplicate the demonstration records.
        seed_data.seed(self.test_db)
        self.assertEqual(
            len(db.get_all_expenses(db_name=self.test_db)),
            len(SAMPLE_EXPENSES),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
