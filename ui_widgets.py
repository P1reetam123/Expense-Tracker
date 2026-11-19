"""
ui_widgets.py - Custom zero-dependency Tkinter widgets:
1. CalendarDateField: Clean date input with a flicker-free Canvas calendar popup.
2. BudgetProgressCanvas: Pill-style budget meter with 90% caution marker.
3. CategoryBarChart: Horizontal category chart with interactive hover tooltips.
4. MonthlyTrendChart: Monthly Budget vs. Spending bar chart with hover tooltips.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
import platform
import tkinter as tk
from tkinter import ttk
from typing import Sequence

from models import CategoryBreakdown, MonthlyTrendPoint, format_inr


def get_ui_font() -> str:
    sys_name = platform.system()
    if sys_name == "Windows":
        return "Segoe UI"
    if sys_name == "Darwin":
        return "SF Pro Text"
    return "DejaVu Sans"


UI_FONT = get_ui_font()

CHART_PALETTE = (
    "#2563eb",
    "#059669",
    "#d97706",
    "#7c3aed",
    "#db2777",
    "#0891b2",
    "#dc2626",
    "#475569",
)

class CalendarDateField(ttk.Frame):
    """Compact date input paired with a freeze-free Canvas-rendered popup calendar."""

    POPUP_W = 276
    POPUP_H = 268
    _active_owner: CalendarDateField | None = None
    _hooked_toplevels: set[int] = set()

    def __init__(self, master: tk.Misc, initial_date: str | None = None):
        super().__init__(master)
        self.var = tk.StringVar(value=initial_date or date.today().isoformat())
        self._popup: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._view_year = date.today().year
        self._view_month = date.today().month

        self._hitboxes: list[tuple[int, int, int, int, tuple[str, object]]] = []
        self._hover_key: tuple[str, object] | None = None

        self.entry = ttk.Entry(self, textvariable=self.var, font=(UI_FONT, 10))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.pick_btn = ttk.Button(
            self, text="Pick", width=5, style="Subtle.TButton", command=self._toggle_popup
        )
        self.pick_btn.pack(side=tk.LEFT, padx=(4, 0))

        self.today_btn = ttk.Button(
            self, text="Today", width=6, style="Subtle.TButton", command=self.set_today
        )
        self.today_btn.pack(side=tk.LEFT, padx=(4, 0))

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str) -> None:
        self.var.set(value)

    def set_today(self) -> None:
        self.var.set(date.today().isoformat())
        self._close_popup()

    def _parsed_current_date(self) -> date:
        try:
            return datetime.strptime(self.var.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            return date.today()

    @classmethod
    def _on_toplevel_click(cls, event: tk.Event) -> None:
        owner = cls._active_owner
        if not owner or not owner._popup or not owner._popup.winfo_exists():
            cls._active_owner = None
            return
        if event.widget is owner.pick_btn:
            return
        px = owner._popup.winfo_rootx()
        py = owner._popup.winfo_rooty()
        pw = owner._popup.winfo_width()
        ph = owner._popup.winfo_height()
        if not (px <= event.x_root <= px + pw and py <= event.y_root <= py + ph):
            owner.after_idle(owner._close_popup)

    def _toggle_popup(self) -> None:
        if self._popup and self._popup.winfo_exists():
            self._close_popup()
            return

        if CalendarDateField._active_owner and CalendarDateField._active_owner is not self:
            CalendarDateField._active_owner._close_popup()

        current = self._parsed_current_date()
        self._view_year = current.year
        self._view_month = current.month
        self._hover_key = None

        top = self.winfo_toplevel()
        top_id = top.winfo_id()
        if top_id not in CalendarDateField._hooked_toplevels:
            CalendarDateField._hooked_toplevels.add(top_id)
            top.bind("<ButtonPress-1>", CalendarDateField._on_toplevel_click, add="+")

        popup = tk.Toplevel(self)
        popup.wm_overrideredirect(True)
        popup.transient(top)
        popup.configure(bg="#cbd5e1", padx=1, pady=1)
        self._popup = popup
        CalendarDateField._active_owner = self

        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height() + 4
        if x + self.POPUP_W > screen_w - 8:
            x = max(8, screen_w - self.POPUP_W - 8)
        if y + self.POPUP_H > screen_h - 32:
            y = max(8, self.entry.winfo_rooty() - self.POPUP_H - 4)

        popup.geometry(f"{self.POPUP_W}x{self.POPUP_H}+{x}+{y}")

        canvas = tk.Canvas(
            popup,
            width=self.POPUP_W - 2,
            height=self.POPUP_H - 2,
            bg="#ffffff",
            highlightthickness=0,
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas = canvas

        canvas.bind("<Motion>", self._on_motion)
        canvas.bind("<Leave>", self._on_leave)
        canvas.bind("<ButtonRelease-1>", self._on_canvas_click)
        popup.bind("<Escape>", lambda _e: self.after_idle(self._close_popup))
        popup.lift()

        self._render_calendar()

    def _close_popup(self) -> None:
        if CalendarDateField._active_owner is self:
            CalendarDateField._active_owner = None
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None
        self._canvas = None

    def _shift_month(self, delta: int) -> None:
        total = self._view_year * 12 + (self._view_month - 1) + delta
        self._view_year = total // 12
        self._view_month = total % 12 + 1
        self._hover_key = None
        self._render_calendar()

    def _on_motion(self, event: tk.Event) -> None:
        hovered = None
        for x1, y1, x2, y2, payload in self._hitboxes:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                hovered = payload
                break
        if hovered != self._hover_key:
            self._hover_key = hovered
            if self._canvas:
                self._canvas.configure(cursor="hand2" if hovered else "")
            self._render_calendar()

    def _on_leave(self, _event: tk.Event) -> None:
        if self._hover_key is not None:
            self._hover_key = None
            if self._canvas:
                self._canvas.configure(cursor="")
            self._render_calendar()

    def _on_canvas_click(self, event: tk.Event) -> None:
        for x1, y1, x2, y2, (action, value) in self._hitboxes:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                if action == "nav":
                    self._shift_month(int(value))  # type: ignore[arg-type]
                elif action == "day":
                    self.var.set(value.isoformat())  # type: ignore[union-attr]
                    self.after_idle(self._close_popup)
                elif action == "today":
                    self.after_idle(self.set_today)
                elif action == "close":
                    self.after_idle(self._close_popup)
                return

    def _render_calendar(self) -> None:
        canvas = self._canvas
        if not canvas or not canvas.winfo_exists():
            return

        canvas.delete("all")
        self._hitboxes.clear()

        w = self.POPUP_W - 2
        h = self.POPUP_H - 2

        canvas.create_rectangle(0, 0, w, 40, fill="#f8fafc", outline="")
        canvas.create_line(0, 40, w, 40, fill="#e2e8f0")

        nav_buttons = (
            (10, 8, 34, 32, "«", -12),
            (38, 8, 62, 32, "‹", -1),
            (w - 62, 8, w - 38, 32, "›", 1),
            (w - 34, 8, w - 10, 32, "»", 12),
        )
        for x1, y1, x2, y2, symbol, delta in nav_buttons:
            key = ("nav", delta)
            bg = "#e2e8f0" if self._hover_key == key else "#f8fafc"
            canvas.create_rectangle(x1, y1, x2, y2, fill=bg, outline="")
            canvas.create_text(
                (x1 + x2) // 2,
                (y1 + y2) // 2,
                text=symbol,
                fill="#0f172a",
                font=(UI_FONT, 11, "bold"),
            )
            self._hitboxes.append((x1, y1, x2, y2, key))

        title = f"{calendar.month_name[self._view_month]} {self._view_year}"
        canvas.create_text(
            w // 2, 20, text=title, fill="#0f172a", font=(UI_FONT, 10, "bold")
        )

        pad_x = 12
        cell_w = (w - pad_x * 2) / 7
        for col, day_name in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            cx = int(pad_x + cell_w * (col + 0.5))
            fg = "#dc2626" if col >= 5 else "#64748b"
            canvas.create_text(cx, 54, text=day_name, fill=fg, font=(UI_FONT, 8, "bold"))

        cal = calendar.Calendar(firstweekday=calendar.MONDAY)
        dates = list(cal.itermonthdates(self._view_year, self._view_month))
        while len(dates) < 42:
            dates.append(date.fromordinal(dates[-1].toordinal() + 1))

        selected = self._parsed_current_date()
        today = date.today()
        grid_top = 68
        cell_h = 26

        for idx, d in enumerate(dates[:42]):
            row = idx // 7
            col = idx % 7
            x1 = int(pad_x + col * cell_w)
            y1 = grid_top + row * cell_h
            x2 = int(x1 + cell_w)
            y2 = y1 + cell_h
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            in_month = d.month == self._view_month
            is_selected = d == selected
            is_today = d == today
            key = ("day", d)
            is_hovered = self._hover_key == key

            if is_selected:
                canvas.create_oval(
                    cx - 12, cy - 11, cx + 12, cy + 11, fill="#2563eb", outline=""
                )
                fg = "#ffffff"
                font_spec = (UI_FONT, 9, "bold")
            elif is_hovered:
                canvas.create_oval(
                    cx - 12, cy - 11, cx + 12, cy + 11, fill="#e2e8f0", outline=""
                )
                fg = "#0f172a" if in_month else "#94a3b8"
                font_spec = (UI_FONT, 9, "bold" if is_today else "normal")
            else:
                if is_today:
                    canvas.create_oval(
                        cx - 12, cy - 11, cx + 12, cy + 11, fill="#eff6ff", outline="#2563eb", width=1
                    )
                    fg = "#1d4ed8"
                    font_spec = (UI_FONT, 9, "bold")
                elif not in_month:
                    fg = "#cbd5e1"
                    font_spec = (UI_FONT, 8)
                elif col >= 5:
                    fg = "#dc2626"
                    font_spec = (UI_FONT, 9)
                else:
                    fg = "#1e293b"
                    font_spec = (UI_FONT, 9)

            canvas.create_text(cx, cy, text=str(d.day), fill=fg, font=font_spec)
            self._hitboxes.append((x1, y1, x2, y2, key))

        foot_y = h - 34
        canvas.create_line(0, foot_y, w, foot_y, fill="#e2e8f0")
        canvas.create_rectangle(0, foot_y + 1, w, h, fill="#f8fafc", outline="")

        today_box = (12, foot_y + 6, 128, h - 6)
        close_box = (w - 86, foot_y + 6, w - 12, h - 6)

        t_key = ("today", None)
        t_bg = "#dbeafe" if self._hover_key == t_key else "#eff6ff"
        canvas.create_rectangle(*today_box, fill=t_bg, outline="#bfdbfe")
        canvas.create_text(
            (today_box[0] + today_box[2]) // 2,
            (today_box[1] + today_box[3]) // 2,
            text="Jump to Today",
            fill="#1d4ed8",
            font=(UI_FONT, 8, "bold"),
        )
        self._hitboxes.append((*today_box, t_key))

        c_key = ("close", None)
        c_bg = "#e2e8f0" if self._hover_key == c_key else "#f1f5f9"
        canvas.create_rectangle(*close_box, fill=c_bg, outline="#cbd5e1")
        canvas.create_text(
            (close_box[0] + close_box[2]) // 2,
            (close_box[1] + close_box[3]) // 2,
            text="Close",
            fill="#334155",
            font=(UI_FONT, 8),
        )
        self._hitboxes.append((*close_box, c_key))

class BudgetProgressCanvas(tk.Canvas):
    """Crisp budget meter with 90% caution marker."""

    def __init__(self, master: tk.Misc):
        super().__init__(master, height=28, bg="#ffffff", highlightthickness=0)
        self._pct = 0.0
        self._color = "#94a3b8"
        self._label = "No budget set"
        self.bind("<Configure>", lambda _e: self.redraw())

    def set_progress(self, percentage_used: float, status_color: str, label: str) -> None:
        self._pct = max(0.0, percentage_used)
        self._color = status_color
        self._label = label
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 140)
        h = max(self.winfo_height(), 26)

        pad_x = 2
        y1, y2 = 4, h - 4
        bar_w = w - pad_x * 2

        self.create_rectangle(
            pad_x, y1, pad_x + bar_w, y2, fill="#e2e8f0", outline="",
        )

        fill_ratio = min(self._pct / 100.0, 1.0)
        if fill_ratio > 0:
            self.create_rectangle(
                pad_x, y1, pad_x + int(bar_w * fill_ratio), y2,
                fill=self._color, outline="",
            )

        # 90% threshold marker
        marker_x = pad_x + int(bar_w * 0.9)
        self.create_line(
            marker_x, y1 - 2, marker_x, y2 + 2,
            fill="#334155", width=2,
        )

        text_color = "#ffffff" if fill_ratio > 0.56 else "#0f172a"
        self.create_text(
            w // 2, h // 2, text=self._label, fill=text_color, font=(UI_FONT, 8, "bold")
        )


class _TooltipHelper:
    """Lightweight floating tooltip for canvas charts."""

    def __init__(self, widget: tk.Widget):
        self.widget = widget
        self.tip: tk.Toplevel | None = None
        self.label: tk.Label | None = None

    def show(self, x_root: int, y_root: int, text: str) -> None:
        if not self.tip or not self.tip.winfo_exists():
            self.tip = tk.Toplevel(self.widget)
            self.tip.wm_overrideredirect(True)
            self.label = tk.Label(
                self.tip,
                text=text,
                bg="#0f172a",
                fg="#f8fafc",
                font=(UI_FONT, 8),
                padx=9,
                pady=5,
                justify=tk.LEFT,
            )
            self.label.pack()
        elif self.label:
            self.label.config(text=text)
        self.tip.geometry(f"+{x_root + 14}+{y_root + 12}")

    def hide(self) -> None:
        if self.tip and self.tip.winfo_exists():
            self.tip.destroy()
        self.tip = None
        self.label = None


class CategoryBarChart(tk.Canvas):
    """Horizontal bar chart of category spending with hover tooltips."""

    def __init__(self, master: tk.Misc):
        super().__init__(master, bg="#ffffff", highlightthickness=0)
        self._items: Sequence[CategoryBreakdown] = ()
        self._bar_boxes: list[tuple[int, int, int, int, str]] = []
        self._tooltip = _TooltipHelper(self)
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", lambda _e: self._tooltip.hide())

    def set_data(self, breakdown: Sequence[CategoryBreakdown]) -> None:
        self._items = breakdown
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        self._bar_boxes.clear()
        w = max(self.winfo_width(), 280)
        h = max(self.winfo_height(), 180)

        if not self._items:
            self.create_text(
                w // 2, h // 2,
                text="No expenses to chart for this selection.",
                fill="#64748b",
                font=(UI_FONT, 10),
            )
            return

        max_val = max(item.total_paise for item in self._items) or 1
        left_pad = 140
        right_pad = 135
        bar_area_w = max(60, w - left_pad - right_pad)
        row_h = min(36, max(22, (h - 24) // max(len(self._items), 1)))
        top_pad = 14

        for idx, item in enumerate(self._items):
            y1 = top_pad + idx * row_h + 5
            y2 = y1 + row_h - 11
            if y2 > h - 8:
                break

            color = CHART_PALETTE[idx % len(CHART_PALETTE)]
            bar_w = max(4, int(bar_area_w * (item.total_paise / max_val)))

            cat_label = item.category if len(item.category) <= 18 else item.category[:16] + ".."
            self.create_text(
                left_pad - 10, (y1 + y2) // 2,
                text=cat_label,
                anchor=tk.E,
                fill="#1e293b",
                font=(UI_FONT, 8, "bold"),
            )

            self.create_rectangle(
                left_pad, y1, left_pad + bar_area_w, y2, fill="#f1f5f9", outline=""
            )
            self.create_rectangle(
                left_pad, y1, left_pad + bar_w, y2, fill=color, outline=""
            )

            self.create_text(
                left_pad + bar_area_w + 10, (y1 + y2) // 2,
                text=f"{format_inr(item.total_paise)}  ({item.percentage:.1f}%)",
                anchor=tk.W,
                fill="#334155",
                font=(UI_FONT, 8),
            )

            tip = (
                f"{item.category}\n"
                f"Spent: {format_inr(item.total_paise)} ({item.percentage:.1f}%)\n"
                f"Transactions: {item.count}"
            )
            self._bar_boxes.append((left_pad, y1, left_pad + bar_area_w, y2, tip))

    def _on_motion(self, event: tk.Event) -> None:
        for x1, y1, x2, y2, tip in self._bar_boxes:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self._tooltip.show(event.x_root, event.y_root, tip)
                return
        self._tooltip.hide()


class MonthlyTrendChart(tk.Canvas):
    """Grouped vertical bar chart comparing Monthly Effective Budget vs. Spent."""

    def __init__(self, master: tk.Misc):
        super().__init__(master, bg="#ffffff", highlightthickness=0)
        self._points: Sequence[MonthlyTrendPoint] = ()
        self._hitboxes: list[tuple[int, int, int, int, str]] = []
        self._tooltip = _TooltipHelper(self)
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", lambda _e: self._tooltip.hide())

    def set_data(self, points: Sequence[MonthlyTrendPoint]) -> None:
        self._points = points
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        self._hitboxes.clear()
        w = max(self.winfo_width(), 320)
        h = max(self.winfo_height(), 180)

        if not self._points:
            self.create_text(
                w // 2, h // 2,
                text="Add expenses or budgets to view monthly trends.",
                fill="#64748b",
                font=(UI_FONT, 10),
            )
            return

        # Legend
        self.create_rectangle(w - 235, 10, w - 223, 20, fill="#93c5fd", outline="")
        self.create_text(w - 218, 15, text="Effective Budget", anchor=tk.W, fill="#334155", font=(UI_FONT, 8))
        self.create_rectangle(w - 115, 10, w - 103, 20, fill="#2563eb", outline="")
        self.create_text(w - 98, 15, text="Spent", anchor=tk.W, fill="#334155", font=(UI_FONT, 8))
        self.create_rectangle(w - 58, 10, w - 46, 20, fill="#dc2626", outline="")
        self.create_text(w - 41, 15, text="Over", anchor=tk.W, fill="#334155", font=(UI_FONT, 8))

        left_pad, right_pad, top_pad, bottom_pad = 68, 22, 34, 36
        plot_w = max(100, w - left_pad - right_pad)
        plot_h = max(60, h - top_pad - bottom_pad)
        baseline_y = top_pad + plot_h

        max_val = max(
            max(p.effective_budget_paise, p.spent_paise) for p in self._points
        ) or 100

        for step in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = int(baseline_y - plot_h * step)
            self.create_line(left_pad, y, left_pad + plot_w, y, fill="#f1f5f9" if step > 0 else "#cbd5e1")
            val_rupees = int(max_val * step) // 100
            label = f"₹{val_rupees // 1000}k" if val_rupees >= 10000 else f"₹{val_rupees:,}"
            self.create_text(
                left_pad - 8, y, text=label, anchor=tk.E, fill="#64748b", font=(UI_FONT, 7)
            )

        group_w = plot_w / len(self._points)
        bar_w = max(10, min(28, int(group_w * 0.28)))

        for idx, pt in enumerate(self._points):
            cx = int(left_pad + group_w * (idx + 0.5))
            bud_h = int(plot_h * (pt.effective_budget_paise / max_val))
            spent_h = int(plot_h * (pt.spent_paise / max_val))

            if bud_h > 0:
                self.create_rectangle(
                    cx - bar_w - 2, baseline_y - bud_h, cx - 2, baseline_y,
                    fill="#93c5fd", outline="",
                )

            spent_color = (
                "#dc2626"
                if pt.effective_budget_paise > 0 and pt.spent_paise > pt.effective_budget_paise
                else "#2563eb"
            )
            if spent_h > 0:
                self.create_rectangle(
                    cx + 2, baseline_y - spent_h, cx + 2 + bar_w, baseline_y,
                    fill=spent_color, outline="",
                )

            self.create_text(
                cx, baseline_y + 14, text=pt.month, fill="#334155", font=(UI_FONT, 8, "bold")
            )

            diff = pt.effective_budget_paise - pt.spent_paise
            tip = (
                f"{pt.month}\n"
                f"Effective Budget: {format_inr(pt.effective_budget_paise)}\n"
                f"Spent: {format_inr(pt.spent_paise)}\n"
                f"Balance: {format_inr(diff, show_sign=True)}"
            )
            self._hitboxes.append((cx - bar_w - 8, top_pad, cx + bar_w + 8, baseline_y, tip))

    def _on_motion(self, event: tk.Event) -> None:
        for x1, y1, x2, y2, tip in self._hitboxes:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self._tooltip.show(event.x_root, event.y_root, tip)
                return
        self._tooltip.hide()