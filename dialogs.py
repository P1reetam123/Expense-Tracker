"""
dialogs.py - Clean modal dialogs for Budget Allowances, Bulk CSV Import,
and Application Settings / Custom Categories.
"""

from __future__ import annotations

from datetime import date
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable

import calculations as calc
import database as db
from models import (
    CarryforwardMode,
    ImportPreview,
    ValidationError,
    format_inr,
    paise_to_input_str,
    parse_rupees_to_paise,
)
from ui_widgets import CalendarDateField, UI_FONT


class AdjustmentDialog(tk.Toplevel):
    """Manage mid-month budget allowances and deductions (single month or All)."""

    def __init__(self, master: tk.Misc, month: str, on_change: Callable[[], None]):
        super().__init__(master)
        self.selected_month = month
        self.on_change = on_change
        self.configure(bg="#f1f5f9")
        self.title(
            "All Budget Allowances & Adjustments"
            if month == "All"
            else f"Budget Allowances & Adjustments ({month})"
        )
        self.geometry("640x510")
        self.minsize(560, 460)
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._load_rows()

    def _build_ui(self) -> None:
        # Pin bottom footer first so action buttons are always visible.
        bottom = ttk.Frame(self, padding=(12, 6, 12, 12))
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(
            bottom, text="Delete Selected", style="Danger.TButton", command=self._delete
        ).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Close", style="Secondary.TButton", command=self.destroy).pack(
            side=tk.RIGHT
        )

        # Top Add Form
        top = ttk.LabelFrame(self, text=" Log Allowance / Deduction ", padding=10)
        top.pack(fill=tk.X, padx=12, pady=(12, 8))

        self.kind_var = tk.StringVar(value="allowance")
        kind_row = ttk.Frame(top)
        kind_row.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))
        ttk.Radiobutton(
            kind_row,
            text="+ Allowance / Bonus (Increases budget)",
            variable=self.kind_var,
            value="allowance",
        ).pack(side=tk.LEFT, padx=(0, 14))
        ttk.Radiobutton(
            kind_row,
            text="- Deduction (Moves out of budget)",
            variable=self.kind_var,
            value="deduction",
        ).pack(side=tk.LEFT)

        months = [m for m in db.get_available_months() if m != "All"]
        curr = date.today().strftime("%Y-%m")
        if curr not in months:
            months.insert(0, curr)
        initial_month = curr if self.selected_month == "All" else self.selected_month
        if initial_month not in months:
            months.insert(0, initial_month)

        ttk.Label(top, text="Target Month:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.target_month_var = tk.StringVar(value=initial_month)
        self.month_cb = ttk.Combobox(
            top, textvariable=self.target_month_var, values=months, state="readonly"
        )
        self.month_cb.grid(row=1, column=1, sticky=tk.EW, pady=4)

        ttk.Label(top, text="Amount (₹):").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.amount_entry = ttk.Entry(top)
        self.amount_entry.grid(row=2, column=1, sticky=tk.EW, pady=4)

        ttk.Label(top, text="Reason:").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.reason_entry = ttk.Entry(top)
        self.reason_entry.grid(row=3, column=1, sticky=tk.EW, pady=4)

        ttk.Label(top, text="Date:").grid(row=4, column=0, sticky=tk.W, pady=4)
        default_date = (
            date.today().isoformat()
            if date.today().strftime("%Y-%m") == initial_month
            else f"{initial_month}-01"
        )
        self.date_field = CalendarDateField(top, initial_date=default_date)
        self.date_field.grid(row=4, column=1, sticky=tk.EW, pady=4)

        top.columnconfigure(1, weight=1)

        ttk.Button(
            top, text="Save Adjustment", style="Primary.TButton", command=self._save
        ).grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

        # Filter + Table
        filter_row = ttk.Frame(self, padding=(12, 0, 12, 4))
        filter_row.pack(fill=tk.X)
        ttk.Label(filter_row, text="Viewing:", font=(UI_FONT, 8, "bold")).pack(side=tk.LEFT)
        self.view_filter_var = tk.StringVar(value=self.selected_month)
        view_cb = ttk.Combobox(
            filter_row,
            textvariable=self.view_filter_var,
            values=["All", *months],
            state="readonly",
            width=10,
        )
        view_cb.pack(side=tk.LEFT, padx=6)
        view_cb.bind("<<ComboboxSelected>>", lambda _e: self._load_rows())

        list_frame = ttk.Frame(self, padding=(12, 0, 12, 4))
        list_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "month", "date", "amount", "reason")
        self.tree = ttk.Treeview(
            list_frame, columns=cols, show="headings", selectmode="browse", height=6
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("month", text="Month")
        self.tree.heading("date", text="Date")
        self.tree.heading("amount", text="Adjustment")
        self.tree.heading("reason", text="Reason")
        self.tree.column("id", width=38, anchor=tk.CENTER)
        self.tree.column("month", width=78, anchor=tk.CENTER)
        self.tree.column("date", width=90, anchor=tk.CENTER)
        self.tree.column("amount", width=105, anchor=tk.E)
        self.tree.column("reason", width=260)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _load_rows(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        scope = self.view_filter_var.get()
        for adj in db.get_adjustments(scope):
            self.tree.insert(
                "",
                tk.END,
                values=(
                    adj.id,
                    adj.month,
                    adj.date,
                    format_inr(adj.amount_paise, show_sign=True),
                    adj.reason,
                ),
            )

    def _save(self) -> None:
        try:
            paise, reason, adj_date = calc.validate_adjustment_input(
                self.amount_entry.get(),
                self.reason_entry.get(),
                self.date_field.get(),
                is_deduction=(self.kind_var.get() == "deduction"),
            )
        except ValidationError as exc:
            messagebox.showerror("Validation Error", str(exc), parent=self)
            return

        target_month = self.target_month_var.get()
        db.add_adjustment(target_month, paise, reason, adj_date)
        self.amount_entry.delete(0, tk.END)
        self.reason_entry.delete(0, tk.END)
        self._load_rows()
        self.on_change()

    def _delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select Row", "Select an adjustment row to delete.", parent=self)
            return
        adj_id = int(self.tree.item(sel[0], "values")[0])
        if db.delete_adjustment(adj_id):
            self._load_rows()
            self.on_change()


class CsvImportDialog(tk.Toplevel):
    """Preview and validate bulk CSV rows before single-transaction import."""

    def __init__(
        self,
        master: tk.Misc,
        preview: ImportPreview,
        on_imported: Callable[[int], None],
    ):
        super().__init__(master)
        self.preview = preview
        self.on_imported = on_imported
        self.configure(bg="#f1f5f9")
        self.title("Bulk CSV Import Preview")
        self.geometry("780x490")
        self.minsize(660, 410)
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        footer = ttk.Frame(self, padding=12)
        footer.pack(side=tk.BOTTOM, fill=tk.X)

        self.skip_dups_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            footer,
            text="Skip detected duplicates",
            variable=self.skip_dups_var,
            command=self._sync_import_button,
        ).pack(side=tk.LEFT)

        ttk.Button(
            footer, text="Cancel", style="Secondary.TButton", command=self.destroy
        ).pack(side=tk.RIGHT)

        self.import_btn = ttk.Button(
            footer,
            text="Import Valid Rows",
            style="Primary.TButton",
            command=self._commit_import,
        )
        self.import_btn.pack(side=tk.RIGHT, padx=(0, 8))

        summary_text = (
            f"Total Rows: {len(self.preview.rows)}   |   "
            f"Ready (New): {len(self.preview.new_valid_rows)}   |   "
            f"Potential Duplicates: {len(self.preview.duplicate_rows)}   |   "
            f"Errors: {len(self.preview.error_rows)}"
        )
        ttk.Label(
            self, text=summary_text, font=(UI_FONT, 10, "bold"), padding=12
        ).pack(fill=tk.X)

        frame = ttk.Frame(self, padding=(12, 0, 12, 4))
        frame.pack(fill=tk.BOTH, expand=True)

        cols = ("line", "status", "date", "category", "mode", "amount", "detail")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        tree.heading("line", text="Line")
        tree.heading("status", text="Status")
        tree.heading("date", text="Date")
        tree.heading("category", text="Category")
        tree.heading("mode", text="Mode")
        tree.heading("amount", text="Amount")
        tree.heading("detail", text="Notes / Error")

        tree.column("line", width=45, anchor=tk.CENTER)
        tree.column("status", width=85, anchor=tk.CENTER)
        tree.column("date", width=90, anchor=tk.CENTER)
        tree.column("category", width=120)
        tree.column("mode", width=65, anchor=tk.CENTER)
        tree.column("amount", width=90, anchor=tk.E)
        tree.column("detail", width=230)

        tree.tag_configure("err", foreground="#b91c1c")
        tree.tag_configure("dup", foreground="#b45309")
        tree.tag_configure("ok", foreground="#15803d")

        for r in self.preview.rows:
            if not r.is_valid:
                status, tag, detail, amt = "Error", "err", r.error, "-"
            elif r.is_duplicate:
                status, tag, detail, amt = (
                    "Duplicate",
                    "dup",
                    r.note or "Matches an existing expense",
                    format_inr(r.amount_paise),
                )
            else:
                status, tag, detail, amt = (
                    "Valid",
                    "ok",
                    r.note or r.description,
                    format_inr(r.amount_paise),
                )

            tree.insert(
                "",
                tk.END,
                values=(r.line_number, status, r.date, r.category, r.payment_mode, amt, detail),
                tags=(tag,),
            )

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._sync_import_button()

    def _sync_import_button(self) -> None:
        chosen = (
            self.preview.new_valid_rows
            if self.skip_dups_var.get()
            else self.preview.valid_rows
        )
        n = len(chosen)
        self.import_btn.config(text=f"Import {n} Row{'s' if n != 1 else ''}")
        if n == 0:
            self.import_btn.state(["disabled"])
        else:
            self.import_btn.state(["!disabled"])

    def _commit_import(self) -> None:
        chosen = (
            self.preview.new_valid_rows
            if self.skip_dups_var.get()
            else self.preview.valid_rows
        )
        if not chosen:
            return

        batch = [
            (r.amount_paise, r.discount_paise, r.category, r.payment_mode, r.description, r.date)
            for r in chosen
        ]
        count = db.add_expenses_batch(batch)
        self.on_imported(count)
        self.destroy()


class SettingsDialog(tk.Toplevel):
    """Manage carryforward behavior, default monthly budget, and custom categories."""

    def __init__(self, master: tk.Misc, on_saved: Callable[[], None]):
        super().__init__(master)
        self.on_saved = on_saved
        self.configure(bg="#f1f5f9")
        self.title("Preferences & Categories")
        self.geometry("500x520")
        self.minsize(460, 460)
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        # Pin footer first so Save Settings is never pushed out of view.
        footer = ttk.Frame(self, padding=12)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(footer, text="Cancel", style="Secondary.TButton", command=self.destroy).pack(
            side=tk.RIGHT
        )
        ttk.Button(
            footer, text="Save Settings", style="Primary.TButton", command=self._save
        ).pack(side=tk.RIGHT, padx=(0, 8))

        budget_sec = ttk.LabelFrame(self, text=" Budget Rules ", padding=10)
        budget_sec.pack(fill=tk.X, padx=12, pady=(12, 8))

        ttk.Label(
            budget_sec, text="Month-to-Month Carryforward:", font=(UI_FONT, 9, "bold")
        ).pack(anchor=tk.W, pady=(0, 4))

        self.carry_var = tk.StringVar(value=db.get_carryforward_mode().value)
        for mode in CarryforwardMode:
            ttk.Radiobutton(
                budget_sec,
                text=mode.label,
                variable=self.carry_var,
                value=mode.value,
            ).pack(anchor=tk.W, pady=2)

        def_row = ttk.Frame(budget_sec)
        def_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(def_row, text="Auto-default budget for new months (₹, 0 = off):").pack(
            side=tk.LEFT
        )
        default_paise = db.get_default_budget_paise()
        self.default_budget_entry = ttk.Entry(def_row, width=10)
        self.default_budget_entry.pack(side=tk.RIGHT)
        self.default_budget_entry.insert(
            0, paise_to_input_str(default_paise) if default_paise > 0 else "0"
        )

        # Categories section
        cat_sec = ttk.LabelFrame(self, text=" Expense Categories ", padding=10)
        cat_sec.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        add_row = ttk.Frame(cat_sec)
        add_row.pack(fill=tk.X, pady=(0, 6))
        self.new_cat_entry = ttk.Entry(add_row)
        self.new_cat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(add_row, text="Add", style="Subtle.TButton", command=self._add_cat).pack(
            side=tk.RIGHT
        )

        list_box_frame = ttk.Frame(cat_sec)
        list_box_frame.pack(fill=tk.BOTH, expand=True)

        self.cat_listbox = tk.Listbox(
            list_box_frame,
            height=6,
            font=(UI_FONT, 9),
            bg="#ffffff",
            fg="#0f172a",
            selectbackground="#dbeafe",
            selectforeground="#0f172a",
        )
        self.cat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(list_box_frame, orient=tk.VERTICAL, command=self.cat_listbox.yview)
        self.cat_listbox.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        cat_btns = ttk.Frame(cat_sec)
        cat_btns.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(
            cat_btns, text="Rename Selected", style="Subtle.TButton", command=self._rename_cat
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            cat_btns,
            text="Remove Selected (moves items to 'Other')",
            style="Subtle.TButton",
            command=self._remove_cat,
        ).pack(side=tk.LEFT)

        self._refresh_categories()

    def _refresh_categories(self) -> None:
        self.cat_listbox.delete(0, tk.END)
        for c in db.get_categories():
            self.cat_listbox.insert(tk.END, c)

    def _add_cat(self) -> None:
        name = self.new_cat_entry.get().strip()
        if not name:
            return
        if not db.add_category(name):
            messagebox.showwarning("Duplicate", f"Category '{name}' already exists.", parent=self)
            return
        self.new_cat_entry.delete(0, tk.END)
        self._refresh_categories()
        self.on_saved()

    def _rename_cat(self) -> None:
        sel = self.cat_listbox.curselection()
        if not sel:
            messagebox.showwarning("Select Category", "Select a category to rename.", parent=self)
            return
        old_name = self.cat_listbox.get(sel[0])
        if old_name == "Other":
            messagebox.showwarning("Protected", "'Other' cannot be renamed.", parent=self)
            return

        new_name = simpledialog.askstring(
            "Rename Category",
            f"Enter new name for '{old_name}':",
            initialvalue=old_name,
            parent=self,
        )
        if not new_name or not new_name.strip() or new_name.strip() == old_name:
            return

        if not db.rename_category(old_name, new_name):
            messagebox.showwarning(
                "Duplicate Name", f"Category '{new_name.strip()}' already exists.", parent=self
            )
            return
        self._refresh_categories()
        self.on_saved()

    def _remove_cat(self) -> None:
        sel = self.cat_listbox.curselection()
        if not sel:
            return
        name = self.cat_listbox.get(sel[0])
        if name == "Other":
            messagebox.showwarning("Protected", "'Other' cannot be removed.", parent=self)
            return
        db.delete_category(name)
        self._refresh_categories()
        self.on_saved()

    def _save(self) -> None:
        try:
            default_paise = parse_rupees_to_paise(
                self.default_budget_entry.get(),
                field_name="Default budget",
                allow_zero=True,
            )
        except ValidationError as exc:
            messagebox.showerror("Invalid Input", str(exc), parent=self)
            return

        db.set_carryforward_mode(CarryforwardMode(self.carry_var.get()))
        db.set_default_budget_paise(default_paise)
        self.on_saved()
        self.destroy()