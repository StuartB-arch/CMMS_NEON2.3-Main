"""
Corrective Maintenance (CM) Management Tab - PyQt5 Version

This module provides complete corrective maintenance management functionality including:
- CM work order tracking (create, edit, complete, close)
- Equipment missing parts tracking
- Status filtering and multi-select operations
- Parts consumption integration
- Calendar date pickers
- Complete CRUD operations with validation
- Database integration with PostgreSQL

Author: CMMS Development Team
Version: 2.2
Date: 2025-11-15
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QComboBox, QDialog, QFormLayout,
    QTextEdit, QLineEdit, QMessageBox, QGroupBox, QRadioButton,
    QButtonGroup, QScrollArea, QFrame, QSplitter, QHeaderView,
    QAbstractItemView, QDateEdit, QDialogButtonBox, QCalendarWidget
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
from datetime import datetime, timedelta
import psycopg2
from psycopg2 import extras
from typing import Optional, Callable, List, Tuple


class CMManagementTab(QWidget):
    """
    Corrective Maintenance Management Tab

    Provides comprehensive CM management including:
    - Open/Closed CM tracking
    - Equipment missing parts tracking
    - Filtering and search capabilities
    - Complete workflow management
    """

    def __init__(self, db_connection, user_name: str, user_role: str,
                 technicians: List[str], parent=None):
        """
        Initialize CM Management Tab

        Args:
            db_connection: PostgreSQL database connection
            user_name: Current logged-in user name
            user_role: User role (Manager, Technician, etc.)
            technicians: List of available technicians
            parent: Parent widget
        """
        super().__init__(parent)
        self.conn = db_connection
        self.user_name = user_name
        self.user_role = user_role
        self.technicians = technicians
        self.cm_original_data = []
        self.parts_integration = None  # Optional parts integration module

        self.init_ui()
        self.load_data()

    def set_parts_integration(self, parts_integration):
        """Set the parts integration module for parts consumption tracking"""
        self.parts_integration = parts_integration

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create controls section
        controls_group = self.create_controls_section()
        layout.addWidget(controls_group)

        # Create splitter for CM list and Missing Parts list
        splitter = QSplitter(Qt.Vertical)

        # CM List Section
        cm_group = self.create_cm_list_section()
        splitter.addWidget(cm_group)

        # Missing Parts Section
        missing_parts_group = self.create_missing_parts_section()
        splitter.addWidget(missing_parts_group)

        # Set initial sizes (60% for CM, 40% for missing parts)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter, 1)

        # Statistics section
        stats_group = self.create_statistics_section()
        layout.addWidget(stats_group)

    def create_controls_section(self) -> QGroupBox:
        """Create the controls section with buttons and filters"""
        group = QGroupBox("CM Controls")
        layout = QVBoxLayout()

        # First row - CM operations
        row1 = QHBoxLayout()

        btn_new_cm = QPushButton("Create New CM")
        btn_new_cm.clicked.connect(self.create_cm_dialog)
        row1.addWidget(btn_new_cm)

        btn_edit_cm = QPushButton("Edit CM")
        btn_edit_cm.clicked.connect(self.edit_cm_dialog)
        row1.addWidget(btn_edit_cm)

        btn_complete_cm = QPushButton("Complete CM")
        btn_complete_cm.clicked.connect(self.complete_cm_dialog)
        row1.addWidget(btn_complete_cm)

        btn_refresh = QPushButton("Refresh CM List")
        btn_refresh.clicked.connect(self.load_corrective_maintenance)
        row1.addWidget(btn_refresh)

        row1.addStretch()
        layout.addLayout(row1)

        # Second row - Filters
        row2 = QHBoxLayout()

        row2.addWidget(QLabel("Filter by Status:"))

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Open", "Closed"])
        self.filter_combo.currentTextChanged.connect(self.filter_cm_list)
        row2.addWidget(self.filter_combo)

        btn_clear_filter = QPushButton("Clear Filter")
        btn_clear_filter.clicked.connect(self.clear_cm_filter)
        row2.addWidget(btn_clear_filter)

        row2.addStretch()
        layout.addLayout(row2)

        # Third row - Missing Parts operations
        row3 = QHBoxLayout()

        row3.addWidget(QLabel("Equipment Missing Parts:"))

        btn_report_missing = QPushButton("Report Missing Parts")
        btn_report_missing.clicked.connect(self.create_missing_parts_dialog)
        row3.addWidget(btn_report_missing)

        btn_edit_missing = QPushButton("Edit Missing Parts Entry")
        btn_edit_missing.clicked.connect(self.edit_missing_parts_dialog)
        row3.addWidget(btn_edit_missing)

        btn_close_missing = QPushButton("Close Missing Parts Entry")
        btn_close_missing.clicked.connect(self.close_missing_parts_dialog)
        row3.addWidget(btn_close_missing)

        row3.addStretch()
        layout.addLayout(row3)

        group.setLayout(layout)
        return group

    def create_cm_list_section(self) -> QGroupBox:
        """Create the CM list section"""
        group = QGroupBox("Corrective Maintenance List")
        layout = QVBoxLayout()

        # Create table
        self.cm_table = QTableWidget()
        self.cm_table.setColumnCount(8)
        self.cm_table.setHorizontalHeaderLabels([
            'CM Number', 'BFM', 'Description', 'Priority',
            'Assigned', 'Status', 'Created', 'Source'
        ])

        # Set column widths
        header = self.cm_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # CM Number
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # BFM
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Description
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Priority
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Assigned
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Created
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Source

        # Enable sorting
        self.cm_table.setSortingEnabled(True)

        # Enable multi-selection
        self.cm_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cm_table.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Set minimum height
        self.cm_table.setMinimumHeight(250)

        layout.addWidget(self.cm_table)
        group.setLayout(layout)
        return group

    def create_missing_parts_section(self) -> QGroupBox:
        """Create the missing parts list section"""
        group = QGroupBox("⚠ EQUIPMENT WITH MISSING PARTS - SEPARATE LIST ⚠")
        layout = QVBoxLayout()

        # Info label
        info_label = QLabel(
            "This is a SEPARATE list from CM items above - entries you create will appear here"
        )
        info_label.setStyleSheet("color: blue; font-style: italic;")
        layout.addWidget(info_label)

        # Refresh button
        btn_refresh = QPushButton("🔄 Refresh Missing Parts List")
        btn_refresh.clicked.connect(self.load_missing_parts_list)
        layout.addWidget(btn_refresh)

        # Create table
        self.emp_table = QTableWidget()
        self.emp_table.setColumnCount(8)
        self.emp_table.setHorizontalHeaderLabels([
            'EMP Number', 'BFM', 'Description', 'Priority',
            'Assigned', 'Status', 'Reported Date', 'Missing Parts'
        ])

        # Set column widths
        header = self.emp_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # EMP Number
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # BFM
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Description
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Priority
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Assigned
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Reported Date
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # Missing Parts

        # Enable sorting
        self.emp_table.setSortingEnabled(True)

        # Enable multi-selection
        self.emp_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.emp_table.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Set minimum height
        self.emp_table.setMinimumHeight(200)

        layout.addWidget(self.emp_table)
        group.setLayout(layout)
        return group

    def create_statistics_section(self) -> QGroupBox:
        """Create statistics display section"""
        group = QGroupBox("CM Statistics")
        layout = QHBoxLayout()

        self.stats_label = QLabel("Loading statistics...")
        layout.addWidget(self.stats_label)
        layout.addStretch()

        group.setLayout(layout)
        return group

    def load_data(self):
        """Load all data (CM and missing parts)"""
        self.load_corrective_maintenance()
        self.load_missing_parts_list()
        self.update_statistics()

    def load_corrective_maintenance(self):
        """Load corrective maintenance data with enhanced source tracking"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT cm_number, bfm_equipment_no, description, priority,
                    assigned_technician, status, created_date, notes
                FROM corrective_maintenance
                ORDER BY created_date DESC
            ''')

            # Clear table
            self.cm_table.setRowCount(0)
            self.cm_original_data = []

            # Add CM records
            for idx, cm in enumerate(cursor.fetchall()):
                cm_number, bfm_no, description, priority, assigned, status, created, notes = cm

                # Determine source
                source = "SharePoint" if notes and "Imported from SharePoint" in notes else "Manual"

                # Truncate description for display
                display_desc = (description[:47] + '...') if description and len(description) > 50 else (description or '')

                # Store original data for filtering
                row_data = (cm_number, bfm_no, display_desc, priority, assigned, status, created, source)
                self.cm_original_data.append(row_data)

                # Add to table
                self.cm_table.insertRow(idx)
                for col, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value) if value else '')
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Make read-only
                    self.cm_table.setItem(idx, col, item)

            cursor.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load corrective maintenance: {str(e)}")

    def filter_cm_list(self):
        """Filter the CM list based on selected status"""
        if not self.cm_original_data:
            return

        selected_filter = self.filter_combo.currentText()

        # Clear current table
        self.cm_table.setRowCount(0)

        # Re-add filtered data
        row_idx = 0
        for row_data in self.cm_original_data:
            status = row_data[5]  # Status is at index 5

            # Apply filter
            if selected_filter == "All" or selected_filter == status:
                self.cm_table.insertRow(row_idx)
                for col, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value) if value else '')
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.cm_table.setItem(row_idx, col, item)
                row_idx += 1

    def clear_cm_filter(self):
        """Clear the filter and show all items"""
        self.filter_combo.setCurrentText("All")
        self.filter_cm_list()

    def load_missing_parts_list(self):
        """Load equipment missing parts data"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Fetch all missing parts records
            cursor.execute('''
                SELECT emp_number, bfm_equipment_no, description, priority,
                    assigned_technician, status, reported_date, missing_parts_description
                FROM equipment_missing_parts
                ORDER BY reported_date DESC
            ''')

            # Clear table
            self.emp_table.setRowCount(0)

            # Add missing parts records
            records = cursor.fetchall()
            for idx, emp in enumerate(records):
                emp_number, bfm_no, description, priority, assigned, status, reported_date, missing_parts = emp

                # Truncate description and missing parts for display
                display_desc = (description[:47] + '...') if description and len(description) > 50 else (description or '')
                display_parts = (missing_parts[:97] + '...') if missing_parts and len(missing_parts) > 100 else (missing_parts or '')

                self.emp_table.insertRow(idx)
                row_data = (emp_number, bfm_no, display_desc, priority, assigned, status, reported_date, display_parts)

                for col, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value) if value else '')
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.emp_table.setItem(idx, col, item)

            cursor.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load equipment missing parts: {str(e)}")

    def update_statistics(self):
        """Update CM statistics display"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Total CMs
            cursor.execute("SELECT COUNT(*) FROM corrective_maintenance")
            total_cms = cursor.fetchone()[0]

            # Open CMs
            cursor.execute("SELECT COUNT(*) FROM corrective_maintenance WHERE status = 'Open'")
            open_cms = cursor.fetchone()[0]

            # Closed this month
            cursor.execute("""
                SELECT COUNT(*) FROM corrective_maintenance
                WHERE status = 'Closed'
                AND EXTRACT(MONTH FROM completion_date::DATE) = EXTRACT(MONTH FROM CURRENT_DATE)
                AND EXTRACT(YEAR FROM completion_date::DATE) = EXTRACT(YEAR FROM CURRENT_DATE)
            """)
            closed_this_month = cursor.fetchone()[0]

            # Missing parts count
            cursor.execute("SELECT COUNT(*) FROM equipment_missing_parts WHERE status = 'Open'")
            missing_parts_open = cursor.fetchone()[0]

            stats_text = (
                f"Total CMs: {total_cms} | "
                f"Open: {open_cms} | "
                f"Closed This Month: {closed_this_month} | "
                f"Missing Parts (Open): {missing_parts_open}"
            )

            self.stats_label.setText(stats_text)
            cursor.close()

        except Exception as e:
            self.stats_label.setText(f"Statistics unavailable: {str(e)}")

    def create_cm_dialog(self):
        """Create new Corrective Maintenance work order"""
        dialog = CreateCMDialog(self.conn, self.user_name, self.user_role,
                               self.technicians, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_corrective_maintenance()
            self.update_statistics()

    def edit_cm_dialog(self):
        """Edit existing Corrective Maintenance work order"""
        selected_rows = self.cm_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a CM to edit")
            return

        # Get CM number from first column of selected row
        row = self.cm_table.currentRow()
        cm_number = self.cm_table.item(row, 0).text()

        dialog = EditCMDialog(self.conn, cm_number, self.user_name,
                             self.user_role, self.technicians,
                             self.parts_integration, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_corrective_maintenance()
            self.update_statistics()

    def complete_cm_dialog(self):
        """Complete selected CM work order"""
        selected_rows = self.cm_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a CM to complete")
            return

        # Get CM number from first column of selected row
        row = self.cm_table.currentRow()
        cm_number = self.cm_table.item(row, 0).text()

        dialog = CompleteCMDialog(self.conn, cm_number, self.user_name,
                                 self.parts_integration, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_corrective_maintenance()
            self.update_statistics()

    def create_missing_parts_dialog(self):
        """Create new Equipment Missing Parts entry"""
        dialog = CreateMissingPartsDialog(self.conn, self.user_name,
                                         self.user_role, self.technicians, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_missing_parts_list()
            self.update_statistics()

    def edit_missing_parts_dialog(self):
        """Edit existing Equipment Missing Parts entry"""
        selected_rows = self.emp_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning",
                              "Please select an equipment missing parts entry to edit")
            return

        # Get EMP number from first column of selected row
        row = self.emp_table.currentRow()
        emp_number = self.emp_table.item(row, 0).text()

        dialog = EditMissingPartsDialog(self.conn, emp_number, self.user_name,
                                       self.user_role, self.technicians, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_missing_parts_list()
            self.update_statistics()

    def close_missing_parts_dialog(self):
        """Close an Equipment Missing Parts entry"""
        selected_rows = self.emp_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning",
                              "Please select an equipment missing parts entry to close")
            return

        # Get EMP number from first column of selected row
        row = self.emp_table.currentRow()
        emp_number = self.emp_table.item(row, 0).text()

        dialog = CloseMissingPartsDialog(self.conn, emp_number, self.user_name, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_missing_parts_list()
            self.update_statistics()


class DatePickerWidget(QWidget):
    """Custom date picker widget with calendar button"""

    dateChanged = pyqtSignal(QDate)

    def __init__(self, initial_date: QDate = None, parent=None):
        super().__init__(parent)
        self.init_ui(initial_date or QDate.currentDate())

    def init_ui(self, initial_date: QDate):
        """Initialize the UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Date edit field
        self.date_edit = QDateEdit()
        self.date_edit.setDate(initial_date)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.dateChanged.connect(self.on_date_changed)
        layout.addWidget(self.date_edit)

        # Calendar button
        btn_calendar = QPushButton("📅 Pick Date")
        btn_calendar.clicked.connect(self.show_calendar)
        layout.addWidget(btn_calendar)

        # Today button
        btn_today = QPushButton("Today")
        btn_today.clicked.connect(self.set_today)
        layout.addWidget(btn_today)

    def show_calendar(self):
        """Show calendar dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Date")
        layout = QVBoxLayout(dialog)

        calendar = QCalendarWidget()
        calendar.setSelectedDate(self.date_edit.date())
        layout.addWidget(calendar)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self.accept_date(calendar.selectedDate(), dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec_()

    def accept_date(self, date: QDate, dialog: QDialog):
        """Accept selected date"""
        self.date_edit.setDate(date)
        dialog.accept()

    def set_today(self):
        """Set date to today"""
        self.date_edit.setDate(QDate.currentDate())

    def on_date_changed(self, date: QDate):
        """Handle date change"""
        self.dateChanged.emit(date)

    def date(self) -> QDate:
        """Get current date"""
        return self.date_edit.date()

    def set_date(self, date: QDate):
        """Set date"""
        self.date_edit.setDate(date)

    def text(self) -> str:
        """Get date as text in YYYY-MM-DD format"""
        return self.date_edit.date().toString("yyyy-MM-dd")


class CreateCMDialog(QDialog):
    """Dialog for creating a new Corrective Maintenance work order"""

    def __init__(self, db_connection, user_name: str, user_role: str,
                 technicians: List[str], parent=None):
        super().__init__(parent)
        self.conn = db_connection
        self.user_name = user_name
        self.user_role = user_role
        self.technicians = technicians

        self.setWindowTitle("Create New Corrective Maintenance")
        self.setMinimumWidth(600)
        self.setMinimumHeight(550)

        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)

        # Generate next CM number
        self.cm_number = self.generate_next_cm_number()

        # CM Number (read-only)
        cm_number_label = QLabel(self.cm_number)
        cm_number_label.setStyleSheet("font-weight: bold;")
        form_layout.addRow("CM Number:", cm_number_label)

        # CM Date with calendar picker
        self.date_picker = DatePickerWidget()
        form_layout.addRow("CM Date:", self.date_picker)

        # Equipment Selection
        self.equipment_combo = QComboBox()
        self.equipment_combo.setEditable(True)
        self.load_equipment_list()
        form_layout.addRow("Equipment (BFM):", self.equipment_combo)

        # Description
        self.description_text = QTextEdit()
        self.description_text.setMaximumHeight(100)
        form_layout.addRow("Description*:", self.description_text)

        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setCurrentText("Medium")
        form_layout.addRow("Priority:", self.priority_combo)

        # Assigned Technician
        self.assigned_combo = QComboBox()
        self.assigned_combo.addItems(self.technicians)
        if self.user_role == 'Technician':
            # Auto-assign to current technician
            self.assigned_combo.setCurrentText(self.user_name)
            self.assigned_combo.setEnabled(False)
        form_layout.addRow("Assigned Technician:", self.assigned_combo)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def generate_next_cm_number(self) -> str:
        """Generate next CM number in format CM-YYYYMMDD-XXXX"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            today = datetime.now().strftime('%Y%m%d')

            cursor.execute(
                "SELECT MAX(CAST(SPLIT_PART(cm_number, '-', 3) AS INTEGER)) "
                "FROM corrective_maintenance "
                "WHERE cm_number LIKE %s",
                (f'CM-{today}-%',)
            )

            result = cursor.fetchone()[0]
            next_seq = (result + 1) if result else 1
            cm_number = f"CM-{today}-{next_seq:04d}"

            cursor.close()
            return cm_number

        except Exception as e:
            print(f"Error generating CM number: {e}")
            return f"CM-{datetime.now().strftime('%Y%m%d')}-0001"

    def load_equipment_list(self):
        """Load active equipment list"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute(
                "SELECT DISTINCT bfm_equipment_no FROM equipment "
                "WHERE status = 'Active' ORDER BY bfm_equipment_no"
            )

            equipment_list = [row['bfm_equipment_no'] for row in cursor.fetchall()]
            self.equipment_combo.addItems(equipment_list)
            cursor.close()

        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to load equipment list: {str(e)}")

    def validate_and_save(self):
        """Validate input and save CM"""
        # Validate date
        cm_date = self.date_picker.text()
        if not cm_date:
            QMessageBox.critical(self, "Error", "Please enter a CM date")
            return

        # Check for future dates
        selected_date = datetime.strptime(cm_date, '%Y-%m-%d')
        if selected_date > datetime.now() + timedelta(days=1):
            reply = QMessageBox.question(
                self, "Future Date Warning",
                f"The CM date '{cm_date}' is in the future.\n\nAre you sure this is correct?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Check for old dates
        if selected_date < datetime.now() - timedelta(days=365):
            reply = QMessageBox.question(
                self, "Old Date Warning",
                f"The CM date '{cm_date}' is more than 1 year ago.\n\nAre you sure this is correct?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Validate equipment
        equipment = self.equipment_combo.currentText()
        if not equipment:
            QMessageBox.critical(self, "Error", "Please select equipment")
            return

        # Validate description
        description = self.description_text.toPlainText().strip()
        if not description:
            QMessageBox.critical(self, "Error", "Please enter a description")
            return

        # Save to database
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                INSERT INTO corrective_maintenance
                (cm_number, bfm_equipment_no, description, priority, assigned_technician, created_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                self.cm_number,
                equipment,
                description,
                self.priority_combo.currentText(),
                self.assigned_combo.currentText(),
                cm_date
            ))

            self.conn.commit()
            cursor.close()

            QMessageBox.information(
                self, "Success",
                f"Corrective Maintenance created successfully!\n\n"
                f"CM Number: {self.cm_number}\n"
                f"CM Date: {cm_date}\n"
                f"Equipment: {equipment}\n"
                f"Assigned to: {self.assigned_combo.currentText()}"
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create CM: {str(e)}")


class EditCMDialog(QDialog):
    """Dialog for editing an existing Corrective Maintenance work order"""

    def __init__(self, db_connection, cm_number: str, user_name: str,
                 user_role: str, technicians: List[str],
                 parts_integration, parent=None):
        super().__init__(parent)
        self.conn = db_connection
        self.cm_number = cm_number
        self.user_name = user_name
        self.user_role = user_role
        self.technicians = technicians
        self.parts_integration = parts_integration

        self.setWindowTitle(f"Edit Corrective Maintenance - {cm_number}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        self.load_cm_data()
        self.init_ui()

    def load_cm_data(self):
        """Load CM data from database"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT cm_number, bfm_equipment_no, description, priority, assigned_technician,
                    status, created_date, completion_date, labor_hours, notes, root_cause, corrective_action
                FROM corrective_maintenance
                WHERE cm_number = %s
            ''', (self.cm_number,))

            cm_data = cursor.fetchone()
            if not cm_data:
                raise Exception("CM not found in database")

            (self.orig_cm_number, self.orig_bfm, self.orig_desc, self.orig_priority,
             self.orig_assigned, self.orig_status, self.orig_created, self.orig_completion,
             self.orig_hours, self.orig_notes, self.orig_root_cause,
             self.orig_corrective_action) = cm_data

            cursor.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CM data: {str(e)}")
            self.reject()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # CM Information Section
        info_group = QGroupBox("CM Information")
        info_layout = QFormLayout()

        # CM Number (read-only)
        cm_number_label = QLabel(self.orig_cm_number)
        cm_number_label.setStyleSheet("font-weight: bold;")
        info_layout.addRow("CM Number:", cm_number_label)

        # Equipment
        self.equipment_combo = QComboBox()
        self.equipment_combo.setEditable(True)
        self.load_equipment_list()
        self.equipment_combo.setCurrentText(self.orig_bfm or '')
        info_layout.addRow("BFM Equipment No:", self.equipment_combo)

        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Emergency"])
        self.priority_combo.setCurrentText(self.orig_priority or 'Medium')
        info_layout.addRow("Priority:", self.priority_combo)

        # Assigned Technician
        self.assigned_combo = QComboBox()
        self.assigned_combo.addItems(self.technicians)
        self.assigned_combo.setCurrentText(self.orig_assigned or '')
        info_layout.addRow("Assigned Technician:", self.assigned_combo)

        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Open", "Closed"])
        self.status_combo.setCurrentText(self.orig_status or 'Open')
        info_layout.addRow("Status:", self.status_combo)

        info_group.setLayout(info_layout)
        scroll_layout.addWidget(info_group)

        # Description Section
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout()
        self.description_text = QTextEdit()
        self.description_text.setPlainText(self.orig_desc or '')
        self.description_text.setMaximumHeight(100)
        desc_layout.addWidget(self.description_text)
        desc_group.setLayout(desc_layout)
        scroll_layout.addWidget(desc_group)

        # Completion Information Section
        completion_group = QGroupBox("Completion Information")
        completion_layout = QFormLayout()

        self.labor_hours_edit = QLineEdit(str(self.orig_hours or ''))
        completion_layout.addRow("Labor Hours:", self.labor_hours_edit)

        self.completion_date_edit = QLineEdit(self.orig_completion or '')
        completion_layout.addRow("Completion Date:", self.completion_date_edit)

        completion_group.setLayout(completion_layout)
        scroll_layout.addWidget(completion_group)

        # Notes Section
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout()
        self.notes_text = QTextEdit()
        self.notes_text.setPlainText(self.orig_notes or '')
        self.notes_text.setMaximumHeight(80)
        notes_layout.addWidget(self.notes_text)
        notes_group.setLayout(notes_layout)
        scroll_layout.addWidget(notes_group)

        # Root Cause Section
        root_cause_group = QGroupBox("Root Cause Analysis")
        root_cause_layout = QVBoxLayout()
        self.root_cause_text = QTextEdit()
        self.root_cause_text.setPlainText(self.orig_root_cause or '')
        self.root_cause_text.setMaximumHeight(80)
        root_cause_layout.addWidget(self.root_cause_text)
        root_cause_group.setLayout(root_cause_layout)
        scroll_layout.addWidget(root_cause_group)

        # Corrective Action Section
        corrective_action_group = QGroupBox("Corrective Action")
        corrective_action_layout = QVBoxLayout()
        self.corrective_action_text = QTextEdit()
        self.corrective_action_text.setPlainText(self.orig_corrective_action or '')
        self.corrective_action_text.setMaximumHeight(80)
        corrective_action_layout.addWidget(self.corrective_action_text)
        corrective_action_group.setLayout(corrective_action_layout)
        scroll_layout.addWidget(corrective_action_group)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()

        btn_save = QPushButton("Save Changes")
        btn_save.clicked.connect(self.save_changes)
        button_layout.addWidget(btn_save)

        btn_delete = QPushButton("Delete CM")
        btn_delete.clicked.connect(self.delete_cm)
        button_layout.addWidget(btn_delete)

        if self.parts_integration:
            # Check if parts were used
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('SELECT COUNT(*) FROM cm_parts_used WHERE cm_number = %s',
                         (self.orig_cm_number,))
            parts_count = cursor.fetchone()[0]
            cursor.close()

            btn_text = f"View Parts Used ({parts_count})" if parts_count > 0 else "No Parts Used"
            btn_parts = QPushButton(btn_text)
            btn_parts.clicked.connect(self.show_parts_details)
            button_layout.addWidget(btn_parts)

        button_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)

        layout.addLayout(button_layout)

    def load_equipment_list(self):
        """Load equipment list"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('SELECT bfm_equipment_no FROM equipment ORDER BY bfm_equipment_no')
            equipment_list = [row['bfm_equipment_no'] for row in cursor.fetchall()]
            self.equipment_combo.addItems(equipment_list)
            cursor.close()
        except Exception as e:
            print(f"Error loading equipment: {e}")

    def save_changes(self):
        """Save changes to CM"""
        # Validate description
        description = self.description_text.toPlainText().strip()
        if not description:
            QMessageBox.critical(self, "Error", "Please enter a description")
            return

        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Convert labor hours
            labor_hours = None
            if self.labor_hours_edit.text():
                try:
                    labor_hours = float(self.labor_hours_edit.text())
                except ValueError:
                    QMessageBox.critical(self, "Error", "Invalid labor hours value")
                    return

            cursor.execute('''
                UPDATE corrective_maintenance SET
                bfm_equipment_no = %s,
                description = %s,
                priority = %s,
                assigned_technician = %s,
                status = %s,
                labor_hours = %s,
                completion_date = %s,
                notes = %s,
                root_cause = %s,
                corrective_action = %s
                WHERE cm_number = %s
            ''', (
                self.equipment_combo.currentText(),
                description,
                self.priority_combo.currentText(),
                self.assigned_combo.currentText(),
                self.status_combo.currentText(),
                labor_hours,
                self.completion_date_edit.text() if self.completion_date_edit.text() else None,
                self.notes_text.toPlainText(),
                self.root_cause_text.toPlainText(),
                self.corrective_action_text.toPlainText(),
                self.orig_cm_number
            ))

            self.conn.commit()
            cursor.close()

            QMessageBox.information(self, "Success",
                                  f"CM {self.orig_cm_number} updated successfully!")
            self.accept()

        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            QMessageBox.critical(self, "Error", f"Failed to update CM: {str(e)}")

    def delete_cm(self):
        """Delete CM"""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete CM {self.orig_cm_number}?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
                # Delete child records first
                cursor.execute('DELETE FROM cm_parts_requests WHERE cm_number = %s',
                             (self.orig_cm_number,))
                cursor.execute('DELETE FROM corrective_maintenance WHERE cm_number = %s',
                             (self.orig_cm_number,))
                self.conn.commit()
                cursor.close()

                QMessageBox.information(self, "Success",
                                      f"CM {self.orig_cm_number} deleted successfully!")
                self.accept()

            except Exception as e:
                try:
                    self.conn.rollback()
                except:
                    pass
                QMessageBox.critical(self, "Error", f"Failed to delete CM: {str(e)}")

    def show_parts_details(self):
        """Show parts usage details"""
        if self.parts_integration:
            self.parts_integration.show_cm_parts_details(self.orig_cm_number)


class CompleteCMDialog(QDialog):
    """Dialog for completing a CM work order"""

    def __init__(self, db_connection, cm_number: str, user_name: str,
                 parts_integration, parent=None):
        super().__init__(parent)
        self.conn = db_connection
        self.cm_number = cm_number
        self.user_name = user_name
        self.parts_integration = parts_integration

        self.setWindowTitle(f"Complete CM - {cm_number}")
        self.setMinimumWidth(950)
        self.setMinimumHeight(750)

        self.load_cm_data()
        self.init_ui()

    def load_cm_data(self):
        """Load CM data from database"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT cm_number, bfm_equipment_no, description, assigned_technician,
                    status, labor_hours, notes, root_cause, corrective_action
                FROM corrective_maintenance
                WHERE cm_number = %s
            ''', (self.cm_number,))

            cm_data = cursor.fetchone()
            if not cm_data:
                raise Exception("CM not found")

            (self.cm_num, self.equipment, self.desc, self.tech, self.status,
             self.labor_hrs, self.notes, self.root_cause, self.corr_action) = cm_data

            # Check if already closed
            if self.status in ['Closed', 'Completed']:
                QMessageBox.information(self, "Info", f"CM {cm_number} is already closed")
                self.reject()
                return

            cursor.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CM data: {str(e)}")
            self.reject()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel(f"Complete Corrective Maintenance\nCM Number: {self.cm_number}\nEquipment: {self.equipment}")
        header_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header_label)

        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)

        # Completion Date
        self.completion_date_picker = DatePickerWidget()
        form_layout.addRow("Completion Date*:", self.completion_date_picker)

        # Labor Hours
        self.labor_hours_edit = QLineEdit(str(self.labor_hrs) if self.labor_hrs else '')
        form_layout.addRow("Total Labor Hours*:", self.labor_hours_edit)

        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        form_layout.addRow(separator)

        # Root Cause
        self.root_cause_text = QTextEdit()
        self.root_cause_text.setPlainText(self.root_cause or '')
        self.root_cause_text.setMaximumHeight(100)
        form_layout.addRow("Root Cause*:", self.root_cause_text)

        # Corrective Action
        self.corr_action_text = QTextEdit()
        self.corr_action_text.setPlainText(self.corr_action or '')
        self.corr_action_text.setMaximumHeight(100)
        form_layout.addRow("Corrective Action Taken*:", self.corr_action_text)

        # Additional Notes
        self.notes_text = QTextEdit()
        self.notes_text.setPlainText(self.notes or '')
        self.notes_text.setMaximumHeight(100)
        form_layout.addRow("Additional Notes:", self.notes_text)

        # Add separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        form_layout.addRow(separator2)

        # Parts consumption question
        parts_label = QLabel("Were any parts used from MRO Stock?")
        parts_label.setStyleSheet("color: blue; font-weight: bold; font-size: 11pt;")
        form_layout.addRow(parts_label)

        self.parts_button_group = QButtonGroup()
        self.parts_no_radio = QRadioButton("No parts were used")
        self.parts_yes_radio = QRadioButton("Yes, parts were used (will open parts dialog)")
        self.parts_button_group.addButton(self.parts_no_radio)
        self.parts_button_group.addButton(self.parts_yes_radio)
        self.parts_no_radio.setChecked(True)

        form_layout.addRow(self.parts_no_radio)
        form_layout.addRow(self.parts_yes_radio)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_proceed)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def gather_form_values(self) -> Optional[dict]:
        """Validate and gather form values"""
        # Validate completion date
        completion_date = self.completion_date_picker.text()
        if not completion_date:
            QMessageBox.critical(self, "Error", "Completion date is required")
            return None

        # Validate labor hours
        labor_hours_text = self.labor_hours_edit.text().strip()
        if not labor_hours_text:
            QMessageBox.critical(self, "Error", "Labor hours is required")
            return None

        try:
            labor_hours = float(labor_hours_text)
            if labor_hours < 0:
                QMessageBox.critical(self, "Error", "Labor hours cannot be negative")
                return None
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid labor hours value")
            return None

        # Validate root cause
        root_cause = self.root_cause_text.toPlainText().strip()
        if not root_cause:
            QMessageBox.critical(self, "Error", "Root cause is required")
            return None

        # Validate corrective action
        corr_action = self.corr_action_text.toPlainText().strip()
        if not corr_action:
            QMessageBox.critical(self, "Error", "Corrective action is required")
            return None

        return {
            'completion_date': completion_date,
            'labor_hours': labor_hours,
            'root_cause': root_cause,
            'corrective_action': corr_action,
            'notes': self.notes_text.toPlainText().strip()
        }

    def finalize_closure(self, form_values: dict, parts_recorded: bool):
        """Finalize CM closure after parts handling"""
        if not parts_recorded and self.parts_yes_radio.isChecked():
            # User cancelled parts dialog, don't close CM
            return

        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Update CM record
            cursor.execute('''
                UPDATE corrective_maintenance
                SET status = 'Closed',
                    completion_date = %s,
                    labor_hours = %s,
                    root_cause = %s,
                    corrective_action = %s,
                    notes = %s
                WHERE cm_number = %s
            ''', (
                form_values['completion_date'],
                form_values['labor_hours'],
                form_values['root_cause'],
                form_values['corrective_action'],
                form_values['notes'],
                self.cm_number
            ))

            self.conn.commit()
            cursor.close()

            QMessageBox.information(
                self, "Success",
                f"CM {self.cm_number} completed successfully!\n\n"
                f"Completion Date: {form_values['completion_date']}\n"
                f"Labor Hours: {form_values['labor_hours']}\n"
                f"Status: Closed"
            )

            self.accept()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error", f"Failed to complete CM: {str(e)}")

    def validate_and_proceed(self):
        """Validate closure form and proceed to parts or close"""
        form_values = self.gather_form_values()
        if form_values is None:
            return

        # Check if parts were used
        if self.parts_yes_radio.isChecked():
            # Open parts consumption dialog
            if self.parts_integration:
                self.close()  # Close this dialog
                self.parts_integration.show_parts_consumption_dialog(
                    cm_number=self.cm_number,
                    technician_name=self.tech or 'Unknown',
                    callback=lambda success: self.finalize_closure(form_values, success)
                )
            else:
                reply = QMessageBox.warning(
                    self, "Warning",
                    "Parts integration module not initialized.\n"
                    "Continue without recording parts?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.finalize_closure(form_values, True)
        else:
            # No parts used, close directly
            self.finalize_closure(form_values, True)


class CreateMissingPartsDialog(QDialog):
    """Dialog for creating a new Equipment Missing Parts entry"""

    def __init__(self, db_connection, user_name: str, user_role: str,
                 technicians: List[str], parent=None):
        super().__init__(parent)
        self.conn = db_connection
        self.user_name = user_name
        self.user_role = user_role
        self.technicians = technicians

        self.setWindowTitle("Report Equipment with Missing Parts")
        self.setMinimumWidth(650)
        self.setMinimumHeight(700)

        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)

        # Generate next EMP number
        self.emp_number = self.generate_next_emp_number()

        # EMP Number (read-only)
        emp_number_label = QLabel(self.emp_number)
        emp_number_label.setStyleSheet("font-weight: bold;")
        form_layout.addRow("EMP Number:", emp_number_label)

        # Reported Date with calendar picker
        self.date_picker = DatePickerWidget()
        form_layout.addRow("Reported Date:", self.date_picker)

        # Equipment Selection
        self.equipment_combo = QComboBox()
        self.equipment_combo.setEditable(True)
        self.load_equipment_list()
        form_layout.addRow("Equipment (BFM):", self.equipment_combo)

        # Description
        self.description_text = QTextEdit()
        self.description_text.setMaximumHeight(80)
        form_layout.addRow("Description*:", self.description_text)

        # Missing Parts Description
        missing_parts_label = QLabel("Missing Parts*\n(List all missing parts)")
        form_layout.addRow(missing_parts_label)

        self.missing_parts_text = QTextEdit()
        self.missing_parts_text.setMaximumHeight(120)
        form_layout.addRow(self.missing_parts_text)

        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setCurrentText("Medium")
        form_layout.addRow("Priority:", self.priority_combo)

        # Assigned Technician
        self.assigned_combo = QComboBox()
        self.assigned_combo.addItems(self.technicians)
        if self.user_role == 'Technician':
            self.assigned_combo.setCurrentText(self.user_name)
            self.assigned_combo.setEnabled(False)
        form_layout.addRow("Assigned Technician:", self.assigned_combo)

        # Additional Notes
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        form_layout.addRow("Additional Notes:", self.notes_text)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def generate_next_emp_number(self) -> str:
        """Generate next EMP number in format EMP-YYYYMMDD-XXXX"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            today = datetime.now().strftime('%Y%m%d')

            cursor.execute(
                "SELECT MAX(CAST(SPLIT_PART(emp_number, '-', 3) AS INTEGER)) "
                "FROM equipment_missing_parts "
                "WHERE emp_number LIKE %s",
                (f'EMP-{today}-%',)
            )

            result = cursor.fetchone()[0]
            next_seq = (result + 1) if result else 1
            emp_number = f"EMP-{today}-{next_seq:04d}"

            cursor.close()
            return emp_number

        except Exception as e:
            print(f"Error generating EMP number: {e}")
            return f"EMP-{datetime.now().strftime('%Y%m%d')}-0001"

    def load_equipment_list(self):
        """Load active equipment list"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute(
                "SELECT DISTINCT bfm_equipment_no FROM equipment "
                "WHERE status = 'Active' ORDER BY bfm_equipment_no"
            )

            equipment_list = [row['bfm_equipment_no'] for row in cursor.fetchall()]
            self.equipment_combo.addItems(equipment_list)
            cursor.close()

        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to load equipment list: {str(e)}")

    def validate_and_save(self):
        """Validate input and save entry"""
        # Validate date
        emp_date = self.date_picker.text()
        if not emp_date:
            QMessageBox.critical(self, "Error", "Please enter a reported date")
            return

        # Check for future dates
        selected_date = datetime.strptime(emp_date, '%Y-%m-%d')
        if selected_date > datetime.now() + timedelta(days=1):
            reply = QMessageBox.question(
                self, "Future Date Warning",
                f"The date '{emp_date}' is in the future.\n\nAre you sure this is correct?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Validate equipment
        equipment = self.equipment_combo.currentText()
        if not equipment:
            QMessageBox.critical(self, "Error", "Please select equipment")
            return

        # Validate description
        description = self.description_text.toPlainText().strip()
        if not description:
            QMessageBox.critical(self, "Error", "Please enter a description")
            return

        # Validate missing parts
        missing_parts = self.missing_parts_text.toPlainText().strip()
        if not missing_parts:
            QMessageBox.critical(self, "Error", "Please enter missing parts details")
            return

        # Save to database
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                INSERT INTO equipment_missing_parts
                (emp_number, bfm_equipment_no, description, priority, assigned_technician,
                 reported_date, missing_parts_description, notes, reported_by, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                self.emp_number,
                equipment,
                description,
                self.priority_combo.currentText(),
                self.assigned_combo.currentText(),
                emp_date,
                missing_parts,
                self.notes_text.toPlainText(),
                self.user_name,
                'Open'
            ))

            self.conn.commit()
            cursor.close()

            QMessageBox.information(
                self, "Success",
                f"Equipment Missing Parts entry created successfully!\n\n"
                f"EMP Number: {self.emp_number}\n"
                f"Date: {emp_date}\n"
                f"Equipment: {equipment}\n"
                f"Assigned to: {self.assigned_combo.currentText()}\n\n"
                f"Check the 'Equipment with Missing Parts' section!"
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create missing parts entry: {str(e)}")


class EditMissingPartsDialog(QDialog):
    """Dialog for editing an existing Equipment Missing Parts entry"""

    def __init__(self, db_connection, emp_number: str, user_name: str,
                 user_role: str, technicians: List[str], parent=None):
        super().__init__(parent)
        self.conn = db_connection
        self.emp_number = emp_number
        self.user_name = user_name
        self.user_role = user_role
        self.technicians = technicians

        self.setWindowTitle(f"Edit Equipment Missing Parts - {emp_number}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(700)

        self.load_emp_data()
        self.init_ui()

    def load_emp_data(self):
        """Load EMP data from database"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT emp_number, bfm_equipment_no, description, priority, assigned_technician,
                    status, reported_date, missing_parts_description, notes, reported_by,
                    closed_date, closed_by
                FROM equipment_missing_parts
                WHERE emp_number = %s
            ''', (self.emp_number,))

            emp_data = cursor.fetchone()
            if not emp_data:
                raise Exception("Equipment missing parts entry not found in database")

            (self.orig_emp_number, self.orig_bfm, self.orig_desc, self.orig_priority,
             self.orig_assigned, self.orig_status, self.orig_reported_date,
             self.orig_missing_parts, self.orig_notes, self.orig_reported_by,
             self.orig_closed_date, self.orig_closed_by) = emp_data

            cursor.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load entry data: {str(e)}")
            self.reject()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel(f"Equipment Missing Parts - {self.emp_number}")
        header_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header_label)

        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)

        # Equipment
        self.equipment_combo = QComboBox()
        self.equipment_combo.setEditable(True)
        self.load_equipment_list()
        self.equipment_combo.setCurrentText(self.orig_bfm or '')
        form_layout.addRow("BFM Equipment No:", self.equipment_combo)

        # Description
        self.description_text = QTextEdit()
        self.description_text.setPlainText(self.orig_desc or '')
        self.description_text.setMaximumHeight(80)
        form_layout.addRow("Description:", self.description_text)

        # Missing Parts
        self.missing_parts_text = QTextEdit()
        self.missing_parts_text.setPlainText(self.orig_missing_parts or '')
        self.missing_parts_text.setMaximumHeight(120)
        form_layout.addRow("Missing Parts:", self.missing_parts_text)

        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setCurrentText(self.orig_priority or 'Medium')
        form_layout.addRow("Priority:", self.priority_combo)

        # Assigned Technician
        self.assigned_combo = QComboBox()
        self.assigned_combo.addItems(self.technicians)
        self.assigned_combo.setCurrentText(self.orig_assigned or '')
        form_layout.addRow("Assigned Technician:", self.assigned_combo)

        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Open", "Closed"])
        self.status_combo.setCurrentText(self.orig_status or 'Open')
        form_layout.addRow("Status:", self.status_combo)

        # Notes
        self.notes_text = QTextEdit()
        self.notes_text.setPlainText(self.orig_notes or '')
        self.notes_text.setMaximumHeight(100)
        form_layout.addRow("Notes:", self.notes_text)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()

        btn_save = QPushButton("Save Changes")
        btn_save.clicked.connect(self.save_changes)
        button_layout.addWidget(btn_save)

        btn_delete = QPushButton("Delete Entry")
        btn_delete.clicked.connect(self.delete_entry)
        button_layout.addWidget(btn_delete)

        button_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)

        layout.addLayout(button_layout)

    def load_equipment_list(self):
        """Load equipment list"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('SELECT bfm_equipment_no FROM equipment ORDER BY bfm_equipment_no')
            equipment_list = [row['bfm_equipment_no'] for row in cursor.fetchall()]
            self.equipment_combo.addItems(equipment_list)
            cursor.close()
        except Exception as e:
            print(f"Error loading equipment: {e}")

    def save_changes(self):
        """Save changes to entry"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                UPDATE equipment_missing_parts SET
                bfm_equipment_no = %s,
                description = %s,
                missing_parts_description = %s,
                priority = %s,
                assigned_technician = %s,
                status = %s,
                notes = %s,
                updated_date = CURRENT_TIMESTAMP
                WHERE emp_number = %s
            ''', (
                self.equipment_combo.currentText(),
                self.description_text.toPlainText(),
                self.missing_parts_text.toPlainText(),
                self.priority_combo.currentText(),
                self.assigned_combo.currentText(),
                self.status_combo.currentText(),
                self.notes_text.toPlainText(),
                self.orig_emp_number
            ))

            self.conn.commit()
            cursor.close()

            QMessageBox.information(self, "Success",
                                  f"Entry {self.orig_emp_number} updated successfully!")
            self.accept()

        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            QMessageBox.critical(self, "Error", f"Failed to update entry: {str(e)}")

    def delete_entry(self):
        """Delete entry"""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete entry {self.orig_emp_number}?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
                cursor.execute('DELETE FROM equipment_missing_parts WHERE emp_number = %s',
                             (self.orig_emp_number,))
                self.conn.commit()
                cursor.close()

                QMessageBox.information(self, "Success",
                                      f"Entry {self.orig_emp_number} deleted successfully!")
                self.accept()

            except Exception as e:
                try:
                    self.conn.rollback()
                except:
                    pass
                QMessageBox.critical(self, "Error", f"Failed to delete entry: {str(e)}")


class CloseMissingPartsDialog(QDialog):
    """Dialog for closing an Equipment Missing Parts entry"""

    def __init__(self, db_connection, emp_number: str, user_name: str, parent=None):
        super().__init__(parent)
        self.conn = db_connection
        self.emp_number = emp_number
        self.user_name = user_name

        self.setWindowTitle(f"Close Equipment Missing Parts - {emp_number}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)

        self.load_emp_data()
        self.init_ui()

    def load_emp_data(self):
        """Load EMP data from database"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT emp_number, bfm_equipment_no, description, status, missing_parts_description
                FROM equipment_missing_parts
                WHERE emp_number = %s
            ''', (self.emp_number,))

            emp_data = cursor.fetchone()
            if not emp_data:
                raise Exception("Equipment missing parts entry not found")

            (self.orig_emp_number, self.orig_bfm, self.orig_desc,
             self.orig_status, self.orig_missing_parts) = emp_data

            if self.orig_status == 'Closed':
                QMessageBox.information(self, "Already Closed",
                                      f"Entry {emp_number} is already closed.")
                self.reject()
                return

            cursor.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load entry data: {str(e)}")
            self.reject()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # Entry Information
        info_group = QGroupBox("Entry Information")
        info_layout = QFormLayout()

        info_layout.addRow("EMP Number:", QLabel(self.emp_number))
        info_layout.addRow("Equipment:", QLabel(self.orig_bfm or 'N/A'))

        desc_label = QLabel(self.orig_desc or 'N/A')
        desc_label.setWordWrap(True)
        info_layout.addRow("Description:", desc_label)

        parts_label = QLabel(self.orig_missing_parts or 'N/A')
        parts_label.setWordWrap(True)
        info_layout.addRow("Missing Parts:", parts_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Closure Information
        closure_group = QGroupBox("Closure Information")
        closure_layout = QFormLayout()

        # Closure Date
        self.closure_date_picker = DatePickerWidget()
        closure_layout.addRow("Closure Date:", self.closure_date_picker)

        # Closure Notes
        notes_label = QLabel("Closure Notes:\n(Parts procured, issue resolved, etc.)")
        notes_label.setStyleSheet("color: gray; font-style: italic;")
        closure_layout.addRow(notes_label)

        self.closure_notes_text = QTextEdit()
        self.closure_notes_text.setMaximumHeight(120)
        closure_layout.addRow(self.closure_notes_text)

        closure_group.setLayout(closure_layout)
        layout.addWidget(closure_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_closure)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save_closure(self):
        """Save the closure"""
        closure_date = self.closure_date_picker.text()
        if not closure_date:
            QMessageBox.critical(self, "Error", "Please enter a closure date")
            return

        closure_notes = self.closure_notes_text.toPlainText().strip()

        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                UPDATE equipment_missing_parts
                SET status = 'Closed',
                    closed_date = %s,
                    closed_by = %s,
                    notes = COALESCE(notes, '') || %s,
                    updated_date = CURRENT_TIMESTAMP
                WHERE emp_number = %s
            ''', (
                closure_date,
                self.user_name,
                '\n\n[CLOSURE NOTES]\n' + closure_notes if closure_notes else '',
                self.emp_number
            ))

            self.conn.commit()
            cursor.close()

            QMessageBox.information(
                self, "Success",
                f"Entry {self.emp_number} closed successfully!\n\n"
                f"Closed Date: {closure_date}\n"
                f"Closed By: {self.user_name}"
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to close entry: {str(e)}")


# Example usage
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    # This is just for testing - in production, you would pass real DB connection
    app = QApplication(sys.argv)

    # Mock connection for testing
    # In production: conn = psycopg2.connect(...)

    # tab = CMManagementTab(conn, "Test User", "Manager", ["Tech1", "Tech2", "Tech3"])
    # tab.show()

    print("CM Management Tab Module Loaded Successfully")
    print("Import this module and instantiate CMManagementTab with proper DB connection")

    # sys.exit(app.exec_())
