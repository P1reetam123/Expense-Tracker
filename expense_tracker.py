# ==============================================================================
# Course Assignment - Marks: 20
# Problem 4: Personal Expense Tracker
# Description: GUI application to record everyday student expenses and monitor budget.
# Concepts used: Tkinter widgets, SQLite, datetime, dictionaries, calculations, exception handling.
# ==============================================================================

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

import calculations as calc
import database as db


# ------------------------------------------------------------------------------
# GUI APPLICATION (Tkinter Widgets and Event Handling)
# ------------------------------------------------------------------------------

class ExpenseTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Personal Expense Tracker")
        self.root.geometry("1000x680")
        self.root.minsize(900, 600)

        # Track which expense ID is currently being edited (None if adding new)
        self.selected_expense_id = None

        # Categories are shared with the optional demonstration data.
        self.categories = list(calc.EXPENSE_CATEGORIES)

        # Initialize the SQLite schema. The first run starts with no sample
        # expenses; seed_data.py can populate a demonstration database.
        db.init_db()

        # Apply a predictable cross-platform style to colored buttons.
        self._configure_styles()

        # Build user interface
        self.create_gui()

        # Load initial data
        self.update_month_dropdown()
        self.load_expenses_and_totals()

    def _configure_styles(self):
        """Configure consistent button colors across supported platforms."""
        self.style = ttk.Style(self.root)

        # Aqua on macOS does not expose all button color options. The clam
        # theme supports explicit colors and is available with standard Tk.
        try:
            if "clam" in self.style.theme_names():
                self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure(
            "Primary.TButton",
            background="#27ae60",
            foreground="#ffffff",
            font=("Arial", 9, "bold"),
            padding=(10, 6),
            borderwidth=0,
        )
        self.style.map(
            "Primary.TButton",
            background=[("pressed", "#1e8449"), ("active", "#229954")],
            foreground=[("disabled", "#ecf0f1"), ("!disabled", "#ffffff")],
        )
        self.style.configure(
            "Secondary.TButton",
            background="#bdc3c7",
            foreground="#2c3e50",
            font=("Arial", 9),
            padding=(9, 6),
        )
        self.style.map(
            "Secondary.TButton",
            background=[("pressed", "#aeb6bf"), ("active", "#d5d8dc")],
        )
        self.style.configure(
            "Warning.TButton",
            background="#f39c12",
            foreground="#ffffff",
            font=("Arial", 9, "bold"),
            padding=(9, 6),
        )
        self.style.map(
            "Warning.TButton",
            background=[("pressed", "#d68910"), ("active", "#e67e22")],
            foreground=[("!disabled", "#ffffff")],
        )
        self.style.configure(
            "Danger.TButton",
            background="#e74c3c",
            foreground="#ffffff",
            font=("Arial", 9, "bold"),
            padding=(9, 6),
        )
        self.style.map(
            "Danger.TButton",
            background=[("pressed", "#c0392b"), ("active", "#cb4335")],
            foreground=[("!disabled", "#ffffff")],
        )
        self.style.configure(
            "Info.TButton",
            background="#2980b9",
            foreground="#ffffff",
            font=("Arial", 9, "bold"),
            padding=(9, 5),
        )
        self.style.map(
            "Info.TButton",
            background=[("pressed", "#21618c"), ("active", "#2471a3")],
            foreground=[("!disabled", "#ffffff")],
        )


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

        self.submit_btn = ttk.Button(
            btn_box,
            text="Add Expense",
            style="Primary.TButton",
            command=self.save_expense,
        )
        self.submit_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.clear_btn = ttk.Button(
            btn_box,
            text="Clear",
            style="Secondary.TButton",
            command=self.reset_form,
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

        save_budget_btn = ttk.Button(
            b_input_box,
            text="Save Budget",
            style="Info.TButton",
            command=self.save_budget,
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

        edit_btn = ttk.Button(
            action_bar,
            text="Edit Selected",
            style="Warning.TButton",
            command=self.start_edit_expense,
        )
        edit_btn.pack(side=tk.LEFT, padx=(0, 6))

        delete_btn = ttk.Button(
            action_bar,
            text="Delete Selected",
            style="Danger.TButton",
            command=self.delete_expense,
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
        """Refresh the month filter using months stored in SQLite."""
        try:
            months = db.get_available_months()
        except RuntimeError as exc:
            messagebox.showerror("Database Error", str(exc))
            return

        current_month = date.today().strftime("%Y-%m")
        if current_month not in months:
            months.insert(0, current_month)
        months.append("All")
        self.month_dropdown["values"] = months

        if self.month_var.get() not in months:
            self.month_var.set(current_month)

    def save_expense(self):
        """Validate form fields, then insert or update an expense."""
        try:
            amount, category, description, expense_date = (
                calc.validate_expense_inputs(
                    self.amount_entry.get(),
                    self.category_cb.get(),
                    self.desc_entry.get(),
                    self.date_entry.get(),
                )
            )
        except ValueError as exc:
            messagebox.showerror("Validation Error", str(exc))
            return

        try:
            if self.selected_expense_id is None:
                db.add_expense(amount, category, description, expense_date)
                messagebox.showinfo(
                    "Success",
                    f"Expense of Rs. {amount:.2f} added successfully!",
                )
            else:
                updated = db.update_expense(
                    self.selected_expense_id,
                    amount,
                    category,
                    description,
                    expense_date,
                )
                if not updated:
                    messagebox.showwarning(
                        "Expense Not Found",
                        "This expense no longer exists. Refresh the list and try again.",
                    )
                    self.reset_form()
                    self.load_expenses_and_totals()
                    return
                messagebox.showinfo(
                    "Success",
                    f"Expense #{self.selected_expense_id} updated successfully!",
                )

            self.reset_form()
            self.update_month_dropdown()
            self.load_expenses_and_totals()
        except RuntimeError as exc:
            messagebox.showerror("Database Error", str(exc))

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
        self.submit_btn.config(text="Save Changes", style="Warning.TButton")

    def delete_expense(self):
        """Delete the selected expense after explicit confirmation."""
        selected_item = self.expense_tree.selection()
        if not selected_item:
            messagebox.showwarning(
                "Select Item",
                "Please select an expense row from the table to delete.",
            )
            return

        values = self.expense_tree.item(selected_item[0], "values")
        expense_id = int(values[0])
        category = values[2]
        amount = values[4]

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete Expense #{expense_id} "
            f"({category} - Rs. {amount})?",
        )
        if not confirm:
            return

        try:
            deleted = db.delete_expense(expense_id)
            if not deleted:
                messagebox.showwarning(
                    "Expense Not Found",
                    "This expense no longer exists. Refresh the list and try again.",
                )
            else:
                if self.selected_expense_id == expense_id:
                    self.reset_form()
                messagebox.showinfo(
                    "Deleted", f"Expense #{expense_id} deleted successfully."
                )

            self.update_month_dropdown()
            self.load_expenses_and_totals()
        except RuntimeError as exc:
            messagebox.showerror("Database Error", str(exc))

    def reset_form(self):
        """Clear form and revert back to Add mode."""
        self.selected_expense_id = None
        self.amount_entry.delete(0, tk.END)
        self.category_cb.current(0)
        self.desc_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, date.today().strftime("%Y-%m-%d"))

        self.form_frame.config(text=" Add / Edit Expense ")
        self.submit_btn.config(text="Add Expense", style="Primary.TButton")

    def save_budget(self):
        """Validate and save a budget for the currently selected month."""
        month = self.month_var.get()
        if not month or month == "All":
            messagebox.showwarning(
                "Select Month",
                "Please select a specific month (for example, 2026-11) to set a budget.",
            )
            return

        try:
            budget = calc.validate_budget_input(self.budget_entry.get())
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            return

        try:
            db.set_budget(month, budget)
            messagebox.showinfo(
                "Budget Set",
                f"Budget for {month} saved as Rs. {budget:,.2f}",
            )
            self.update_month_dropdown()
            self.load_expenses_and_totals()
        except RuntimeError as exc:
            messagebox.showerror("Database Error", str(exc))

    def load_expenses_and_totals(self):
        """Load the selected month's records and display calculated summaries."""
        month = self.month_var.get()

        try:
            expenses = db.get_all_expenses(month)
            monthly_budget = (
                db.get_budget(month) if month and month != "All" else 0.0
            )
        except RuntimeError as exc:
            messagebox.showerror("Database Error", str(exc))
            return

        # Refresh the expense table.
        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        for expense in expenses:
            self.expense_tree.insert(
                "",
                tk.END,
                values=(
                    expense["id"],
                    expense["date"],
                    expense["category"],
                    expense["description"] or "",
                    f'{float(expense["amount"]):.2f}',
                ),
            )

        self.entries_count_label.config(
            text=f"{len(expenses)} entries found"
        )

        # All financial calculations live in calculations.py.
        try:
            summary = calc.compute_spending_summary(expenses, monthly_budget)
        except ValueError as exc:
            messagebox.showerror("Calculation Error", str(exc))
            return

        total_spending = summary["total_spending"]
        self.total_spent_label.config(text=f"Rs. {total_spending:,.2f}")

        # Reset the input before displaying the selected month's budget.
        self.budget_entry.delete(0, tk.END)

        if monthly_budget > 0:
            self.budget_entry.insert(0, f"{monthly_budget:.2f}")
            self.budget_label.config(text=f"Rs. {monthly_budget:,.2f}")
        else:
            self.budget_label.config(text="Not Set")

        budget_status = summary["budget_status"]
        if budget_status == "exceeded":
            exceeded_by = summary["exceeded_by"]
            self.status_title_label.config(text="OVER BUDGET BY", fg="#c0392b")
            self.balance_label.config(
                text=f"Rs. {exceeded_by:,.2f}", fg="#c0392b"
            )
            self.warning_banner.config(
                text=summary["warning_message"],
                bg="#fadbd8",
                fg="#922b21",
            )
        elif budget_status == "caution":
            remaining = summary["difference"]
            self.status_title_label.config(
                text="REMAINING BUDGET", fg="#b9770e"
            )
            self.balance_label.config(
                text=f"Rs. {remaining:,.2f}", fg="#b9770e"
            )
            self.warning_banner.config(
                text=summary["warning_message"],
                bg="#fdebd0",
                fg="#b9770e",
            )
        elif budget_status == "healthy":
            remaining = summary["difference"]
            self.status_title_label.config(
                text="REMAINING BUDGET", fg="#27ae60"
            )
            self.balance_label.config(
                text=f"Rs. {remaining:,.2f}", fg="#27ae60"
            )
            self.warning_banner.config(
                text=summary["warning_message"],
                bg="#d5f5e3",
                fg="#1e8449",
            )
        else:
            self.status_title_label.config(text="REMAINING", fg="#7f8c8d")
            self.balance_label.config(text="N/A", fg="#7f8c8d")
            self.warning_banner.config(
                text=summary["warning_message"],
                bg="#f2f3f4",
                fg="#7f8c8d",
            )

        # Display the category-wise totals returned by calculations.py.
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)

        for row in summary["category_breakdown"]:
            self.category_tree.insert(
                "",
                tk.END,
                values=(
                    row["category"],
                    f'Rs. {row["total"]:,.2f}',
                    f'{row["percentage"]:.1f}%',
                ),
            )
