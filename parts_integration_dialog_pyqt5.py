"""
CM Parts Integration Dialog - PyQt5 Implementation
Handles parts consumption tracking for Corrective Maintenance work orders
Complete port from Tkinter to PyQt5
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QMessageBox, QHeaderView, QGroupBox,
    QFormLayout, QFrame, QAbstractItemView, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
from psycopg2 import extras


class CMPartsIntegrationDialog(QDialog):
    """Dialog for recording parts consumed during corrective maintenance"""

    parts_saved = pyqtSignal(bool)  # Signal emitted when parts are saved

    def __init__(self, cm_number, technician_name, conn, parent=None):
        """
        Initialize Parts Integration Dialog

        Args:
            cm_number: The CM work order number
            technician_name: Name of technician performing the work
            conn: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.cm_number = cm_number
        self.technician_name = technician_name
        self.conn = conn
        self.all_parts_data = []
        self.consumed_parts = []

        self.setWindowTitle(f"Parts Consumption - CM {cm_number}")
        self.setMinimumSize(950, 750)
        self.setModal(True)

        self.init_ui()
        self.load_mro_parts()

    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # Header Section
        header_frame = self.create_header()
        main_layout.addWidget(header_frame)

        # Search Section
        search_frame = self.create_search_section()
        main_layout.addWidget(search_frame)

        # Available Parts Section
        parts_group = self.create_available_parts_section()
        main_layout.addWidget(parts_group)

        # Entry Section for Adding Parts
        entry_group = self.create_entry_section()
        main_layout.addWidget(entry_group)

        # Consumed Parts List
        consumed_group = self.create_consumed_parts_section()
        main_layout.addWidget(consumed_group)

        # Bottom Buttons
        button_frame = self.create_button_frame()
        main_layout.addWidget(button_frame)

        self.setLayout(main_layout)

    def create_header(self):
        """Create header section"""
        frame = QFrame()
        layout = QVBoxLayout()

        # Title
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label = QLabel(f"MRO Parts Consumption - CM {self.cm_number} - Technician: {self.technician_name}")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Subtitle
        subtitle_font = QFont()
        subtitle_font.setPointSize(9)
        subtitle_label = QLabel("Select parts consumed from MRO stock during this corrective maintenance.")
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: gray;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle_label)

        frame.setLayout(layout)
        return frame

    def create_search_section(self):
        """Create search section"""
        frame = QFrame()
        layout = QHBoxLayout()

        # Search label
        search_label = QLabel("Search:")
        search_label_font = QFont()
        search_label_font.setPointSize(10)
        search_label_font.setBold(True)
        search_label.setFont(search_label_font)
        layout.addWidget(search_label)

        # Search entry
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Enter part number or description...")
        self.search_entry.textChanged.connect(self.filter_parts)
        layout.addWidget(self.search_entry)

        # Help text
        help_label = QLabel("(by part number or description)")
        help_font = QFont()
        help_font.setPointSize(9)
        help_font.setItalic(True)
        help_label.setFont(help_font)
        help_label.setStyleSheet("color: gray;")
        layout.addWidget(help_label)

        frame.setLayout(layout)
        return frame

    def create_available_parts_section(self):
        """Create available parts section with legend"""
        group = QGroupBox("Available MRO Stock Parts")
        layout = QVBoxLayout()

        # Legend
        legend_frame = QFrame()
        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(5, 2, 5, 2)

        legend_title = QLabel("Legend:")
        legend_font = QFont()
        legend_font.setPointSize(9)
        legend_font.setBold(True)
        legend_title.setFont(legend_font)
        legend_layout.addWidget(legend_title)

        in_stock_label = QLabel("● In Stock")
        in_stock_label.setStyleSheet("color: black;")
        legend_layout.addWidget(in_stock_label)

        low_stock_label = QLabel("● Low Stock")
        low_stock_label.setStyleSheet("color: orange;")
        legend_layout.addWidget(low_stock_label)

        out_stock_label = QLabel("● Out of Stock")
        out_stock_label.setStyleSheet("color: gray; font-style: italic;")
        legend_layout.addWidget(out_stock_label)

        legend_layout.addStretch()
        legend_frame.setLayout(legend_layout)
        layout.addWidget(legend_frame)

        # Parts Table
        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(4)
        self.parts_table.setHorizontalHeaderLabels(['Part Number', 'Description', 'Location', 'Qty Available'])
        self.parts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.parts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.parts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.parts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.parts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.parts_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.parts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.parts_table.itemSelectionChanged.connect(self.on_part_select)

        layout.addWidget(self.parts_table)
        group.setLayout(layout)
        return group

    def create_entry_section(self):
        """Create entry section for adding consumed parts"""
        group = QGroupBox("Add Parts Consumed")
        layout = QFormLayout()

        # Selected Part Label
        self.selected_part_label = QLabel("(Select a part from list above)")
        self.selected_part_label.setStyleSheet("color: gray;")
        layout.addRow("Selected Part:", self.selected_part_label)

        # Quantity Entry
        self.qty_entry = QLineEdit()
        self.qty_entry.setText("1")
        self.qty_entry.setMaximumWidth(200)
        layout.addRow("Quantity Used:", self.qty_entry)

        # Buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("Add to Consumed List")
        add_btn.clicked.connect(self.add_consumed_part)
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_consumed_part)
        button_layout.addWidget(remove_btn)

        button_layout.addStretch()
        layout.addRow("", button_layout)

        group.setLayout(layout)
        return group

    def create_consumed_parts_section(self):
        """Create consumed parts list section"""
        group = QGroupBox("Parts to be Consumed")
        layout = QVBoxLayout()

        # Consumed Parts Table
        self.consumed_table = QTableWidget()
        self.consumed_table.setColumnCount(3)
        self.consumed_table.setHorizontalHeaderLabels(['Part Number', 'Description', 'Qty Used'])
        self.consumed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.consumed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.consumed_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.consumed_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.consumed_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.consumed_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.consumed_table.setMaximumHeight(150)

        layout.addWidget(self.consumed_table)
        group.setLayout(layout)
        return group

    def create_button_frame(self):
        """Create bottom button frame"""
        frame = QFrame()
        layout = QHBoxLayout()

        save_btn = QPushButton("Save and Complete")
        save_btn.setMinimumWidth(150)
        save_btn.clicked.connect(self.save_and_close)
        layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(150)
        cancel_btn.clicked.connect(self.cancel_dialog)
        layout.addWidget(cancel_btn)

        layout.addStretch()
        frame.setLayout(layout)
        return frame

    def load_mro_parts(self):
        """Load all MRO parts from inventory"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT part_number, name, location, quantity_in_stock
                FROM mro_inventory
                WHERE status = 'Active'
                ORDER BY part_number
            ''')

            self.all_parts_data = cursor.fetchall()
            self.filter_parts()  # Display all parts initially

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load MRO inventory: {str(e)}")

    def filter_parts(self):
        """Filter parts based on search term"""
        search_term = self.search_entry.text().lower().strip()

        # Clear table
        self.parts_table.setRowCount(0)

        # Filter and display parts
        for part in self.all_parts_data:
            part_number = str(part[0]).lower()
            description = str(part[1]).lower()
            qty_available = float(part[3]) if part[3] else 0.0

            # Show part if search term matches
            if not search_term or search_term in part_number or search_term in description:
                row = self.parts_table.rowCount()
                self.parts_table.insertRow(row)

                # Add items
                self.parts_table.setItem(row, 0, QTableWidgetItem(str(part[0])))
                self.parts_table.setItem(row, 1, QTableWidgetItem(str(part[1])))
                self.parts_table.setItem(row, 2, QTableWidgetItem(str(part[2]) if part[2] else ""))
                self.parts_table.setItem(row, 3, QTableWidgetItem(f"{qty_available:.2f}"))

                # Apply color coding based on stock level
                if qty_available <= 0:
                    color = QColor('gray')
                    font = QFont()
                    font.setItalic(True)
                elif qty_available <= 5:
                    color = QColor('orange')
                    font = QFont()
                else:
                    color = QColor('black')
                    font = QFont()

                for col in range(4):
                    item = self.parts_table.item(row, col)
                    item.setForeground(color)
                    if qty_available <= 0:
                        item.setFont(font)

    def on_part_select(self):
        """Update selected part label when user selects from available parts"""
        selected_items = self.parts_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            part_num = self.parts_table.item(row, 0).text()
            desc = self.parts_table.item(row, 1).text()
            self.selected_part_label.setText(f"{part_num} - {desc}")
            self.selected_part_label.setStyleSheet("color: black;")

    def add_consumed_part(self):
        """Add selected part to consumed list"""
        selected_items = self.parts_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a part from the available parts list")
            return

        try:
            qty_used = float(self.qty_entry.text())
            if qty_used <= 0:
                QMessageBox.critical(self, "Error", "Quantity must be greater than 0")
                return
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid quantity value")
            return

        row = selected_items[0].row()
        part_num = self.parts_table.item(row, 0).text()
        desc = self.parts_table.item(row, 1).text()
        qty_available = float(self.parts_table.item(row, 3).text())

        # Check stock availability
        if qty_available <= 0:
            QMessageBox.critical(self, "Part Out of Stock",
                                f"Part {part_num} is currently out of stock.\n\n"
                                f"Available quantity: {qty_available}\n"
                                f"Please replenish stock before recording consumption.")
            return

        if qty_used > qty_available:
            QMessageBox.critical(self, "Insufficient Stock",
                                f"Quantity used ({qty_used}) exceeds available quantity ({qty_available})\n\n"
                                f"Part: {part_num}\n"
                                f"Please adjust the quantity or replenish stock.")
            return

        # Check if part already added
        for existing in self.consumed_parts:
            if existing['part_number'] == part_num:
                QMessageBox.warning(self, "Warning",
                                   "This part is already in the consumed list. Remove it first if you need to change the quantity.")
                return

        # Add to consumed list
        self.consumed_parts.append({
            'part_number': part_num,
            'description': desc,
            'quantity': qty_used
        })

        # Update consumed table
        consumed_row = self.consumed_table.rowCount()
        self.consumed_table.insertRow(consumed_row)
        self.consumed_table.setItem(consumed_row, 0, QTableWidgetItem(part_num))
        self.consumed_table.setItem(consumed_row, 1, QTableWidgetItem(desc))
        self.consumed_table.setItem(consumed_row, 2, QTableWidgetItem(f"{qty_used:.2f}"))

        # Reset quantity entry
        self.qty_entry.setText("1")
        QMessageBox.information(self, "Success", f"Added {part_num} to consumed parts list")

    def remove_consumed_part(self):
        """Remove selected part from consumed list"""
        selected_items = self.consumed_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a part to remove from the consumed list")
            return

        row = selected_items[0].row()
        part_num = self.consumed_table.item(row, 0).text()

        # Remove from list
        self.consumed_parts = [p for p in self.consumed_parts if p['part_number'] != part_num]

        # Remove from table
        self.consumed_table.removeRow(row)

    def save_and_close(self):
        """Save consumed parts to database and close dialog"""
        if not self.consumed_parts:
            reply = QMessageBox.question(self, "Confirm",
                                        "No parts were added to the consumed list. Continue without recording parts?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
            self.parts_saved.emit(True)
            self.accept()
            return

        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Record each consumed part
            for part in self.consumed_parts:
                # Get unit price for cost calculation
                cursor.execute('''
                    SELECT unit_price FROM mro_inventory WHERE part_number = %s
                ''', (part['part_number'],))
                result = cursor.fetchone()
                unit_price = float(result[0]) if result and result[0] else 0.0
                total_cost = unit_price * part['quantity']

                # Create transaction record
                cursor.execute('''
                    INSERT INTO mro_stock_transactions
                    (part_number, transaction_type, quantity, technician_name, notes, transaction_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (
                    part['part_number'],
                    'Issue',
                    -part['quantity'],  # Negative for consumption
                    self.technician_name,
                    f"CM Work Order: {self.cm_number}",
                    datetime.now()
                ))

                # Record in cm_parts_used table for tracking and reporting
                cursor.execute('''
                    INSERT INTO cm_parts_used
                    (cm_number, part_number, quantity_used, total_cost, recorded_date, recorded_by, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    self.cm_number,
                    part['part_number'],
                    part['quantity'],
                    total_cost,
                    datetime.now(),
                    self.technician_name,
                    f"Parts consumed during CM {self.cm_number}"
                ))

                # Update inventory quantity
                cursor.execute('''
                    UPDATE mro_inventory
                    SET quantity_in_stock = quantity_in_stock - %s,
                        last_updated = %s
                    WHERE part_number = %s
                ''', (part['quantity'], datetime.now(), part['part_number']))

            self.conn.commit()

            QMessageBox.information(self, "Success",
                                   f"Successfully recorded {len(self.consumed_parts)} part(s) consumed for CM {self.cm_number}")
            self.parts_saved.emit(True)
            self.accept()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error", f"Failed to record parts consumption: {str(e)}")
            self.parts_saved.emit(False)

    def cancel_dialog(self):
        """Cancel without saving"""
        if self.consumed_parts:
            reply = QMessageBox.question(self, "Confirm",
                                        "Parts have been added but not saved. Cancel without saving?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.parts_saved.emit(False)
        self.reject()


class CMPartsViewDialog(QDialog):
    """Read-only view of parts consumed for a specific CM"""

    def __init__(self, cm_number, conn, parent=None):
        """
        Initialize Parts View Dialog

        Args:
            cm_number: The CM work order number to view parts for
            conn: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.cm_number = cm_number
        self.conn = conn

        self.setWindowTitle(f"Parts Used - CM {cm_number}")
        self.setMinimumSize(800, 500)
        self.setModal(True)

        self.init_ui()
        self.load_parts_data()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()

        # Header
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header_label = QLabel(f"Parts Consumed - CM {self.cm_number}")
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        # Parts table
        parts_group = QGroupBox("Parts Details")
        parts_layout = QVBoxLayout()

        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(6)
        self.parts_table.setHorizontalHeaderLabels([
            'Part Number', 'Description', 'Qty Used', 'Cost', 'Date', 'Recorded By'
        ])
        self.parts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.parts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.parts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.parts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.parts_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.parts_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.parts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.parts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        parts_layout.addWidget(self.parts_table)
        parts_group.setLayout(parts_layout)
        layout.addWidget(parts_group)

        # Summary section
        self.summary_label = QLabel()
        summary_font = QFont()
        summary_font.setPointSize(11)
        summary_font.setBold(True)
        self.summary_label.setFont(summary_font)
        self.summary_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.summary_label)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def load_parts_data(self):
        """Load parts data from database"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT
                    cp.part_number,
                    mi.name,
                    cp.quantity_used,
                    cp.total_cost,
                    cp.recorded_date,
                    cp.recorded_by,
                    cp.notes
                FROM cm_parts_used cp
                LEFT JOIN mro_inventory mi ON cp.part_number = mi.part_number
                WHERE cp.cm_number = %s
                ORDER BY cp.recorded_date DESC
            ''', (self.cm_number,))

            parts_data = cursor.fetchall()
            total_cost = 0.0

            if not parts_data:
                QMessageBox.information(self, "No Data", "No parts recorded for this CM")
                return

            # Populate table
            self.parts_table.setRowCount(len(parts_data))
            for row, part in enumerate(parts_data):
                part_number = part[0]
                description = part[1] if part[1] else "N/A"
                qty_used = f"{part[2]:.2f}" if part[2] else "0"
                cost = part[3] if part[3] else 0.0
                total_cost += cost
                date_recorded = str(part[4])[:19] if part[4] else "N/A"
                recorded_by = part[5] if part[5] else "N/A"

                self.parts_table.setItem(row, 0, QTableWidgetItem(part_number))
                self.parts_table.setItem(row, 1, QTableWidgetItem(description))
                self.parts_table.setItem(row, 2, QTableWidgetItem(qty_used))
                self.parts_table.setItem(row, 3, QTableWidgetItem(f"${cost:.2f}"))
                self.parts_table.setItem(row, 4, QTableWidgetItem(date_recorded))
                self.parts_table.setItem(row, 5, QTableWidgetItem(recorded_by))

            # Update summary
            self.summary_label.setText(f"Total Cost: ${total_cost:.2f}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load parts data: {str(e)}")


# Convenience functions for compatibility
def show_parts_consumption_dialog(cm_number, technician_name, conn, parent=None):
    """
    Show parts consumption dialog for a CM work order

    Args:
        cm_number: The CM work order number
        technician_name: Name of technician performing the work
        conn: Database connection
        parent: Parent widget

    Returns:
        Dialog instance
    """
    dialog = CMPartsIntegrationDialog(cm_number, technician_name, conn, parent)
    return dialog


def show_cm_parts_details(cm_number, conn, parent=None):
    """
    Show read-only view of parts consumed for a specific CM

    Args:
        cm_number: The CM work order number to view parts for
        conn: Database connection
        parent: Parent widget

    Returns:
        Dialog instance
    """
    dialog = CMPartsViewDialog(cm_number, conn, parent)
    return dialog
