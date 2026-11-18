"""
calculations.py - Input validation, expense aggregation, and budget warnings.

This module contains application business logic independent of the Tkinter GUI
and SQLite implementation.
"""

import math
from datetime import datetime
from typing import Any


# Keep the selectable categories in one place so the GUI and demo data agree.
EXPENSE_CATEGORIES = (
    "Food & Canteen",
    "Books & Stationery",
    "Hostel & Rent",
    "Travel & Bus",
    "Course Fees",
    "Entertainment",
    "Personal & Medical",
    "Other",
)


def validate_expense_inputs(
    amount_str: str,
    category: str,
    description: str,
    date_str: str,
) -> tuple[float, str, str, str]:
    """Validate and normalize the fields required to save an expense."""
    clean_category = category.strip()
    if not clean_category:
        raise ValueError("Please select a category.")

    clean_amount = amount_str.strip()
    if not clean_amount:
        raise ValueError("Amount cannot be empty.")

    try:
        amount = float(clean_amount)
    except ValueError as exc:
        raise ValueError(
            f"Invalid amount '{clean_amount}'. Enter a number such as 250.50."
        ) from exc

    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("Amount must be a finite number greater than zero.")

    clean_date = date_str.strip()
    if not clean_date:
        raise ValueError("Date cannot be empty.")

    try:
        parsed_date = datetime.strptime(clean_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            f"Invalid date '{clean_date}'. Expected YYYY-MM-DD "
            "(for example, 2026-11-18)."
        ) from exc

    # strptime can accept some non-zero-padded values on some platforms.
    # Require the exact format shown to the user.
    normalized_date = parsed_date.strftime("%Y-%m-%d")
    if normalized_date != clean_date:
        raise ValueError("Date must use the YYYY-MM-DD format.")

    return round(amount, 2), clean_category, description.strip(), normalized_date


def validate_budget_input(budget_str: str) -> float:
    """Validate a monthly budget; a useful budget must be greater than zero."""
    clean_value = budget_str.strip()
    if not clean_value:
        raise ValueError("Budget amount cannot be empty.")

    try:
        budget = float(clean_value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid budget '{clean_value}'. Enter a valid positive number."
        ) from exc

    if not math.isfinite(budget) or budget <= 0:
        raise ValueError("Budget must be a finite number greater than zero.")

    return round(budget, 2)


def compute_spending_summary(
    expenses: list[dict[str, Any]],
    monthly_budget: float = 0.0,
) -> dict[str, Any]:
    """
    Calculate total spending, category totals, percentages, and budget status.

    `monthly_budget=0` means no budget is set. The returned `budget_status`
    is one of: "no_budget", "healthy", "caution", or "exceeded".
    """
    budget = float(monthly_budget)
    if not math.isfinite(budget) or budget < 0:
        raise ValueError("Monthly budget must be a finite, non-negative number.")

    total_spending = 0.0
    category_totals: dict[str, float] = {}

    for expense in expenses:
        try:
            amount = float(expense.get("amount", 0.0))
        except (TypeError, ValueError) as exc:
            raise ValueError("Expense amounts must be numeric.") from exc

        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Expense amounts must be finite and non-negative.")

        category = str(expense.get("category") or "Uncategorized").strip()
        if not category:
            category = "Uncategorized"

        total_spending += amount
        category_totals[category] = category_totals.get(category, 0.0) + amount

    total_spending = round(total_spending, 2)

    category_breakdown = []
    for category, category_total in sorted(
        category_totals.items(), key=lambda item: item[1], reverse=True
    ):
        percentage = (
            category_total / total_spending * 100.0
            if total_spending > 0
            else 0.0
        )
        category_breakdown.append(
            {
                "category": category,
                "total": round(category_total, 2),
                "percentage": round(percentage, 1),
            }
        )

    difference = round(budget - total_spending, 2) if budget > 0 else 0.0
    exceeded_by = 0.0
    percentage_used = (
        round(total_spending / budget * 100.0, 1) if budget > 0 else 0.0
    )

    if budget <= 0:
        budget_status = "no_budget"
        warning_message = "No budget set for this month. Set a budget to monitor spending."
        is_over_budget = False
    elif total_spending > budget:
        budget_status = "exceeded"
        is_over_budget = True
        exceeded_by = round(total_spending - budget, 2)
        warning_message = (
            f"WARNING: Spending of ₹{total_spending:,.2f} exceeds budget "
            f"of ₹{budget:,.2f} by ₹{exceeded_by:,.2f}!"
        )
    elif total_spending >= budget * 0.9:
        budget_status = "caution"
        is_over_budget = False
        warning_message = (
            f"Caution: You have used {percentage_used:.1f}% of your "
            f"₹{budget:,.2f} budget."
        )
    else:
        budget_status = "healthy"
        is_over_budget = False
        warning_message = (
            f"Budget Healthy: ₹{difference:,.2f} remaining out of "
            f"₹{budget:,.2f}."
        )

    return {
        "total_spending": total_spending,
        "category_totals": {
            category: round(total, 2)
            for category, total in category_totals.items()
        },
        "category_breakdown": category_breakdown,
        "monthly_budget": budget,
        "is_over_budget": is_over_budget,
        "difference": difference,
        "exceeded_by": exceeded_by,
        "percentage_used": percentage_used,
        "budget_status": budget_status,
        "warning_message": warning_message,
    }
