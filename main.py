# ==============================================================================
# Course Assignment - Problem 4: Personal Expense Tracker
# Group Project (Marks: 20)
# Concepts demonstrated: Tkinter widgets, SQLite, datetime, dictionaries, calculations, exception handling
# ==============================================================================

import tkinter as tk
from expense_tracker import ExpenseTrackerApp

def main():
    root = tk.Tk()
    app = ExpenseTrackerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
