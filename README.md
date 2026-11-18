# Student Personal Expense Tracker

A desktop application built with Python, Tkinter, and SQLite. It helps students
record everyday expenses, review monthly spending, and monitor a monthly budget.

## Assignment requirements

This project addresses Problem 4: Personal Expense Tracker.

1. **Add expenses:** Record an amount, category, short description, and date.
2. **View expenses:** Display saved entries in a table and filter by month.
3. **Edit and delete:** Select an existing entry to update it or delete it after confirmation.
4. **Monthly calculations:** Calculate total spending and category-wise totals for the selected month.
5. **Monthly budget:** Save a budget for a selected month and display a warning when spending reaches 90% or exceeds the budget.

## Python concepts demonstrated

- Tkinter widgets and event-driven GUI programming
- SQLite database creation, queries, and CRUD operations
- `datetime` for date defaults and validation
- Dictionaries for category-wise expense aggregation
- Functions, modules, and separation of concerns
- Exception handling and automated unit tests

## Features

- Add, view, edit, and delete expenses.
- Filter entries by month or view all recorded expenses.
- Review total spending and category-wise totals and percentages.
- Set and persist a budget for each month.
- Display healthy, caution (90% or more used), and over-budget warnings.
- Validate expense amounts, categories, dates, and budget inputs.

CSV export is not included in this version.

## Project structure

Expense-Tracker/
├── main.py                  # Application entry point
├── expense_tracker.py       # Tkinter interface and event handlers
├── database.py              # SQLite schema and data operations
├── calculations.py          # Input validation and spending calculations
├── seed_data.py              # Optional sample data for demonstrations
├── test_expense_tracker.py  # Automated tests
├── .gitignore
└── README.md

## Requirements

- Python 3.10 or later
- Tkinter (normally included with standard Python distributions)
- SQLite (included with Python's `sqlite3` module)

No third-party Python packages are required.

## Run the application

Open a terminal in the project directory and run:

python main.py

On first launch, the application creates `expenses.db` and the required tables
beside the Python source files. The database starts empty; sample records are
not inserted automatically.

## Optional demonstration data

To populate a new or empty database with sample student expenses and a sample
monthly budget, run:

python seed_data.py
python main.py

The seed script will not add duplicate sample records when expenses already
exist. The sample dates are generated for the current month.

## Run automated tests

python -m unittest -v

The tests use temporary SQLite databases and do not modify the application's
`expenses.db`.

## Database and generated files

`expenses.db` is created locally when the application is first run. It is not
required to be committed to Git: every group member can generate their own
database by running the application. Use `seed_data.py` when a shared
demonstration dataset is needed. Python cache files and local databases are
excluded through `.gitignore`.
