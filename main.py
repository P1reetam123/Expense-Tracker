"""
main.py - Application entry point for Personal Expense Tracker.
"""

import tkinter as tk
from expense_tracker import ExpenseTrackerApp


def main() -> None:
    root = tk.Tk()
    ExpenseTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()