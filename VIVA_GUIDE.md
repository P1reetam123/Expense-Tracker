# Viva Voce Preparation Guide: Personal Expense Tracker
**Assignment - Problem 4: Personal Expense Tracker (Marks: 20)**

This document provides exact, step-by-step explanations for the viva questions mentioned in the assignment prompt, as well as answers to probable questions by the examiner.

---

## 1. Primary Viva Questions (Directly From Prompt)

### Q1: Explain how expense totals are computed.
**Answer:**
1. **Data Retrieval:** We query expenses from the SQLite database using SQL filtering for the selected month:
   ```sql
   SELECT id, amount, category, description, date 
   FROM expenses 
   WHERE strftime('%Y-%m', date) = ?
   ```
2. **Dictionary Accumulation:** We loop through each expense record in Python and aggregate spending both as a cumulative total and per category using a Python dictionary:
   ```python
   total_spending = 0.0
   category_totals = {}

   for exp in expenses:
       amt = float(exp["amount"])
       cat = exp["category"]
       
       total_spending += amt
       # If category already exists, add to it; otherwise initialize with 0.0
       category_totals[cat] = category_totals.get(cat, 0.0) + amt
   ```
3. **Category Breakdown & Percentages:** We calculate each category's share of total spending:
   $$\text{Percentage} = \left(\frac{\text{Category Total}}{\text{Total Spending}}\right) \times 100$$
   This dictionary is then sorted and displayed in the **Category Breakdown** table.

---

### Q2: Explain how budget warnings are computed.
**Answer:**
1. **Budget Retrieval:** For the selected month (e.g., `2026-11`), we retrieve the assigned monthly budget from the `budgets` table:
   ```sql
   SELECT budget_amount FROM budgets WHERE month = ?
   ```
2. **Comparison & Calculations:**
   $$\text{Difference} = \text{Monthly Budget} - \text{Total Spending}$$
   - **Case 1: Over Budget ($\text{Total Spending} > \text{Monthly Budget}$)**
     $$\text{Exceeded Amount} = \text{Total Spending} - \text{Monthly Budget}$$
     The warning flag `is_over_budget` is set to `True`. The GUI changes the banner color to red (`#ffebee`) and displays:
     > `🚨 WARNING: Spending of ₹X,XXX.XX exceeds budget of ₹Y,YYY.YY by ₹Z,ZZZ.ZZ!`
   - **Case 2: Caution ($\ge 90\%$ of Budget consumed)**
     The banner turns amber/yellow to warn the student they are approaching their limit.
   - **Case 3: Under Budget / Healthy ($\text{Total Spending} \le \text{Monthly Budget}$)**
     The banner turns green (`#e8f5e9`) and displays the remaining balance:
     > `✅ Budget Healthy: ₹X,XXX.XX remaining out of ₹Y,YYY.YY.`

---

### Q3: Explain how saved entries are updated.
**Answer:**
The edit and update workflow consists of 3 distinct steps:
1. **Row Selection & Extraction:**
   The user clicks an entry in the Tkinter `Treeview` and presses **✏️ Edit Selected**.
   We retrieve the selected row's values:
   ```python
   selected_item = self.tree.selection()
   values = self.tree.item(selected_item[0], "values")
   # values = (id, date, category, description, amount)
   ```
2. **Form Population & State Shift:**
   The application stores the record's primary key in `self.editing_expense_id`, fills the input fields with the existing data, and toggles the action button from **➕ Add Expense** to **💾 Save Changes**.
3. **Validation & SQL Execution:**
   When the user submits the modified values, `validate_expense_inputs()` ensures all fields (amount, category, date) are valid. Then an SQL `UPDATE` statement executes:
   ```sql
   UPDATE expenses
   SET amount = ?, category = ?, description = ?, date = ?
   WHERE id = ?
   ```
   Finally, the form resets, the database connection commits and closes, and `load_expenses()` re-renders the table and recalculates totals and budget warnings.

---

## 2. Explanation of Core Concepts Demonstrated

| Concept | Where & How It Is Used in Code |
| :--- | :--- |
| **Tkinter Widgets** | `ttk.Treeview` (display expenses/categories), `ttk.Combobox` (category dropdown & month selector), `ttk.Entry` (inputs), `ttk.Notebook` (tabbed view), `ttk.Button` / `tk.Button` (styled actions), `tk.LabelFrame` (grouping sections), and `messagebox` (alerts & confirmations). |
| **SQLite & CSV** | `sqlite3` manages relational data (`expenses` and `budgets` tables) with parameterized queries preventing SQL injection. `csv.DictWriter` allows exporting filtered tables to CSV files. |
| **datetime Module** | `datetime.strptime(date_str, "%Y-%m-%d")` validates proper calendar dates. `date.today()` defaults today's date in form. `strftime('%Y-%m')` groups entries by month. |
| **Dictionaries** | Used in `category_totals[cat] = ...` for aggregation, SQLite row-factory mapping (`dict(row)`), and structured communication between the calculations module and GUI. |
| **Calculations** | Summation of expenses, percentage calculations, subtraction for remaining budget, absolute difference for overspent amount. |
| **Exception Handling** | Extensive `try...except` blocks catching `ValueError` (invalid float, invalid dates, empty category) and `RuntimeError` / `sqlite3.Error` (database issues) with user-friendly GUI popups. |

---

## 3. Likely Follow-Up Viva Questions

### Q4: Why did you use `sqlite3.Row` instead of standard tuples?
> **Answer:** By setting `conn.row_factory = sqlite3.Row`, SQLite results can be accessed either by column index or by column name as a dictionary (e.g., `row["amount"]`). This improves code readability and prevents index errors.

### Q5: How do you prevent invalid dates like "2026-02-31" or "2026-13-45"?
> **Answer:** In `calculations.py`, `datetime.strptime(clean_date_str, "%Y-%m-%d")` is called inside a `try...except ValueError` block. The `strptime` parser validates both the format and the calendar validity of days and months, raising a `ValueError` if the date does not exist.

### Q6: How do you prevent SQL Injection?
> **Answer:** All database queries use parameterized placeholders (`?`) rather than Python f-strings or string concatenation. The SQLite driver handles value escaping safely.

### Q7: Why are connections closed in a `finally` block?
> **Answer:** In Python and Windows, unclosed database handles can lock the `.db` file (`PermissionError: [WinError 32]`). Placing `conn.close()` in a `finally` block guarantees that the connection is closed even if an exception occurs during query execution.
