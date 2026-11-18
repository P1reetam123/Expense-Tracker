# Student Personal Expense Tracker 💰

A desktop GUI application built in Python using **Tkinter**, **SQLite**, and the **datetime** module. Designed to help students record everyday expenses, monitor category spending, and maintain a monthly budget with visual alert warnings.

---

## 🌟 Features & Requirements Satisfied

1. **Add Expenses**:
   - Fields: Amount (₹), Category (Dropdown), Short Description, and Date (`YYYY-MM-DD`).
   - Quick **"Today"** button to auto-fill today's date.
   - Comprehensive validation to prevent negative amounts, empty categories, or invalid calendar dates.

2. **View Saved Expenses**:
   - Multi-column `ttk.Treeview` table with ID, Date, Category, Description, and formatted Amount.
   - Scrollbar support for smooth navigation through long lists.
   - Filter by month or view all recorded expenses.

3. **Edit & Delete Records**:
   - **Edit**: Select an entry and click **✏️ Edit Selected** to populate the form, switch to Edit mode, and update the entry.
   - **Delete**: Select an entry and click **🗑️ Delete Selected** with safety confirmation dialogs.

4. **Spending Calculations & Category-Wise Breakdown**:
   - Real-time KPI summary cards displaying Total Spending, Monthly Budget, and Remaining Budget.
   - Dedicated **Category Breakdown tab** displaying total expenditure per category and percentage share.
   - Computed using Python dictionaries for grouping and aggregation.

5. **Monthly Budget & Warning System**:
   - Set monthly budgets stored directly in the database.
   - Dynamic alert banners:
     - 🔴 **Red Banner (Alert)**: Displayed when total spending exceeds the budget, showing the exact amount overspent.
     - 🟡 **Yellow Banner (Caution)**: Displayed when spending reaches 90% or more of the budget.
     - 🟢 **Green Banner (Healthy)**: Displayed when spending is comfortably within budget.

6. **Bonus: CSV Export**:
   - Export filtered or all expenses to a `.csv` file with a single click.

---

## 📁 Project Structure

```text
expense_tracker/
├── main.py                   # Main Tkinter GUI application
├── database.py               # SQLite database setup and CRUD operations
├── calculations.py           # Business logic, dictionary aggregations, & validation
├── seed_data.py              # Script to populate sample student expenses for demo
├── test_expense_tracker.py   # Unit test suite verifying all logic
├── VIVA_GUIDE.md             # Complete Viva Voce answers and explanation guide
└── README.md                 # Project documentation and instructions
```

---

## 🚀 How to Run the Application

### 1. Requirements
- Python 3.10+ (Python 3.14 recommended, standard library only - no external pip packages required).

### 2. Run the Application
Open a terminal in the project directory:
```bash
python main.py
```

### 3. (Optional) Populate Sample Demo Data
To test with sample student expenses (books, cafeteria, hostel rent, etc.):
```bash
python seed_data.py
python main.py
```

### 4. Run Automated Unit Tests
```bash
python test_expense_tracker.py
```

---

## 📚 Viva Preparation
See the full Viva Preparation Guide in [`VIVA_GUIDE.md`](VIVA_GUIDE.md) covering:
- How expense totals are computed.
- How budget warnings are computed.
- How saved entries are updated.
- Detailed breakdown of all six course concepts.
