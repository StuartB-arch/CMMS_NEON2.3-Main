"""
MRO Stock Management Tab - PyQt5 Implementation
Complete port from mro_stock_module.py Tkinter version

This module provides a comprehensive MRO (Maintenance, Repair, Operations) Stock
Management interface with the following features:

- Complete inventory management with search and filtering
- Add, Edit, and Delete parts with picture upload support
- Stock transaction tracking (add, remove, consume)
- Transaction history for each part
- CM (Corrective Maintenance) parts usage integration
- CSV Import/Export with column mapping
- Low stock alerts and notifications
- Comprehensive stock reports
- Statistics dashboard (total items, total value, low stock items)
- Multi-column sorting capability
- Location/Rack/Bin organization
- Supplier tracking
- Real-time stock level calculations

Database Tables:
- mro_inventory: Main parts inventory table
- mro_stock_transactions: Stock movement tracking
- cm_parts_used: Parts used in corrective maintenance
"""

from psycopg2 import extras
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QDialog, QFormLayout,
    QMessageBox, QFileDialog, QGroupBox, QHeaderView, QTextEdit,
    QScrollArea, QFrame, QAbstractItemView, QSpinBox, QDoubleSpinBox,
    QTabWidget, QDialogButtonBox, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QByteArray
from PyQt5.QtGui import QFont, QColor, QPixmap, QImage
from datetime import datetime
import traceback
import csv
import os
import io


class AddEditPartDialog(QDialog):
    """Dialog for adding or editing MRO parts"""

    def __init__(self, conn, part_data=None, parent=None):
        """
        Initialize dialog

        Args:
            conn: Database connection
            part_data: Dictionary of part data for editing (None for new part)
            parent: Parent widget
        """
        super().__init__(parent)
        self.conn = conn
        self.part_data = part_data
        self.is_edit_mode = part_data is not None

        self.picture_1_data = None
        self.picture_2_data = None

        # If editing, preserve existing pictures
        if self.is_edit_mode and part_data:
            self.picture_1_data = part_data.get('picture_1_data')
            self.picture_2_data = part_data.get('picture_2_data')

        self.setWindowTitle("Edit Part" if self.is_edit_mode else "Add New Part")
        self.setMinimumSize(800, 900)
        self.setup_ui()

        if self.is_edit_mode:
            self.populate_fields()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Create scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # Basic Information Section
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(10)

        self.name_edit = QLineEdit()
        self.part_number_edit = QLineEdit()
        if self.is_edit_mode:
            self.part_number_edit.setReadOnly(True)  # Don't allow changing part number
        self.model_number_edit = QLineEdit()
        self.equipment_edit = QLineEdit()

        basic_layout.addRow("Name*:", self.name_edit)
        basic_layout.addRow("Part Number*:", self.part_number_edit)
        basic_layout.addRow("Model Number:", self.model_number_edit)
        basic_layout.addRow("Equipment:", self.equipment_edit)

        basic_group.setLayout(basic_layout)
        scroll_layout.addWidget(basic_group)

        # Stock Information Section
        stock_group = QGroupBox("Stock Information")
        stock_layout = QFormLayout()
        stock_layout.setSpacing(10)

        self.engineering_system_combo = QComboBox()
        self.engineering_system_combo.addItems([
            '', 'Mechanical', 'Electrical', 'Pneumatic', 'Hydraulic', 'Other'
        ])

        self.unit_of_measure_edit = QLineEdit()
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0, 999999)
        self.quantity_spin.setDecimals(2)

        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setRange(0, 999999)
        self.unit_price_spin.setDecimals(2)
        self.unit_price_spin.setPrefix("$ ")

        self.minimum_stock_spin = QDoubleSpinBox()
        self.minimum_stock_spin.setRange(0, 999999)
        self.minimum_stock_spin.setDecimals(2)

        self.supplier_edit = QLineEdit()

        stock_layout.addRow("Engineering System*:", self.engineering_system_combo)
        stock_layout.addRow("Unit of Measure*:", self.unit_of_measure_edit)
        stock_layout.addRow("Quantity in Stock*:", self.quantity_spin)
        stock_layout.addRow("Unit Price:", self.unit_price_spin)
        stock_layout.addRow("Minimum Stock*:", self.minimum_stock_spin)
        stock_layout.addRow("Supplier:", self.supplier_edit)

        stock_group.setLayout(stock_layout)
        scroll_layout.addWidget(stock_group)

        # Location Information Section
        location_group = QGroupBox("Location Information")
        location_layout = QFormLayout()
        location_layout.setSpacing(10)

        self.location_edit = QLineEdit()
        self.rack_edit = QLineEdit()
        self.row_edit = QLineEdit()
        self.bin_edit = QLineEdit()

        location_layout.addRow("Location*:", self.location_edit)
        location_layout.addRow("Rack:", self.rack_edit)
        location_layout.addRow("Row:", self.row_edit)
        location_layout.addRow("Bin:", self.bin_edit)

        location_group.setLayout(location_layout)
        scroll_layout.addWidget(location_group)

        # Status Section (only show in edit mode)
        if self.is_edit_mode:
            status_group = QGroupBox("Status")
            status_layout = QFormLayout()

            self.status_combo = QComboBox()
            self.status_combo.addItems(['Active', 'Inactive'])

            status_layout.addRow("Status:", self.status_combo)
            status_group.setLayout(status_layout)
            scroll_layout.addWidget(status_group)

        # Pictures Section
        pictures_group = QGroupBox("Pictures")
        pictures_layout = QVBoxLayout()

        # Picture 1
        pic1_layout = QHBoxLayout()
        pic1_label = QLabel("Picture 1:")
        self.pic1_status_label = QLabel("No photo")
        self.pic1_status_label.setStyleSheet("color: gray;")
        pic1_browse_btn = QPushButton("Browse...")
        pic1_browse_btn.clicked.connect(lambda: self.browse_picture(1))
        pic1_clear_btn = QPushButton("Clear")
        pic1_clear_btn.clicked.connect(lambda: self.clear_picture(1))

        pic1_layout.addWidget(pic1_label)
        pic1_layout.addWidget(self.pic1_status_label, 1)
        pic1_layout.addWidget(pic1_browse_btn)
        pic1_layout.addWidget(pic1_clear_btn)
        pictures_layout.addLayout(pic1_layout)

        # Picture 1 preview
        self.pic1_preview = QLabel()
        self.pic1_preview.setFixedSize(200, 200)
        self.pic1_preview.setFrameStyle(QFrame.Box)
        self.pic1_preview.setAlignment(Qt.AlignCenter)
        self.pic1_preview.setScaledContents(False)
        pictures_layout.addWidget(self.pic1_preview)

        # Picture 2
        pic2_layout = QHBoxLayout()
        pic2_label = QLabel("Picture 2:")
        self.pic2_status_label = QLabel("No photo")
        self.pic2_status_label.setStyleSheet("color: gray;")
        pic2_browse_btn = QPushButton("Browse...")
        pic2_browse_btn.clicked.connect(lambda: self.browse_picture(2))
        pic2_clear_btn = QPushButton("Clear")
        pic2_clear_btn.clicked.connect(lambda: self.clear_picture(2))

        pic2_layout.addWidget(pic2_label)
        pic2_layout.addWidget(self.pic2_status_label, 1)
        pic2_layout.addWidget(pic2_browse_btn)
        pic2_layout.addWidget(pic2_clear_btn)
        pictures_layout.addLayout(pic2_layout)

        # Picture 2 preview
        self.pic2_preview = QLabel()
        self.pic2_preview.setFixedSize(200, 200)
        self.pic2_preview.setFrameStyle(QFrame.Box)
        self.pic2_preview.setAlignment(Qt.AlignCenter)
        self.pic2_preview.setScaledContents(False)
        pictures_layout.addWidget(self.pic2_preview)

        pictures_group.setLayout(pictures_layout)
        scroll_layout.addWidget(pictures_group)

        # Notes Section
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout()

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_edit)

        notes_group.setLayout(notes_layout)
        scroll_layout.addWidget(notes_group)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_part)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Update picture previews if editing
        if self.is_edit_mode:
            self.update_picture_preview(1)
            self.update_picture_preview(2)

    def populate_fields(self):
        """Populate fields with existing part data"""
        if not self.part_data:
            return

        self.name_edit.setText(self.part_data.get('name', ''))
        self.part_number_edit.setText(self.part_data.get('part_number', ''))
        self.model_number_edit.setText(self.part_data.get('model_number', ''))
        self.equipment_edit.setText(self.part_data.get('equipment', ''))

        eng_sys = self.part_data.get('engineering_system', '')
        index = self.engineering_system_combo.findText(eng_sys)
        if index >= 0:
            self.engineering_system_combo.setCurrentIndex(index)

        self.unit_of_measure_edit.setText(self.part_data.get('unit_of_measure', ''))
        self.quantity_spin.setValue(float(self.part_data.get('quantity_in_stock', 0)))
        self.unit_price_spin.setValue(float(self.part_data.get('unit_price', 0)))
        self.minimum_stock_spin.setValue(float(self.part_data.get('minimum_stock', 0)))
        self.supplier_edit.setText(self.part_data.get('supplier', ''))

        self.location_edit.setText(self.part_data.get('location', ''))
        self.rack_edit.setText(self.part_data.get('rack', ''))
        self.row_edit.setText(self.part_data.get('row', ''))
        self.bin_edit.setText(self.part_data.get('bin', ''))

        if hasattr(self, 'status_combo'):
            status = self.part_data.get('status', 'Active')
            index = self.status_combo.findText(status)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)

        self.notes_edit.setPlainText(self.part_data.get('notes', ''))

        # Update picture status labels
        if self.picture_1_data:
            self.pic1_status_label.setText("Photo stored in database")
            self.pic1_status_label.setStyleSheet("color: green;")

        if self.picture_2_data:
            self.pic2_status_label.setText("Photo stored in database")
            self.pic2_status_label.setStyleSheet("color: green;")

    def browse_picture(self, pic_num):
        """Browse for a picture file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select Picture {pic_num}",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    picture_data = f.read()

                if pic_num == 1:
                    self.picture_1_data = picture_data
                    self.pic1_status_label.setText(f"Selected: {os.path.basename(file_path)}")
                    self.pic1_status_label.setStyleSheet("color: green;")
                    self.update_picture_preview(1)
                else:
                    self.picture_2_data = picture_data
                    self.pic2_status_label.setText(f"Selected: {os.path.basename(file_path)}")
                    self.pic2_status_label.setStyleSheet("color: green;")
                    self.update_picture_preview(2)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image:\n{str(e)}")

    def clear_picture(self, pic_num):
        """Clear a picture"""
        if pic_num == 1:
            self.picture_1_data = None
            self.pic1_status_label.setText("No photo")
            self.pic1_status_label.setStyleSheet("color: gray;")
            self.pic1_preview.clear()
            self.pic1_preview.setText("")
        else:
            self.picture_2_data = None
            self.pic2_status_label.setText("No photo")
            self.pic2_status_label.setStyleSheet("color: gray;")
            self.pic2_preview.clear()
            self.pic2_preview.setText("")

    def update_picture_preview(self, pic_num):
        """Update picture preview"""
        picture_data = self.picture_1_data if pic_num == 1 else self.picture_2_data
        preview_label = self.pic1_preview if pic_num == 1 else self.pic2_preview

        if picture_data:
            try:
                pixmap = QPixmap()
                pixmap.loadFromData(picture_data)

                # Scale to fit preview while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                preview_label.setPixmap(scaled_pixmap)
            except Exception as e:
                preview_label.setText("Error loading preview")
        else:
            preview_label.clear()
            preview_label.setText("")

    def validate_fields(self):
        """Validate required fields"""
        required_fields = {
            'Name': self.name_edit.text().strip(),
            'Part Number': self.part_number_edit.text().strip(),
            'Engineering System': self.engineering_system_combo.currentText().strip(),
            'Unit of Measure': self.unit_of_measure_edit.text().strip(),
            'Location': self.location_edit.text().strip(),
        }

        for field_name, value in required_fields.items():
            if not value:
                QMessageBox.warning(self, "Validation Error",
                                  f"Please fill in: {field_name}")
                return False

        return True

    def save_part(self):
        """Save or update part"""
        if not self.validate_fields():
            return

        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            if self.is_edit_mode:
                # Update existing part
                cursor.execute('''
                    UPDATE mro_inventory SET
                        name = %s, model_number = %s, equipment = %s, engineering_system = %s,
                        unit_of_measure = %s, quantity_in_stock = %s, unit_price = %s,
                        minimum_stock = %s, supplier = %s, location = %s, rack = %s,
                        row = %s, bin = %s, picture_1_data = %s, picture_2_data = %s,
                        notes = %s, status = %s, last_updated = %s
                    WHERE part_number = %s
                ''', (
                    self.name_edit.text().strip(),
                    self.model_number_edit.text().strip(),
                    self.equipment_edit.text().strip(),
                    self.engineering_system_combo.currentText(),
                    self.unit_of_measure_edit.text().strip(),
                    self.quantity_spin.value(),
                    self.unit_price_spin.value(),
                    self.minimum_stock_spin.value(),
                    self.supplier_edit.text().strip(),
                    self.location_edit.text().strip(),
                    self.rack_edit.text().strip(),
                    self.row_edit.text().strip(),
                    self.bin_edit.text().strip(),
                    self.picture_1_data,
                    self.picture_2_data,
                    self.notes_edit.toPlainText(),
                    self.status_combo.currentText() if hasattr(self, 'status_combo') else 'Active',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    self.part_number_edit.text().strip()
                ))

                self.conn.commit()
                QMessageBox.information(self, "Success", "Part updated successfully!")
            else:
                # Insert new part
                cursor.execute('''
                    INSERT INTO mro_inventory (
                        name, part_number, model_number, equipment, engineering_system,
                        unit_of_measure, quantity_in_stock, unit_price, minimum_stock,
                        supplier, location, rack, row, bin, picture_1_data, picture_2_data, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    self.name_edit.text().strip(),
                    self.part_number_edit.text().strip(),
                    self.model_number_edit.text().strip(),
                    self.equipment_edit.text().strip(),
                    self.engineering_system_combo.currentText(),
                    self.unit_of_measure_edit.text().strip(),
                    self.quantity_spin.value(),
                    self.unit_price_spin.value(),
                    self.minimum_stock_spin.value(),
                    self.supplier_edit.text().strip(),
                    self.location_edit.text().strip(),
                    self.rack_edit.text().strip(),
                    self.row_edit.text().strip(),
                    self.bin_edit.text().strip(),
                    self.picture_1_data,
                    self.picture_2_data,
                    self.notes_edit.toPlainText()
                ))

                self.conn.commit()
                QMessageBox.information(self, "Success", "Part added successfully!")

            self.accept()

        except Exception as e:
            self.conn.rollback()
            error_msg = str(e).lower()
            if 'unique' in error_msg or 'duplicate' in error_msg:
                QMessageBox.critical(self, "Error", "Part number already exists!")
            else:
                QMessageBox.critical(self, "Error",
                                   f"Failed to save part:\n{str(e)}\n\n{traceback.format_exc()}")


class PartDetailsDialog(QDialog):
    """Dialog to view detailed part information with tabs"""

    def __init__(self, conn, part_number, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.part_number = part_number
        self.setWindowTitle(f"Part Details - {part_number}")
        self.setMinimumSize(900, 700)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Tab 1: Part Information
        self.info_tab = QWidget()
        self.setup_info_tab()
        self.tab_widget.addTab(self.info_tab, "Part Information")

        # Tab 2: CM Usage History
        self.cm_history_tab = QWidget()
        self.setup_cm_history_tab()
        self.tab_widget.addTab(self.cm_history_tab, "CM Usage History")

        # Tab 3: All Transactions
        self.transactions_tab = QWidget()
        self.setup_transactions_tab()
        self.tab_widget.addTab(self.transactions_tab, "All Transactions")

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)

    def setup_info_tab(self):
        """Setup part information tab"""
        layout = QVBoxLayout(self.info_tab)

        # Scroll area for info
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_widget = QWidget()
        self.info_layout = QVBoxLayout(scroll_widget)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

    def setup_cm_history_tab(self):
        """Setup CM usage history tab"""
        layout = QVBoxLayout(self.cm_history_tab)

        # Header
        header_label = QLabel()
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)
        self.cm_header_label = header_label

        # Statistics group
        self.cm_stats_group = QGroupBox("Usage Statistics")
        stats_layout = QVBoxLayout()
        self.cm_stats_label = QLabel()
        stats_layout.addWidget(self.cm_stats_label)
        self.cm_stats_group.setLayout(stats_layout)
        layout.addWidget(self.cm_stats_group)

        # History table
        self.cm_history_table = QTableWidget()
        self.cm_history_table.setColumnCount(9)
        self.cm_history_table.setHorizontalHeaderLabels([
            'CM #', 'Description', 'Equipment', 'Qty Used', 'Cost',
            'Date', 'Technician', 'Status', 'Notes'
        ])
        self.cm_history_table.horizontalHeader().setStretchLastSection(True)
        self.cm_history_table.setAlternatingRowColors(True)
        self.cm_history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.cm_history_table)

    def setup_transactions_tab(self):
        """Setup all transactions tab"""
        layout = QVBoxLayout(self.transactions_tab)

        # Header
        header_label = QLabel()
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)
        self.trans_header_label = header_label

        # Transactions table
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(6)
        self.trans_table.setHorizontalHeaderLabels([
            'Date', 'Type', 'Quantity', 'Technician', 'Work Order', 'Notes'
        ])
        self.trans_table.horizontalHeader().setStretchLastSection(True)
        self.trans_table.setAlternatingRowColors(True)
        self.trans_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.trans_table)

    def load_data(self):
        """Load all data for the part"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Get part data
            cursor.execute('''
                SELECT id, name, part_number, model_number, equipment, engineering_system,
                       unit_of_measure, quantity_in_stock, unit_price, minimum_stock,
                       supplier, location, rack, row, bin, picture_1_data, picture_2_data,
                       notes, last_updated, created_date, status
                FROM mro_inventory WHERE part_number = %s
            ''', (self.part_number,))

            part_data = cursor.fetchone()

            if not part_data:
                QMessageBox.critical(self, "Error", "Part not found in database!")
                self.close()
                return

            # Load part information tab
            self.load_part_info(part_data)

            # Load CM history
            self.load_cm_history(part_data)

            # Load transactions
            self.load_transactions()

        except Exception as e:
            QMessageBox.critical(self, "Error",
                               f"Failed to load part data:\n{str(e)}\n\n{traceback.format_exc()}")

    def load_part_info(self, part_data):
        """Load part information into info tab"""
        # Clear existing widgets
        for i in reversed(range(self.info_layout.count())):
            self.info_layout.itemAt(i).widget().setParent(None)

        # Create info display
        info_widget = QWidget()
        info_form = QFormLayout(info_widget)
        info_form.setSpacing(10)

        bold_font = QFont()
        bold_font.setBold(True)

        # Display fields
        fields = [
            ("Part Number:", part_data['part_number']),
            ("Part Name:", part_data['name']),
            ("Model Number:", part_data['model_number'] or 'N/A'),
            ("Equipment:", part_data['equipment'] or 'N/A'),
            ("Engineering System:", part_data['engineering_system'] or 'N/A'),
            ("", ""),  # Spacer
            ("Quantity in Stock:", f"{part_data['quantity_in_stock']:.2f} {part_data['unit_of_measure']}"),
            ("Minimum Stock:", f"{part_data['minimum_stock']:.2f} {part_data['unit_of_measure']}"),
            ("Unit of Measure:", part_data['unit_of_measure']),
            ("Unit Price:", f"${part_data['unit_price']:.2f}"),
            ("Total Value:", f"${part_data['quantity_in_stock'] * part_data['unit_price']:.2f}"),
            ("", ""),  # Spacer
            ("Supplier:", part_data['supplier'] or 'N/A'),
            ("Location:", part_data['location'] or 'N/A'),
            ("Rack:", part_data['rack'] or 'N/A'),
            ("Row:", part_data['row'] or 'N/A'),
            ("Bin:", part_data['bin'] or 'N/A'),
            ("", ""),  # Spacer
            ("Status:", part_data['status']),
            ("Created Date:", str(part_data['created_date'])[:10] if part_data['created_date'] else 'N/A'),
            ("Last Updated:", str(part_data['last_updated'])[:10] if part_data['last_updated'] else 'N/A'),
        ]

        for label_text, value in fields:
            if label_text:  # Not a spacer
                label = QLabel(label_text)
                label.setFont(bold_font)
                value_label = QLabel(str(value))
                info_form.addRow(label, value_label)

        # Notes
        if part_data['notes']:
            notes_label = QLabel("Notes:")
            notes_label.setFont(bold_font)
            notes_text = QTextEdit()
            notes_text.setPlainText(part_data['notes'])
            notes_text.setReadOnly(True)
            notes_text.setMaximumHeight(80)
            info_form.addRow(notes_label, notes_text)

        self.info_layout.addWidget(info_widget)

        # Pictures
        if part_data['picture_1_data'] or part_data['picture_2_data']:
            pictures_group = QGroupBox("Pictures")
            pictures_layout = QHBoxLayout()

            if part_data['picture_1_data']:
                pic1_label = QLabel()
                pixmap = QPixmap()
                pixmap.loadFromData(part_data['picture_1_data'])
                scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pic1_label.setPixmap(scaled_pixmap)
                pic1_label.setFrameStyle(QFrame.Box)
                pictures_layout.addWidget(pic1_label)

            if part_data['picture_2_data']:
                pic2_label = QLabel()
                pixmap = QPixmap()
                pixmap.loadFromData(part_data['picture_2_data'])
                scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pic2_label.setPixmap(scaled_pixmap)
                pic2_label.setFrameStyle(QFrame.Box)
                pictures_layout.addWidget(pic2_label)

            pictures_layout.addStretch()
            pictures_group.setLayout(pictures_layout)
            self.info_layout.addWidget(pictures_group)

        # Stock status indicator
        qty = part_data['quantity_in_stock']
        min_stock = part_data['minimum_stock']

        status_label = QLabel()
        status_font = QFont()
        status_font.setPointSize(11)
        status_font.setBold(True)
        status_label.setFont(status_font)

        if qty < min_stock:
            status_label.setText("⚠ LOW STOCK - Reorder Recommended")
            status_label.setStyleSheet("color: red;")
        elif qty < min_stock * 1.5:
            status_label.setText("⚡ Stock Getting Low")
            status_label.setStyleSheet("color: orange;")
        else:
            status_label.setText("✓ Stock Level OK")
            status_label.setStyleSheet("color: green;")

        status_label.setAlignment(Qt.AlignCenter)
        self.info_layout.addWidget(status_label)

        self.info_layout.addStretch()

    def load_cm_history(self, part_data):
        """Load CM usage history"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            self.cm_header_label.setText(f"Corrective Maintenance History for {self.part_number}")

            # Get CM history
            cursor.execute('''
                SELECT
                    cp.cm_number,
                    cm.description,
                    cm.bfm_equipment_no,
                    cp.quantity_used,
                    cp.total_cost,
                    cp.recorded_date,
                    cp.recorded_by,
                    cm.status,
                    cp.notes
                FROM cm_parts_used cp
                LEFT JOIN corrective_maintenance cm ON cp.cm_number = cm.cm_number
                WHERE cp.part_number = %s
                ORDER BY cp.recorded_date DESC
                LIMIT 50
            ''', (self.part_number,))

            cm_history = cursor.fetchall()

            if cm_history:
                # Calculate statistics
                total_cms = len(cm_history)
                total_qty_used = sum(row['quantity_used'] for row in cm_history)
                total_cost = sum(row['total_cost'] or 0 for row in cm_history)

                # Get recent usage (last 30 days)
                cursor.execute('''
                    SELECT SUM(quantity_used)
                    FROM cm_parts_used
                    WHERE part_number = %s
                    AND recorded_date::timestamp >= CURRENT_DATE - INTERVAL '30 days'
                ''', (self.part_number,))

                recent_result = cursor.fetchone()
                recent_usage = recent_result['sum'] if recent_result and recent_result['sum'] else 0

                stats_text = (f"Total CMs: {total_cms} | "
                            f"Total Quantity Used: {total_qty_used:.2f} {part_data['unit_of_measure']} | "
                            f"Total Cost: ${total_cost:.2f}\n"
                            f"Usage Last 30 Days: {recent_usage:.2f} {part_data['unit_of_measure']}")

                self.cm_stats_label.setText(stats_text)

                # Populate table
                self.cm_history_table.setRowCount(len(cm_history))
                for row_idx, row in enumerate(cm_history):
                    self.cm_history_table.setItem(row_idx, 0, QTableWidgetItem(row['cm_number'] or ''))

                    desc = row['description'] or 'N/A'
                    if len(desc) > 30:
                        desc = desc[:30] + '...'
                    self.cm_history_table.setItem(row_idx, 1, QTableWidgetItem(desc))

                    self.cm_history_table.setItem(row_idx, 2, QTableWidgetItem(row['bfm_equipment_no'] or 'N/A'))
                    self.cm_history_table.setItem(row_idx, 3, QTableWidgetItem(f"{row['quantity_used']:.2f}"))
                    self.cm_history_table.setItem(row_idx, 4, QTableWidgetItem(f"${row['total_cost']:.2f}" if row['total_cost'] else '$0.00'))
                    self.cm_history_table.setItem(row_idx, 5, QTableWidgetItem(str(row['recorded_date'])[:10] if row['recorded_date'] else ''))
                    self.cm_history_table.setItem(row_idx, 6, QTableWidgetItem(row['recorded_by'] or 'N/A'))
                    self.cm_history_table.setItem(row_idx, 7, QTableWidgetItem(row['status'] or 'Unknown'))

                    notes = row['notes'] or ''
                    if len(notes) > 20:
                        notes = notes[:20] + '...'
                    self.cm_history_table.setItem(row_idx, 8, QTableWidgetItem(notes))

                self.cm_history_table.resizeColumnsToContents()
            else:
                self.cm_stats_label.setText("No CM usage history available")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CM history:\n{str(e)}")

    def load_transactions(self):
        """Load all stock transactions"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            self.trans_header_label.setText(f"All Stock Transactions for {self.part_number}")

            # Get transactions
            cursor.execute('''
                SELECT
                    transaction_date,
                    transaction_type,
                    quantity,
                    technician_name,
                    work_order,
                    notes
                FROM mro_stock_transactions
                WHERE part_number = %s
                ORDER BY transaction_date DESC
                LIMIT 100
            ''', (self.part_number,))

            transactions = cursor.fetchall()

            if transactions:
                self.trans_table.setRowCount(len(transactions))
                for row_idx, row in enumerate(transactions):
                    # Date
                    date_str = str(row['transaction_date'])[:19] if row['transaction_date'] else ''
                    self.trans_table.setItem(row_idx, 0, QTableWidgetItem(date_str))

                    # Type
                    self.trans_table.setItem(row_idx, 1, QTableWidgetItem(row['transaction_type'] or 'N/A'))

                    # Quantity (with + or - prefix)
                    qty = row['quantity']
                    qty_display = f"+{qty:.2f}" if qty > 0 else f"{qty:.2f}"
                    qty_item = QTableWidgetItem(qty_display)

                    # Color code based on add/remove
                    if qty > 0:
                        qty_item.setForeground(QColor('green'))
                    else:
                        qty_item.setForeground(QColor('red'))

                    self.trans_table.setItem(row_idx, 2, qty_item)

                    # Technician
                    self.trans_table.setItem(row_idx, 3, QTableWidgetItem(row['technician_name'] or 'N/A'))

                    # Work Order
                    self.trans_table.setItem(row_idx, 4, QTableWidgetItem(row['work_order'] or 'N/A'))

                    # Notes
                    self.trans_table.setItem(row_idx, 5, QTableWidgetItem(row['notes'] or ''))

                self.trans_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load transactions:\n{str(e)}")


class StockTransactionDialog(QDialog):
    """Dialog for stock transactions (add/remove stock)"""

    def __init__(self, conn, part_number, current_user='System', parent=None):
        super().__init__(parent)
        self.conn = conn
        self.part_number = part_number
        self.current_user = current_user

        self.setWindowTitle(f"Stock Transaction: {part_number}")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_current_stock()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Part info labels
        self.part_name_label = QLabel()
        part_font = QFont()
        part_font.setPointSize(12)
        part_font.setBold(True)
        self.part_name_label.setFont(part_font)
        layout.addWidget(self.part_name_label)

        self.current_stock_label = QLabel()
        stock_font = QFont()
        stock_font.setPointSize(11)
        self.current_stock_label.setFont(stock_font)
        layout.addWidget(self.current_stock_label)

        layout.addSpacing(20)

        # Transaction type
        type_group = QGroupBox("Transaction Type")
        type_layout = QVBoxLayout()

        self.add_radio = QPushButton("Add Stock")
        self.add_radio.setCheckable(True)
        self.add_radio.setChecked(True)
        self.add_radio.clicked.connect(lambda: self.remove_radio.setChecked(False))

        self.remove_radio = QPushButton("Remove Stock")
        self.remove_radio.setCheckable(True)
        self.remove_radio.clicked.connect(lambda: self.add_radio.setChecked(False))

        type_layout.addWidget(self.add_radio)
        type_layout.addWidget(self.remove_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Form
        form_layout = QFormLayout()

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.01, 999999)
        self.quantity_spin.setDecimals(2)

        self.work_order_edit = QLineEdit()

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)

        form_layout.addRow("Quantity:", self.quantity_spin)
        form_layout.addRow("Work Order (Optional):", self.work_order_edit)
        form_layout.addRow("Notes:", self.notes_edit)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.process_transaction)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_current_stock(self):
        """Load current stock information"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT quantity_in_stock, unit_of_measure, name
                FROM mro_inventory
                WHERE part_number = %s
            ''', (self.part_number,))

            result = cursor.fetchone()
            if result:
                self.current_stock = result['quantity_in_stock']
                self.unit = result['unit_of_measure']
                part_name = result['name']

                self.part_name_label.setText(f"Part: {part_name}")
                self.current_stock_label.setText(f"Current Stock: {self.current_stock:.2f} {self.unit}")
            else:
                QMessageBox.critical(self, "Error", "Part not found!")
                self.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load stock:\n{str(e)}")
            self.close()

    def process_transaction(self):
        """Process the stock transaction"""
        try:
            qty = self.quantity_spin.value()

            if qty <= 0:
                QMessageBox.warning(self, "Validation Error", "Please enter a quantity greater than 0")
                return

            # Determine transaction type and calculate new stock
            if self.remove_radio.isChecked():
                trans_type = 'Remove'
                qty = -qty
            else:
                trans_type = 'Add'

            new_stock = self.current_stock + qty

            if new_stock < 0:
                QMessageBox.critical(self, "Error", "Cannot remove more stock than available!")
                return

            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Update stock
            cursor.execute('''
                UPDATE mro_inventory
                SET quantity_in_stock = %s, last_updated = %s
                WHERE part_number = %s
            ''', (new_stock, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.part_number))

            # Log transaction
            cursor.execute('''
                INSERT INTO mro_stock_transactions
                (part_number, transaction_type, quantity, technician_name, work_order, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                self.part_number,
                trans_type,
                abs(qty),
                self.current_user,
                self.work_order_edit.text().strip(),
                self.notes_edit.toPlainText()
            ))

            self.conn.commit()

            QMessageBox.information(self, "Success",
                                  f"Stock updated!\n\n"
                                  f"Previous: {self.current_stock:.2f} {self.unit}\n"
                                  f"Change: {qty:+.2f} {self.unit}\n"
                                  f"New Stock: {new_stock:.2f} {self.unit}")

            self.accept()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Error", f"Transaction failed:\n{str(e)}\n\n{traceback.format_exc()}")


class CSVImportDialog(QDialog):
    """Dialog for importing MRO parts from CSV"""

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.csv_file = None
        self.headers = []

        self.setWindowTitle("Import MRO Parts from CSV")
        self.setMinimumSize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # File selection
        file_group = QGroupBox("CSV File")
        file_layout = QHBoxLayout()

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_path_edit, 1)
        file_layout.addWidget(browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Column mapping
        mapping_group = QGroupBox("Column Mapping")
        mapping_layout = QFormLayout()

        # Required fields
        required_info = QLabel("Required fields are marked with *")
        required_info.setStyleSheet("color: red; font-weight: bold;")
        mapping_layout.addRow(required_info)

        self.mapping_combos = {}

        fields = [
            ('name', 'Name*', True),
            ('part_number', 'Part Number*', True),
            ('model_number', 'Model Number', False),
            ('equipment', 'Equipment', False),
            ('engineering_system', 'Engineering System*', True),
            ('unit_of_measure', 'Unit of Measure*', True),
            ('quantity_in_stock', 'Quantity in Stock*', True),
            ('unit_price', 'Unit Price', False),
            ('minimum_stock', 'Minimum Stock*', True),
            ('supplier', 'Supplier', False),
            ('location', 'Location*', True),
            ('rack', 'Rack', False),
            ('row', 'Row', False),
            ('bin', 'Bin', False),
        ]

        for field_key, field_label, is_required in fields:
            combo = QComboBox()
            combo.addItem("-- Not Mapped --")
            self.mapping_combos[field_key] = combo
            mapping_layout.addRow(field_label + ":", combo)

        mapping_group.setLayout(mapping_layout)

        scroll = QScrollArea()
        scroll.setWidget(mapping_group)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        # Import button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.import_csv)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def browse_file(self):
        """Browse for CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            self.file_path_edit.setText(file_path)
            self.csv_file = file_path
            self.load_csv_headers()

    def load_csv_headers(self):
        """Load CSV headers and populate combo boxes"""
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                self.headers = next(reader)

            # Populate combo boxes
            for combo in self.mapping_combos.values():
                combo.clear()
                combo.addItem("-- Not Mapped --")
                combo.addItems(self.headers)

            # Auto-map based on column names
            self.auto_map_columns()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read CSV file:\n{str(e)}")

    def auto_map_columns(self):
        """Automatically map columns based on common names"""
        mapping = {
            'name': ['name', 'part name', 'item name'],
            'part_number': ['part number', 'part_number', 'partnumber', 'part #'],
            'model_number': ['model number', 'model_number', 'model'],
            'equipment': ['equipment'],
            'engineering_system': ['engineering system', 'system', 'engineering_system'],
            'unit_of_measure': ['unit of measure', 'unit', 'uom', 'unit_of_measure'],
            'quantity_in_stock': ['quantity in stock', 'quantity', 'qty', 'stock', 'quantity_in_stock'],
            'unit_price': ['unit price', 'price', 'unit_price'],
            'minimum_stock': ['minimum stock', 'min stock', 'minimum', 'minimum_stock'],
            'supplier': ['supplier', 'vendor'],
            'location': ['location'],
            'rack': ['rack'],
            'row': ['row'],
            'bin': ['bin'],
        }

        for field_key, possible_names in mapping.items():
            for header in self.headers:
                if header.lower() in possible_names:
                    index = self.headers.index(header) + 1  # +1 for "Not Mapped" option
                    self.mapping_combos[field_key].setCurrentIndex(index)
                    break

    def import_csv(self):
        """Import CSV data"""
        if not self.csv_file:
            QMessageBox.warning(self, "Error", "Please select a CSV file")
            return

        # Validate required mappings
        required_fields = ['name', 'part_number', 'engineering_system',
                          'unit_of_measure', 'quantity_in_stock', 'minimum_stock', 'location']

        for field in required_fields:
            if self.mapping_combos[field].currentText() == "-- Not Mapped --":
                QMessageBox.warning(self, "Validation Error",
                                  f"Please map required field: {field.replace('_', ' ').title()}")
                return

        try:
            # Read CSV
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                imported_count = 0
                skipped_count = 0
                error_messages = []

                for row_idx, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    try:
                        # Build insert data
                        part_data = {}
                        for field_key, combo in self.mapping_combos.items():
                            csv_column = combo.currentText()
                            if csv_column != "-- Not Mapped --":
                                part_data[field_key] = row.get(csv_column, '')

                        # Validate required fields
                        if not all(part_data.get(f) for f in required_fields):
                            skipped_count += 1
                            error_messages.append(f"Row {row_idx}: Missing required fields")
                            continue

                        # Insert into database
                        cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
                        cursor.execute('''
                            INSERT INTO mro_inventory (
                                name, part_number, model_number, equipment, engineering_system,
                                unit_of_measure, quantity_in_stock, unit_price, minimum_stock,
                                supplier, location, rack, row, bin
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (part_number) DO NOTHING
                        ''', (
                            part_data.get('name', ''),
                            part_data.get('part_number', ''),
                            part_data.get('model_number', ''),
                            part_data.get('equipment', ''),
                            part_data.get('engineering_system', ''),
                            part_data.get('unit_of_measure', ''),
                            float(part_data.get('quantity_in_stock', 0) or 0),
                            float(part_data.get('unit_price', 0) or 0),
                            float(part_data.get('minimum_stock', 0) or 0),
                            part_data.get('supplier', ''),
                            part_data.get('location', ''),
                            part_data.get('rack', ''),
                            part_data.get('row', ''),
                            part_data.get('bin', '')
                        ))

                        imported_count += 1

                    except Exception as e:
                        skipped_count += 1
                        error_messages.append(f"Row {row_idx}: {str(e)}")

                self.conn.commit()

                result_msg = f"Import Complete!\n\n"
                result_msg += f"Successfully imported: {imported_count} parts\n"
                result_msg += f"Skipped (duplicates/errors): {skipped_count} parts"

                if error_messages and len(error_messages) <= 10:
                    result_msg += "\n\nErrors:\n" + "\n".join(error_messages[:10])

                QMessageBox.information(self, "Import Complete", result_msg)
                self.accept()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Import Error",
                               f"Failed to import CSV:\n{str(e)}\n\n{traceback.format_exc()}")


class MROStockTab(QWidget):
    """MRO Stock Management Tab Widget"""

    status_updated = pyqtSignal(str)  # Signal to update status bar

    def __init__(self, conn, current_user='System', parent=None):
        """
        Initialize MRO Stock Tab

        Args:
            conn: Database connection object
            current_user: Current logged-in user name
            parent: Parent widget
        """
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self.inventory_data = []

        self.init_database()
        self.init_ui()
        self.refresh_inventory()

    def init_database(self):
        """Initialize database tables and indexes"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Create mro_inventory table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mro_inventory (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    part_number TEXT UNIQUE NOT NULL,
                    model_number TEXT,
                    equipment TEXT,
                    engineering_system TEXT,
                    unit_of_measure TEXT,
                    quantity_in_stock REAL DEFAULT 0,
                    unit_price REAL DEFAULT 0,
                    minimum_stock REAL DEFAULT 0,
                    supplier TEXT,
                    location TEXT,
                    rack TEXT,
                    row TEXT,
                    bin TEXT,
                    picture_1_path TEXT,
                    picture_2_path TEXT,
                    picture_1_data BYTEA,
                    picture_2_data BYTEA,
                    notes TEXT,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'Active'
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mro_part_number ON mro_inventory(part_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mro_name ON mro_inventory(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mro_engineering_system_lower ON mro_inventory(LOWER(engineering_system))')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mro_status_lower ON mro_inventory(LOWER(status))')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mro_location_lower ON mro_inventory(LOWER(location))')

            # Create stock transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mro_stock_transactions (
                    id SERIAL PRIMARY KEY,
                    part_number TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    technician_name TEXT,
                    work_order TEXT,
                    notes TEXT,
                    FOREIGN KEY (part_number) REFERENCES mro_inventory (part_number)
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mro_transactions_part_number ON mro_stock_transactions(part_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mro_transactions_date ON mro_stock_transactions(transaction_date)')

            # Create CM parts used table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cm_parts_used (
                    id SERIAL PRIMARY KEY,
                    cm_number TEXT NOT NULL,
                    part_number TEXT NOT NULL,
                    quantity_used REAL NOT NULL,
                    total_cost REAL DEFAULT 0,
                    recorded_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    recorded_by TEXT,
                    notes TEXT,
                    FOREIGN KEY (part_number) REFERENCES mro_inventory (part_number)
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cm_parts_cm_number ON cm_parts_used(cm_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cm_parts_part_number ON cm_parts_used(part_number)')

            self.conn.commit()
            print("MRO inventory database initialized successfully")

        except Exception as e:
            self.conn.rollback()
            print(f"Error initializing MRO database: {e}")
            traceback.print_exc()

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

        # Inventory Table
        self.create_inventory_table()
        layout.addWidget(self.inventory_table)

        self.setLayout(layout)

    def create_statistics_group(self):
        """Create statistics display group box"""
        group = QGroupBox("Inventory Statistics")
        layout = QHBoxLayout()

        bold_font = QFont()
        bold_font.setBold(True)
        bold_font.setPointSize(10)

        self.stats_total_label = QLabel("Total Parts: 0")
        self.stats_total_label.setFont(bold_font)

        self.stats_value_label = QLabel("Total Value: $0.00")
        self.stats_value_label.setFont(bold_font)
        self.stats_value_label.setStyleSheet("color: green;")

        self.stats_low_stock_label = QLabel("Low Stock Items: 0")
        self.stats_low_stock_label.setFont(bold_font)
        self.stats_low_stock_label.setStyleSheet("color: red;")

        refresh_stats_btn = QPushButton("Refresh Stats")
        refresh_stats_btn.clicked.connect(self.update_statistics)

        layout.addWidget(self.stats_total_label)
        layout.addWidget(self.stats_value_label)
        layout.addWidget(self.stats_low_stock_label)
        layout.addStretch()
        layout.addWidget(refresh_stats_btn)

        group.setLayout(layout)
        return group

    def create_controls_group(self):
        """Create controls group box"""
        group = QGroupBox("MRO Stock Controls")
        main_layout = QVBoxLayout()

        # Row 1
        row1 = QHBoxLayout()

        add_btn = QPushButton("Add New Part")
        add_btn.clicked.connect(self.add_part)

        edit_btn = QPushButton("Edit Selected Part")
        edit_btn.clicked.connect(self.edit_selected_part)

        delete_btn = QPushButton("Delete Selected Part")
        delete_btn.clicked.connect(self.delete_selected_part)

        details_btn = QPushButton("View Full Details")
        details_btn.clicked.connect(self.view_part_details)

        transaction_btn = QPushButton("Stock Transaction")
        transaction_btn.clicked.connect(self.stock_transaction)

        row1.addWidget(add_btn)
        row1.addWidget(edit_btn)
        row1.addWidget(delete_btn)
        row1.addWidget(details_btn)
        row1.addWidget(transaction_btn)

        # Row 2
        row2 = QHBoxLayout()

        import_btn = QPushButton("Import from CSV")
        import_btn.clicked.connect(self.import_from_csv)

        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_to_csv)

        report_btn = QPushButton("Stock Report")
        report_btn.clicked.connect(self.generate_stock_report)

        low_stock_btn = QPushButton("Low Stock Alert")
        low_stock_btn.clicked.connect(self.show_low_stock_alert)

        row2.addWidget(import_btn)
        row2.addWidget(export_btn)
        row2.addWidget(report_btn)
        row2.addWidget(low_stock_btn)
        row2.addStretch()

        main_layout.addLayout(row1)
        main_layout.addLayout(row2)

        group.setLayout(main_layout)
        return group

    def create_search_frame(self):
        """Create search and filter frame"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(frame)

        # Search
        layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name, part number, model, equipment, location...")
        self.search_edit.textChanged.connect(self.filter_inventory)
        layout.addWidget(self.search_edit, 1)

        # System filter
        layout.addWidget(QLabel("System:"))
        self.system_filter = QComboBox()
        self.system_filter.addItems(['All', 'Mechanical', 'Electrical', 'Pneumatic', 'Hydraulic', 'Other'])
        self.system_filter.currentTextChanged.connect(self.filter_inventory)
        layout.addWidget(self.system_filter)

        # Status filter
        layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(['Active', 'All', 'Inactive', 'Low Stock'])
        self.status_filter.currentTextChanged.connect(self.filter_inventory)
        layout.addWidget(self.status_filter)

        # Location filter
        layout.addWidget(QLabel("Location:"))
        self.location_filter = QComboBox()
        self.location_filter.addItem('All')
        self.location_filter.currentTextChanged.connect(self.filter_inventory)
        layout.addWidget(self.location_filter)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_inventory)
        layout.addWidget(refresh_btn)

        return frame

    def create_inventory_table(self):
        """Create inventory table widget"""
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(11)
        self.inventory_table.setHorizontalHeaderLabels([
            'Part Number', 'Name', 'Model', 'Equipment', 'System',
            'Qty', 'Min Stock', 'Unit', 'Price', 'Location', 'Status'
        ])

        # Configure table
        self.inventory_table.setAlternatingRowColors(True)
        self.inventory_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.inventory_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.inventory_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.inventory_table.setSortingEnabled(True)

        # Set column widths
        header = self.inventory_table.horizontalHeader()
        header.setStretchLastSection(True)
        self.inventory_table.setColumnWidth(0, 120)  # Part Number
        self.inventory_table.setColumnWidth(1, 200)  # Name
        self.inventory_table.setColumnWidth(2, 100)  # Model
        self.inventory_table.setColumnWidth(3, 120)  # Equipment
        self.inventory_table.setColumnWidth(4, 100)  # System
        self.inventory_table.setColumnWidth(5, 70)   # Qty
        self.inventory_table.setColumnWidth(6, 80)   # Min Stock
        self.inventory_table.setColumnWidth(7, 60)   # Unit
        self.inventory_table.setColumnWidth(8, 80)   # Price
        self.inventory_table.setColumnWidth(9, 100)  # Location

        # Double-click to view details
        self.inventory_table.doubleClicked.connect(self.view_part_details)

    def refresh_inventory(self):
        """Refresh inventory list"""
        self.update_location_filter()
        self.filter_inventory()
        self.update_statistics()

    def filter_inventory(self):
        """Filter inventory based on search and filters"""
        search_term = self.search_edit.text().lower()
        system_filter = self.system_filter.currentText()
        status_filter = self.status_filter.currentText()
        location_filter = self.location_filter.currentText()

        try:
            # Build query
            query = '''
                SELECT part_number, name, model_number, equipment, engineering_system,
                       unit_of_measure, quantity_in_stock, unit_price, minimum_stock,
                       location, status
                FROM mro_inventory WHERE 1=1
            '''
            params = []

            # System filter
            if system_filter != 'All':
                query += ' AND LOWER(engineering_system) = LOWER(%s)'
                params.append(system_filter)

            # Status filter
            if status_filter == 'Low Stock':
                query += ' AND quantity_in_stock < minimum_stock'
            elif status_filter != 'All':
                query += ' AND LOWER(status) = LOWER(%s)'
                params.append(status_filter)

            # Location filter
            if location_filter != 'All':
                query += ' AND LOWER(location) = LOWER(%s)'
                params.append(location_filter)

            # Search term
            if search_term:
                query += ''' AND (
                    LOWER(name) LIKE %s OR
                    LOWER(part_number) LIKE %s OR
                    LOWER(model_number) LIKE %s OR
                    LOWER(equipment) LIKE %s OR
                    LOWER(location) LIKE %s
                )'''
                search_param = f'%{search_term}%'
                params.extend([search_param] * 5)

            query += ' ORDER BY part_number'

            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute(query, params)
            results = cursor.fetchall()

            # Clear and populate table
            self.inventory_table.setSortingEnabled(False)
            self.inventory_table.setRowCount(0)

            for row_data in results:
                row = self.inventory_table.rowCount()
                self.inventory_table.insertRow(row)

                part_number = row_data['part_number']
                name = row_data['name']
                model = row_data['model_number'] or ''
                equipment = row_data['equipment'] or ''
                system = row_data['engineering_system'] or ''
                unit = row_data['unit_of_measure'] or ''
                qty = float(row_data['quantity_in_stock'])
                price = float(row_data['unit_price'])
                min_stock = float(row_data['minimum_stock'])
                location = row_data['location'] or ''
                status = row_data['status']

                # Determine display status
                if qty < min_stock:
                    display_status = '⚠ LOW'
                else:
                    display_status = status

                # Add items
                self.inventory_table.setItem(row, 0, QTableWidgetItem(part_number))
                self.inventory_table.setItem(row, 1, QTableWidgetItem(name))
                self.inventory_table.setItem(row, 2, QTableWidgetItem(model))
                self.inventory_table.setItem(row, 3, QTableWidgetItem(equipment))
                self.inventory_table.setItem(row, 4, QTableWidgetItem(system))
                self.inventory_table.setItem(row, 5, QTableWidgetItem(f"{qty:.1f}"))
                self.inventory_table.setItem(row, 6, QTableWidgetItem(f"{min_stock:.1f}"))
                self.inventory_table.setItem(row, 7, QTableWidgetItem(unit))
                self.inventory_table.setItem(row, 8, QTableWidgetItem(f"${price:.2f}"))
                self.inventory_table.setItem(row, 9, QTableWidgetItem(location))

                status_item = QTableWidgetItem(display_status)
                if qty < min_stock:
                    status_item.setBackground(QColor('#ffcccc'))
                    status_item.setForeground(QColor('red'))
                self.inventory_table.setItem(row, 10, status_item)

            self.inventory_table.setSortingEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to filter inventory:\n{str(e)}")
            traceback.print_exc()

    def update_location_filter(self):
        """Update location filter dropdown"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT DISTINCT location
                FROM mro_inventory
                WHERE location IS NOT NULL AND location != ''
                ORDER BY location
            ''')

            locations = ['All'] + [row['location'] for row in cursor.fetchall()]

            current_value = self.location_filter.currentText()
            self.location_filter.clear()
            self.location_filter.addItems(locations)

            # Preserve selection if it still exists
            index = self.location_filter.findText(current_value)
            if index >= 0:
                self.location_filter.setCurrentIndex(index)

        except Exception as e:
            print(f"Error updating location filter: {e}")

    def update_statistics(self):
        """Update inventory statistics"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Combined query for efficiency
            cursor.execute('''
                SELECT
                    COUNT(*) as total_parts,
                    COALESCE(SUM(quantity_in_stock * unit_price), 0) as total_value,
                    COUNT(*) FILTER (WHERE quantity_in_stock < minimum_stock) as low_stock_count
                FROM mro_inventory
                WHERE status = 'Active'
            ''')

            result = cursor.fetchone()
            total = result['total_parts']
            value = result['total_value']
            low_stock = result['low_stock_count']

            self.stats_total_label.setText(f"Total Parts: {total}")
            self.stats_value_label.setText(f"Total Value: ${value:,.2f}")
            self.stats_low_stock_label.setText(f"Low Stock Items: {low_stock}")

        except Exception as e:
            print(f"Error updating statistics: {e}")

    def add_part(self):
        """Open dialog to add new part"""
        dialog = AddEditPartDialog(self.conn, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_inventory()
            self.status_updated.emit("New part added successfully")

    def edit_selected_part(self):
        """Edit selected part"""
        selected_rows = self.inventory_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a part to edit")
            return

        row = self.inventory_table.currentRow()
        part_number = self.inventory_table.item(row, 0).text()

        # Get full part data
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT id, name, part_number, model_number, equipment, engineering_system,
                       unit_of_measure, quantity_in_stock, unit_price, minimum_stock,
                       supplier, location, rack, row, bin, picture_1_data, picture_2_data,
                       notes, last_updated, created_date, status
                FROM mro_inventory WHERE part_number = %s
            ''', (part_number,))

            part_data = cursor.fetchone()

            if part_data:
                dialog = AddEditPartDialog(self.conn, dict(part_data), parent=self)
                if dialog.exec_() == QDialog.Accepted:
                    self.refresh_inventory()
                    self.status_updated.emit("Part updated successfully")
            else:
                QMessageBox.critical(self, "Error", "Part not found!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load part:\n{str(e)}")

    def delete_selected_part(self):
        """Delete selected part"""
        selected_rows = self.inventory_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a part to delete")
            return

        row = self.inventory_table.currentRow()
        part_number = self.inventory_table.item(row, 0).text()
        part_name = self.inventory_table.item(row, 1).text()

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete:\n\n"
            f"Part Number: {part_number}\n"
            f"Name: {part_name}\n\n"
            f"This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
                cursor.execute('DELETE FROM mro_inventory WHERE part_number = %s', (part_number,))
                self.conn.commit()

                QMessageBox.information(self, "Success", "Part deleted successfully!")
                self.refresh_inventory()
                self.status_updated.emit("Part deleted")

            except Exception as e:
                self.conn.rollback()
                QMessageBox.critical(self, "Error", f"Failed to delete part:\n{str(e)}")

    def view_part_details(self):
        """View detailed part information"""
        selected_rows = self.inventory_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a part to view")
            return

        row = self.inventory_table.currentRow()
        part_number = self.inventory_table.item(row, 0).text()

        dialog = PartDetailsDialog(self.conn, part_number, parent=self)
        dialog.exec_()

    def stock_transaction(self):
        """Open stock transaction dialog"""
        selected_rows = self.inventory_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a part for stock transaction")
            return

        row = self.inventory_table.currentRow()
        part_number = self.inventory_table.item(row, 0).text()

        dialog = StockTransactionDialog(self.conn, part_number, self.current_user, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_inventory()
            self.status_updated.emit("Stock transaction completed")

    def import_from_csv(self):
        """Import parts from CSV"""
        dialog = CSVImportDialog(self.conn, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_inventory()
            self.status_updated.emit("CSV import completed")

    def export_to_csv(self):
        """Export inventory to CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Inventory to CSV",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT id, name, part_number, model_number, equipment, engineering_system,
                       unit_of_measure, quantity_in_stock, unit_price, minimum_stock,
                       supplier, location, rack, row, bin, notes,
                       last_updated, created_date, status
                FROM mro_inventory ORDER BY part_number
            ''')

            rows = cursor.fetchall()

            columns = ['ID', 'Name', 'Part Number', 'Model Number', 'Equipment',
                      'Engineering System', 'Unit of Measure', 'Quantity in Stock',
                      'Unit Price', 'Minimum Stock', 'Supplier', 'Location', 'Rack',
                      'Row', 'Bin', 'Notes', 'Last Updated', 'Created Date', 'Status']

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)

                for row in rows:
                    writer.writerow([
                        row['id'], row['name'], row['part_number'], row['model_number'],
                        row['equipment'], row['engineering_system'], row['unit_of_measure'],
                        row['quantity_in_stock'], row['unit_price'], row['minimum_stock'],
                        row['supplier'], row['location'], row['rack'], row['row'], row['bin'],
                        row['notes'], row['last_updated'], row['created_date'], row['status']
                    ])

            QMessageBox.information(self, "Success", f"Inventory exported to:\n{file_path}")
            self.status_updated.emit("Inventory exported to CSV")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")

    def generate_stock_report(self):
        """Generate comprehensive stock report"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            report = []
            report.append("=" * 80)
            report.append("MRO INVENTORY STOCK REPORT")
            report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("=" * 80)
            report.append("")

            # Summary statistics
            cursor.execute("SELECT COUNT(*) FROM mro_inventory WHERE status = 'Active'")
            total_parts = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(quantity_in_stock * unit_price) FROM mro_inventory WHERE status = 'Active'")
            total_value = cursor.fetchone()[0] or 0

            cursor.execute('''
                SELECT COUNT(*) FROM mro_inventory
                WHERE quantity_in_stock < minimum_stock AND status = 'Active'
            ''')
            low_stock_count = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(quantity_in_stock) FROM mro_inventory WHERE status = 'Active'")
            total_quantity = cursor.fetchone()[0] or 0

            report.append("SUMMARY")
            report.append("-" * 80)
            report.append(f"Total Active Parts: {total_parts}")
            report.append(f"Total Quantity in Stock: {total_quantity:,.1f}")
            report.append(f"Total Inventory Value: ${total_value:,.2f}")
            report.append(f"Low Stock Items: {low_stock_count}")
            report.append("")

            # Low stock items
            if low_stock_count > 0:
                report.append("LOW STOCK ALERTS")
                report.append("-" * 80)
                cursor.execute('''
                    SELECT part_number, name, quantity_in_stock, minimum_stock,
                           unit_of_measure, location
                    FROM mro_inventory
                    WHERE quantity_in_stock < minimum_stock AND status = 'Active'
                    ORDER BY (minimum_stock - quantity_in_stock) DESC
                ''')

                for row in cursor.fetchall():
                    deficit = row['minimum_stock'] - row['quantity_in_stock']
                    report.append(f"  Part: {row['part_number']} - {row['name']}")
                    report.append(f"  Current: {row['quantity_in_stock']:.1f} {row['unit_of_measure']} | "
                                f"Minimum: {row['minimum_stock']:.1f} {row['unit_of_measure']} | "
                                f"Deficit: {deficit:.1f} {row['unit_of_measure']}")
                    report.append(f"  Location: {row['location']}")
                    report.append("")

            # Inventory by system
            report.append("INVENTORY BY ENGINEERING SYSTEM")
            report.append("-" * 80)
            cursor.execute('''
                SELECT engineering_system, COUNT(*), SUM(quantity_in_stock * unit_price)
                FROM mro_inventory
                WHERE status = 'Active'
                GROUP BY engineering_system
                ORDER BY engineering_system
            ''')

            for row in cursor.fetchall():
                system = row['engineering_system'] or 'Unknown'
                count = row['count']
                value = row['sum'] or 0
                report.append(f"  {system}: {count} parts, ${value:,.2f} value")

            report.append("")
            report.append("=" * 80)
            report.append("END OF REPORT")
            report.append("=" * 80)

            # Display report in dialog
            report_dialog = QDialog(self)
            report_dialog.setWindowTitle("Stock Report")
            report_dialog.setMinimumSize(900, 700)

            layout = QVBoxLayout(report_dialog)

            report_text = QTextEdit()
            report_text.setPlainText('\n'.join(report))
            report_text.setReadOnly(True)
            report_text.setFont(QFont('Courier', 10))
            layout.addWidget(report_text)

            # Export button
            def export_report():
                file_path, _ = QFileDialog.getSaveFileName(
                    report_dialog,
                    "Export Stock Report",
                    "",
                    "Text Files (*.txt);;All Files (*)"
                )
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(report))
                    QMessageBox.information(report_dialog, "Success", f"Report exported to:\n{file_path}")

            export_btn = QPushButton("Export Report")
            export_btn.clicked.connect(export_report)
            layout.addWidget(export_btn)

            report_dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report:\n{str(e)}")

    def show_low_stock_alert(self):
        """Show low stock alert dialog"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT part_number, name, quantity_in_stock, minimum_stock,
                       unit_of_measure, location, supplier
                FROM mro_inventory
                WHERE quantity_in_stock < minimum_stock AND status = 'Active'
                ORDER BY (minimum_stock - quantity_in_stock) DESC
            ''')

            low_stock_items = cursor.fetchall()

            if not low_stock_items:
                QMessageBox.information(self, "Stock Status", "✓ All items are adequately stocked!")
                return

            # Create alert dialog
            alert_dialog = QDialog(self)
            alert_dialog.setWindowTitle(f"⚠ Low Stock Alert ({len(low_stock_items)} items)")
            alert_dialog.setMinimumSize(1000, 600)

            layout = QVBoxLayout(alert_dialog)

            # Header
            header = QLabel(f"⚠ {len(low_stock_items)} items are below minimum stock level")
            header_font = QFont()
            header_font.setPointSize(12)
            header_font.setBold(True)
            header.setFont(header_font)
            header.setStyleSheet("color: red;")
            layout.addWidget(header)

            # Table
            table = QTableWidget()
            table.setColumnCount(8)
            table.setHorizontalHeaderLabels([
                'Part Number', 'Name', 'Current', 'Minimum', 'Deficit',
                'Unit', 'Location', 'Supplier'
            ])
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.horizontalHeader().setStretchLastSection(True)

            table.setRowCount(len(low_stock_items))
            for row_idx, item in enumerate(low_stock_items):
                deficit = item['minimum_stock'] - item['quantity_in_stock']

                table.setItem(row_idx, 0, QTableWidgetItem(item['part_number']))
                table.setItem(row_idx, 1, QTableWidgetItem(item['name']))
                table.setItem(row_idx, 2, QTableWidgetItem(f"{item['quantity_in_stock']:.1f}"))
                table.setItem(row_idx, 3, QTableWidgetItem(f"{item['minimum_stock']:.1f}"))
                table.setItem(row_idx, 4, QTableWidgetItem(f"{deficit:.1f}"))
                table.setItem(row_idx, 5, QTableWidgetItem(item['unit_of_measure']))
                table.setItem(row_idx, 6, QTableWidgetItem(item['location'] or 'N/A'))
                table.setItem(row_idx, 7, QTableWidgetItem(item['supplier'] or 'N/A'))

            table.resizeColumnsToContents()
            layout.addWidget(table)

            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(alert_dialog.close)
            layout.addWidget(close_btn)

            alert_dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load low stock items:\n{str(e)}")


if __name__ == '__main__':
    """Test the MRO Stock Tab standalone"""
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import psycopg2
    from psycopg2.extras import RealDictCursor

    app = QApplication(sys.argv)

    # Test database connection (replace with your credentials)
    try:
        conn = psycopg2.connect(
            host="your_host",
            database="your_database",
            user="your_user",
            password="your_password",
            cursor_factory=RealDictCursor
        )

        window = QMainWindow()
        window.setWindowTitle("MRO Stock Management - Test")
        window.setGeometry(100, 100, 1400, 800)

        tab = MROStockTab(conn, current_user="Test User")
        window.setCentralWidget(tab)

        window.show()
        sys.exit(app.exec_())

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
