"""
expense_tracker.py - Main Tkinter GUI controller with modern card layout,
prominent carryforward/allowance breakdown, and streamlined interaction.
"""

from __future__ import annotations

from datetime import date
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import calculations as calc
import database as db
from dialogs import AdjustmentDialog, CsvImportDialog, SettingsDialog
from models import (
    BudgetStatus,
    ExpenseTrackerError,
    PaymentMode,
    ValidationError,
    format_inr,
    paise_to_input_str,
)
from ui_widgets import (
    BudgetProgressCanvas,
    CalendarDateField,
    CategoryBarChart,
    MonthlyTrendChart,
    UI_FONT,
)


class ExpenseTrackerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Personal Expense Tracker")
        self.root.geometry("1160x740")
        self.root.minsize(1000, 660)

        self.selected_expense_id: int | None = None
        self.sort_col: str = "date"
        self.sort_desc: bool = True
        self._status_after_id: str | None = None

        db.init_db()

        self._configure_styles()
        self._build_gui()
        self._bind_shortcuts()

        self.refresh_categories()
        self.update_month_dropdown()
        self.load_expenses_and_totals()

    def _configure_styles(self) -> None:
        self.style = ttk.Style(self.root)
        try:
            if "clam" in self.style.theme_names():
                self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.root.configure(bg="#f1f5f9")

        self.style.configure("TFrame", background="#f1f5f9")
        self.style.configure("Card.TFrame", background="#ffffff")
        self.style.configure("TLabel", background="#f1f5f9", foreground="#1e293b", font=(UI_FONT, 9))
        self.style.configure("Card.TLabel", background="#ffffff", foreground="#1e293b", font=(UI_FONT, 9))
        self.style.configure("FieldLabel.TLabel", background="#ffffff", foreground="#475569", font=(UI_FONT, 8, "bold"))

        self.style.configure(
            "TEntry",
            padding=(7, 5),
            fieldbackground="#ffffff",
            foreground="#0f172a",
            insertcolor="#0f172a",
            bordercolor="#cbd5e1",
        )
        self.style.map("TEntry", bordercolor=[("focus", "#2563eb")])

        self.style.configure(
            "TCombobox",
            padding=(6, 5),
            fieldbackground="#ffffff",
            foreground="#0f172a",
            bordercolor="#cbd5e1",
        )
        self.style.map("TCombobox", bordercolor=[("focus", "#2563eb")])

        self.style.configure(
            "Primary.TButton",
            background="#16a34a", foreground="#ffffff",
            font=(UI_FONT, 9, "bold"), padding=(12, 7), borderwidth=0,
        )
        self.style.map(
            "Primary.TButton",
            background=[("disabled", "#cbd5e1"), ("active", "#15803d"), ("pressed", "#166534")],
            foreground=[("disabled", "#64748b"), ("!disabled", "#ffffff")],
        )

        self.style.configure(
            "Secondary.TButton",
            background="#e2e8f0", foreground="#0f172a",
            font=(UI_FONT, 9), padding=(10, 7), borderwidth=0,
        )
        self.style.map("Secondary.TButton", background=[("active", "#cbd5e1")])

        self.style.configure(
            "Subtle.TButton",
            background="#f1f5f9", foreground="#334155",
            font=(UI_FONT, 8, "bold"), padding=(6, 4), bordercolor="#cbd5e1",
        )
        self.style.map("Subtle.TButton", background=[("active", "#e2e8f0")])

        self.style.configure(
            "Warning.TButton",
            background="#d97706", foreground="#ffffff",
            font=(UI_FONT, 9, "bold"), padding=(10, 6), borderwidth=0,
        )
        self.style.map("Warning.TButton", background=[("active", "#b45309")])

        self.style.configure(
            "Danger.TButton",
            background="#dc2626", foreground="#ffffff",
            font=(UI_FONT, 9, "bold"), padding=(10, 6), borderwidth=0,
        )
        self.style.map("Danger.TButton", background=[("active", "#b91c1c")])

        self.style.configure(
            "Info.TButton",
            background="#2563eb", foreground="#ffffff",
            font=(UI_FONT, 9, "bold"), padding=(10, 5), borderwidth=0,
        )
        self.style.map(
            "Info.TButton",
            background=[("disabled", "#cbd5e1"), ("active", "#1d4ed8")],
            foreground=[("disabled", "#64748b"), ("!disabled", "#ffffff")],
        )
        self.style.configure(
            "HeaderPill.TButton",
            background="#1d4ed8",
            foreground="#ffffff",
            font=(UI_FONT, 8, "bold"),
            padding=(10, 5),
            borderwidth=0,
            focusthickness=0,
        )
        self.style.map(
            "HeaderPill.TButton",
            background=[("active", "#2563eb"), ("pressed", "#1e40af")],
            foreground=[("!disabled", "#ffffff")],
        )

        self.style.configure(
            "HeaderAction.TButton",
            background="#334155",
            foreground="#ffffff",
            font=(UI_FONT, 8, "bold"),
            padding=(10, 5),
            borderwidth=1,
            bordercolor="#475569",
            focusthickness=0,
        )
        self.style.map(
            "HeaderAction.TButton",
            background=[("active", "#475569"), ("pressed", "#1e293b")],
            foreground=[("!disabled", "#ffffff")],
        )

        # Clean flat Notebook tabs
        self.style.configure("TNotebook", background="#f1f5f9", borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background="#e2e8f0", foreground="#475569",
            padding=(14, 7), font=(UI_FONT, 9, "bold"), borderwidth=0,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", "#ffffff"), ("active", "#f8fafc")],
            foreground=[("selected", "#0f172a")],
        )

        # Airy Treeview
        self.style.configure(
            "Treeview",
            background="#ffffff", fieldbackground="#ffffff",
            foreground="#0f172a", rowheight=28,
            font=(UI_FONT, 9), borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            background="#f8fafc", foreground="#334155",
            font=(UI_FONT, 9, "bold"), padding=(6, 6), relief="flat",
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", "#0f172a")],
        )

    def _make_card(self, parent: tk.Misc, **pack_opts) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg="#ffffff",
            highlightbackground="#e2e8f0",
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        card.pack(**pack_opts)
        return card

    def _build_gui(self) -> None:
        # 1. Header Bar
        header = tk.Frame(self.root, bg="#0f172a", pady=11, padx=16)
        header.pack(fill=tk.X)

        left_hdr = tk.Frame(header, bg="#0f172a")
        left_hdr.pack(side=tk.LEFT)
        tk.Label(
            left_hdr,
            text="Personal Expense Tracker",
            font=(UI_FONT, 15, "bold"),
            bg="#0f172a",
            fg="#f8fafc",
        ).pack(anchor=tk.W)
        tk.Label(
            left_hdr,
            text="Paise-exact ledger  •  Rollover budgeting  •  Allowances & coupon savings",
            font=(UI_FONT, 8),
            bg="#0f172a",
            fg="#94a3b8",
        ).pack(anchor=tk.W)

        right_hdr = tk.Frame(header, bg="#0f172a")
        right_hdr.pack(side=tk.RIGHT)

        self.carry_pill = ttk.Button(
            right_hdr,
            text="Rollover: Both",
            style="HeaderPill.TButton",
            cursor="hand2",
            command=self.open_settings,
        )
        self.carry_pill.pack(side=tk.LEFT, padx=(0, 8))

        for label, cmd in (
            ("CSV Template", self.download_csv_template),
            ("Import CSV", self.import_csv),
            ("Export CSV", self.export_csv),
            ("Settings", self.open_settings),
        ):
            ttk.Button(
                right_hdr,
                text=label,
                style="HeaderAction.TButton",
                cursor="hand2",
                command=cmd,
            ).pack(side=tk.LEFT, padx=3)

        # 2. Main Split Workspace
        body = ttk.Frame(self.root, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(body, width=348)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        left_panel.pack_propagate(False)

        right_panel = ttk.Frame(body)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # ----------------- LEFT SIDEBAR CARDS -----------------
        form_card = self._make_card(left_panel, fill=tk.X, pady=(0, 10))

        self.form_title_label = tk.Label(
            form_card,
            text="Add Expense",
            font=(UI_FONT, 11, "bold"),
            bg="#ffffff",
            fg="#0f172a",
        )
        self.form_title_label.pack(anchor=tk.W, pady=(0, 8))

        # Row 1: Amount + Coupon side-by-side
        r1 = ttk.Frame(form_card, style="Card.TFrame")
        r1.pack(fill=tk.X, pady=(0, 6))
        r1.columnconfigure(0, weight=3)
        r1.columnconfigure(1, weight=2)

        ttk.Label(r1, text="AMOUNT PAID (₹)", style="FieldLabel.TLabel").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(r1, text="COUPON SAVED (₹)", style="FieldLabel.TLabel").grid(row=0, column=1, sticky=tk.W, padx=(8, 0))

        self.amount_entry = ttk.Entry(r1, font=(UI_FONT, 10))
        self.amount_entry.grid(row=1, column=0, sticky=tk.EW, pady=(2, 0))

        self.discount_entry = ttk.Entry(r1, font=(UI_FONT, 10))
        self.discount_entry.grid(row=1, column=1, sticky=tk.EW, padx=(8, 0), pady=(2, 0))
        self.discount_entry.insert(0, "0")

        # Row 2: Category + Payment Mode side-by-side
        r2 = ttk.Frame(form_card, style="Card.TFrame")
        r2.pack(fill=tk.X, pady=(0, 6))
        r2.columnconfigure(0, weight=3)
        r2.columnconfigure(1, weight=2)

        ttk.Label(r2, text="CATEGORY", style="FieldLabel.TLabel").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(r2, text="MODE", style="FieldLabel.TLabel").grid(row=0, column=1, sticky=tk.W, padx=(8, 0))

        self.category_cb = ttk.Combobox(r2, state="readonly", font=(UI_FONT, 9))
        self.category_cb.grid(row=1, column=0, sticky=tk.EW, pady=(2, 0))

        self.mode_cb = ttk.Combobox(
            r2, values=[m.value for m in PaymentMode], state="readonly", font=(UI_FONT, 9)
        )
        self.mode_cb.grid(row=1, column=1, sticky=tk.EW, padx=(8, 0), pady=(2, 0))
        self.mode_cb.current(0)

        # Row 3: Description (full width)
        ttk.Label(form_card, text="DESCRIPTION", style="FieldLabel.TLabel").pack(anchor=tk.W)
        self.desc_entry = ttk.Entry(form_card, font=(UI_FONT, 10))
        self.desc_entry.pack(fill=tk.X, pady=(2, 6))

        # Row 4: Date with Calendar Picker (full width)
        ttk.Label(form_card, text="DATE (YYYY-MM-DD)", style="FieldLabel.TLabel").pack(anchor=tk.W)
        self.date_field = CalendarDateField(form_card)
        self.date_field.pack(fill=tk.X, pady=(2, 10))

        # Row 5: Submit + Clear
        btn_row = ttk.Frame(form_card, style="Card.TFrame")
        btn_row.pack(fill=tk.X)
        self.submit_btn = ttk.Button(
            btn_row, text="Add Expense", style="Primary.TButton", command=self.save_expense
        )
        self.submit_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.clear_btn = ttk.Button(
            btn_row, text="Clear", style="Secondary.TButton", command=self.reset_form
        )
        self.clear_btn.pack(side=tk.RIGHT)

        # Card 2: Monthly Budget & Rollover Breakdown
        budget_card = self._make_card(left_panel, fill=tk.BOTH, expand=True)

        tk.Label(
            budget_card,
            text="Budget & Allowances",
            font=(UI_FONT, 11, "bold"),
            bg="#ffffff",
            fg="#0f172a",
        ).pack(anchor=tk.W)

        self.budget_hint_label = tk.Label(
            budget_card,
            text="Base planned budget for the selected month",
            font=(UI_FONT, 8),
            bg="#ffffff",
            fg="#64748b",
        )
        self.budget_hint_label.pack(anchor=tk.W, pady=(1, 8))

        b_row = ttk.Frame(budget_card, style="Card.TFrame")
        b_row.pack(fill=tk.X)
        self.budget_entry = ttk.Entry(b_row, font=(UI_FONT, 10))
        self.budget_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.save_budget_btn = ttk.Button(
            b_row, text="Set Base", style="Info.TButton", command=self.save_budget
        )
        self.save_budget_btn.pack(side=tk.RIGHT)

        self.adj_btn = ttk.Button(
            budget_card,
            text="+ Log Allowance / Deduction",
            style="Subtle.TButton",
            command=self.open_adjustments,
        )
        self.adj_btn.pack(fill=tk.X, pady=(8, 10))

        # Structured breakdown table inside the card
        breakdown_box = tk.Frame(budget_card, bg="#f8fafc", highlightbackground="#e2e8f0", highlightthickness=1, padx=10, pady=8)
        breakdown_box.pack(fill=tk.X)

        self._bd_base_lbl = self._add_breakdown_row(breakdown_box, "Planned Base", "₹0.00")
        self._bd_adj_lbl = self._add_breakdown_row(breakdown_box, "Allowances / Adj.", "₹0.00")
        self._bd_carry_lbl = self._add_breakdown_row(breakdown_box, "Prev. Carryforward", "₹0.00")
        tk.Frame(breakdown_box, height=1, bg="#cbd5e1").pack(fill=tk.X, pady=5)
        self._bd_eff_lbl = self._add_breakdown_row(breakdown_box, "Effective Budget", "₹0.00", bold=True)

        # ----------------- RIGHT WORKSPACE -----------------
        # Filter Bar Card
        filter_card = tk.Frame(
            right_panel,
            bg="#ffffff",
            highlightbackground="#e2e8f0",
            highlightthickness=1,
            padx=10,
            pady=8,
        )
        filter_card.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(filter_card, text="Month:", style="FieldLabel.TLabel").pack(side=tk.LEFT)
        self.month_var = tk.StringVar(value=date.today().strftime("%Y-%m"))
        self.month_dropdown = ttk.Combobox(
            filter_card, textvariable=self.month_var, state="readonly", width=10
        )
        self.month_dropdown.pack(side=tk.LEFT, padx=(5, 12))
        self.month_dropdown.bind("<<ComboboxSelected>>", self._on_month_changed)

        ttk.Label(filter_card, text="Category:", style="FieldLabel.TLabel").pack(side=tk.LEFT)
        self.filter_cat_var = tk.StringVar(value="All")
        self.filter_cat_cb = ttk.Combobox(
            filter_card, textvariable=self.filter_cat_var, state="readonly", width=16
        )
        self.filter_cat_cb.pack(side=tk.LEFT, padx=(5, 12))
        self.filter_cat_cb.bind("<<ComboboxSelected>>", lambda _e: self._render_filtered_table())

        ttk.Label(filter_card, text="Search:", style="FieldLabel.TLabel").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_card, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 6))
        self.search_var.trace_add("write", lambda *_args: self._render_filtered_table())

        ttk.Button(
            filter_card, text="Reset", style="Subtle.TButton", command=self._clear_filters
        ).pack(side=tk.RIGHT, padx=(0, 4))
        ttk.Button(
            filter_card, text="Refresh", style="Subtle.TButton", command=self.load_expenses_and_totals
        ).pack(side=tk.RIGHT, padx=(0, 4))

        # 4 KPI Cards
        cards = ttk.Frame(right_panel)
        cards.pack(fill=tk.X, pady=(0, 8))

        self.total_spent_label = self._create_kpi_card(
            cards, "TOTAL SPENT", "₹0.00", "#0f172a", "#334155"
        )
        self.budget_title_lbl, self.budget_label = self._create_kpi_card(
            cards, "EFFECTIVE BUDGET", "Not Set", "#16a34a", "#16a34a", return_title=True
        )
        self.status_title_label, self.balance_label = self._create_kpi_card(
            cards, "REMAINING", "N/A", "#2563eb", "#2563eb", return_title=True
        )
        self.coupon_saved_label = self._create_kpi_card(
            cards, "COUPON SAVED", "₹0.00", "#7c3aed", "#7c3aed"
        )

        # Budget Health Bar + Alert Strip
        health_card = tk.Frame(
            right_panel,
            bg="#ffffff",
            highlightbackground="#e2e8f0",
            highlightthickness=1,
            padx=10,
            pady=8,
        )
        health_card.pack(fill=tk.X, pady=(0, 8))

        self.progress_bar = BudgetProgressCanvas(health_card)
        self.progress_bar.pack(fill=tk.X, pady=(0, 6))

        self.warning_banner = tk.Label(
            health_card,
            text="",
            font=(UI_FONT, 9, "bold"),
            pady=5,
            padx=10,
            anchor=tk.W,
        )
        self.warning_banner.pack(fill=tk.X)

        # Notebook Tabs
        notebook = ttk.Notebook(right_panel)
        notebook.pack(fill=tk.BOTH, expand=True)

        # TAB 1: Ledger
        tab1 = tk.Frame(notebook, bg="#ffffff", padx=4, pady=4)
        notebook.add(tab1, text="  Expenses Ledger  ")

        cols = ("id", "date", "category", "payment_mode", "description", "discount", "amount")
        self.expense_tree = ttk.Treeview(tab1, columns=cols, show="headings", selectmode="browse")
        self._col_meta = {
            "id": ("ID", 44, tk.CENTER),
            "date": ("Date", 95, tk.CENTER),
            "category": ("Category", 135, tk.W),
            "payment_mode": ("Mode", 68, tk.CENTER),
            "description": ("Description", 205, tk.W),
            "discount": ("Saved", 78, tk.E),
            "amount": ("Paid", 98, tk.E),
        }
        for col, (text, width, anchor) in self._col_meta.items():
            self.expense_tree.heading(col, text=text, command=lambda c=col: self._sort_by(c))
            self.expense_tree.column(col, width=width, anchor=anchor)

        self.expense_tree.tag_configure("even", background="#ffffff")
        self.expense_tree.tag_configure("odd", background="#f8fafc")
        self.expense_tree.bind("<Double-1>", lambda _e: self.start_edit_expense())

        sb1 = ttk.Scrollbar(tab1, orient=tk.VERTICAL, command=self.expense_tree.yview)
        self.expense_tree.configure(yscrollcommand=sb1.set)
        self.expense_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb1.pack(side=tk.RIGHT, fill=tk.Y)

        # TAB 2: Categories & Chart
        tab2 = tk.Frame(notebook, bg="#ffffff", padx=8, pady=8)
        notebook.add(tab2, text="  Categories & Chart  ")

        cat_pane = ttk.PanedWindow(tab2, orient=tk.HORIZONTAL)
        cat_pane.pack(fill=tk.BOTH, expand=True)

        cat_left = tk.Frame(cat_pane, bg="#ffffff")
        cat_pane.add(cat_left, weight=2)

        self.category_tree = ttk.Treeview(
            cat_left,
            columns=("category", "count", "total", "percentage"),
            show="headings",
            selectmode="none",
        )
        self.category_tree.heading("category", text="Category")
        self.category_tree.heading("count", text="Txns")
        self.category_tree.heading("total", text="Total Spent")
        self.category_tree.heading("percentage", text="Share")
        self.category_tree.column("category", width=140)
        self.category_tree.column("count", width=48, anchor=tk.CENTER)
        self.category_tree.column("total", width=105, anchor=tk.E)
        self.category_tree.column("percentage", width=65, anchor=tk.E)
        self.category_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb2 = ttk.Scrollbar(cat_left, orient=tk.VERTICAL, command=self.category_tree.yview)
        self.category_tree.configure(yscrollcommand=sb2.set)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)

        self.cat_chart = CategoryBarChart(cat_pane)
        cat_pane.add(self.cat_chart, weight=3)

        # TAB 3: Monthly Trends
        tab3 = tk.Frame(notebook, bg="#ffffff", padx=8, pady=8)
        notebook.add(tab3, text="  Monthly Trends  ")
        self.trend_chart = MonthlyTrendChart(tab3)
        self.trend_chart.pack(fill=tk.BOTH, expand=True)

        # Action Bar
        action_bar = ttk.Frame(right_panel, padding=(0, 8, 0, 0))
        action_bar.pack(fill=tk.X)

        ttk.Button(
            action_bar, text="Edit Selected", style="Warning.TButton", command=self.start_edit_expense
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            action_bar, text="Delete Selected", style="Danger.TButton", command=self.delete_expense
        ).pack(side=tk.LEFT)

        self.entries_count_label = ttk.Label(
            action_bar, text="0 entries", font=(UI_FONT, 8, "italic"), foreground="#475569"
        )
        self.entries_count_label.pack(side=tk.RIGHT)

        # 3. Status Bar
        self.status_var = tk.StringVar(value="Ready  •  Double-click any row to edit  •  Ctrl+F to search")
        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg="#e2e8f0",
            fg="#334155",
            font=(UI_FONT, 8),
            anchor=tk.W,
            padx=14,
            pady=4,
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _add_breakdown_row(
        self, parent: tk.Frame, title: str, initial: str, *, bold: bool = False
    ) -> tk.Label:
        row = tk.Frame(parent, bg="#f8fafc")
        row.pack(fill=tk.X, pady=2)
        font_spec = (UI_FONT, 9, "bold") if bold else (UI_FONT, 8)
        tk.Label(row, text=title, font=font_spec, bg="#f8fafc", fg="#475569").pack(side=tk.LEFT)
        val = tk.Label(row, text=initial, font=font_spec, bg="#f8fafc", fg="#0f172a")
        val.pack(side=tk.RIGHT)
        return val

    def _create_kpi_card(
        self,
        parent: ttk.Frame,
        title: str,
        value: str,
        value_color: str,
        accent_color: str,
        *,
        return_title: bool = False,
    ):
        outer = tk.Frame(parent, bg="#ffffff", highlightbackground="#e2e8f0", highlightthickness=1)
        outer.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

        tk.Frame(outer, height=3, bg=accent_color).pack(fill=tk.X)
        inner = tk.Frame(outer, bg="#ffffff", padx=10, pady=7)
        inner.pack(fill=tk.BOTH, expand=True)

        title_lbl = tk.Label(
            inner, text=title, font=(UI_FONT, 7, "bold"), bg="#ffffff", fg="#64748b"
        )
        title_lbl.pack(anchor=tk.W)
        val_lbl = tk.Label(
            inner, text=value, font=(UI_FONT, 12, "bold"), bg="#ffffff", fg=value_color
        )
        val_lbl.pack(anchor=tk.W, pady=(2, 0))
        return (title_lbl, val_lbl) if return_title else val_lbl

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Escape>", lambda _e: self.reset_form())
        self.root.bind("<Control-f>", lambda _e: self.search_entry.focus_set())
        for widget in (self.amount_entry, self.discount_entry, self.desc_entry):
            widget.bind("<Return>", lambda _e: self.save_expense())
        self.expense_tree.bind("<Delete>", lambda _e: self.delete_expense())

    def set_status(self, message: str) -> None:
        self.status_var.set(message)
        if self._status_after_id:
            self.root.after_cancel(self._status_after_id)
        self._status_after_id = self.root.after(
            4500,
            lambda: self.status_var.set("Ready  •  Double-click any row to edit  •  Ctrl+F to search"),
        )

    # ----------------- DATA LOADING & RENDERING -----------------

    def refresh_categories(self) -> None:
        cats = db.get_categories()
        self.category_cb["values"] = cats
        if cats and self.category_cb.get() not in cats:
            self.category_cb.current(0)

        self.filter_cat_cb["values"] = ["All", *cats]
        if self.filter_cat_var.get() not in ("All", *cats):
            self.filter_cat_var.set("All")

    def update_month_dropdown(self) -> None:
        months = db.get_available_months()
        current = date.today().strftime("%Y-%m")
        if current not in months:
            months.insert(0, current)
        months.append("All")
        self.month_dropdown["values"] = months
        if self.month_var.get() not in months:
            self.month_var.set(current)

    def _clear_filters(self) -> None:
        self.filter_cat_var.set("All")
        self.search_var.set("")
        self._render_filtered_table()

    def _on_month_changed(self, _event: tk.Event) -> None:
        self._sync_budget_entry()
        self.load_expenses_and_totals()

    def _sync_budget_entry(self) -> None:
        month = self.month_var.get()
        is_all = month == "All"

        self.budget_entry.configure(state="normal")
        self.budget_entry.delete(0, tk.END)

        if is_all:
            self.budget_entry.insert(0, "All Months")
            self.budget_entry.configure(state="disabled")
            self.save_budget_btn.state(["disabled"])
            self.adj_btn.state(["!disabled"])
            self.adj_btn.config(text="View / Log All Allowances")
            self.budget_hint_label.config(text="Select a specific month to edit base budget")   
        else:
            base_paise = db.get_budget(month)
            if base_paise == 0:
                default_paise = db.get_default_budget_paise()
                if default_paise > 0:
                    db.set_budget(month, default_paise)
                    base_paise = default_paise
            if base_paise > 0:
                self.budget_entry.insert(0, paise_to_input_str(base_paise))
            self.save_budget_btn.state(["!disabled"])
            self.adj_btn.state(["!disabled"])
            self.adj_btn.config(text="+ Log Allowance / Deduction")
            self.budget_hint_label.config(text=f"Base planned budget for {month}")

    def load_expenses_and_totals(self) -> None:
        month = self.month_var.get()
        try:
            all_expenses = db.get_all_expenses()
            budgets_by_month = db.get_all_budgets()
            all_adjustments = db.get_adjustments()
            carry_mode = db.get_carryforward_mode()
        except ExpenseTrackerError as exc:
            messagebox.showerror("Database Error", str(exc))
            return

        short_mode = {
            "off": "Rollover: Off",
            "both": "Rollover: Surplus & Deficit",
            "deficit_only": "Rollover: Deficit Only",
        }[carry_mode.value]
        self.carry_pill.config(text=short_mode)

        self._month_expenses = (
            all_expenses
            if month == "All"
            else [e for e in all_expenses if e.date.startswith(month)]
        )

        if self.root.focus_get() != self.budget_entry:
            self._sync_budget_entry()

        summary = calc.compute_spending_summary(
            selected_month=month,
            all_expenses=all_expenses,
            budgets_by_month=budgets_by_month,
            all_adjustments=all_adjustments,
            carryforward_mode=carry_mode,
        )

        # KPI Cards & Budget Breakdown
        self.total_spent_label.config(text=format_inr(summary.total_spent_paise))
        self.coupon_saved_label.config(text=format_inr(summary.total_discount_paise))

        self._bd_base_lbl.config(text=format_inr(summary.base_budget_paise))
        self._bd_adj_lbl.config(
            text=format_inr(summary.adjustments_paise, show_sign=True),
            fg="#16a34a" if summary.adjustments_paise > 0 else ("#dc2626" if summary.adjustments_paise < 0 else "#0f172a"),
        )
        if month == "All":
            self.budget_title_lbl.config(text=f"TOTAL BUDGET ({summary.budgeted_months_count}M)")
            self._bd_carry_lbl.config(text="N/A (All)", fg="#64748b")
        else:
            self.budget_title_lbl.config(text="EFFECTIVE BUDGET")
            self._bd_carry_lbl.config(
                text=format_inr(summary.carryforward_in_paise, show_sign=True),
                fg="#16a34a" if summary.carryforward_in_paise > 0 else ("#dc2626" if summary.carryforward_in_paise < 0 else "#0f172a"),
            )
        self._bd_eff_lbl.config(text=format_inr(summary.effective_budget_paise))

        if summary.budget_status == BudgetStatus.NO_BUDGET:
            self.budget_label.config(text="Not Set", fg="#64748b")
            self.status_title_label.config(text="REMAINING", fg="#64748b")
            self.balance_label.config(text="N/A", fg="#64748b")
            self.warning_banner.config(text=summary.warning_message, bg="#f1f5f9", fg="#334155")
            self.progress_bar.set_progress(0.0, "#94a3b8", "No budget set")
        elif summary.budget_status == BudgetStatus.EXCEEDED:
            self.budget_label.config(text=format_inr(summary.effective_budget_paise), fg="#dc2626")
            self.status_title_label.config(text="OVER BUDGET", fg="#dc2626")
            self.balance_label.config(text=format_inr(summary.exceeded_by_paise), fg="#dc2626")
            self.warning_banner.config(text=summary.warning_message, bg="#fee2e2", fg="#991b1b")
            self.progress_bar.set_progress(
                summary.percentage_used, "#dc2626", f"{summary.percentage_used:.1f}% used (Over Budget)"
            )
        elif summary.budget_status == BudgetStatus.CAUTION:
            self.budget_label.config(text=format_inr(summary.effective_budget_paise), fg="#d97706")
            self.status_title_label.config(text="REMAINING", fg="#d97706")
            self.balance_label.config(text=format_inr(summary.remaining_paise), fg="#d97706")
            self.warning_banner.config(text=summary.warning_message, bg="#fef3c7", fg="#92400e")
            self.progress_bar.set_progress(
                summary.percentage_used, "#d97706", f"{summary.percentage_used:.1f}% used (Caution ≥90%)"
            )
        else:
            self.budget_label.config(text=format_inr(summary.effective_budget_paise), fg="#16a34a")
            self.status_title_label.config(text="REMAINING", fg="#16a34a")
            self.balance_label.config(text=format_inr(summary.remaining_paise), fg="#16a34a")
            self.warning_banner.config(text=summary.warning_message, bg="#dcfce7", fg="#166534")
            self.progress_bar.set_progress(
                summary.percentage_used, "#16a34a", f"{summary.percentage_used:.1f}% used"
            )

        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
        for row in summary.category_breakdown:
            self.category_tree.insert(
                "",
                tk.END,
                values=(
                    row.category,
                    row.count,
                    format_inr(row.total_paise),
                    f"{row.percentage:.1f}%",
                ),
            )
        self.cat_chart.set_data(summary.category_breakdown)

        trends = calc.compute_monthly_trends(
            all_expenses, budgets_by_month, all_adjustments, carry_mode
        )
        self.trend_chart.set_data(trends)

        self._render_filtered_table()

    def _sort_by(self, col: str) -> None:
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = col in ("date", "amount", "discount", "id")
        self._render_filtered_table()

    def _render_filtered_table(self) -> None:
        # Update sort arrow indicators on column headers
        for col, (label, _w, _a) in self._col_meta.items():
            arrow = (" ▼" if self.sort_desc else " ▲") if col == self.sort_col else ""
            self.expense_tree.heading(col, text=f"{label}{arrow}")

        filtered = calc.filter_expenses(
            getattr(self, "_month_expenses", ()),
            category_filter=self.filter_cat_var.get(),
            search_query=self.search_var.get(),
        )
        ordered = calc.sort_expenses(filtered, self.sort_col, self.sort_desc)
        self._displayed_expenses = ordered

        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        for idx, exp in enumerate(ordered):
            tag = "even" if idx % 2 == 0 else "odd"
            disc_str = format_inr(exp.discount_paise) if exp.discount_paise > 0 else "-"
            self.expense_tree.insert(
                "",
                tk.END,
                values=(
                    exp.id,
                    exp.date,
                    exp.category,
                    exp.payment_mode,
                    exp.description,
                    disc_str,
                    format_inr(exp.amount_paise),
                ),
                tags=(tag,),
            )

        total_shown = sum(e.amount_paise for e in ordered)
        total_in_month = len(getattr(self, "_month_expenses", ()))
        if len(ordered) == total_in_month:
            self.entries_count_label.config(text=f"{len(ordered)} entries")
        else:
            self.entries_count_label.config(
                text=f"Showing {len(ordered)} of {total_in_month} ({format_inr(total_shown)})"
            )

    # ----------------- CRUD HANDLERS -----------------

    def save_expense(self) -> None:
        try:
            amount_paise, discount_paise, category, mode, desc, exp_date = (
                calc.validate_expense_inputs(
                    self.amount_entry.get(),
                    self.category_cb.get(),
                    self.desc_entry.get(),
                    self.date_field.get(),
                    self.discount_entry.get(),
                    self.mode_cb.get(),
                )
            )
        except ValidationError as exc:
            messagebox.showerror("Validation Error", str(exc))
            return

        try:
            if self.selected_expense_id is None:
                db.add_expense(
                    amount_paise,
                    category,
                    desc,
                    exp_date,
                    discount_paise=discount_paise,
                    payment_mode=mode,
                )
                msg = f"✓ Added {format_inr(amount_paise)} ({category})"
            else:
                updated = db.update_expense(
                    self.selected_expense_id,
                    amount_paise,
                    category,
                    desc,
                    exp_date,
                    discount_paise=discount_paise,
                    payment_mode=mode,
                )
                if not updated:
                    messagebox.showwarning("Not Found", "This expense no longer exists.")
                    self.reset_form()
                    self.load_expenses_and_totals()
                    return
                msg = f"✓ Updated Expense #{self.selected_expense_id}"

            self.reset_form()
            self.update_month_dropdown()
            self.load_expenses_and_totals()
            self.set_status(msg)
            self.amount_entry.focus_set()
        except ExpenseTrackerError as exc:
            messagebox.showerror("Database Error", str(exc))

    def start_edit_expense(self) -> None:
        sel = self.expense_tree.selection()
        if not sel:
            messagebox.showwarning("Select Item", "Please select an expense row to edit.")
            return

        expense_id = int(self.expense_tree.item(sel[0], "values")[0])
        exp = db.get_expense_by_id(expense_id)
        if not exp:
            messagebox.showwarning("Not Found", "Selected expense no longer exists.")
            self.load_expenses_and_totals()
            return

        self.selected_expense_id = exp.id
        self.amount_entry.delete(0, tk.END)
        self.amount_entry.insert(0, paise_to_input_str(exp.amount_paise))

        self.discount_entry.delete(0, tk.END)
        self.discount_entry.insert(
            0, paise_to_input_str(exp.discount_paise) if exp.discount_paise > 0 else "0"
        )

        self.category_cb.set(exp.category)
        self.mode_cb.set(exp.payment_mode)

        self.desc_entry.delete(0, tk.END)
        self.desc_entry.insert(0, exp.description)

        self.date_field.set(exp.date)

        self.form_title_label.config(text=f"Editing Expense #{exp.id}", fg="#b45309")
        self.submit_btn.config(text="Save Changes", style="Warning.TButton")
        self.amount_entry.focus_set()

    def delete_expense(self) -> None:
        sel = self.expense_tree.selection()
        if not sel:
            messagebox.showwarning("Select Item", "Please select an expense row to delete.")
            return

        expense_id = int(self.expense_tree.item(sel[0], "values")[0])
        exp = db.get_expense_by_id(expense_id)
        if not exp:
            self.load_expenses_and_totals()
            return

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete Expense #{exp.id} ({exp.category} — {format_inr(exp.amount_paise)})?",
        ):
            return

        db.delete_expense(expense_id)
        if self.selected_expense_id == expense_id:
            self.reset_form()
        self.update_month_dropdown()
        self.load_expenses_and_totals()
        self.set_status(f"✓ Deleted Expense #{expense_id}")

    def reset_form(self) -> None:
        self.selected_expense_id = None
        self.amount_entry.delete(0, tk.END)
        self.discount_entry.delete(0, tk.END)
        self.discount_entry.insert(0, "0")
        if self.category_cb["values"]:
            self.category_cb.current(0)
        self.mode_cb.current(0)
        self.desc_entry.delete(0, tk.END)
        self.date_field.set_today()

        self.form_title_label.config(text="Add Expense", fg="#0f172a")
        self.submit_btn.config(text="Add Expense", style="Primary.TButton")

    def save_budget(self) -> None:
        month = self.month_var.get()
        if not month or month == "All":
            return

        try:
            budget_paise = calc.validate_budget_input(self.budget_entry.get())
        except ValidationError as exc:
            messagebox.showerror("Input Error", str(exc))
            return

        db.set_budget(month, budget_paise)
        self.update_month_dropdown()
        self.load_expenses_and_totals()
        self.set_status(f"✓ Base budget for {month} set to {format_inr(budget_paise)}")

    # ----------------- DIALOGS & CSV -----------------

    def open_adjustments(self) -> None:
        month = self.month_var.get() or "All"
        AdjustmentDialog(self.root, month, on_change=self.load_expenses_and_totals)

    def open_settings(self) -> None:
        def _after_settings() -> None:
            self.refresh_categories()
            self.load_expenses_and_totals()
            self.set_status("✓ Settings updated")

        SettingsDialog(self.root, on_saved=_after_settings)

    def download_csv_template(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="expense_import_template.csv",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not path:
            return
        calc.write_csv_template(path)
        self.set_status("✓ CSV import template saved")
    
    def export_csv(self) -> None:
        rows = getattr(self, "_displayed_expenses", [])
        if not rows:
            messagebox.showinfo("Nothing to Export", "No expenses match the current view.")
            return

        month_slug = self.month_var.get().lower()
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"expenses_{month_slug}.csv",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not path:
            return

        count = calc.export_expenses_to_csv(rows, path)
        self.set_status(f"✓ Exported {count} expenses to CSV")

    def import_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not path:
            return

        try:
            preview = calc.build_import_preview(
                path, db.get_categories(), db.get_existing_expense_counts()
            )
        except ExpenseTrackerError as exc:
            messagebox.showerror("Import Error", str(exc))
            return

        if not preview.rows:
            messagebox.showinfo("Empty CSV", "No expense rows were found in that file.")
            return

        def _after_import(count: int) -> None:
            self.update_month_dropdown()
            self.load_expenses_and_totals()
            self.set_status(f"✓ Imported {count} expenses from CSV")

        CsvImportDialog(self.root, preview, on_imported=_after_import)