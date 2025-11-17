# CMMS NEON 2.2 - Tkinter to PyQt5 Conversion Strategy

## Executive Summary

This document provides a comprehensive conversion strategy for migrating the AIT Complete CMMS system from Tkinter to PyQt5. The main application (`AIT_CMMS_REV3.py`) is approximately 19,000 lines of code with extensive UI components across 8 Python files.

**Key Statistics:**
- Total Lines: 18,996 (main file)
- ttk Widget Usages: 863
- tk Widget Usages: 888
- MessageBox Dialogs: 294
- FileDialog Operations: 5
- Geometry Manager Calls: 894 (pack, grid, place)
- Supporting UI Modules: 8 files

---

## 1. Main Architecture Analysis

### 1.1 Current Tkinter Structure

**Main Class:** `AITCMMSSystem` (starts at line 3041)

**Key Components:**
- Main window with maximized display and DPI awareness
- Menu bar with Account menu
- Toolbar (Manager role only)
- Scrollable canvas containing notebook (tabbed interface)
- Status bar with user information
- Role-based tab visibility (Manager, Technician, Parts Coordinator)

**Initialization Flow:**
1. DPI awareness setup (lines 49-76)
2. Database connection pool initialization
3. User authentication (login dialog)
4. Window maximization
5. GUI creation based on role
6. Deferred data loading

### 1.2 Suggested PyQt5 Architecture

```python
class AITCMMSMainWindow(QMainWindow):
    """Main application window - replaces AITCMMSSystem"""

    def __init__(self):
        super().__init__()
        self.db_config = {...}
        self.session_manager = SessionManager()
        self.user_manager = UserManager()

        # Initialize subsystems
        self.init_database()
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        self.setup_window()
        self.create_menu_bar()
        self.create_toolbar()
        self.create_central_widget()
        self.create_status_bar()

    def create_central_widget(self):
        """Create main tabbed interface"""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add tabs based on user role
        if self.current_user_role == 'Manager':
            self.create_all_manager_tabs()
        elif self.current_user_role == 'Parts Coordinator':
            self.create_parts_coordinator_tabs()
        else:
            self.create_technician_tabs()
```

---

## 2. Comprehensive Tkinter-to-PyQt5 Widget Mapping

### 2.1 Core Widgets

| Tkinter Widget | PyQt5 Equivalent | Conversion Notes |
|----------------|------------------|------------------|
| `tk.Tk()` | `QMainWindow` or `QApplication` | Main window becomes QMainWindow |
| `tk.Toplevel()` | `QDialog` | Use for modal dialogs with `exec_()` |
| `ttk.Frame` | `QFrame` or `QWidget` | QWidget is more common |
| `ttk.LabelFrame` | `QGroupBox` | Similar grouping functionality |
| `ttk.Label` | `QLabel` | Direct replacement |
| `ttk.Button` | `QPushButton` | Use `clicked.connect(method)` for events |
| `ttk.Entry` | `QLineEdit` | Single-line text input |
| `tk.Text` | `QTextEdit` or `QPlainTextEdit` | Multi-line text widget |
| `ttk.Combobox` | `QComboBox` | Dropdown selection |
| `ttk.Checkbutton` | `QCheckBox` | Checkbox widget |
| `ttk.Radiobutton` | `QRadioButton` | Radio button (use QButtonGroup) |
| `ttk.Spinbox` | `QSpinBox` or `QDoubleSpinBox` | Numeric input with up/down buttons |
| `ttk.Progressbar` | `QProgressBar` | Progress indication |
| `ttk.Separator` | `QFrame` with special style | Use `setFrameShape(QFrame.HLine)` |
| `ttk.Scrollbar` | `QScrollBar` (often automatic) | Usually handled by scroll areas |
| `tk.Canvas` | `QGraphicsView` or `QScrollArea` | For scrollable content use QScrollArea |
| `tk.Listbox` | `QListWidget` or `QListView` | List display widget |
| `tk.Menu` | `QMenu` / `QMenuBar` | Menu system |
| `ttk.Notebook` | `QTabWidget` | Tabbed interface |
| `ttk.Treeview` | `QTreeWidget` or `QTableWidget` | **Critical for this app** - extensive use |
| `tk.StringVar()` | Direct assignment or signals | No need for variable objects |
| `tk.IntVar()` | Direct assignment or signals | No need for variable objects |

### 2.2 Treeview to QTableWidget Mapping (CRITICAL)

**Current Usage:** 15+ Treeview instances for:
- Equipment list
- PM schedules
- CM list
- PM completion records
- Missing parts list
- Cannot Find assets
- Run to Failure list
- MRO stock inventory
- KPI data
- User management
- Session tracking

**PyQt5 Approach:**

```python
# Tkinter Treeview
self.equipment_tree = ttk.Treeview(
    list_frame,
    columns=('SAP', 'BFM', 'Description', 'Location', 'LIN', 'Monthly', 'Six Month', 'Annual', 'Status'),
    show='headings'
)

# PyQt5 QTableWidget
self.equipment_table = QTableWidget()
self.equipment_table.setColumnCount(9)
self.equipment_table.setHorizontalHeaderLabels([
    'SAP Material No.', 'BFM Equipment No.', 'Description', 'Location',
    'Master LIN', 'Monthly PM', '6-Month PM', 'Annual PM', 'Status'
])
self.equipment_table.horizontalHeader().setStretchLastSection(True)
self.equipment_table.setSelectionBehavior(QTableWidget.SelectRows)
self.equipment_table.setEditTriggers(QTableWidget.NoEditTriggers)
```

**Key Conversion Points:**
- `tree.heading()` → `setHorizontalHeaderLabels()`
- `tree.column()` → `setColumnWidth()`
- `tree.insert()` → `insertRow()` + `setItem()`
- `tree.selection()` → `selectedItems()` or `currentRow()`
- `tree.item()` → `item(row, col).text()`
- `tree.bind()` → `itemDoubleClicked.connect()` or `itemSelectionChanged.connect()`

---

## 3. Geometry Manager Conversion

### 3.1 Pack → QVBoxLayout / QHBoxLayout

**Tkinter Pack (894 total usages):**
```python
frame.pack(side='left', fill='x', expand=True, padx=10, pady=5)
```

**PyQt5 Layout:**
```python
layout = QHBoxLayout()
layout.addWidget(widget)
layout.setContentsMargins(10, 5, 10, 5)
parent.setLayout(layout)
```

**Conversion Map:**
- `side='top'` → QVBoxLayout with `addWidget()`
- `side='bottom'` → QVBoxLayout with `addWidget()` at end
- `side='left'` → QHBoxLayout with `addWidget()`
- `side='right'` → QHBoxLayout with `addWidget()` at end
- `fill='x'` → `setStretch()` or `addStretch()`
- `expand=True` → `addWidget(widget, stretch=1)`
- `padx/pady` → `setContentsMargins()` or `setSpacing()`

### 3.2 Grid → QGridLayout

**Tkinter Grid:**
```python
label.grid(row=0, column=0, sticky='w', padx=10, pady=5)
entry.grid(row=0, column=1, sticky='ew', padx=10, pady=5)
```

**PyQt5 Grid:**
```python
layout = QGridLayout()
layout.addWidget(label, 0, 0, Qt.AlignLeft)
layout.addWidget(entry, 0, 1)
layout.setContentsMargins(10, 5, 10, 5)
```

**Conversion Map:**
- `row` → first parameter in `addWidget(widget, row, col)`
- `column` → second parameter
- `sticky='w'` → `Qt.AlignLeft` as 4th parameter
- `sticky='e'` → `Qt.AlignRight`
- `sticky='n'` → `Qt.AlignTop`
- `sticky='s'` → `Qt.AlignBottom`
- `sticky='ew'` → `widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)`
- `columnspan` → 4th parameter: `addWidget(widget, row, col, rowspan, colspan)`

### 3.3 Place → Absolute Positioning (Rare)

**Use QWidget.move()** - But avoid if possible, prefer layouts

---

## 4. Dialog Conversion Strategy

### 4.1 Dialog Types Used

**Count:** 20+ dialog methods including:
- `show_login_dialog()` - Authentication
- `create_cm_dialog()` - Create corrective maintenance
- `edit_cm_dialog()` - Edit CM
- `complete_cm_dialog()` - Complete CM
- `add_equipment_dialog()` - Add equipment
- `edit_equipment_dialog()` - Edit equipment
- `create_custom_pm_template_dialog()` - PM templates
- `create_missing_parts_dialog()` - Parts tracking
- `show_csv_mapping_dialog()` - CSV import
- `open_user_management()` - User admin
- `open_change_password()` - Password change

### 4.2 Modal Dialog Pattern

**Tkinter Pattern:**
```python
def create_cm_dialog(self):
    dialog = tk.Toplevel(self.root)
    dialog.title("Create New Corrective Maintenance")
    dialog.geometry("600x550")
    dialog.transient(self.root)
    dialog.grab_set()  # Make modal

    # Form fields...
    ttk.Button(dialog, text="Save", command=save_function).pack()
```

**PyQt5 Pattern:**
```python
class CreateCMDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Corrective Maintenance")
        self.resize(600, 550)
        self.setModal(True)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Form fields...
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_function)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def save_function(self):
        # Validation and save logic
        self.accept()  # Close dialog with success

# Usage:
def create_cm_dialog(self):
    dialog = CreateCMDialog(self)
    if dialog.exec_() == QDialog.Accepted:
        # Handle success
        pass
```

### 4.3 MessageBox Conversion (294 usages)

| Tkinter | PyQt5 | Notes |
|---------|-------|-------|
| `messagebox.showinfo()` | `QMessageBox.information()` | Info dialog |
| `messagebox.showwarning()` | `QMessageBox.warning()` | Warning dialog |
| `messagebox.showerror()` | `QMessageBox.critical()` | Error dialog |
| `messagebox.askyesno()` | `QMessageBox.question()` | Yes/No question |
| `messagebox.askokcancel()` | `QMessageBox.question()` with Ok/Cancel | Ok/Cancel question |

**Example:**
```python
# Tkinter
result = messagebox.askyesno("Confirm", "Are you sure?")

# PyQt5
result = QMessageBox.question(
    self,
    "Confirm",
    "Are you sure?",
    QMessageBox.Yes | QMessageBox.No
)
if result == QMessageBox.Yes:
    # Handle yes
```

### 4.4 FileDialog Conversion (5 usages)

| Tkinter | PyQt5 | Notes |
|---------|-------|-------|
| `filedialog.askopenfilename()` | `QFileDialog.getOpenFileName()` | Select file to open |
| `filedialog.asksaveasfilename()` | `QFileDialog.getSaveFileName()` | Select save location |
| `filedialog.askdirectory()` | `QFileDialog.getExistingDirectory()` | Select directory |

---

## 5. Color Scheme and Styling

### 5.1 Current Color Palette (from setup_program_colors)

```python
# Tkinter Colors:
Background: "#e8f4f8"  # Light blue-gray
Text: "#1e3a8a"        # Dark blue
White fields: "#ffffff"
Headers: "#3b82f6"     # Blue
Header text: "white"
Hover: "#60a5fa"       # Light blue
Pressed: "#1d4ed8"     # Dark blue
Scrollbar: "#d1d5db"   # Gray
Trough: "#f3f4f6"      # Light gray
```

### 5.2 PyQt5 Styling with QSS (Qt Style Sheets)

**Approach 1: Global Stylesheet**
```python
def setup_program_colors(self):
    """Set up Qt stylesheet for entire application"""
    stylesheet = """
        QMainWindow {
            background-color: #e8f4f8;
        }

        QTableWidget {
            background-color: #ffffff;
            color: #1e3a8a;
            gridline-color: #e5e7eb;
            selection-background-color: #3b82f6;
            selection-color: white;
        }

        QHeaderView::section {
            background-color: #3b82f6;
            color: white;
            padding: 8px;
            border: 1px solid #2563eb;
            font-weight: bold;
            font-size: 14px;
        }

        QPushButton {
            background-color: #3b82f6;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 13px;
            border-radius: 4px;
        }

        QPushButton:hover {
            background-color: #60a5fa;
        }

        QPushButton:pressed {
            background-color: #1d4ed8;
        }

        QGroupBox {
            background-color: #e8f4f8;
            color: #1e3a8a;
            border: 2px groove #cbd5e1;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
            font-size: 14px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            padding: 0 5px;
        }

        QLineEdit, QTextEdit, QComboBox {
            background-color: #ffffff;
            color: #1e3a8a;
            border: 1px solid #cbd5e1;
            padding: 5px;
            border-radius: 3px;
        }

        QScrollBar:vertical {
            background: #f3f4f6;
            width: 15px;
            border: 1px solid #d1d5db;
        }

        QScrollBar::handle:vertical {
            background: #d1d5db;
            min-height: 20px;
            border-radius: 3px;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: #3b82f6;
            height: 15px;
        }

        QTabWidget::pane {
            border: 1px solid #cbd5e1;
            background-color: #e8f4f8;
        }

        QTabBar::tab {
            background-color: #cbd5e1;
            color: #1e3a8a;
            padding: 10px 20px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background-color: #3b82f6;
            color: white;
        }

        QStatusBar {
            background-color: #f3f4f6;
            color: #1e3a8a;
        }
    """
    self.setStyleSheet(stylesheet)
```

**Approach 2: Programmatic Styling**
```python
# Set palette colors
palette = QPalette()
palette.setColor(QPalette.Window, QColor("#e8f4f8"))
palette.setColor(QPalette.WindowText, QColor("#1e3a8a"))
palette.setColor(QPalette.Base, QColor("#ffffff"))
palette.setColor(QPalette.Button, QColor("#3b82f6"))
palette.setColor(QPalette.ButtonText, QColor("white"))
QApplication.setPalette(palette)
```

### 5.3 Font Configuration

**Tkinter:**
```python
default_font.configure(size=12)
text_font.configure(size=12)
fixed_font.configure(size=11)
```

**PyQt5:**
```python
def setup_fonts(self):
    """Configure application fonts"""
    # Default font
    font = QFont("Arial", 12)
    QApplication.setFont(font)

    # Specific widget fonts
    header_font = QFont("Arial", 14, QFont.Bold)
    self.table.horizontalHeader().setFont(header_font)

    # Fixed-width font for code/data
    fixed_font = QFont("Courier", 11)
    self.text_edit.setFont(fixed_font)
```

---

## 6. Tab Structure Conversion

### 6.1 Current Tab Architecture

**Manager Tabs (12 tabs):**
1. Equipment Management
2. PM Scheduling
3. PM Completion
4. Corrective Maintenance
5. Cannot Find
6. Run to Failure
7. PM History Search
8. Custom PM Templates
9. MRO Stock Management
10. KPI Dashboard
11. (Analytics Dashboard - commented out)

**Technician Tabs (2 tabs):**
1. Corrective Maintenance
2. System Info

**Parts Coordinator Tabs (3 tabs):**
1. PM Completion
2. MRO Stock Management
3. System Info

### 6.2 PyQt5 Tab Implementation

```python
def create_all_manager_tabs(self):
    """Create all tabs for manager access"""
    self.tabs.addTab(self.create_equipment_tab(), "Equipment Management")
    self.tabs.addTab(self.create_pm_scheduling_tab(), "PM Scheduling")
    self.tabs.addTab(self.create_pm_completion_tab(), "PM Completion")
    self.tabs.addTab(self.create_cm_management_tab(), "Corrective Maintenance")
    self.tabs.addTab(self.create_cannot_find_tab(), "Cannot Find")
    self.tabs.addTab(self.create_run_to_failure_tab(), "Run to Failure")
    self.tabs.addTab(self.create_pm_history_search_tab(), "PM History Search")
    self.tabs.addTab(self.create_custom_pm_templates_tab(), "Custom PM Templates")
    self.tabs.addTab(self.create_mro_tab(), "MRO Stock")
    self.tabs.addTab(self.create_kpi_tab(), "KPI Dashboard")

def create_equipment_tab(self):
    """Create equipment management tab"""
    widget = QWidget()
    layout = QVBoxLayout()

    # Controls group
    controls_group = QGroupBox("Equipment Controls")
    controls_layout = QHBoxLayout()
    controls_layout.addWidget(QPushButton("Import Equipment CSV"))
    controls_layout.addWidget(QPushButton("Add Equipment"))
    controls_layout.addWidget(QPushButton("Edit Equipment"))
    controls_layout.addWidget(QPushButton("Refresh List"))
    controls_layout.addWidget(QPushButton("Export Equipment"))
    controls_group.setLayout(controls_layout)
    layout.addWidget(controls_group)

    # Statistics group
    stats_group = QGroupBox("Equipment Statistics")
    stats_layout = QHBoxLayout()
    self.stats_total_label = QLabel("Total Assets: 0")
    self.stats_cf_label = QLabel("Cannot Find: 0")
    # ... more labels
    stats_layout.addWidget(self.stats_total_label)
    stats_layout.addWidget(self.stats_cf_label)
    stats_group.setLayout(stats_layout)
    layout.addWidget(stats_group)

    # Search frame
    search_layout = QHBoxLayout()
    search_layout.addWidget(QLabel("Search Equipment:"))
    self.equipment_search_entry = QLineEdit()
    self.equipment_search_entry.textChanged.connect(self.filter_equipment_list)
    search_layout.addWidget(self.equipment_search_entry)
    layout.addLayout(search_layout)

    # Equipment table
    self.equipment_table = QTableWidget()
    self.equipment_table.setColumnCount(9)
    self.equipment_table.setHorizontalHeaderLabels([
        'SAP Material No.', 'BFM Equipment No.', 'Description',
        'Location', 'Master LIN', 'Monthly PM', '6-Month PM',
        'Annual PM', 'Status'
    ])
    layout.addWidget(self.equipment_table)

    widget.setLayout(layout)
    return widget
```

---

## 7. Event Handling Conversion

### 7.1 Button Events

**Tkinter:**
```python
ttk.Button(frame, text="Save", command=self.save_data).pack()
```

**PyQt5:**
```python
save_btn = QPushButton("Save")
save_btn.clicked.connect(self.save_data)
layout.addWidget(save_btn)
```

### 7.2 Entry/Input Events

**Tkinter:**
```python
entry.bind('<KeyRelease>', self.on_key_release)
entry.bind('<Return>', self.on_enter_key)
```

**PyQt5:**
```python
entry = QLineEdit()
entry.textChanged.connect(self.on_text_changed)
entry.returnPressed.connect(self.on_enter_key)
```

### 7.3 Treeview/Table Events

**Tkinter:**
```python
tree.bind('<Double-1>', self.on_double_click)
tree.bind('<<TreeviewSelect>>', self.on_selection_changed)
```

**PyQt5:**
```python
table.itemDoubleClicked.connect(self.on_double_click)
table.itemSelectionChanged.connect(self.on_selection_changed)
```

### 7.4 Combobox Events

**Tkinter:**
```python
combo.bind('<<ComboboxSelected>>', self.on_combo_changed)
```

**PyQt5:**
```python
combo = QComboBox()
combo.currentIndexChanged.connect(self.on_combo_changed)
# OR
combo.currentTextChanged.connect(self.on_combo_text_changed)
```

### 7.5 Mouse Wheel Scrolling

**Tkinter:**
```python
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
canvas.bind_all("<MouseWheel>", _on_mousewheel)
```

**PyQt5:**
```python
# Automatic with QScrollArea - no manual binding needed
scroll_area = QScrollArea()
scroll_area.setWidget(content_widget)
scroll_area.setWidgetResizable(True)
```

---

## 8. Scrollable Content Conversion

### 8.1 Current Tkinter Implementation

```python
# Canvas with scrollbar for notebook
self.main_canvas = tk.Canvas(main_container, highlightthickness=0)
scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=self.main_canvas.yview)
self.scrollable_frame = ttk.Frame(self.main_canvas)
self.scrollable_frame.bind("<Configure>", lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
self.canvas_window = self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
self.main_canvas.configure(yscrollcommand=scrollbar.set)
```

### 8.2 PyQt5 QScrollArea Approach

```python
def create_central_widget(self):
    """Create scrollable central widget with tabs"""
    # Create scroll area
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    # Create tabs widget
    self.tabs = QTabWidget()

    # Set tabs as scroll area content
    scroll_area.setWidget(self.tabs)

    # Set as central widget
    self.setCentralWidget(scroll_area)
```

**Note:** In most cases, QTabWidget handles scrolling automatically, so explicit QScrollArea may not be needed.

---

## 9. Variable Binding Conversion

### 9.1 Tkinter Variable Classes

**Tkinter uses:**
- `tk.StringVar()`
- `tk.IntVar()`
- `tk.DoubleVar()`
- `tk.BooleanVar()`

**PyQt5 Approach:**
- Direct access to widget values
- Use signals/slots for reactive updates
- No intermediate variable objects needed

### 9.2 Examples

**Tkinter:**
```python
self.bfm_var = tk.StringVar()
entry = ttk.Entry(form_frame, textvariable=self.bfm_var, width=20)
# Later:
value = self.bfm_var.get()
self.bfm_var.set("new value")
```

**PyQt5:**
```python
self.bfm_entry = QLineEdit()
self.bfm_entry.setMaxLength(20)
# Later:
value = self.bfm_entry.text()
self.bfm_entry.setText("new value")
```

**Reactive Updates with Signals:**
```python
# Update label when entry changes
self.bfm_entry.textChanged.connect(self.update_display_label)

def update_display_label(self, text):
    self.display_label.setText(f"BFM: {text}")
```

---

## 10. Special Widget Conversions

### 10.1 Calendar Widget

**Tkinter (tkcalendar):**
```python
from tkcalendar import Calendar

cal = Calendar(cal_dialog,
    selectmode='day',
    year=current_date.year,
    month=current_date.month,
    day=current_date.day,
    date_pattern='yyyy-mm-dd')
```

**PyQt5:**
```python
from PyQt5.QtWidgets import QCalendarWidget

cal = QCalendarWidget()
cal.setSelectedDate(QDate.currentDate())
cal.setGridVisible(True)
cal.clicked.connect(self.on_date_selected)

def on_date_selected(self, date):
    date_string = date.toString("yyyy-MM-dd")
```

### 10.2 Progress Bar

**Tkinter:**
```python
progress = ttk.Progressbar(frame, length=200, mode='determinate')
progress['value'] = 50  # 50%
```

**PyQt5:**
```python
progress = QProgressBar()
progress.setMinimum(0)
progress.setMaximum(100)
progress.setValue(50)  # 50%
```

### 10.3 Spinbox

**Tkinter:**
```python
spinbox = ttk.Spinbox(frame, from_=0, to=100, increment=1)
```

**PyQt5:**
```python
spinbox = QSpinBox()
spinbox.setMinimum(0)
spinbox.setMaximum(100)
spinbox.setSingleStep(1)
```

---

## 11. Menu Bar Conversion

### 11.1 Current Implementation

```python
menubar = tk.Menu(self.root)
self.root.config(menu=menubar)

account_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Account", menu=account_menu)
account_menu.add_command(label="Change Password", command=self.open_change_password)
account_menu.add_separator()
account_menu.add_command(label="Logout", command=self.logout)
```

### 11.2 PyQt5 Implementation

```python
def create_menu_bar(self):
    """Create application menu bar"""
    menubar = self.menuBar()

    # Account menu
    account_menu = menubar.addMenu("Account")

    change_pwd_action = QAction("Change Password", self)
    change_pwd_action.triggered.connect(self.open_change_password)
    account_menu.addAction(change_pwd_action)

    account_menu.addSeparator()

    logout_action = QAction("Logout", self)
    logout_action.triggered.connect(self.logout)
    account_menu.addAction(logout_action)

    # Optional: Add keyboard shortcuts
    change_pwd_action.setShortcut("Ctrl+P")
    logout_action.setShortcut("Ctrl+L")
```

---

## 12. Status Bar Conversion

### 12.1 Current Implementation

```python
status_frame = ttk.Frame(self.root)
status_frame.pack(side='bottom', fill='x')

self.status_bar = ttk.Label(status_frame,
    text=f"AIT CMMS Ready - Logged in as: {self.user_name} ({self.current_user_role})",
    relief='sunken')
self.status_bar.pack(side='left', fill='x', expand=True)
```

### 12.2 PyQt5 Implementation

```python
def create_status_bar(self):
    """Create status bar"""
    self.status_bar = self.statusBar()
    self.status_bar.showMessage(
        f"AIT CMMS Ready - Logged in as: {self.user_name} ({self.current_user_role})"
    )

def update_status(self, message):
    """Update status bar message"""
    self.status_bar.showMessage(message)
    # Optional: Auto-clear after delay
    # self.status_bar.showMessage(message, 5000)  # 5 seconds
```

---

## 13. High DPI / Scaling Support

### 13.1 Current Tkinter DPI Handling

```python
# Windows DPI awareness (lines 49-76)
ctypes.windll.shcore.SetProcessDpiAwareness(2)

# Tkinter scaling
scaling_factor = get_scaling_factor()
self.root.tk.call('tk', 'scaling', scaling_factor)
```

### 13.2 PyQt5 High DPI Support

```python
# Add BEFORE creating QApplication
import sys
from PyQt5.QtCore import Qt

if __name__ == '__main__':
    # Enable High DPI scaling (Qt 5.6+)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Optional: Set scaling factor manually
    # QApplication.setHighDpiScaleFactorRoundingPolicy(
    #     Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    # )

    window = AITCMMSMainWindow()
    window.show()
    sys.exit(app.exec_())
```

**Font Scaling:**
```python
def setup_fonts(self):
    """Setup fonts with appropriate scaling"""
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch()

    # Calculate scale factor
    scale = dpi / 96.0  # 96 is standard DPI

    # Set base font size scaled for DPI
    base_size = int(12 * scale)
    font = QFont("Arial", base_size)
    QApplication.setFont(font)
```

---

## 14. Supporting Module Conversions

### 14.1 Files Requiring Conversion

1. **user_management_ui.py** (UserManagementDialog)
   - Treeview → QTableWidget
   - Dialog structure → QDialog class
   - Complexity: Medium

2. **password_change_ui.py** (PasswordChangeDialog)
   - Entry fields → QLineEdit
   - Simple dialog → QDialog class
   - Complexity: Low

3. **mro_stock_module.py** (MROStockManager)
   - Treeview → QTableWidget
   - Tab creation → QWidget return
   - Complexity: High

4. **cm_parts_integration.py** (CMPartsIntegration)
   - Dialog integration
   - Complexity: Medium

5. **kpi_ui.py** (KPI visualization)
   - Check for matplotlib integration
   - Complexity: Medium-High

6. **equipment_history.py**
   - Data display dialogs
   - Complexity: Medium

### 14.2 Conversion Priority

**Phase 1 (Core):**
1. Main window structure (AITCMMSMainWindow)
2. Login dialog
3. Basic tab structure
4. Menu and status bar

**Phase 2 (Data Display):**
1. Equipment tab (QTableWidget)
2. PM Completion tab
3. CM Management tab

**Phase 3 (Dialogs):**
1. Create/Edit dialogs
2. MessageBox conversions
3. FileDialog conversions

**Phase 4 (Supporting Modules):**
1. User management
2. Password change
3. MRO stock module
4. Parts integration

**Phase 5 (Advanced):**
1. KPI dashboard
2. Analytics features
3. Styling refinements

---

## 15. Method-by-Method Conversion Complexity

### 15.1 Low Complexity Methods (Quick Conversion)

**Simple data operations (no UI):**
- `init_database()` - No change
- `load_equipment_data()` - No change
- `get_week_start()` - No change
- `calculate_pm_due_date()` - No change
- Database query methods - No change

**Estimate:** ~100 methods, 1-5 minutes each

### 15.2 Medium Complexity Methods (Moderate Refactoring)

**Simple dialogs and forms:**
- `open_change_password()` - QDialog creation
- `logout()` - Message box + navigation
- `refresh_equipment_list()` - Table population
- `load_recent_completions()` - Table population
- `filter_equipment_list()` - Table filtering

**Estimate:** ~50 methods, 15-30 minutes each

### 15.3 High Complexity Methods (Significant Refactoring)

**Complex dialogs with multiple controls:**
- `create_cm_dialog()` - Full dialog with calendar, combos, validation
- `edit_equipment_dialog()` - Multi-field form with autocomplete
- `create_custom_pm_template_dialog()` - Complex nested form
- `show_csv_mapping_dialog()` - Dynamic column mapping
- `complete_cm_dialog()` - Multi-step workflow with parts integration

**Tab creation methods:**
- `create_equipment_tab()` - Statistics, search, table, controls
- `create_pm_completion_tab()` - Form + table + multiple buttons
- `create_cm_management_tab()` - Multiple tables, filters, controls
- `create_kpi_tab()` - Charts and data visualization

**Estimate:** ~30 methods, 1-3 hours each

### 15.4 Very High Complexity Methods (Major Refactoring)

**Advanced features:**
- `create_gui()` - Main UI construction with role-based logic
- `setup_program_colors()` - Complete stylesheet creation
- `__init__()` - Application initialization flow
- CSV import with mapping - Complex UI + validation
- Report generation with previews - Multi-step workflow

**Estimate:** ~10 methods, 3-8 hours each

---

## 16. Testing Strategy

### 16.1 Unit Testing Approach

```python
import unittest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

class TestEquipmentTab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    def setUp(self):
        self.window = AITCMMSMainWindow()
        self.equipment_tab = self.window.equipment_table

    def test_equipment_table_columns(self):
        """Test equipment table has correct columns"""
        self.assertEqual(self.equipment_tab.columnCount(), 9)

    def test_search_filter(self):
        """Test equipment search filtering"""
        # Populate test data
        self.window.refresh_equipment_list()
        initial_count = self.equipment_tab.rowCount()

        # Type in search box
        self.window.equipment_search_entry.setText("BFM-001")

        # Verify filtering
        filtered_count = self.equipment_tab.rowCount()
        self.assertLess(filtered_count, initial_count)

    def test_add_equipment_dialog(self):
        """Test add equipment dialog opens"""
        dialog = self.window.add_equipment_dialog()
        self.assertIsNotNone(dialog)
        self.assertTrue(dialog.isModal())
```

### 16.2 Integration Testing

- Database connection testing
- Login flow testing
- Role-based access testing
- Data persistence testing
- Multi-user session testing

### 16.3 UI Testing Checklist

- [ ] All tabs load without errors
- [ ] All buttons are clickable and functional
- [ ] All dialogs open and close properly
- [ ] Data displays correctly in all tables
- [ ] Search/filter functions work
- [ ] Keyboard shortcuts work
- [ ] High DPI displays render correctly
- [ ] Window resizing works properly
- [ ] Scrolling works in all areas
- [ ] Status bar updates correctly

---

## 17. Migration Gotchas and Common Pitfalls

### 17.1 Critical Differences

**1. Application Event Loop:**
```python
# Tkinter
root = tk.Tk()
# ... setup ...
root.mainloop()

# PyQt5
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())
```

**2. Modal Dialogs:**
```python
# Tkinter - grab_set() + wait_window()
dialog.grab_set()
dialog.wait_window()

# PyQt5 - exec_() is blocking
result = dialog.exec_()
```

**3. Table Row/Column Access:**
```python
# Tkinter - column names
values = tree.item(item_id, 'values')
bfm = values[1]  # Column index

# PyQt5 - QTableWidgetItem objects
item = table.item(row, col)
text = item.text() if item else ""
```

**4. Layout Management:**
```python
# Tkinter - widgets manage themselves
button.pack(side='left')

# PyQt5 - layouts manage widgets
layout = QHBoxLayout()
layout.addWidget(button)
parent.setLayout(layout)
```

**5. Window Closing:**
```python
# Tkinter
dialog.destroy()

# PyQt5
dialog.close()  # Or dialog.accept() / dialog.reject()
```

### 17.2 Common Errors

**Error 1: Forgetting to set layout**
```python
# Wrong:
widget = QWidget()
button = QPushButton("Click", widget)

# Correct:
widget = QWidget()
layout = QVBoxLayout()
layout.addWidget(QPushButton("Click"))
widget.setLayout(layout)
```

**Error 2: Mixing layout types**
```python
# Wrong:
widget = QWidget()
widget.setLayout(QVBoxLayout())
# Later trying to use grid positioning - ERROR!

# Correct: Choose one layout type per widget
widget = QWidget()
layout = QVBoxLayout()  # Stick with this
widget.setLayout(layout)
```

**Error 3: Not connecting signals**
```python
# Wrong (no action on click):
button = QPushButton("Save")

# Correct:
button = QPushButton("Save")
button.clicked.connect(self.save_data)
```

**Error 4: Table item is None**
```python
# Wrong:
text = table.item(row, col).text()  # Crashes if cell empty

# Correct:
item = table.item(row, col)
text = item.text() if item else ""
```

**Error 5: Creating QApplication multiple times**
```python
# Wrong:
def create_dialog():
    app = QApplication([])  # ERROR if already created
    dialog = MyDialog()
    dialog.show()

# Correct:
# Create QApplication once at program start
app = QApplication(sys.argv)
# Then create widgets
dialog = MyDialog()
dialog.show()
```

---

## 18. Recommended Class Structure for PyQt5 Version

```python
# main.py
from PyQt5.QtWidgets import QApplication, QMainWindow
from ui.login_dialog import LoginDialog
from ui.main_window import AITCMMSMainWindow
import sys

def main():
    # Enable High DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Show login dialog
    login = LoginDialog()
    if login.exec_() == QDialog.Accepted:
        # Create main window with user info
        window = AITCMMSMainWindow(
            user_id=login.user_id,
            user_name=login.user_name,
            user_role=login.user_role
        )
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()

# ui/main_window.py
class AITCMMSMainWindow(QMainWindow):
    def __init__(self, user_id, user_name, user_role):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.user_role = user_role

        self.init_database()
        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        self.setWindowTitle("AIT Complete CMMS")
        self.setup_window()
        self.create_menu_bar()
        self.create_toolbar()
        self.create_central_widget()
        self.create_status_bar()
        self.setup_stylesheet()

    def create_central_widget(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.create_tabs_for_role()

# ui/tabs/equipment_tab.py
class EquipmentTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.create_controls())
        layout.addWidget(self.create_statistics())
        layout.addWidget(self.create_search())
        layout.addWidget(self.create_table())
        self.setLayout(layout)

# ui/dialogs/create_cm_dialog.py
class CreateCMDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Corrective Maintenance")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addLayout(self.create_form())
        layout.addWidget(self.create_buttons())
        self.setLayout(layout)

    def create_form(self):
        # Form layout with fields
        pass

    def save(self):
        # Validation and save logic
        if self.validate():
            self.accept()

# utils/database.py
# Keep existing database utilities - no changes needed

# utils/styling.py
class StyleManager:
    @staticmethod
    def get_stylesheet():
        return """
        /* Full QSS stylesheet */
        """

    @staticmethod
    def apply_to_application(app):
        app.setStyleSheet(StyleManager.get_stylesheet())
```

---

## 19. Estimated Conversion Timeline

### 19.1 Phase Breakdown

| Phase | Component | Estimated Time | Priority |
|-------|-----------|----------------|----------|
| **Phase 1** | Project setup & structure | 4 hours | Critical |
| | Main window skeleton | 8 hours | Critical |
| | Login dialog | 4 hours | Critical |
| | Menu bar & status bar | 2 hours | Critical |
| | Database integration | 2 hours | Critical |
| **Phase 2** | Equipment tab | 12 hours | High |
| | PM Completion tab | 10 hours | High |
| | CM Management tab | 12 hours | High |
| | Basic dialogs (5-6) | 8 hours | High |
| **Phase 3** | Remaining tabs (7) | 40 hours | Medium |
| | Complex dialogs (10-12) | 30 hours | Medium |
| | Search/filter functions | 8 hours | Medium |
| **Phase 4** | User management UI | 6 hours | Medium |
| | Password change UI | 3 hours | Low |
| | MRO stock module | 12 hours | High |
| | Parts integration | 8 hours | Medium |
| **Phase 5** | KPI dashboard | 15 hours | Medium |
| | Styling & themes | 8 hours | Low |
| | High DPI optimization | 4 hours | Medium |
| **Phase 6** | Testing & debugging | 30 hours | Critical |
| | Documentation | 10 hours | Medium |
| | Deployment prep | 5 hours | High |

**Total Estimated Time:** 241 hours (~6 weeks at 40 hours/week)

### 19.2 Risk Factors

- **High:** Complex table interactions (sorting, filtering, multi-select)
- **Medium:** Calendar widget integration
- **Medium:** CSV import with column mapping
- **Low:** Basic forms and dialogs

---

## 20. File Organization Structure

```
CMMS_NEON2.2_PyQt5/
│
├── main.py                          # Application entry point
│
├── config/
│   ├── __init__.py
│   ├── database.py                  # Database configuration
│   └── settings.py                  # Application settings
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py               # Main window class
│   │
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── login_dialog.py
│   │   ├── cm_dialogs.py           # CM create/edit/complete
│   │   ├── equipment_dialogs.py
│   │   ├── pm_dialogs.py
│   │   ├── user_management_dialog.py
│   │   └── password_change_dialog.py
│   │
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── equipment_tab.py
│   │   ├── pm_scheduling_tab.py
│   │   ├── pm_completion_tab.py
│   │   ├── cm_management_tab.py
│   │   ├── cannot_find_tab.py
│   │   ├── run_to_failure_tab.py
│   │   ├── pm_history_tab.py
│   │   ├── pm_templates_tab.py
│   │   ├── mro_stock_tab.py
│   │   └── kpi_tab.py
│   │
│   └── widgets/
│       ├── __init__.py
│       ├── custom_table.py         # Reusable table widget
│       ├── date_picker.py          # Calendar widget
│       └── search_bar.py           # Reusable search widget
│
├── utils/
│   ├── __init__.py
│   ├── database_utils.py           # Existing - minimal changes
│   ├── styling.py                  # QSS stylesheets
│   ├── validators.py               # Input validation
│   └── helpers.py                  # Utility functions
│
├── models/
│   ├── __init__.py
│   ├── equipment.py                # Data models
│   ├── pm.py
│   ├── cm.py
│   └── user.py
│
├── managers/
│   ├── __init__.py
│   ├── mro_stock_manager.py       # Adapted from existing
│   ├── cm_parts_integration.py    # Adapted from existing
│   ├── kpi_manager.py             # Adapted from existing
│   └── backup_manager.py          # Adapted from existing
│
├── resources/
│   ├── icons/                      # Application icons
│   ├── images/                     # Logos, etc.
│   └── styles/                     # Additional QSS files
│
├── tests/
│   ├── __init__.py
│   ├── test_ui/
│   ├── test_database/
│   └── test_integration/
│
├── requirements.txt
├── README.md
└── .gitignore
```

**requirements.txt:**
```
PyQt5>=5.15.0
psycopg2-binary>=2.9.0
pandas>=1.3.0
reportlab>=3.6.0
python-dateutil>=2.8.0
```

---

## 21. Critical Conversion Checklist

### 21.1 Pre-Conversion

- [ ] Backup entire Tkinter codebase
- [ ] Set up new PyQt5 project structure
- [ ] Install PyQt5 and dependencies
- [ ] Create virtual environment
- [ ] Set up version control (Git)
- [ ] Document current functionality
- [ ] Create test database snapshot

### 21.2 During Conversion

- [ ] Convert main window structure
- [ ] Convert login system
- [ ] Convert menu bar
- [ ] Convert status bar
- [ ] Convert Equipment tab (pilot)
- [ ] Test pilot tab thoroughly
- [ ] Convert remaining tabs systematically
- [ ] Convert all dialogs
- [ ] Convert supporting modules
- [ ] Implement styling
- [ ] Add high DPI support
- [ ] Convert all event handlers
- [ ] Update all database calls (if needed)

### 21.3 Post-Conversion

- [ ] Full application testing
- [ ] User acceptance testing
- [ ] Performance testing
- [ ] Database integrity testing
- [ ] Multi-user testing
- [ ] High DPI display testing
- [ ] Documentation update
- [ ] Training material creation
- [ ] Deployment planning
- [ ] Rollback plan creation

---

## 22. Key PyQt5 Advantages

### 22.1 Improvements Over Tkinter

1. **Better Performance**
   - Faster rendering for large tables
   - More efficient event handling
   - Better memory management

2. **Modern Look and Feel**
   - Native OS styling
   - Professional appearance
   - Better high DPI support

3. **Rich Widget Set**
   - QTableWidget with built-in features (sorting, filtering)
   - Better calendar widget
   - More dialog options
   - Rich text support

4. **Better Documentation**
   - Extensive official documentation
   - Large community
   - Many examples available

5. **Cross-Platform Consistency**
   - More consistent behavior across OS
   - Better theme support
   - Professional appearance on all platforms

6. **Advanced Features**
   - Model/View architecture for complex data
   - Built-in printing support
   - Better graphics capabilities
   - Animation support

---

## 23. Recommended Development Tools

### 23.1 IDE and Tools

1. **PyCharm Professional** (Recommended)
   - PyQt5 integration
   - Qt Designer integration
   - Database tools
   - Excellent debugging

2. **Qt Designer**
   - Visual UI design
   - Generate .ui files
   - Convert to Python with pyuic5

3. **Qt Creator** (Optional)
   - Complete Qt IDE
   - Designer + code editor

### 23.2 Testing Tools

- **pytest-qt**: PyQt5-specific testing
- **pytest**: General testing framework
- **coverage.py**: Code coverage analysis

### 23.3 Debugging Tools

- **PyQt5 Inspector**: Runtime widget inspection
- **QDebug**: Qt debugging output
- **Python debugger**: Standard debugging

---

## 24. Migration Strategy Recommendation

### 24.1 Recommended Approach: **Incremental Parallel Development**

**Why:**
1. Maintain working Tkinter version during conversion
2. Test PyQt5 version thoroughly before full switch
3. Train users on new interface gradually
4. Roll back if issues arise

**Process:**
1. Create new PyQt5 project alongside Tkinter
2. Share database and utility modules
3. Convert one tab at a time
4. Test each tab before moving to next
5. Run both versions in parallel during transition
6. Full switch after complete testing

### 24.2 Alternative Approach: **Big Bang Conversion**

**Only if:**
- Very tight deadline
- Small user base
- Can afford downtime
- Confident in testing

**Not Recommended** for production CMMS system

---

## 25. Next Steps

### 25.1 Immediate Actions

1. **Review this strategy document** with stakeholders
2. **Set up development environment** with PyQt5
3. **Create pilot conversion** of one simple tab (e.g., System Info tab)
4. **Test pilot** thoroughly
5. **Estimate refined timeline** based on pilot experience
6. **Plan resource allocation**
7. **Begin systematic conversion**

### 25.2 Success Criteria

- [ ] All functionality from Tkinter version works in PyQt5
- [ ] UI is more responsive and professional-looking
- [ ] High DPI displays render correctly
- [ ] All database operations work correctly
- [ ] Multi-user functionality preserved
- [ ] Role-based access control works
- [ ] All reports generate correctly
- [ ] Performance is equal or better than Tkinter
- [ ] Users successfully trained on new interface
- [ ] No critical bugs in production

---

## Appendix A: Quick Reference Tables

### A.1 Most Common Conversions

| Tkinter | PyQt5 | Frequency |
|---------|-------|-----------|
| ttk.Button | QPushButton | Very High |
| ttk.Label | QLabel | Very High |
| ttk.Entry | QLineEdit | Very High |
| ttk.Frame | QWidget | Very High |
| ttk.Treeview | QTableWidget | High |
| tk.Text | QTextEdit | High |
| ttk.Combobox | QComboBox | High |
| messagebox.showinfo | QMessageBox.information | High |
| .pack() | QVBoxLayout/QHBoxLayout | Very High |
| .grid() | QGridLayout | High |

### A.2 Event Conversion Reference

| Tkinter Event | PyQt5 Signal |
|---------------|--------------|
| command=func | clicked.connect(func) |
| `<KeyRelease>` | textChanged.connect(func) |
| `<Return>` | returnPressed.connect(func) |
| `<Double-1>` | itemDoubleClicked.connect(func) |
| `<<TreeviewSelect>>` | itemSelectionChanged.connect(func) |
| `<<ComboboxSelected>>` | currentIndexChanged.connect(func) |

---

## Conclusion

This conversion strategy provides a comprehensive roadmap for migrating the AIT CMMS system from Tkinter to PyQt5. The estimated timeline of 241 hours (6 weeks) is realistic for a systematic, tested conversion. The recommended incremental approach minimizes risk while ensuring a high-quality result.

**Key Success Factors:**
1. Follow the structured conversion approach
2. Test thoroughly at each phase
3. Maintain parallel systems during transition
4. Train users on new interface
5. Have rollback plan ready

**Expected Benefits:**
- Modern, professional UI
- Better performance
- Improved high DPI support
- Enhanced maintainability
- Cross-platform consistency

This document should be treated as a living guide, updated as conversion progresses and new challenges or optimizations are discovered.

---

**Document Version:** 1.0
**Created:** 2025-11-15
**Author:** Analysis of AIT_CMMS_REV3.py
**Total Pages:** 24
