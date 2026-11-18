# ==============================================================================
# Course Assignment - Marks: 20
# Problem 4: Personal Expense Tracker
# Description: GUI application to record everyday student expenses and monitor budget.
# Concepts used: Tkinter widgets, SQLite, datetime, dictionaries, calculations, exception handling.
# ==============================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, date

# Database file name
DB_NAME = "expenses.db"


# ------------------------------------------------------------------------------
# 1. DATABASE FUNCTIONS (SQLite)
# ------------------------------------------------------------------------------

def init_database():
    """Create expenses and budget tables if they do not exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Table to store individual expenses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL
        )
    """)

    # Table to store monthly budget (format: YYYY-MM)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            month TEXT PRIMARY KEY,
            budget_amount REAL NOT NULL
        )
    """)

    conn.commit()

    # Add a few default sample student expenses if table is completely empty
    cursor.execute("SELECT COUNT(*) FROM expenses")
    count = cursor.fetchone()[0]
    if count == 0:
        sample_data = [
            (120.0, "Food & Canteen", "Lunch at college canteen", "2026-11-02"),
            (450.0, "Books & Stationery", "Notebooks and pens", "2026-11-05"),
            (50.0, "Travel & Bus", "Bus fare to university", "2026-11-07"),
            (3500.0, "Hostel & Rent", "Hostel room sharing", "2026-11-10"),
            (250.0, "Food & Canteen", "Evening snacks with friends", "2026-11-12"),
            (800.0, "Course Fees", "Online Python workshop", "2026-11-15"),
        ]
        cursor.executemany("""
            INSERT INTO expenses (amount, category, description, date)
            VALUES (?, ?, ?, ?)
        """, sample_data)

        # Set default budget for demo
        cursor.execute("INSERT OR REPLACE INTO budgets (month, budget_amount) VALUES (?, ?)", ("2026-11", 6000.0))
        conn.commit()

    conn.close()


def add_expense_to_db(amount, category, description, expense_date):
    """Insert a new expense row into the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses (amount, category, description, date)
        VALUES (?, ?, ?, ?)
    """, (amount, category, description, expense_date))
    conn.commit()
    conn.close()


def fetch_expenses(selected_month=None):
    """
    Fetch expenses from the database.
    If a month is selected, filter by that month (e.g. '2026-11').
    Returns list of rows as tuples: (id, amount, category, description, date).
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if selected_month and selected_month != "All":
        cursor.execute("""
            SELECT id, amount, category, description, date 
            FROM expenses 
            WHERE strftime('%Y-%m', date) = ?
            ORDER BY date DESC, id DESC
        """, (selected_month,))
    else:
        cursor.execute("""
            SELECT id, amount, category, description, date 
            FROM expenses 
            ORDER BY date DESC, id DESC
        """)

    rows = cursor.fetchall()
    conn.close()
    return rows


def update_expense_in_db(expense_id, amount, category, description, expense_date):
    """Update an existing expense in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE expenses
        SET amount = ?, category = ?, description = ?, date = ?
        WHERE id = ?
    """, (amount, category, description, expense_date, expense_id))
    conn.commit()
    conn.close()


def delete_expense_from_db(expense_id):
    """Delete an expense record by its ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def save_budget_to_db(month, budget_amount):
    """Save or update monthly budget in SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO budgets (month, budget_amount)
        VALUES (?, ?)
        ON CONFLICT(month) DO UPDATE SET budget_amount = excluded.budget_amount
    """, (month, budget_amount))
    conn.commit()
    conn.close()


def get_budget_from_db(month):
    """Retrieve monthly budget amount from database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT budget_amount FROM budgets WHERE month = ?", (month,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0.0


def get_available_months():
    """Get all unique months present in expenses and budget."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT strftime('%Y-%m', date) FROM expenses WHERE date IS NOT NULL
        UNION
        SELECT month FROM budgets
        ORDER BY 1 DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]


# ------------------------------------------------------------------------------
# 2. GUI APPLICATION (Tkinter Widgets, Dictionaries, Calculations, & Exception Handling)
# ------------------------------------------------------------------------------

class ExpenseTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Personal Expense Tracker")
        self.root.geometry("1000x680")
        self.root.minsize(900, 600)

        # Track which expense ID is currently being edited (None if adding new)
        self.selected_expense_id = None

        # Pre-defined student categories
        self.categories = [
            "Food & Canteen",
            "Books & Stationery",
            "Hostel & Rent",
            "Travel & Bus",
            "Course Fees",
            "Entertainment",
            "Personal & Medical",
            "Other"
        ]

        # Initialize SQLite database
        init_database()

        # Build user interface
        self.create_gui()

        # Load initial data
        self.update_month_dropdown()
        self.load_expenses_and_totals()

    def create_gui(self):
        # 1. Header Title Banner
        header = tk.Frame(self.root, bg="#2c3e50", pady=12)
        header.pack(fill=tk.X)
        title_label = tk.Label(
            header,
            text="Personal Expense Tracker",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack()
        subtitle = tk.Label(
            header,
            text="Track daily student spending, view category breakdown, and manage monthly budget",
            font=("Arial", 9),
            bg="#2c3e50",
            fg="#ecf0f1"
        )
        subtitle.pack()

        # Main Body (Split into Left Side: Inputs, Right Side: Tables & Summaries)
        body = tk.Frame(self.root, padx=10, pady=10)
        body.pack(fill=tk.BOTH, expand=True)

        left_panel = tk.Frame(body, width=340)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        right_panel = tk.Frame(body)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # ----------------- LEFT PANEL: FORM & BUDGET -----------------
        # Form Frame
        self.form_frame = tk.LabelFrame(left_panel, text=" Add / Edit Expense ", font=("Arial", 10, "bold"), padx=10, pady=10)
        self.form_frame.pack(fill=tk.X, pady=(0, 10))

        # Amount
        tk.Label(self.form_frame, text="Amount (Rs.):", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.amount_entry = ttk.Entry(self.form_frame, font=("Arial", 10))
        self.amount_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)

        # Category
        tk.Label(self.form_frame, text="Category:", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.category_cb = ttk.Combobox(self.form_frame, values=self.categories, state="readonly", font=("Arial", 9))
        self.category_cb.grid(row=1, column=1, sticky=tk.EW, pady=5)
        self.category_cb.current(0)

        # Description
        tk.Label(self.form_frame, text="Description:", font=("Arial", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.desc_entry = ttk.Entry(self.form_frame, font=("Arial", 10))
        self.desc_entry.grid(row=2, column=1, sticky=tk.EW, pady=5)

        # Date
        tk.Label(self.form_frame, text="Date (YYYY-MM-DD):", font=("Arial", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5)
        date_box = tk.Frame(self.form_frame)
        date_box.grid(row=3, column=1, sticky=tk.EW, pady=5)

        self.date_entry = ttk.Entry(date_box, font=("Arial", 10))
        self.date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.date_entry.insert(0, date.today().strftime("%Y-%m-%d"))

        today_btn = ttk.Button(date_box, text="Today", width=6, command=self.set_today_date)
        today_btn.pack(side=tk.RIGHT, padx=(4, 0))

        self.form_frame.columnconfigure(1, weight=1)

        # Buttons (Add/Save and Clear)
        btn_box = tk.Frame(self.form_frame)
        btn_box.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(10, 0))

        self.submit_btn = tk.Button(
            btn_box,
            text="Add Expense",
            bg="#27ae60",
            fg="white",
            font=("Arial", 9, "bold"),
            relief=tk.RAISED,
            command=self.save_expense
        )
        self.submit_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.clear_btn = tk.Button(
            btn_box,
            text="Clear",
            bg="#bdc3c7",
            font=("Arial", 9),
            command=self.reset_form
        )
        self.clear_btn.pack(side=tk.RIGHT)

        # Budget Frame
        budget_box = tk.LabelFrame(left_panel, text=" Monthly Budget ", font=("Arial", 10, "bold"), padx=10, pady=10)
        budget_box.pack(fill=tk.X)

        tk.Label(budget_box, text="Set budget for the selected month to get alerts when spending exceeds it.", font=("Arial", 8), fg="#555", wraplength=300).pack(pady=(0, 6))
        
        b_input_box = tk.Frame(budget_box)
        b_input_box.pack(fill=tk.X)

        tk.Label(b_input_box, text="Budget (Rs.):", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        self.budget_entry = ttk.Entry(b_input_box, width=12, font=("Arial", 9))
        self.budget_entry.pack(side=tk.LEFT, padx=6)

        save_budget_btn = tk.Button(
            b_input_box,
            text="Save Budget",
            bg="#2980b9",
            fg="white",
            font=("Arial", 9, "bold"),
            command=self.save_budget
        )
        save_budget_btn.pack(side=tk.LEFT)

        # ----------------- RIGHT PANEL: FILTER, CARDS, TABLE -----------------
        # Filter Bar
        filter_frame = tk.Frame(right_panel)
        filter_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Label(filter_frame, text="Select Month:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.month_var = tk.StringVar(value=date.today().strftime("%Y-%m"))
        self.month_dropdown = ttk.Combobox(filter_frame, textvariable=self.month_var, state="readonly", width=12)
        self.month_dropdown.pack(side=tk.LEFT, padx=(0, 8))
        self.month_dropdown.bind("<<ComboboxSelected>>", lambda e: self.load_expenses_and_totals())

        refresh_btn = ttk.Button(filter_frame, text="Refresh", command=self.load_expenses_and_totals)
        refresh_btn.pack(side=tk.LEFT)

        # KPI Summary Cards (Total Spending, Budget, Remaining)
        cards_frame = tk.Frame(right_panel)
        cards_frame.pack(fill=tk.X, pady=(0, 8))

        # Card 1: Total Spending
        c1 = tk.Frame(cards_frame, bg="#ecf0f1", relief=tk.GROOVE, bd=2, padx=10, pady=6)
        c1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Label(c1, text="TOTAL SPENT", font=("Arial", 8, "bold"), bg="#ecf0f1", fg="#7f8c8d").pack(anchor=tk.W)
        self.total_spent_label = tk.Label(c1, text="Rs. 0.00", font=("Arial", 13, "bold"), bg="#ecf0f1", fg="#2c3e50")
        self.total_spent_label.pack(anchor=tk.W)

        # Card 2: Budget
        c2 = tk.Frame(cards_frame, bg="#ecf0f1", relief=tk.GROOVE, bd=2, padx=10, pady=6)
        c2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Label(c2, text="MONTHLY BUDGET", font=("Arial", 8, "bold"), bg="#ecf0f1", fg="#7f8c8d").pack(anchor=tk.W)
        self.budget_label = tk.Label(c2, text="Rs. 0.00", font=("Arial", 13, "bold"), bg="#ecf0f1", fg="#27ae60")
        self.budget_label.pack(anchor=tk.W)

        # Card 3: Remaining / Overspent
        c3 = tk.Frame(cards_frame, bg="#ecf0f1", relief=tk.GROOVE, bd=2, padx=10, pady=6)
        c3.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.status_title_label = tk.Label(c3, text="REMAINING", font=("Arial", 8, "bold"), bg="#ecf0f1", fg="#7f8c8d")
        self.status_title_label.pack(anchor=tk.W)
        self.balance_label = tk.Label(c3, text="Rs. 0.00", font=("Arial", 13, "bold"), bg="#ecf0f1", fg="#2980b9")
        self.balance_label.pack(anchor=tk.W)

        # Budget Warning Banner (Turns Red when spending exceeds budget)
        self.warning_banner = tk.Label(
            right_panel,
            text="",
            font=("Arial", 9, "bold"),
            pady=5
        )
        self.warning_banner.pack(fill=tk.X, pady=(0, 6))

        # Tabs: Tab 1 = Expenses Table, Tab 2 = Category-wise Totals
        notebook = ttk.Notebook(right_panel)
        notebook.pack(fill=tk.BOTH, expand=True)

        # TAB 1: Expenses Table
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text=" All Expenses ")

        columns = ("id", "date", "category", "description", "amount")
        self.expense_tree = ttk.Treeview(tab1, columns=columns, show="headings", selectmode="browse")
        self.expense_tree.heading("id", text="ID")
        self.expense_tree.heading("date", text="Date")
        self.expense_tree.heading("category", text="Category")
        self.expense_tree.heading("description", text="Description")
        self.expense_tree.heading("amount", text="Amount (Rs.)")

        self.expense_tree.column("id", width=40, anchor=tk.CENTER)
        self.expense_tree.column("date", width=90, anchor=tk.CENTER)
        self.expense_tree.column("category", width=140)
        self.expense_tree.column("description", width=220)
        self.expense_tree.column("amount", width=100, anchor=tk.E)

        scrollbar = ttk.Scrollbar(tab1, orient=tk.VERTICAL, command=self.expense_tree.yview)
        self.expense_tree.configure(yscrollcommand=scrollbar.set)

        self.expense_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Edit & Delete Buttons below Table
        action_bar = tk.Frame(right_panel, pady=6)
        action_bar.pack(fill=tk.X)

        edit_btn = tk.Button(
            action_bar,
            text="Edit Selected",
            bg="#f39c12",
            fg="white",
            font=("Arial", 9, "bold"),
            command=self.start_edit_expense
        )
        edit_btn.pack(side=tk.LEFT, padx=(0, 6))

        delete_btn = tk.Button(
            action_bar,
            text="Delete Selected",
            bg="#e74c3c",
            fg="white",
            font=("Arial", 9, "bold"),
            command=self.delete_expense
        )
        delete_btn.pack(side=tk.LEFT)

        self.entries_count_label = tk.Label(action_bar, text="0 entries", font=("Arial", 8, "italic"), fg="#7f8c8d")
        self.entries_count_label.pack(side=tk.RIGHT)

        # TAB 2: Category Totals Breakdown
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text=" Category Totals ")

        cat_cols = ("category", "total", "percentage")
        self.category_tree = ttk.Treeview(tab2, columns=cat_cols, show="headings", selectmode="none")
        self.category_tree.heading("category", text="Category")
        self.category_tree.heading("total", text="Total Spent (Rs.)")
        self.category_tree.heading("percentage", text="% of Spending")

        self.category_tree.column("category", width=200)
        self.category_tree.column("total", width=130, anchor=tk.E)
        self.category_tree.column("percentage", width=110, anchor=tk.E)

        cat_scroll = ttk.Scrollbar(tab2, orient=tk.VERTICAL, command=self.category_tree.yview)
        self.category_tree.configure(yscrollcommand=cat_scroll.set)

        self.category_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cat_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # ----------------- EVENT HANDLERS & LOGIC -----------------

    def set_today_date(self):
        """Set today's date into the date field."""
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, date.today().strftime("%Y-%m-%d"))

    def update_month_dropdown(self):
        """Refresh months list from SQLite data."""
        months = get_available_months()
        current_m = date.today().strftime("%Y-%m")
        if current_m not in months:
            months.insert(0, current_m)
        if "All" not in months:
            months.append("All")
        self.month_dropdown["values"] = months
        if self.month_var.get() not in months:
            self.month_var.set(current_m)

    def save_expense(self):
        """
        Add a new expense or update an existing one.
        Demonstrates Exception Handling with try-except blocks.
        """
        amount_text = self.amount_entry.get().strip()
        category = self.category_cb.get().strip()
        description = self.desc_entry.get().strip()
        date_text = self.date_entry.get().strip()

        # 1. Validation for Amount
        if not amount_text:
            messagebox.showerror("Validation Error", "Please enter an amount.")
            return

        try:
            amount = float(amount_text)
            if amount <= 0:
                messagebox.showerror("Validation Error", "Amount must be greater than zero.")
                return
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid amount. Please enter a valid number (e.g. 150.50).")
            return

        # 2. Validation for Category
        if not category:
            messagebox.showerror("Validation Error", "Please select a category.")
            return

        # 3. Validation for Date using datetime.strptime
        if not date_text:
            messagebox.showerror("Validation Error", "Please enter a date.")
            return

        try:
            valid_date_obj = datetime.strptime(date_text, "%Y-%m-%d")
            valid_date_str = valid_date_obj.strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid date format. Expected format is YYYY-MM-DD (e.g. 2026-11-17).")
            return

        # 4. Save to Database (Insert new or Update existing)
        try:
            if self.selected_expense_id is None:
                # Add new expense
                add_expense_to_db(amount, category, description, valid_date_str)
                messagebox.showinfo("Success", f"Expense of Rs. {amount:.2f} added successfully!")
            else:
                # Update existing expense
                update_expense_in_db(self.selected_expense_id, amount, category, description, valid_date_str)
                messagebox.showinfo("Success", f"Expense #{self.selected_expense_id} updated successfully!")

            self.reset_form()
            self.update_month_dropdown()
            self.load_expenses_and_totals()

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to save expense: {e}")

    def start_edit_expense(self):
        """Loads selected table row into input form for editing."""
        selected_item = self.expense_tree.selection()
        if not selected_item:
            messagebox.showwarning("Select Item", "Please select an expense row from the table to edit.")
            return

        # Extract values from selected row
        values = self.expense_tree.item(selected_item[0], "values")
        self.selected_expense_id = int(values[0])
        exp_date = values[1]
        exp_cat = values[2]
        exp_desc = values[3]
        exp_amt = values[4]

        # Populate form
        self.amount_entry.delete(0, tk.END)
        self.amount_entry.insert(0, str(exp_amt))

        self.category_cb.set(exp_cat)

        self.desc_entry.delete(0, tk.END)
        self.desc_entry.insert(0, exp_desc)

        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, exp_date)

        # Switch button text and style
        self.form_frame.config(text=f" Editing Expense #{self.selected_expense_id} ")
        self.submit_btn.config(text="Save Changes", bg="#f39c12")

    def delete_expense(self):
        """Delete selected expense with user confirmation."""
        selected_item = self.expense_tree.selection()
        if not selected_item:
            messagebox.showwarning("Select Item", "Please select an expense row from the table to delete.")
            return

        values = self.expense_tree.item(selected_item[0], "values")
        expense_id = int(values[0])
        exp_cat = values[2]
        exp_amt = values[4]

        # Confirm before deletion
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete Expense #{expense_id} ({exp_cat} - Rs. {exp_amt})?"
        )
        if not confirm:
            return

        try:
            delete_expense_from_db(expense_id)
            if self.selected_expense_id == expense_id:
                self.reset_form()
            messagebox.showinfo("Deleted", f"Expense #{expense_id} deleted successfully.")
            self.update_month_dropdown()
            self.load_expenses_and_totals()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete expense: {e}")

    def reset_form(self):
        """Clear form and revert back to Add mode."""
        self.selected_expense_id = None
        self.amount_entry.delete(0, tk.END)
        self.category_cb.current(0)
        self.desc_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, date.today().strftime("%Y-%m-%d"))

        self.form_frame.config(text=" Add / Edit Expense ")
        self.submit_btn.config(text="Add Expense", bg="#27ae60")

    def save_budget(self):
        """Save monthly budget entered by the student."""
        month = self.month_var.get()
        if not month or month == "All":
            messagebox.showwarning("Select Month", "Please select a specific month (e.g. 2026-11) to set a budget.")
            return

        budget_text = self.budget_entry.get().strip()
        if not budget_text:
            messagebox.showerror("Input Error", "Please enter a budget amount.")
            return

        try:
            budget = float(budget_text)
            if budget < 0:
                messagebox.showerror("Input Error", "Budget cannot be negative.")
                return

            save_budget_to_db(month, budget)
            messagebox.showinfo("Budget Set", f"Budget for {month} saved as Rs. {budget:,.2f}")
            self.load_expenses_and_totals()

        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid numeric budget amount.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to save budget: {e}")

    def load_expenses_and_totals(self):
        """
        Calculates:
        1. Total spending for the selected month
        2. Category-wise totals using a dictionary
        3. Monthly budget check and warning logic
        """
        month = self.month_var.get()

        # 1. Fetch expenses from SQLite
        expenses = fetch_expenses(month)

        # Clear existing table rows
        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        # Populate table
        for row in expenses:
            exp_id, amt, cat, desc, dt = row
            self.expense_tree.insert("", tk.END, values=(exp_id, dt, cat, desc or "-", f"{amt:.2f}"))

        self.entries_count_label.config(text=f"{len(expenses)} entries found")

        # 2. Compute Total Spending and Category-wise Totals using a Dictionary
        total_spending = 0.0
        category_totals = {}

        for row in expenses:
            amt = float(row[1])
            cat = row[2]
            total_spending += amt

            # Dictionary calculation: count sum per category
            if cat in category_totals:
                category_totals[cat] += amt
            else:
                category_totals[cat] = amt

        # Update Total Spent Card
        self.total_spent_label.config(text=f"Rs. {total_spending:,.2f}")

        # 3. Retrieve and Check Monthly Budget
        monthly_budget = 0.0
        if month and month != "All":
            monthly_budget = get_budget_from_db(month)
            self.budget_entry.delete(0, tk.END)
            if monthly_budget > 0:
                self.budget_entry.insert(0, f"{monthly_budget:.2f}")

        # Update Budget Card
        if monthly_budget > 0:
            self.budget_label.config(text=f"Rs. {monthly_budget:,.2f}")
            difference = monthly_budget - total_spending

            if total_spending > monthly_budget:
                # Exceeded Budget Warning!
                overspent = total_spending - monthly_budget
                self.status_title_label.config(text="OVER BUDGET BY", fg="#c0392b")
                self.balance_label.config(text=f"Rs. {overspent:,.2f}", fg="#c0392b")

                self.warning_banner.config(
                    text=f"WARNING: Monthly spending of Rs. {total_spending:,.2f} exceeds your budget of Rs. {monthly_budget:,.2f} by Rs. {overspent:,.2f}!",
                    bg="#fadbd8",
                    fg="#922b21"
                )
            else:
                # Within Budget
                self.status_title_label.config(text="REMAINING BUDGET", fg="#27ae60")
                self.balance_label.config(text=f"Rs. {difference:,.2f}", fg="#27ae60")

                if monthly_budget > 0 and total_spending >= monthly_budget * 0.9:
                    self.warning_banner.config(
                        text=f"Caution: You have spent {(total_spending/monthly_budget)*100:.1f}% of your budget.",
                        bg="#fdebd0",
                        fg="#b9770e"
                    )
                else:
                    self.warning_banner.config(
                        text=f"Budget Healthy: Rs. {difference:,.2f} remaining for this month.",
                        bg="#d5f5e3",
                        fg="#1e8449"
                    )
        else:
            self.budget_label.config(text="Not Set")
            self.status_title_label.config(text="REMAINING", fg="#7f8c8d")
            self.balance_label.config(text="N/A", fg="#7f8c8d")
            self.warning_banner.config(
                text="No budget set for this month. Set a budget on the left to monitor spending.",
                bg="#f2f3f4",
                fg="#7f8c8d"
            )

        # 4. Populate Category-wise Totals Tab
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)

        # Sort categories by highest spending first
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        for cat, total in sorted_categories:
            percentage = (total / total_spending * 100) if total_spending > 0 else 0
            self.category_tree.insert("", tk.END, values=(cat, f"Rs. {total:,.2f}", f"{percentage:.1f}%"))


# ------------------------------------------------------------------------------
# 3. PROGRAM ENTRY POINT
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = ExpenseTrackerApp(root)
    root.mainloop()
