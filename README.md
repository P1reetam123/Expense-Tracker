# Personal Expense Tracker

A desktop application built with Python, Tkinter, and SQLite. It helps users
record everyday expenses, track coupon savings, manage monthly budgets with
carryforward and mid-month allowances, visualize spending trends, and import or
export records via CSV.

## Features

- **Exact INR Accounting:** Uses `decimal.Decimal` at input boundaries and
  integer paise internally so totals, percentages, and rollovers never suffer
  from floating-point rounding drift.
- **Expense Management:** Add, edit, and delete expenses with amount paid,
  optional coupon/discount saved, category, payment mode (`UPI`, `Cash`,
  `Card`, `Bank`), description, and a popup calendar date picker.
- **Filtering, Search & Sorting:** Filter by month (`YYYY-MM` or `All`), filter
  by category, search live across descriptions/modes (`Ctrl+F`), and sort
  columns ascending or descending.
- **Dynamic Monthly Budgets & Rollover:** Set a planned base budget per month,
  configure month-to-month carryforward (`Off`, `Surplus & Overspend`, or
  `Overspend only`), and optionally set an auto-default budget for new months.
- **Allowances & Adjustments:** Log mid-month budget bonuses/allowances or
  deductions with reasons and dates without overwriting your planned base
  budget, viewable per month or across all months.
- **Visual Analytics & Alerts:** Live budget health progress bar with a 90%
  caution marker, healthy/caution/over-budget alerts, interactive category
  horizontal bar chart, and multi-month budget-vs-spending trend chart.
- **Custom Categories:** Add, rename, and remove expense categories (removed
  categories safely reassign existing entries to `Other`).
- **CSV Template, Bulk Import & Export:** Download an import template, preview
  CSV imports with row-level validation and multiset duplicate detection before
  committing in a single transaction, and export filtered views to UTF-8 CSV.

## Python Concepts Demonstrated

- Tkinter & custom `tk.Canvas` widgets (calendar popup, progress meter, charts)
- Event-driven GUI programming and keyboard shortcuts
- SQLite schema versioning (`PRAGMA user_version`), indexes, CRUD, and batch transactions
- Context managers (`@contextlib.contextmanager`) for safe DB sessions
- Frozen `@dataclass` models, `Enum`, and custom exception hierarchies
- `decimal.Decimal` fixed-point parsing and integer paise currency math
- Generators (`yield`) for streaming CSV validation and export
- Automated unit testing with `unittest` and temporary SQLite databases

## Project Structure

    Expense-Tracker/
    ├── main.py                  # Application entry point
    ├── models.py                # Domain dataclasses, enums, exceptions, and INR formatting
    ├── database.py              # Transactional SQLite persistence, schema & indexes
    ├── calculations.py          # Validation, carryforward engine, summaries, CSV pipelines
    ├── ui_widgets.py            # Popup calendar date field and Canvas-based charts
    ├── dialogs.py               # Allowances, CSV import preview, and settings dialogs
    ├── expense_tracker.py       # Main Tkinter interface, shortcuts, and event handlers
    ├── seed_data.py             # Optional multi-month sample data for demonstrations
    ├── test_expense_tracker.py  # Automated unit test suite
    ├── .gitignore
    └── README.md

## Requirements

- Python 3.10 or later
- Tkinter (included with standard Python distributions)
- SQLite (included with Python's `sqlite3` module)

No third-party Python packages are required.

## Run the Application

Open a terminal in the project directory and run:

    python main.py

On first launch, the application creates `expenses.db` with the required tables,
indexes, default categories, and default settings beside the Python source
files. The database starts empty; sample records are not inserted automatically.

## Keyboard Shortcuts

- `Return` (in expense form fields): Save expense
- `Escape`: Clear form / cancel edit mode
- `Double-click` on a table row: Load expense into edit mode
- `Delete` (on selected table row): Delete expense after confirmation
- `Ctrl+F`: Jump to search box

## Optional Demonstration Data

To populate an empty database with 4 months of sample expenses, budgets,
allowances, and coupon discounts, run:

    python seed_data.py
    python main.py

To flush existing local data and re-seed fresh sample data, run:

    python seed_data.py --reset
    python main.py

## Run Automated Tests

    python -m unittest -v

The tests use temporary SQLite databases and do not modify the application's
`expenses.db`.

## Database and Generated Files

`expenses.db` is created locally when the application is first run and is not
tracked in Git. Python cache files and local databases are excluded through
`.gitignore`.