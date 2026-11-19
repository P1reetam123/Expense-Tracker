"""
calculations.py - Pure business logic: validation, carryforward engine,
summaries, filtering/sorting, and streaming CSV import/export.

Contains zero SQLite or Tkinter imports.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from models import (
    BudgetAdjustment,
    BudgetStatus,
    CarryforwardMode,
    CategoryBreakdown,
    Expense,
    ImportFormatError,
    ImportPreview,
    ImportRowResult,
    MonthlyTrendPoint,
    PaymentMode,
    SpendingSummary,
    ValidationError,
    format_inr,
    paise_to_input_str,
    parse_rupees_to_paise,
)


CSV_HEADERS = ("date", "category", "payment_mode", "description", "amount", "discount")


# ----------------- VALIDATION -----------------

def validate_date_str(date_str: str) -> str:
    clean = date_str.strip()
    if not clean:
        raise ValidationError("Date cannot be empty.")
    try:
        parsed = datetime.strptime(clean, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError(
            f"Invalid date '{clean}'. Expected YYYY-MM-DD (e.g., 2026-11-18)."
        ) from exc

    normalized = parsed.strftime("%Y-%m-%d")
    if normalized != clean:
        raise ValidationError("Date must use the YYYY-MM-DD format.")
    return normalized


def validate_expense_inputs(
    amount_str: str,
    category: str,
    description: str,
    date_str: str,
    discount_str: str = "0",
    payment_mode: str = PaymentMode.UPI.value,
) -> tuple[int, int, str, str, str, str]:
    """Validate and return (amount_paise, discount_paise, category, payment_mode, description, date)."""
    clean_category = category.strip()
    if not clean_category:
        raise ValidationError("Please select a category.")

    amount_paise = parse_rupees_to_paise(amount_str, field_name="Amount")
    discount_paise = parse_rupees_to_paise(
        discount_str, field_name="Coupon / Discount", allow_zero=True
    )
    clean_date = validate_date_str(date_str)
    clean_mode = payment_mode.strip() or PaymentMode.UPI.value

    return (
        amount_paise,
        discount_paise,
        clean_category,
        clean_mode,
        description.strip(),
        clean_date,
    )


def validate_budget_input(budget_str: str) -> int:
    return parse_rupees_to_paise(budget_str, field_name="Budget")


def validate_adjustment_input(
    amount_str: str, reason: str, date_str: str, *, is_deduction: bool = False
) -> tuple[int, str, str]:
    paise = parse_rupees_to_paise(amount_str, field_name="Adjustment amount")
    if is_deduction:
        paise = -paise
    clean_reason = reason.strip()
    if not clean_reason:
        raise ValidationError("Please enter a short reason for this adjustment.")
    clean_date = validate_date_str(date_str)
    return paise, clean_reason, clean_date


# ----------------- BUDGET & CARRYFORWARD ENGINE -----------------

def _aggregate_spent_by_month(expenses: Iterable[Expense]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for exp in expenses:
        totals[exp.date[:7]] += exp.amount_paise
    return totals


def _aggregate_adj_by_month(adjustments: Iterable[BudgetAdjustment]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for adj in adjustments:
        totals[adj.month] += adj.amount_paise
    return totals


def compute_chronological_budgets(
    budgets_by_month: dict[str, int],
    all_expenses: Sequence[Expense],
    all_adjustments: Sequence[BudgetAdjustment],
    mode: CarryforwardMode,
    target_months: Iterable[str] = (),
) -> dict[str, tuple[int, int, int, int]]:
    """
    Return per-month tuple: (base_paise, adj_paise, carry_in_paise, effective_paise)
    computed chronologically so edits in older months propagate forward.
    """
    spent_by_month = _aggregate_spent_by_month(all_expenses)
    adj_by_month = _aggregate_adj_by_month(all_adjustments)

    months = sorted(
        set(budgets_by_month)
        | set(adj_by_month)
        | set(spent_by_month)
        | set(target_months)
    )

    result: dict[str, tuple[int, int, int, int]] = {}
    running_carry = 0

    for month in months:
        base = budgets_by_month.get(month, 0)
        adj = adj_by_month.get(month, 0)
        spent = spent_by_month.get(month, 0)

        has_budget_plan = base > 0 or adj != 0
        if not has_budget_plan:
            # Inactive / unbudgeted months pass carryforward through untouched.
            result[month] = (0, 0, 0, 0)
            continue

        carry_in = running_carry if mode != CarryforwardMode.OFF else 0
        effective = base + adj + carry_in
        result[month] = (base, adj, carry_in, effective)

        balance = effective - spent
        if mode == CarryforwardMode.BOTH:
            running_carry = balance
        elif mode == CarryforwardMode.DEFICIT_ONLY:
            running_carry = min(0, balance)
        else:
            running_carry = 0

    return result


def compute_spending_summary(
    *,
    selected_month: str,
    all_expenses: Sequence[Expense],
    budgets_by_month: dict[str, int],
    all_adjustments: Sequence[BudgetAdjustment],
    carryforward_mode: CarryforwardMode,
) -> SpendingSummary:
    """Compute summary for either a specific YYYY-MM month or 'All' months."""
    is_all = selected_month.strip().lower() == "all"

    month_expenses = (
        list(all_expenses)
        if is_all
        else [e for e in all_expenses if e.date.startswith(selected_month)]
    )

    total_spent = sum(e.amount_paise for e in month_expenses)
    total_discount = sum(e.discount_paise for e in month_expenses)

    cat_totals: dict[str, int] = defaultdict(int)
    cat_counts: dict[str, int] = defaultdict(int)
    for exp in month_expenses:
        cat = exp.category.strip() or "Other"
        cat_totals[cat] += exp.amount_paise
        cat_counts[cat] += 1

    breakdown = tuple(
        CategoryBreakdown(
            category=cat,
            total_paise=cat_total,
            percentage=round(cat_total / total_spent * 100.0, 1) if total_spent > 0 else 0.0,
            count=cat_counts[cat],
        )
        for cat, cat_total in sorted(
            cat_totals.items(), key=lambda item: item[1], reverse=True
        )
    )

    if is_all:
        base_budget = sum(budgets_by_month.values())
        adjustments_total = sum(a.amount_paise for a in all_adjustments)
        carry_in = 0  # Internal month-to-month rollovers cancel across all-time total.
        effective_budget = base_budget + adjustments_total

        expense_months = {e.date[:7] for e in all_expenses}
        budgeted_months = set(budgets_by_month)
        budgeted_count = len(budgeted_months)
        unbudgeted_months = tuple(sorted(expense_months - budgeted_months))
        unbudgeted_count = len(unbudgeted_months)
    else:
        timeline = compute_chronological_budgets(
            budgets_by_month,
            all_expenses,
            all_adjustments,
            carryforward_mode,
            target_months=(selected_month,),
        )
        base_budget, adjustments_total, carry_in, effective_budget = timeline.get(
            selected_month, (0, 0, 0, 0)
        )
        budgeted_count = 1 if effective_budget > 0 else 0
        unbudgeted_count = 0
        unbudgeted_months = ()

    if effective_budget <= 0 and base_budget <= 0:
        status = BudgetStatus.NO_BUDGET
        remaining = 0
        exceeded_by = 0
        pct_used = 0.0
        warning = (
            "No budgets recorded yet. Set a monthly budget to monitor spending."
            if is_all
            else "No budget set for this month. Set a budget to monitor spending."
        )
    elif effective_budget <= 0:
        # Prior carryforward/deductions consumed the entire budget already.
        status = BudgetStatus.EXCEEDED
        exceeded_by = total_spent - effective_budget
        remaining = 0
        pct_used = 100.0
        warning = (
            f"WARNING: Effective budget exhausted ({format_inr(effective_budget)}). "
            f"Over by {format_inr(exceeded_by)}!"
        )
    elif total_spent > effective_budget:
        status = BudgetStatus.EXCEEDED
        exceeded_by = total_spent - effective_budget
        remaining = 0
        pct_used = round(total_spent / effective_budget * 100.0, 1)
        warning = (
            f"WARNING: Spent {format_inr(total_spent)} — exceeded budget "
            f"of {format_inr(effective_budget)} by {format_inr(exceeded_by)}!"
        )
    elif total_spent * 10 >= effective_budget * 9:
        status = BudgetStatus.CAUTION
        remaining = effective_budget - total_spent
        exceeded_by = 0
        pct_used = round(total_spent / effective_budget * 100.0, 1)
        warning = (
            f"Caution: Used {pct_used:.1f}% of {format_inr(effective_budget)} "
            f"({format_inr(remaining)} left)."
        )
    else:
        status = BudgetStatus.HEALTHY
        remaining = effective_budget - total_spent
        exceeded_by = 0
        pct_used = round(total_spent / effective_budget * 100.0, 1)
        warning = (
            f"Healthy: {format_inr(remaining)} remaining out of "
            f"{format_inr(effective_budget)}."
        )

    if is_all and unbudgeted_months and status != BudgetStatus.NO_BUDGET:
        shown = ", ".join(unbudgeted_months[:3])
        extra = (
            f" (+{len(unbudgeted_months) - 3} more)"
            if len(unbudgeted_months) > 3
            else ""
        )
        warning += f"  •  Unbudgeted: {shown}{extra}"
    
    return SpendingSummary(
        total_spent_paise=total_spent,
        total_discount_paise=total_discount,
        base_budget_paise=base_budget,
        adjustments_paise=adjustments_total,
        carryforward_in_paise=carry_in,
        effective_budget_paise=effective_budget,
        remaining_paise=remaining,
        exceeded_by_paise=exceeded_by,
        percentage_used=pct_used,
        budget_status=status,
        warning_message=warning,
        category_breakdown=breakdown,
        budgeted_months_count=budgeted_count,
        unbudgeted_months_count=unbudgeted_count,
        unbudgeted_months=unbudgeted_months,
    )


def compute_monthly_trends(
    all_expenses: Sequence[Expense],
    budgets_by_month: dict[str, int],
    all_adjustments: Sequence[BudgetAdjustment],
    carryforward_mode: CarryforwardMode,
    limit: int = 8,
) -> list[MonthlyTrendPoint]:
    spent_by_month = _aggregate_spent_by_month(all_expenses)
    timeline = compute_chronological_budgets(
        budgets_by_month, all_expenses, all_adjustments, carryforward_mode
    )
    months = sorted(timeline.keys())[-limit:]
    return [
        MonthlyTrendPoint(
            month=m,
            effective_budget_paise=max(0, timeline[m][3]),
            spent_paise=spent_by_month.get(m, 0),
        )
        for m in months
    ]


# ----------------- FILTERING & SORTING -----------------

def filter_expenses(
    expenses: Sequence[Expense],
    *,
    category_filter: str = "All",
    search_query: str = "",
) -> list[Expense]:
    query = search_query.strip().lower()
    cat_filter = category_filter.strip()
    filtered = []
    for exp in expenses:
        if cat_filter and cat_filter != "All" and exp.category != cat_filter:
            continue
        if query:
            haystack = f"{exp.description} {exp.category} {exp.payment_mode} {exp.date}".lower()
            if query not in haystack:
                continue
        filtered.append(exp)
    return filtered


def sort_expenses(
    expenses: Sequence[Expense],
    sort_col: str,
    descending: bool,
) -> list[Expense]:
    key_map = {
        "id": lambda e: e.id,
        "date": lambda e: (e.date, e.id),
        "category": lambda e: (e.category.lower(), e.date),
        "payment_mode": lambda e: (e.payment_mode.lower(), e.date),
        "description": lambda e: (e.description.lower(), e.date),
        "amount": lambda e: (e.amount_paise, e.date),
        "discount": lambda e: (e.discount_paise, e.date),
    }
    key_fn = key_map.get(sort_col, key_map["date"])
    return sorted(expenses, key=key_fn, reverse=descending)


# ----------------- CSV STREAMING EXPORT & BULK IMPORT -----------------

def export_expenses_to_csv(expenses: Iterable[Expense], file_path: str | Path) -> int:
    count = 0
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        for exp in expenses:
            writer.writerow(
                (
                    exp.date,
                    exp.category,
                    exp.payment_mode,
                    exp.description,
                    paise_to_input_str(exp.amount_paise),
                    paise_to_input_str(exp.discount_paise),
                )
            )
            count += 1
    return count


def write_csv_template(file_path: str | Path) -> None:
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        writer.writerow(("2026-11-18", "Food & Canteen", "UPI", "Campus lunch", "150.00", "0.00"))
        writer.writerow(("2026-11-18", "Books & Stationery", "Card", "Python reference", "450.00", "50.00"))


def _iter_csv_dicts(file_path: str | Path) -> Iterator[tuple[int, dict[str, str]]]:
    with open(file_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ImportFormatError("The CSV file is empty or missing headers.")
        normalized_headers = {h.strip().lower() for h in reader.fieldnames if h}
        if "date" not in normalized_headers or "amount" not in normalized_headers:
            raise ImportFormatError(
                "CSV must include at least 'date' and 'amount' columns."
            )
        for line_no, raw_row in enumerate(reader, start=2):
            clean_row = {
                (k.strip().lower() if k else ""): (v.strip() if v else "")
                for k, v in raw_row.items()
            }
            if any(clean_row.values()):
                yield line_no, clean_row


def build_import_preview(
    file_path: str | Path,
    known_categories: Sequence[str],
    existing_counts: Counter[tuple[str, str, str, str, int]],
) -> ImportPreview:
    """Stream CSV rows, validate each row, map categories, and detect duplicates."""
    cat_lookup = {c.lower(): c for c in known_categories}
    mode_lookup = {m.value.lower(): m.value for m in PaymentMode}
    remaining_existing = Counter(existing_counts)
    results: list[ImportRowResult] = []

    for line_no, row in _iter_csv_dicts(file_path):
        raw_date = row.get("date", "")
        raw_amount = row.get("amount", "")
        raw_discount = row.get("discount", "") or "0"
        raw_cat = row.get("category", "") or "Other"
        raw_mode = row.get("payment_mode", "") or PaymentMode.UPI.value
        raw_desc = row.get("description", "")

        note = ""
        canonical_cat = cat_lookup.get(raw_cat.lower())
        if canonical_cat is None:
            canonical_cat = "Other" if "other" in cat_lookup else known_categories[-1]
            note = f"Category '{raw_cat}' mapped to '{canonical_cat}'"

        canonical_mode = mode_lookup.get(raw_mode.lower(), PaymentMode.UPI.value)

        try:
            amount_paise, discount_paise, cat, mode, desc, norm_date = (
                validate_expense_inputs(
                    raw_amount,
                    canonical_cat,
                    raw_desc,
                    raw_date,
                    raw_discount,
                    canonical_mode,
                )
            )
            fingerprint = (
                norm_date,
                cat.lower(),
                mode.lower(),
                desc.lower(),
                amount_paise,
            )
            is_dup = remaining_existing[fingerprint] > 0
            if is_dup:
                remaining_existing[fingerprint] -= 1

            results.append(
                ImportRowResult(
                    line_number=line_no,
                    date=norm_date,
                    category=cat,
                    payment_mode=mode,
                    description=desc,
                    amount_paise=amount_paise,
                    discount_paise=discount_paise,
                    is_valid=True,
                    is_duplicate=is_dup,
                    note=note,
                )
            )
        except ValidationError as exc:
            results.append(
                ImportRowResult(
                    line_number=line_no,
                    date=raw_date,
                    category=raw_cat,
                    payment_mode=raw_mode,
                    description=raw_desc,
                    amount_paise=0,
                    discount_paise=0,
                    is_valid=False,
                    error=str(exc),
                )
            )

    return ImportPreview(rows=tuple(results))