"""
calculations.py - Expense analysis, category aggregation, and budget warning logic
Demonstrates: datetime parsing/validation, dictionaries, calculations, and exception handling.
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple


def validate_expense_inputs(amount_str: str, category: str, description: str, date_str: str) -> Tuple[float, str, str, str]:
    """
    Validates user input fields for an expense entry.
    Demonstrates Exception Handling:
    - ValueError for invalid float amounts, non-positive amounts, or bad date formats
    - ValueError for empty categories
    """
    # 1. Validate Category
    clean_category = category.strip()
    if not clean_category:
        raise ValueError("Please select or enter a Category.")

    # 2. Validate Amount
    clean_amount_str = amount_str.strip()
    if not clean_amount_str:
        raise ValueError("Amount cannot be empty.")
    try:
        amount = float(clean_amount_str)
    except ValueError:
        raise ValueError(f"Invalid amount '{clean_amount_str}'. Please enter a valid number (e.g. 250.50).")
    
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    
    # Rounded to 2 decimal places
    amount = round(amount, 2)

    # 3. Validate Date format (YYYY-MM-DD) using datetime
    clean_date_str = date_str.strip()
    if not clean_date_str:
        raise ValueError("Date cannot be empty.")
    try:
        # datetime validation
        parsed_date = datetime.strptime(clean_date_str, "%Y-%m-%d")
        formatted_date = parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date '{clean_date_str}'. Expected format is YYYY-MM-DD (e.g. 2026-11-17).")

    clean_desc = description.strip()

    return amount, clean_category, clean_desc, formatted_date


def validate_budget_input(budget_str: str) -> float:
    """Validates budget input number."""
    clean_str = budget_str.strip()
    if not clean_str:
        raise ValueError("Budget amount cannot be empty.")
    try:
        budget = float(clean_str)
    except ValueError:
        raise ValueError(f"Invalid budget '{clean_str}'. Please enter a valid positive number.")
    if budget < 0:
        raise ValueError("Budget cannot be negative.")
    return round(budget, 2)


def compute_spending_summary(expenses: List[Dict[str, Any]], monthly_budget: float = 0.0) -> Dict[str, Any]:
    """
    Calculates total spending and category-wise totals using dictionaries.
    Also computes budget status and warning flags.

    Concepts Demonstrated:
    - Dictionaries: category_totals accumulator and summary return object.
    - Calculations: total sum, category percentages, budget difference, over-budget flag.
    """
    total_spending = 0.0
    category_totals: Dict[str, float] = {}

    # Iterate through expenses and accumulate totals in a dictionary
    for exp in expenses:
        amt = float(exp.get("amount", 0.0))
        cat = exp.get("category", "Uncategorized")
        
        total_spending += amt
        category_totals[cat] = category_totals.get(cat, 0.0) + amt

    total_spending = round(total_spending, 2)

    # Calculate category percentages
    category_breakdown: List[Dict[str, Any]] = []
    for cat, total in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
        pct = (total / total_spending * 100.0) if total_spending > 0 else 0.0
        category_breakdown.append({
            "category": cat,
            "total": round(total, 2),
            "percentage": round(pct, 1)
        })

    # Budget Warning Logic:
    # Set a monthly budget and show a warning when spending exceeds it.
    is_over_budget = False
    warning_message = ""
    difference = round(monthly_budget - total_spending, 2) if monthly_budget > 0 else 0.0

    if monthly_budget > 0:
        if total_spending > monthly_budget:
            is_over_budget = True
            exceeded_by = round(total_spending - monthly_budget, 2)
            warning_message = f"WARNING: Spending of ₹{total_spending:,.2f} exceeds budget of ₹{monthly_budget:,.2f} by ₹{exceeded_by:,.2f}!"
        elif total_spending >= monthly_budget * 0.9:
            warning_message = f"Caution: You have used {((total_spending/monthly_budget)*100):.1f}% of your ₹{monthly_budget:,.2f} budget."
        else:
            warning_message = f"Budget Healthy: ₹{difference:,.2f} remaining out of ₹{monthly_budget:,.2f}."
    else:
        warning_message = "No budget set for this month. Set a budget to monitor spending."

    return {
        "total_spending": total_spending,
        "category_totals": category_totals,
        "category_breakdown": category_breakdown,
        "monthly_budget": monthly_budget,
        "is_over_budget": is_over_budget,
        "difference": difference,
        "warning_message": warning_message
    }
