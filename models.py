"""
models.py - Domain models, exceptions, enums, and exact INR currency utilities.

All monetary values inside the application are stored and calculated as integer
paise (1 INR = 100 paise) to avoid binary floating-point rounding drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum


DEFAULT_CATEGORIES: tuple[str, ...] = (
    "Food & Canteen",
    "Books & Stationery",
    "Hostel & Rent",
    "Travel & Bus",
    "Course Fees",
    "Entertainment",
    "Personal & Medical",
    "Other",
)


class BudgetStatus(str, Enum):
    NO_BUDGET = "no_budget"
    HEALTHY = "healthy"
    CAUTION = "caution"
    EXCEEDED = "exceeded"


class CarryforwardMode(str, Enum):
    OFF = "off"
    BOTH = "both"
    DEFICIT_ONLY = "deficit_only"

    @property
    def label(self) -> str:
        return {
            CarryforwardMode.OFF: "Off (Independent months)",
            CarryforwardMode.BOTH: "Roll over Surplus & Overspend",
            CarryforwardMode.DEFICIT_ONLY: "Roll over Overspend only",
        }[self]


class PaymentMode(str, Enum):
    UPI = "UPI"
    CASH = "Cash"
    CARD = "Card"
    BANK = "Bank"


class ExpenseTrackerError(Exception):
    """Base exception for all domain and persistence errors."""


class ValidationError(ExpenseTrackerError):
    """Raised when user or CSV input fails domain validation."""


class PersistenceError(ExpenseTrackerError):
    """Raised when a SQLite operation fails."""


class ImportFormatError(ExpenseTrackerError):
    """Raised when a CSV file structure cannot be parsed."""


@dataclass(frozen=True, slots=True)
class Expense:
    id: int
    amount_paise: int
    discount_paise: int
    category: str
    payment_mode: str
    description: str
    date: str


@dataclass(frozen=True, slots=True)
class BudgetAdjustment:
    id: int
    month: str
    amount_paise: int
    reason: str
    date: str


@dataclass(frozen=True, slots=True)
class CategoryBreakdown:
    category: str
    total_paise: int
    percentage: float
    count: int


@dataclass(frozen=True, slots=True)
class MonthlyTrendPoint:
    month: str
    effective_budget_paise: int
    spent_paise: int


@dataclass(frozen=True, slots=True)
class SpendingSummary:
    total_spent_paise: int
    total_discount_paise: int
    base_budget_paise: int
    adjustments_paise: int
    carryforward_in_paise: int
    effective_budget_paise: int
    remaining_paise: int
    exceeded_by_paise: int
    percentage_used: float
    budget_status: BudgetStatus
    warning_message: str
    category_breakdown: tuple[CategoryBreakdown, ...]
    budgeted_months_count: int = 1
    unbudgeted_months_count: int = 0
    unbudgeted_months: tuple[str, ...] = ()
    budgeted_months_count: int = 1
    unbudgeted_months_count: int = 0
    unbudgeted_months: tuple[str, ...] = ()
    total_spent_paise: int
    total_discount_paise: int
    base_budget_paise: int
    adjustments_paise: int
    carryforward_in_paise: int
    effective_budget_paise: int
    remaining_paise: int
    exceeded_by_paise: int
    percentage_used: float
    budget_status: BudgetStatus
    warning_message: str
    category_breakdown: tuple[CategoryBreakdown, ...]
    budgeted_months_count: int = 1
    unbudgeted_months_count: int = 0


@dataclass(frozen=True, slots=True)
class ImportRowResult:
    line_number: int
    date: str
    category: str
    payment_mode: str
    description: str
    amount_paise: int
    discount_paise: int
    is_valid: bool
    is_duplicate: bool = False
    error: str = ""
    note: str = ""


@dataclass(frozen=True, slots=True)
class ImportPreview:
    rows: tuple[ImportRowResult, ...]

    @property
    def valid_rows(self) -> tuple[ImportRowResult, ...]:
        return tuple(r for r in self.rows if r.is_valid)

    @property
    def new_valid_rows(self) -> tuple[ImportRowResult, ...]:
        return tuple(r for r in self.rows if r.is_valid and not r.is_duplicate)

    @property
    def duplicate_rows(self) -> tuple[ImportRowResult, ...]:
        return tuple(r for r in self.rows if r.is_valid and r.is_duplicate)

    @property
    def error_rows(self) -> tuple[ImportRowResult, ...]:
        return tuple(r for r in self.rows if not r.is_valid)


def parse_rupees_to_paise(
    raw: str,
    *,
    field_name: str = "Amount",
    allow_zero: bool = False,
    allow_negative: bool = False,
) -> int:
    """Parse a rupee string safely via Decimal into exact integer paise."""
    clean = raw.strip()
    if not clean:
        if allow_zero:
            return 0
        raise ValidationError(f"{field_name} cannot be empty.")

    # Strip common currency prefixes/commas if pasted from bank statements.
    normalized = clean.replace(",", "").lstrip("₹").strip()
    if normalized.lower().startswith("rs."):
        normalized = normalized[3:].strip()

    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValidationError(
            f"Invalid {field_name.lower()} '{clean}'. Enter a number such as 250.50."
        ) from exc

    if not value.is_finite():
        raise ValidationError(f"{field_name} must be a finite number.")

    exp = value.as_tuple().exponent
    if isinstance(exp, int) and exp < -2:
        raise ValidationError(f"{field_name} can have at most 2 decimal places.")

    paise = int(value * 100)

    if not allow_negative and paise < 0:
        raise ValidationError(f"{field_name} cannot be negative.")
    if not allow_zero and paise == 0:
        raise ValidationError(f"{field_name} cannot be zero.")

    return paise


def paise_to_input_str(paise: int) -> str:
    """Convert integer paise to plain decimal string without float drift."""
    sign = "-" if paise < 0 else ""
    abs_p = abs(paise)
    return f"{sign}{abs_p // 100}.{abs_p % 100:02d}"


def format_inr(paise: int, *, show_sign: bool = False) -> str:
    """Format integer paise as Indian Rupee string (e.g. ₹1,23,456.78)."""
    sign = ""
    if paise < 0:
        sign = "-"
    elif show_sign and paise > 0:
        sign = "+"

    abs_p = abs(paise)
    rupees_str = str(abs_p // 100)
    frac_str = f"{abs_p % 100:02d}"

    if len(rupees_str) > 3:
        last_three = rupees_str[-3:]
        rest = rupees_str[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        grouped = ",".join(reversed(groups)) + "," + last_three
    else:
        grouped = rupees_str

    return f"{sign}₹{grouped}.{frac_str}"