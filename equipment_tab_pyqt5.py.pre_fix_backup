"""
Equipment Management Tab - PyQt5 Implementation
Complete port from Tkinter to PyQt5

This module provides a complete Equipment Management interface including:
- Equipment list with search and filtering
- Add, Edit, and Bulk Edit functionality
- CSV Import/Export with column mapping
- Statistics display (Total, Cannot Find, Run to Failure, Active)
- Database operations with PostgreSQL
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QDialog, QFormLayout,
    QCheckBox, QMessageBox, QFileDialog, QGroupBox, QHeaderView,
    QTextEdit, QListWidget, QDialogButtonBox, QScrollArea, QFrame,
    QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import pandas as pd
from datetime import datetime
from psycopg2 import extras
import traceback


class EquipmentTab(QWidget):
    """Equipment Management Tab Widget"""

    status_updated = pyqtSignal(str)  # Signal to update status bar

    def __init__(self, conn, technicians, parent=None):
        """
        Initialize Equipment Tab

        Args:
            conn: Database connection object
            technicians: List of technician names
            parent: Parent widget
        """
        super().__init__(parent)
        self.conn = conn
        self.technicians = technicians
        self.equipment_data = []

        self.init_ui()
        self.refresh_equipment_list()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Statistics Frame
        stats_group = self.create_statistics_group()
        layout.addWidget(stats_group)

        # Controls Frame
        controls_group = self.create_controls_group()
        layout.addWidget(controls_group)

        # Search Frame
        search_frame = self.create_search_frame()
        layout.addWidget(search_frame)

        # Equipment Table
        self.create_equipment_table()
        layout.addWidget(self.equipment_table)

        self.setLayout(layout)

    def create_statistics_group(self):
        """Create statistics display group box"""
        group = QGroupBox("Equipment Statistics")
        layout = QHBoxLayout()

        # Create statistics labels
        bold_font = QFont()
        bold_font.setBold(True)
        bold_font.setPointSize(10)

        self.stats_total_label = QLabel("Total Assets: 0")
        self.stats_total_label.setFont(bold_font)

        self.stats_cf_label = QLabel("Cannot Find: 0")
        self.stats_cf_label.setFont(bold_font)
        self.stats_cf_label.setStyleSheet("color: red;")

        self.stats_rtf_label = QLabel("Run to Failure: 0")
        self.stats_rtf_label.setFont(bold_font)
        self.stats_rtf_label.setStyleSheet("color: orange;")

        self.stats_active_label = QLabel("Active Assets: 0")
        self.stats_active_label.setFont(bold_font)
        self.stats_active_label.setStyleSheet("color: green;")

        # Refresh button
        refresh_stats_btn = QPushButton("Refresh Stats")
        refresh_stats_btn.clicked.connect(self.update_equipment_statistics)

        # Add to layout
        layout.addWidget(self.stats_total_label)
        layout.addWidget(self.stats_cf_label)
        layout.addWidget(self.stats_rtf_label)
        layout.addWidget(self.stats_active_label)
        layout.addStretch()
        layout.addWidget(refresh_stats_btn)

        group.setLayout(layout)
        return group

    def create_controls_group(self):
        """Create control buttons group box"""
        group = QGroupBox("Equipment Controls")
        layout = QHBoxLayout()

        # Create buttons
        btn_import = QPushButton("Import Equipment CSV")
        btn_import.clicked.connect(self.import_equipment_csv)

        btn_add = QPushButton("Add Equipment")
        btn_add.clicked.connect(self.add_equipment_dialog)

        btn_edit = QPushButton("Edit Equipment")
        btn_edit.clicked.connect(self.edit_equipment_dialog)

        btn_refresh = QPushButton("Refresh List")
        btn_refresh.clicked.connect(self.refresh_equipment_list)

        btn_export = QPushButton("Export Equipment")
        btn_export.clicked.connect(self.export_equipment_list)

        btn_bulk_edit = QPushButton("Bulk Edit PM Cycles")
        btn_bulk_edit.clicked.connect(self.bulk_edit_pm_cycles)

        # Add buttons to layout
        layout.addWidget(btn_import)
        layout.addWidget(btn_add)
        layout.addWidget(btn_edit)
        layout.addWidget(btn_refresh)
        layout.addWidget(btn_export)
        layout.addWidget(btn_bulk_edit)
        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_search_frame(self):
        """Create search and filter frame"""
        frame = QFrame()
        layout = QHBoxLayout()

        # Search label and entry
        search_label = QLabel("Search Equipment:")
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search by SAP, BFM, Description, Location, or LIN...")
        self.search_entry.textChanged.connect(self.filter_equipment_list)
        self.search_entry.setMinimumWidth(250)

        # Location filter
        location_label = QLabel("Filter by Location:")
        self.location_combo = QComboBox()
        self.location_combo.addItem("All Locations")
        self.location_combo.currentTextChanged.connect(self.filter_equipment_list)
        self.location_combo.setMinimumWidth(200)

        # Clear filters button
        btn_clear = QPushButton("Clear Filters")
        btn_clear.clicked.connect(self.clear_equipment_filters)

        # Add to layout
        layout.addWidget(search_label)
        layout.addWidget(self.search_entry)
        layout.addSpacing(20)
        layout.addWidget(location_label)
        layout.addWidget(self.location_combo)
        layout.addWidget(btn_clear)
        layout.addStretch()

        frame.setLayout(layout)
        return frame

    def create_equipment_table(self):
        """Create equipment table widget"""
        self.equipment_table = QTableWidget()

        # Set up columns
        columns = ['SAP Material No.', 'BFM Equipment No.', 'Description',
                   'Location', 'Master LIN', 'Monthly PM', '6-Month PM',
                   'Annual PM', 'Status']
        self.equipment_table.setColumnCount(len(columns))
        self.equipment_table.setHorizontalHeaderLabels(columns)

        # Configure table properties
        self.equipment_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.equipment_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.equipment_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.equipment_table.setAlternatingRowColors(True)
        self.equipment_table.setSortingEnabled(True)

        # Set column widths
        header = self.equipment_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # SAP
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # BFM
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Description
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Location
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # LIN
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Monthly
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 6-Month
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Annual
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Status

        # Enable sorting
        self.equipment_table.setSortingEnabled(True)

    def load_equipment_data(self):
        """Load equipment data from database"""
        try:
            # Rollback any failed transaction before starting
            self.conn.rollback()

            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('SELECT * FROM equipment ORDER BY bfm_equipment_no')
            self.equipment_data = cursor.fetchall()

        except Exception as e:
            self.conn.rollback()
            print(f"Error loading equipment data: {e}")
            traceback.print_exc()
            self.equipment_data = []

    def refresh_equipment_list(self):
        """Refresh equipment list display"""
        try:
            self.load_equipment_data()

            # Disable sorting while updating
            self.equipment_table.setSortingEnabled(False)

            # Clear existing items
            self.equipment_table.setRowCount(0)

            # Add equipment to table
            for equipment in self.equipment_data:
                if equipment:  # Check if equipment dict is not empty
                    row_position = self.equipment_table.rowCount()
                    self.equipment_table.insertRow(row_position)

                    # Create items for each column (now using dictionary keys)
                    items = [
                        equipment.get('sap_material_no') or '',  # SAP
                        equipment.get('bfm_equipment_no') or '',  # BFM
                        equipment.get('description') or '',  # Description
                        equipment.get('location') or '',  # Location
                        equipment.get('master_lin') or '',  # Master LIN
                        'Yes' if equipment.get('monthly_pm') else 'No',  # Monthly PM
                        'Yes' if equipment.get('six_month_pm') else 'No',  # Six Month PM
                        'Yes' if equipment.get('annual_pm') else 'No',  # Annual PM
                        equipment.get('status') or 'Active'  # Status
                    ]

                    for col, item_text in enumerate(items):
                        item = QTableWidgetItem(str(item_text))

                        # Color code status column
                        if col == 8:  # Status column
                            if item_text == 'Cannot Find':
                                item.setForeground(QColor('red'))
                            elif item_text == 'Run to Failure':
                                item.setForeground(QColor('orange'))
                            elif item_text == 'Active':
                                item.setForeground(QColor('green'))

                        self.equipment_table.setItem(row_position, col, item)

            # Re-enable sorting
            self.equipment_table.setSortingEnabled(True)

            # Update statistics
            self.update_equipment_statistics()

            # Update location filter dropdown
            self.populate_location_filter()

            # Update status
            self.status_updated.emit(f"Equipment list refreshed - {len(self.equipment_data)} items")

        except Exception as e:
            print(f"Error refreshing equipment list: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to refresh equipment list: {str(e)}")

    def filter_equipment_list(self):
        """Filter equipment list based on search term and location"""
        try:
            search_term = self.search_entry.text().lower()
            selected_location = self.location_combo.currentText()

            # Disable sorting while filtering
            self.equipment_table.setSortingEnabled(False)

            # Clear existing items
            self.equipment_table.setRowCount(0)

            matches_found = 0

            for equipment in self.equipment_data:
                if equipment:  # Check if equipment dict is not empty
                    equipment_location = equipment.get('location') or ''

                    # Check location filter
                    location_match = (selected_location == "All Locations" or
                                    equipment_location == selected_location)

                    if not location_match:
                        continue

                    # Check if search term matches any field
                    searchable_fields = [
                        equipment.get('sap_material_no') or '',  # SAP
                        equipment.get('bfm_equipment_no') or '',  # BFM
                        equipment.get('description') or '',  # Description
                        equipment_location,  # Location
                        equipment.get('master_lin') or ''   # Master LIN
                    ]

                    if not search_term or any(search_term in field.lower() for field in searchable_fields):
                        row_position = self.equipment_table.rowCount()
                        self.equipment_table.insertRow(row_position)

                        # Create items for each column (now using dictionary keys)
                        items = [
                            equipment.get('sap_material_no') or '',  # SAP
                            equipment.get('bfm_equipment_no') or '',  # BFM
                            equipment.get('description') or '',  # Description
                            equipment_location,  # Location
                            equipment.get('master_lin') or '',  # Master LIN
                            'Yes' if equipment.get('monthly_pm') else 'No',  # Monthly PM
                            'Yes' if equipment.get('six_month_pm') else 'No',  # Six Month PM
                            'Yes' if equipment.get('annual_pm') else 'No',  # Annual PM
                            equipment.get('status') or 'Active'  # Status
                        ]

                        for col, item_text in enumerate(items):
                            item = QTableWidgetItem(str(item_text))

                            # Color code status column
                            if col == 8:  # Status column
                                if item_text == 'Cannot Find':
                                    item.setForeground(QColor('red'))
                                elif item_text == 'Run to Failure':
                                    item.setForeground(QColor('orange'))
                                elif item_text == 'Active':
                                    item.setForeground(QColor('green'))

                            self.equipment_table.setItem(row_position, col, item)

                        matches_found += 1

            # Re-enable sorting
            self.equipment_table.setSortingEnabled(True)

            # Update status
            if search_term:
                self.status_updated.emit(f"Found {matches_found} equipment matching '{search_term}'")
            else:
                self.status_updated.emit(f"Showing {matches_found} equipment items")

        except Exception as e:
            print(f"Error filtering equipment list: {e}")
            traceback.print_exc()
            self.status_updated.emit(f"Error filtering equipment: {e}")

    def populate_location_filter(self):
        """Populate location filter dropdown with distinct locations from database"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT DISTINCT location
                FROM equipment
                WHERE location IS NOT NULL AND location != ''
                ORDER BY location
            ''')
            locations = [row['location'] for row in cursor.fetchall()]

            # Save current selection
            current_location = self.location_combo.currentText()

            # Update combobox
            self.location_combo.clear()
            self.location_combo.addItem("All Locations")
            self.location_combo.addItems(locations)

            # Restore selection if it still exists
            index = self.location_combo.findText(current_location)
            if index >= 0:
                self.location_combo.setCurrentIndex(index)
            else:
                self.location_combo.setCurrentIndex(0)

        except Exception as e:
            print(f"Error populating location filter: {e}")
            traceback.print_exc()

    def clear_equipment_filters(self):
        """Clear all equipment filters and show all equipment"""
        self.search_entry.clear()
        self.location_combo.setCurrentIndex(0)  # Set to "All Locations"
        self.filter_equipment_list()

    def update_equipment_statistics(self):
        """Update equipment statistics display"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Get total assets count
            cursor.execute('SELECT COUNT(*) as count FROM equipment')
            total_assets = cursor.fetchone()['count']

            # Get Cannot Find count from cannot_find_assets table
            cursor.execute('''
                SELECT COUNT(DISTINCT bfm_equipment_no) as count
                FROM cannot_find_assets
                WHERE status = %s
            ''', ('Missing',))
            cannot_find_count = cursor.fetchone()['count']

            # Get Run to Failure count from equipment table
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM equipment
                WHERE status = %s
            ''', ('Run to Failure',))
            rtf_count = cursor.fetchone()['count']

            # Active assets = Total - Cannot Find - Run to Failure
            active_assets = total_assets - cannot_find_count - rtf_count

            # Update labels
            self.stats_total_label.setText(f"Total Assets: {total_assets}")
            self.stats_active_label.setText(f"Active Assets: {active_assets}")
            self.stats_cf_label.setText(f"Cannot Find: {cannot_find_count}")
            self.stats_rtf_label.setText(f"Run to Failure: {rtf_count}")

            # Update status bar
            self.status_updated.emit(
                f"Equipment stats updated - Total: {total_assets}, "
                f"Active: {active_assets}, CF: {cannot_find_count}, RTF: {rtf_count}"
            )

        except Exception as e:
            print(f"Error updating equipment statistics: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to update equipment statistics: {str(e)}")

    def add_equipment_dialog(self):
        """Dialog to add new equipment"""
        dialog = AddEquipmentDialog(self.conn, parent=self)
        if dialog.exec_():
            self.refresh_equipment_list()
            self.status_updated.emit("Equipment added successfully")

    def edit_equipment_dialog(self):
        """Dialog to edit existing equipment"""
        selected_rows = self.equipment_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select equipment to edit")
            return

        # Get BFM number from selected row
        row = selected_rows[0].row()
        bfm_no = self.equipment_table.item(row, 1).text()  # BFM is column 1

        dialog = EditEquipmentDialog(self.conn, bfm_no, self.technicians, parent=self)
        if dialog.exec_():
            self.refresh_equipment_list()
            self.status_updated.emit(f"Equipment {bfm_no} updated successfully")

    def bulk_edit_pm_cycles(self):
        """Edit PM cycles for multiple selected assets"""
        selected_rows = self.equipment_table.selectionModel().selectedRows()

        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection",
                "Please select one or more assets to edit.\n\n"
                "Tip: Hold Ctrl to select multiple items, or Shift to select a range."
            )
            return

        # Get BFM numbers of selected items
        selected_bfms = []
        for row_index in selected_rows:
            row = row_index.row()
            bfm_no = self.equipment_table.item(row, 1).text()  # BFM is column 1
            selected_bfms.append(bfm_no)

        dialog = BulkEditPMCyclesDialog(self.conn, selected_bfms, parent=self)
        if dialog.exec_():
            self.refresh_equipment_list()
            self.status_updated.emit(f"Bulk updated PM cycles for {len(selected_bfms)} assets")

    def import_equipment_csv(self):
        """Import equipment data from CSV file with PM dates"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Equipment CSV File",
            "",
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_path:
            try:
                # Show column mapping dialog
                dialog = CSVMappingDialog(self.conn, file_path, parent=self)
                if dialog.exec_():
                    self.refresh_equipment_list()
                    self.status_updated.emit("CSV import completed")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import CSV file: {str(e)}")
                traceback.print_exc()

    def export_equipment_list(self):
        """Export equipment list to CSV"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Equipment List",
                "equipment_export.csv",
                "CSV files (*.csv);;All files (*.*)"
            )

            if file_path:
                cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
                cursor.execute('''
                    SELECT id, sap_material_no, bfm_equipment_no, description,
                           tool_id_drawing_no, location, master_lin, monthly_pm,
                           six_month_pm, annual_pm, last_monthly_pm, last_six_month_pm,
                           last_annual_pm, next_monthly_pm, next_six_month_pm,
                           next_annual_pm, status, created_date, updated_date
                    FROM equipment
                    ORDER BY bfm_equipment_no
                ''')
                equipment_data = cursor.fetchall()

                # Create DataFrame
                columns = ['ID', 'SAP Material No', 'BFM Equipment No', 'Description',
                          'Tool ID/Drawing No', 'Location', 'Master LIN', 'Monthly PM',
                          'Six Month PM', 'Annual PM', 'Last Monthly PM', 'Last Six Month PM',
                          'Last Annual PM', 'Next Monthly PM', 'Next Six Month PM',
                          'Next Annual PM', 'Status', 'Created Date', 'Updated Date']

                df = pd.DataFrame(equipment_data, columns=columns)
                df.to_csv(file_path, index=False)

                QMessageBox.information(self, "Success", f"Equipment list exported to {file_path}")
                self.status_updated.emit(f"Exported {len(equipment_data)} equipment records")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export equipment list: {str(e)}")
            traceback.print_exc()


class AddEquipmentDialog(QDialog):
    """Dialog for adding new equipment"""

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Add New Equipment")
        self.setModal(True)
        self.resize(500, 400)

        self.init_ui()

    def init_ui(self):
        """Initialize dialog UI"""
        layout = QVBoxLayout()

        # Form fields
        form_layout = QFormLayout()

        self.sap_entry = QLineEdit()
        self.bfm_entry = QLineEdit()
        self.description_entry = QLineEdit()
        self.tool_id_entry = QLineEdit()
        self.location_entry = QLineEdit()
        self.lin_entry = QLineEdit()

        form_layout.addRow("SAP Material No:", self.sap_entry)
        form_layout.addRow("BFM Equipment No:", self.bfm_entry)
        form_layout.addRow("Description:", self.description_entry)
        form_layout.addRow("Tool ID/Drawing No:", self.tool_id_entry)
        form_layout.addRow("Location:", self.location_entry)
        form_layout.addRow("Master LIN:", self.lin_entry)

        layout.addLayout(form_layout)

        # PM Types group
        pm_group = QGroupBox("PM Types")
        pm_layout = QVBoxLayout()

        self.monthly_check = QCheckBox("Monthly PM")
        self.monthly_check.setChecked(True)
        self.six_month_check = QCheckBox("Six Month PM")
        self.six_month_check.setChecked(True)
        self.annual_check = QCheckBox("Annual PM")
        self.annual_check.setChecked(True)

        pm_layout.addWidget(self.monthly_check)
        pm_layout.addWidget(self.six_month_check)
        pm_layout.addWidget(self.annual_check)

        pm_group.setLayout(pm_layout)
        layout.addWidget(pm_group)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_equipment)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setLayout(layout)

    def save_equipment(self):
        """Save new equipment to database"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                INSERT INTO equipment
                (sap_material_no, bfm_equipment_no, description, tool_id_drawing_no,
                 location, master_lin, monthly_pm, six_month_pm, annual_pm)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                self.sap_entry.text().strip() or None,
                self.bfm_entry.text().strip() or None,
                self.description_entry.text().strip() or None,
                self.tool_id_entry.text().strip() or None,
                self.location_entry.text().strip() or None,
                self.lin_entry.text().strip() or None,
                self.monthly_check.isChecked(),
                self.six_month_check.isChecked(),
                self.annual_check.isChecked()
            ))
            self.conn.commit()

            QMessageBox.information(self, "Success", "Equipment added successfully!")
            self.accept()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error", f"Failed to add equipment: {str(e)}")
            traceback.print_exc()


class EditEquipmentDialog(QDialog):
    """Dialog for editing existing equipment"""

    def __init__(self, conn, bfm_no, technicians, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.bfm_no = bfm_no
        self.technicians = technicians
        self.equipment_data = None

        self.setWindowTitle("Edit Equipment")
        self.setModal(True)
        self.resize(500, 600)

        # Load equipment data
        if not self.load_equipment_data():
            return

        self.init_ui()

    def load_equipment_data(self):
        """Load equipment data from database"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('SELECT * FROM equipment WHERE bfm_equipment_no = %s', (self.bfm_no,))
            result = cursor.fetchone()

            if not result:
                QMessageBox.critical(self, "Error", "Equipment not found in database")
                return False

            # Convert to dict for easier access
            columns = [desc[0] for desc in cursor.description]
            self.equipment_data = dict(zip(columns, result))
            return True

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Database error: {str(e)}")
            traceback.print_exc()
            return False

    def init_ui(self):
        """Initialize dialog UI"""
        layout = QVBoxLayout()

        # Form fields
        form_layout = QFormLayout()

        self.sap_entry = QLineEdit(self.equipment_data.get('sap_material_no') or '')
        self.bfm_entry = QLineEdit(self.equipment_data.get('bfm_equipment_no') or '')
        self.bfm_entry.setReadOnly(True)  # Don't allow changing BFM number
        self.description_entry = QLineEdit(self.equipment_data.get('description') or '')
        self.tool_id_entry = QLineEdit(self.equipment_data.get('tool_id_drawing_no') or '')
        self.location_entry = QLineEdit(self.equipment_data.get('location') or '')
        self.lin_entry = QLineEdit(self.equipment_data.get('master_lin') or '')

        form_layout.addRow("SAP Material No:", self.sap_entry)
        form_layout.addRow("BFM Equipment No:", self.bfm_entry)
        form_layout.addRow("Description:", self.description_entry)
        form_layout.addRow("Tool ID/Drawing No:", self.tool_id_entry)
        form_layout.addRow("Location:", self.location_entry)
        form_layout.addRow("Master LIN:", self.lin_entry)

        layout.addLayout(form_layout)

        # PM Types & Equipment Status group
        pm_group = QGroupBox("PM Types & Equipment Status")
        pm_layout = QVBoxLayout()

        # Current status
        current_status = self.equipment_data.get('status') or 'Active'

        # PM checkboxes
        self.monthly_check = QCheckBox("Monthly PM")
        self.monthly_check.setChecked(bool(self.equipment_data.get('monthly_pm')))

        self.six_month_check = QCheckBox("Six Month PM")
        self.six_month_check.setChecked(bool(self.equipment_data.get('six_month_pm')))

        self.annual_check = QCheckBox("Annual PM")
        self.annual_check.setChecked(bool(self.equipment_data.get('annual_pm')))

        pm_layout.addWidget(self.monthly_check)
        pm_layout.addWidget(self.six_month_check)
        pm_layout.addWidget(self.annual_check)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        pm_layout.addWidget(separator)

        # Run to Failure option
        self.rtf_check = QCheckBox("Set as Run to Failure Equipment")
        self.rtf_check.setChecked(current_status == 'Run to Failure')
        self.rtf_check.stateChanged.connect(self.toggle_status_options)
        pm_layout.addWidget(self.rtf_check)

        self.rtf_warning = QLabel("Status: Will be set to Run to Failure")
        self.rtf_warning.setStyleSheet("color: red; font-style: italic;")
        self.rtf_warning.setVisible(current_status == 'Run to Failure')
        pm_layout.addWidget(self.rtf_warning)

        # Cannot Find option
        self.cf_check = QCheckBox("Mark as Cannot Find")
        self.cf_check.setChecked(current_status == 'Cannot Find')
        self.cf_check.stateChanged.connect(self.toggle_status_options)
        pm_layout.addWidget(self.cf_check)

        self.cf_warning = QLabel("Status: Will be set to Cannot Find (PMs disabled)")
        self.cf_warning.setStyleSheet("color: red; font-style: italic;")
        self.cf_warning.setVisible(current_status == 'Cannot Find')
        pm_layout.addWidget(self.cf_warning)

        # Technician selection for Cannot Find
        tech_frame = QWidget()
        tech_layout = QHBoxLayout()
        tech_layout.setContentsMargins(20, 0, 0, 0)
        tech_layout.addWidget(QLabel("Reported By:"))
        self.tech_combo = QComboBox()
        self.tech_combo.addItems(self.technicians)
        tech_layout.addWidget(self.tech_combo)
        tech_frame.setLayout(tech_layout)
        pm_layout.addWidget(tech_frame)

        self.tech_frame = tech_frame
        self.tech_frame.setVisible(current_status == 'Cannot Find')

        # Pre-populate technician if asset is already Cannot Find
        if current_status == 'Cannot Find':
            try:
                cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
                cursor.execute('''
                    SELECT technician_name
                    FROM cannot_find_assets
                    WHERE bfm_equipment_no = %s
                ''', (self.bfm_no,))
                cf_data = cursor.fetchone()
                if cf_data:
                    index = self.tech_combo.findText(cf_data[0])
                    if index >= 0:
                        self.tech_combo.setCurrentIndex(index)
            except Exception as e:
                print(f"Warning: Could not fetch technician data: {e}")

        # Current status label
        status_label = QLabel(f"Current Status: {current_status}")
        status_label.setStyleSheet("font-style: italic;")
        pm_layout.addWidget(status_label)

        # Note
        note_label = QLabel("Run to Failure and Cannot Find equipment will not be scheduled for PMs")
        note_label.setStyleSheet("color: orange; font-size: 9pt;")
        pm_layout.addWidget(note_label)

        pm_group.setLayout(pm_layout)
        layout.addWidget(pm_group)

        # Disable PM checkboxes if currently Cannot Find or Run to Failure
        if current_status in ['Run to Failure', 'Cannot Find']:
            self.monthly_check.setEnabled(False)
            self.six_month_check.setEnabled(False)
            self.annual_check.setEnabled(False)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.update_equipment)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setLayout(layout)

    def toggle_status_options(self):
        """Enable/disable options based on status selections"""
        # Cannot select both Run to Failure and Cannot Find
        if self.rtf_check.isChecked() and self.cf_check.isChecked():
            # If both are checked, uncheck the other one
            sender = self.sender()
            if sender == self.rtf_check:
                self.cf_check.setChecked(False)
            else:
                self.rtf_check.setChecked(False)

        # Update UI based on selections
        if self.rtf_check.isChecked():
            self.monthly_check.setEnabled(False)
            self.six_month_check.setEnabled(False)
            self.annual_check.setEnabled(False)
            self.monthly_check.setChecked(False)
            self.six_month_check.setChecked(False)
            self.annual_check.setChecked(False)
            self.rtf_warning.setVisible(True)
            self.cf_warning.setVisible(False)
            self.tech_frame.setVisible(False)
        elif self.cf_check.isChecked():
            self.monthly_check.setEnabled(False)
            self.six_month_check.setEnabled(False)
            self.annual_check.setEnabled(False)
            self.monthly_check.setChecked(False)
            self.six_month_check.setChecked(False)
            self.annual_check.setChecked(False)
            self.cf_warning.setVisible(True)
            self.rtf_warning.setVisible(False)
            self.tech_frame.setVisible(True)
        else:
            self.monthly_check.setEnabled(True)
            self.six_month_check.setEnabled(True)
            self.annual_check.setEnabled(True)
            self.rtf_warning.setVisible(False)
            self.cf_warning.setVisible(False)
            self.tech_frame.setVisible(False)

    def update_equipment(self):
        """Update equipment in database"""
        try:
            # Determine new status
            if self.rtf_check.isChecked():
                new_status = 'Run to Failure'
            elif self.cf_check.isChecked():
                new_status = 'Cannot Find'
            else:
                new_status = 'Active'

            current_status = self.equipment_data.get('status') or 'Active'

            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Update equipment table
            cursor.execute('''
                UPDATE equipment
                SET sap_material_no = %s,
                    description = %s,
                    tool_id_drawing_no = %s,
                    location = %s,
                    master_lin = %s,
                    monthly_pm = %s,
                    six_month_pm = %s,
                    annual_pm = %s,
                    status = %s
                WHERE bfm_equipment_no = %s
            ''', (
                self.sap_entry.text().strip() or None,
                self.description_entry.text().strip() or None,
                self.tool_id_entry.text().strip() or None,
                self.location_entry.text().strip() or None,
                self.lin_entry.text().strip() or None,
                self.monthly_check.isChecked(),
                self.six_month_check.isChecked(),
                self.annual_check.isChecked(),
                new_status,
                self.bfm_no
            ))

            # Handle Run to Failure status
            if self.rtf_check.isChecked() and current_status != 'Run to Failure':
                # Note: PostgreSQL uses INSERT ... ON CONFLICT, not INSERT OR REPLACE
                cursor.execute('''
                    INSERT INTO run_to_failure_assets
                    (bfm_equipment_no, description, location, technician_name,
                     completion_date, labor_hours, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (bfm_equipment_no) DO UPDATE SET
                        description = EXCLUDED.description,
                        location = EXCLUDED.location,
                        technician_name = EXCLUDED.technician_name,
                        completion_date = EXCLUDED.completion_date,
                        labor_hours = EXCLUDED.labor_hours,
                        notes = EXCLUDED.notes
                ''', (
                    self.bfm_no,
                    self.description_entry.text().strip() or None,
                    self.location_entry.text().strip() or None,
                    'System Change',
                    datetime.now().strftime('%Y-%m-%d'),
                    0.0,
                    'Equipment manually set to Run to Failure status via equipment edit dialog'
                ))

                # Remove from Cannot Find if it was there
                cursor.execute('DELETE FROM cannot_find_assets WHERE bfm_equipment_no = %s',
                             (self.bfm_no,))

            elif not self.rtf_check.isChecked() and current_status == 'Run to Failure':
                cursor.execute('DELETE FROM run_to_failure_assets WHERE bfm_equipment_no = %s',
                             (self.bfm_no,))

            # Handle Cannot Find status
            if self.cf_check.isChecked():
                technician = self.tech_combo.currentText().strip()
                if not technician:
                    QMessageBox.warning(
                        self, "Missing Information",
                        "Please select who is reporting this asset as Cannot Find"
                    )
                    return

                # Add or update in cannot_find_assets table
                cursor.execute('''
                    INSERT INTO cannot_find_assets
                    (bfm_equipment_no, description, location, technician_name,
                     reported_date, status, notes)
                    VALUES (%s, %s, %s, %s, %s, 'Missing', %s)
                    ON CONFLICT (bfm_equipment_no) DO UPDATE SET
                        description = EXCLUDED.description,
                        location = EXCLUDED.location,
                        technician_name = EXCLUDED.technician_name,
                        reported_date = EXCLUDED.reported_date,
                        status = EXCLUDED.status,
                        notes = EXCLUDED.notes
                ''', (
                    self.bfm_no,
                    self.description_entry.text().strip() or None,
                    self.location_entry.text().strip() or None,
                    technician,
                    datetime.now().strftime('%Y-%m-%d'),
                    'Equipment marked as Cannot Find via equipment edit dialog'
                ))

                # Remove from Run to Failure if it was there
                cursor.execute('DELETE FROM run_to_failure_assets WHERE bfm_equipment_no = %s',
                             (self.bfm_no,))

            elif not self.cf_check.isChecked() and current_status == 'Cannot Find':
                # Remove from Cannot Find table
                cursor.execute('DELETE FROM cannot_find_assets WHERE bfm_equipment_no = %s',
                             (self.bfm_no,))

            self.conn.commit()

            # Show appropriate success message
            if self.rtf_check.isChecked():
                success_msg = (
                    f"Equipment {self.bfm_no} updated successfully!\n\n"
                    f"Status changed to: Run to Failure\n"
                    f"- All PM requirements disabled\n"
                    f"- Equipment moved to Run to Failure tab\n"
                    f"- No future PMs will be scheduled"
                )
            elif self.cf_check.isChecked():
                success_msg = (
                    f"Equipment {self.bfm_no} updated successfully!\n\n"
                    f"Status changed to: Cannot Find\n"
                    f"- Reported by: {self.tech_combo.currentText()}\n"
                    f"- Equipment moved to Cannot Find tab\n"
                    f"- All PM requirements disabled\n"
                    f"- No future PMs will be scheduled"
                )
            else:
                success_msg = f"Equipment {self.bfm_no} updated successfully!\n\nStatus: Active"

            QMessageBox.information(self, "Success", success_msg)
            self.accept()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update equipment: {str(e)}")
            traceback.print_exc()


class BulkEditPMCyclesDialog(QDialog):
    """Dialog for bulk editing PM cycles"""

    def __init__(self, conn, selected_bfms, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.selected_bfms = selected_bfms

        self.setWindowTitle("Bulk Edit PM Cycles")
        self.setModal(True)
        self.resize(550, 450)

        self.init_ui()

    def init_ui(self):
        """Initialize dialog UI"""
        layout = QVBoxLayout()

        # Header
        header_label = QLabel("Bulk Edit PM Cycles")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)

        count_label = QLabel(f"Editing {len(self.selected_bfms)} selected asset(s)")
        count_label.setStyleSheet("color: blue;")
        count_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(header_label)
        layout.addWidget(count_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Selected assets list
        assets_group = QGroupBox("Selected Assets")
        assets_layout = QVBoxLayout()

        assets_text = QTextEdit()
        assets_text.setReadOnly(True)
        assets_text.setMaximumHeight(150)

        # Get asset details
        cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
        for i, bfm in enumerate(self.selected_bfms[:20]):  # Show first 20
            cursor.execute('''
                SELECT bfm_equipment_no, description
                FROM equipment
                WHERE bfm_equipment_no = %s
            ''', (bfm,))
            result = cursor.fetchone()
            if result:
                desc = result['description'][:40] if result['description'] else ''
                assets_text.append(f"- {result['bfm_equipment_no']} - {desc}")

        if len(self.selected_bfms) > 20:
            assets_text.append(f"\n... and {len(self.selected_bfms) - 20} more assets")

        assets_layout.addWidget(assets_text)
        assets_group.setLayout(assets_layout)
        layout.addWidget(assets_group)

        # PM Cycle options
        pm_group = QGroupBox("PM Cycle Settings")
        pm_layout = QVBoxLayout()

        pm_label = QLabel("Select which PM cycles to apply:")
        pm_label_font = QFont()
        pm_label_font.setBold(True)
        pm_label.setFont(pm_label_font)
        pm_layout.addWidget(pm_label)

        self.monthly_check = QCheckBox("Monthly PM (every 30 days)")
        self.six_month_check = QCheckBox("Six Month PM (every 180 days)")
        self.annual_check = QCheckBox("Annual PM (every 365 days)")
        self.annual_check.setChecked(True)  # Default to Annual

        pm_layout.addWidget(self.monthly_check)
        pm_layout.addWidget(self.six_month_check)
        pm_layout.addWidget(self.annual_check)

        note_label = QLabel("Note: Unchecked cycles will be DISABLED for selected assets.")
        note_label.setStyleSheet("color: gray; font-size: 9pt;")
        pm_layout.addWidget(note_label)

        pm_group.setLayout(pm_layout)
        layout.addWidget(pm_group)

        # Buttons
        button_box = QDialogButtonBox()
        apply_btn = button_box.addButton("Apply to All Selected", QDialogButtonBox.AcceptRole)
        cancel_btn = button_box.addButton("Cancel", QDialogButtonBox.RejectRole)

        button_box.accepted.connect(self.apply_changes)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setLayout(layout)

    def apply_changes(self):
        """Apply PM cycle changes to all selected assets"""
        try:
            monthly_pm = self.monthly_check.isChecked()
            six_month_pm = self.six_month_check.isChecked()
            annual_pm = self.annual_check.isChecked()

            # Confirm action
            pm_types = []
            if monthly_pm:
                pm_types.append("Monthly")
            if six_month_pm:
                pm_types.append("Six Month")
            if annual_pm:
                pm_types.append("Annual")

            if not pm_types:
                result = QMessageBox.question(
                    self,
                    "Warning - No PM Cycles Selected",
                    f"You are about to DISABLE ALL PM cycles for {len(self.selected_bfms)} asset(s).\n\n"
                    f"This means these assets will NOT be scheduled for any preventive maintenance.\n\n"
                    f"Are you sure you want to continue?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
            else:
                pm_list = ", ".join(pm_types)
                result = QMessageBox.question(
                    self,
                    "Confirm Changes",
                    f"Apply the following PM cycles to {len(self.selected_bfms)} asset(s)?\n\n"
                    f"PM Cycles: {pm_list}\n\n"
                    f"This will update all selected assets.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

            if result != QMessageBox.Yes:
                return

            # Apply changes
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            updated_count = 0

            for bfm in self.selected_bfms:
                cursor.execute('''
                    UPDATE equipment
                    SET monthly_pm = %s, six_month_pm = %s, annual_pm = %s
                    WHERE bfm_equipment_no = %s
                ''', (monthly_pm, six_month_pm, annual_pm, bfm))

                if cursor.rowcount > 0:
                    updated_count += 1

            self.conn.commit()

            # Success message
            QMessageBox.information(
                self,
                "Success",
                f"Successfully updated PM cycles for {updated_count} asset(s)!"
            )

            self.accept()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update PM cycles:\n\n{str(e)}")
            traceback.print_exc()


class CSVMappingDialog(QDialog):
    """Dialog for mapping CSV columns to database fields"""

    def __init__(self, conn, file_path, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.file_path = file_path
        self.mappings = {}

        self.setWindowTitle("Map CSV Columns to Database Fields")
        self.setModal(True)
        self.resize(700, 600)

        # Read CSV to get column headers
        try:
            df = pd.read_csv(file_path, encoding='cp1252', nrows=5)
            self.csv_columns = list(df.columns)
            self.sample_df = df
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read CSV file: {str(e)}")
            self.reject()
            return

        self.init_ui()

    def init_ui(self):
        """Initialize dialog UI"""
        main_layout = QVBoxLayout()

        # Instructions
        instructions = QLabel("Map your CSV columns to the correct database fields:")
        instructions_font = QFont()
        instructions_font.setPointSize(12)
        instructions_font.setBold(True)
        instructions.setFont(instructions_font)
        main_layout.addWidget(instructions)

        # Create scroll area for mappings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Mapping fields
        form_layout = QFormLayout()

        # Database fields that can be mapped
        db_fields = [
            ("SAP Material No", "sap_material_no"),
            ("BFM Equipment No", "bfm_equipment_no"),
            ("Description", "description"),
            ("Tool ID/Drawing No", "tool_id_drawing_no"),
            ("Location", "location"),
            ("Master LIN", "master_lin"),
            ("Last Monthly PM (YYYY-MM-DD)", "last_monthly_pm"),
            ("Last Six Month PM (YYYY-MM-DD)", "last_six_month_pm"),
            ("Last Annual PM (YYYY-MM-DD)", "last_annual_pm"),
            ("Monthly PM Required (1/0 or Y/N)", "monthly_pm"),
            ("Six Month PM Required (1/0 or Y/N)", "six_month_pm"),
            ("Annual PM Required (1/0 or Y/N)", "annual_pm")
        ]

        # Add "None" option to CSV columns
        csv_options = ["(Not in CSV)"] + self.csv_columns

        for field_name, field_key in db_fields:
            combo = QComboBox()
            combo.addItems(csv_options)

            # Try to auto-match common column names
            for csv_col in self.csv_columns:
                csv_lower = csv_col.lower()
                matched = False

                if field_key == 'sap_material_no' and 'sap' in csv_lower:
                    matched = True
                elif field_key == 'bfm_equipment_no' and 'bfm' in csv_lower:
                    matched = True
                elif field_key == 'description' and 'description' in csv_lower:
                    matched = True
                elif field_key == 'location' and 'location' in csv_lower:
                    matched = True
                elif field_key == 'master_lin' and 'lin' in csv_lower:
                    matched = True

                if matched:
                    index = combo.findText(csv_col)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                    break

            form_layout.addRow(field_name + ":", combo)
            self.mappings[field_key] = combo

        scroll_layout.addLayout(form_layout)

        # Sample data display
        sample_group = QGroupBox("Sample Data from Your CSV")
        sample_layout = QVBoxLayout()

        sample_text = QTextEdit()
        sample_text.setReadOnly(True)
        sample_text.setMaximumHeight(120)
        sample_text.setPlainText(self.sample_df.to_string())

        sample_layout.addWidget(sample_text)
        sample_group.setLayout(sample_layout)
        scroll_layout.addWidget(sample_group)

        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # Buttons
        button_box = QDialogButtonBox()
        import_btn = button_box.addButton("Import with These Mappings", QDialogButtonBox.AcceptRole)
        cancel_btn = button_box.addButton("Cancel", QDialogButtonBox.RejectRole)

        button_box.accepted.connect(self.process_import)
        button_box.rejected.connect(self.reject)

        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def process_import(self):
        """Process the import with mapped columns"""
        try:
            # Get the full CSV data
            full_df = pd.read_csv(self.file_path, encoding='cp1252')
            full_df.columns = full_df.columns.str.strip()

            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            imported_count = 0
            error_count = 0

            for index, row in full_df.iterrows():
                try:
                    # Extract mapped data
                    data = {}
                    for field_key, combo in self.mappings.items():
                        csv_column = combo.currentText()
                        if csv_column != "(Not in CSV)" and csv_column in full_df.columns:
                            value = row[csv_column]
                            if pd.isna(value):
                                data[field_key] = None
                            else:
                                # Handle different data types
                                if field_key in ['monthly_pm', 'six_month_pm', 'annual_pm']:
                                    # Convert Y/N or 1/0 to boolean
                                    if str(value).upper() in ['Y', 'YES', '1', 'TRUE']:
                                        data[field_key] = True
                                    else:
                                        data[field_key] = False
                                elif field_key in ['last_monthly_pm', 'last_six_month_pm', 'last_annual_pm']:
                                    # Handle date fields
                                    try:
                                        parsed_date = pd.to_datetime(value).strftime('%Y-%m-%d')
                                        data[field_key] = parsed_date
                                    except:
                                        data[field_key] = None
                                else:
                                    data[field_key] = str(value)
                        else:
                            # Set defaults for unmapped fields
                            if field_key in ['monthly_pm', 'six_month_pm', 'annual_pm']:
                                data[field_key] = True  # Default to requiring all PM types
                            else:
                                data[field_key] = None

                    # Only import if BFM number exists
                    if data.get('bfm_equipment_no'):
                        cursor.execute('''
                            INSERT INTO equipment
                            (sap_material_no, bfm_equipment_no, description, tool_id_drawing_no, location,
                            master_lin, monthly_pm, six_month_pm, annual_pm, last_monthly_pm,
                            last_six_month_pm, last_annual_pm, next_monthly_pm, next_six_month_pm, next_annual_pm)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                CASE WHEN %s IS NOT NULL THEN %s::date + INTERVAL '30 days' ELSE NULL END,
                                CASE WHEN %s IS NOT NULL THEN %s::date + INTERVAL '180 days' ELSE NULL END,
                                CASE WHEN %s IS NOT NULL THEN %s::date + INTERVAL '365 days' ELSE NULL END)
                            ON CONFLICT (bfm_equipment_no) DO UPDATE SET
                                sap_material_no = EXCLUDED.sap_material_no,
                                description = EXCLUDED.description,
                                tool_id_drawing_no = EXCLUDED.tool_id_drawing_no,
                                location = EXCLUDED.location,
                                master_lin = EXCLUDED.master_lin,
                                monthly_pm = EXCLUDED.monthly_pm,
                                six_month_pm = EXCLUDED.six_month_pm,
                                annual_pm = EXCLUDED.annual_pm,
                                last_monthly_pm = EXCLUDED.last_monthly_pm,
                                last_six_month_pm = EXCLUDED.last_six_month_pm,
                                last_annual_pm = EXCLUDED.last_annual_pm,
                                next_monthly_pm = EXCLUDED.next_monthly_pm,
                                next_six_month_pm = EXCLUDED.next_six_month_pm,
                                next_annual_pm = EXCLUDED.next_annual_pm
                        ''', (
                            data.get('sap_material_no'),
                            data.get('bfm_equipment_no'),
                            data.get('description'),
                            data.get('tool_id_drawing_no'),
                            data.get('location'),
                            data.get('master_lin'),
                            data.get('monthly_pm', True),
                            data.get('six_month_pm', True),
                            data.get('annual_pm', True),
                            data.get('last_monthly_pm'),
                            data.get('last_six_month_pm'),
                            data.get('last_annual_pm'),
                            data.get('last_monthly_pm'),
                            data.get('last_monthly_pm'),
                            data.get('last_six_month_pm'),
                            data.get('last_six_month_pm'),
                            data.get('last_annual_pm'),
                            data.get('last_annual_pm')
                        ))
                        imported_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    print(f"Error importing row {index}: {e}")
                    error_count += 1
                    continue

            self.conn.commit()

            # Show results
            result_msg = f"Import completed!\n\n"
            result_msg += f"Successfully imported: {imported_count} records\n"
            if error_count > 0:
                result_msg += f"Skipped (errors): {error_count} records\n"
            result_msg += f"\nTotal processed: {imported_count + error_count} records"

            QMessageBox.information(self, "Import Results", result_msg)
            self.accept()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error", f"Failed to process import: {str(e)}")
            traceback.print_exc()
