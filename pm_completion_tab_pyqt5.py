"""
PM Completion Tab - PyQt5 Implementation
Complete port from AIT_CMMS_REV3.py Tkinter version

This module provides a comprehensive PM (Preventive Maintenance) completion interface
with the following features:
- PM completion form with validation
- Equipment autocomplete
- Recent completions list with filtering
- Statistics tracking
- Equipment PM history dialog
- Duplicate detection
- Database transaction safety
"""

from psycopg2 import extras
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QCompleter, QHeaderView, QDialog, QDialogButtonBox, QFrame
)
from PyQt5.QtCore import Qt, QStringListModel, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime, timedelta
import traceback
import re


class EquipmentPMHistoryDialog(QDialog):
    """Dialog to display PM history for a specific equipment"""

    def __init__(self, conn, bfm_no, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.bfm_no = bfm_no
        self.setWindowTitle(f"PM History - {bfm_no}")
        self.setMinimumSize(700, 500)
        self.setup_ui()
        self.load_history()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Title label
        title = QLabel(f"Recent PM Completions for {self.bfm_no}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            'Date', 'PM Type', 'Technician', 'Hours', 'Notes'
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)

    def load_history(self):
        """Load and display PM history for the equipment"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT pm_type, technician_name, completion_date,
                    (labor_hours + labor_minutes/60.0) as total_hours,
                    notes
                FROM pm_completions
                WHERE bfm_equipment_no = %s
                ORDER BY completion_date DESC LIMIT 20
            ''', (self.bfm_no,))

            completions = cursor.fetchall()

            if completions:
                self.history_table.setRowCount(len(completions))
                for row, completion in enumerate(completions):
                    pm_type = completion['pm_type']
                    tech = completion['technician_name']
                    date = completion['completion_date']
                    hours = completion['total_hours']
                    notes = completion['notes']
                    self.history_table.setItem(row, 0, QTableWidgetItem(str(date)))
                    self.history_table.setItem(row, 1, QTableWidgetItem(pm_type))
                    self.history_table.setItem(row, 2, QTableWidgetItem(tech))
                    self.history_table.setItem(row, 3, QTableWidgetItem(f"{hours:.1f}h" if hours else "0.0h"))
                    notes_text = notes[:100] + "..." if notes and len(notes) > 100 else (notes or "")
                    self.history_table.setItem(row, 4, QTableWidgetItem(notes_text))

                # Resize columns to content
                self.history_table.resizeColumnsToContents()
            else:
                QMessageBox.information(self, "No History",
                                      f"No PM completions found for equipment {self.bfm_no}")

        except Exception as e:
            QMessageBox.critical(self, "Error",
                               f"Failed to load PM history: {str(e)}")


class PMCompletionTab(QWidget):
    """
    Complete PM Completion Tab with all features from the original Tkinter implementation

    Features:
    - PM completion form with all required fields
    - Equipment autocomplete
    - Technician dropdown (loaded from database)
    - Labor time tracking (hours and minutes)
    - Notes and special equipment fields
    - Recent completions table
    - Statistics display
    - Submit and clear functionality
    - Equipment PM history dialog
    - Duplicate detection and validation
    - Database transaction safety
    """

    # Signal emitted when a PM is successfully completed
    pm_completed = pyqtSignal(str, str, str)  # bfm_no, pm_type, technician

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.technicians = []
        self.equipment_list = []

        # Load initial data
        self.load_technicians()
        self.load_equipment_list()

        # Setup UI
        self.setup_ui()

        # Load recent completions
        self.load_recent_completions()

    def setup_ui(self):
        """Setup the complete UI for PM Completion tab"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Create the completion form
        form_group = self.create_completion_form()
        main_layout.addWidget(form_group)

        # Create statistics display
        stats_group = self.create_statistics_display()
        main_layout.addWidget(stats_group)

        # Create recent completions table
        recent_group = self.create_recent_completions_table()
        main_layout.addWidget(recent_group, stretch=1)

    def create_completion_form(self):
        """Create the PM completion entry form"""
        form_group = QGroupBox("PM Completion Entry")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # BFM Equipment Number with autocomplete
        self.bfm_input = QComboBox()
        self.bfm_input.setEditable(True)
        self.bfm_input.setInsertPolicy(QComboBox.NoInsert)
        self.bfm_input.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.bfm_input.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.bfm_input.lineEdit().textChanged.connect(self.update_equipment_suggestions)
        form_layout.addRow("BFM Equipment Number:*", self.bfm_input)

        # PM Type
        self.pm_type_combo = QComboBox()
        self.pm_type_combo.addItems(['', 'Monthly', 'Six Month', 'Annual',
                                     'CANNOT FIND', 'Run to Failure'])
        form_layout.addRow("PM Type:*", self.pm_type_combo)

        # Technician
        self.tech_combo = QComboBox()
        self.tech_combo.addItems([''] + self.technicians)
        form_layout.addRow("Maintenance Technician:*", self.tech_combo)

        # Labor Time - Hours and Minutes
        labor_layout = QHBoxLayout()
        self.labor_hours = QSpinBox()
        self.labor_hours.setRange(0, 24)
        self.labor_hours.setSuffix(" hours")
        labor_layout.addWidget(self.labor_hours)

        self.labor_minutes = QSpinBox()
        self.labor_minutes.setRange(0, 59)
        self.labor_minutes.setSuffix(" minutes")
        labor_layout.addWidget(self.labor_minutes)
        labor_layout.addStretch()

        form_layout.addRow("Labor Time:", labor_layout)

        # PM Due Date
        self.pm_due_date = QLineEdit()
        self.pm_due_date.setPlaceholderText("YYYY-MM-DD (optional)")
        form_layout.addRow("PM Due Date:", self.pm_due_date)

        # Special Equipment
        self.special_equipment = QLineEdit()
        self.special_equipment.setPlaceholderText("Special equipment or tools used")
        form_layout.addRow("Special Equipment Used:", self.special_equipment)

        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        self.notes_input.setPlaceholderText("Enter technician notes here...")
        form_layout.addRow("Notes from Technician:", self.notes_input)

        # Next Annual PM Date
        self.next_annual_pm = QLineEdit()
        self.next_annual_pm.setPlaceholderText("YYYY-MM-DD (auto-calculated for Annual PMs)")
        form_layout.addRow("Next Annual PM Date:", self.next_annual_pm)

        # Buttons
        button_layout = QHBoxLayout()

        self.submit_btn = QPushButton("Submit PM Completion")
        self.submit_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 15px; font-weight: bold;")
        self.submit_btn.clicked.connect(self.submit_pm_completion)
        button_layout.addWidget(self.submit_btn)

        self.clear_btn = QPushButton("Clear Form")
        self.clear_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(self.clear_btn)

        self.history_btn = QPushButton("Show Equipment PM History")
        self.history_btn.clicked.connect(self.show_equipment_history)
        button_layout.addWidget(self.history_btn)

        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.clicked.connect(self.load_recent_completions)
        button_layout.addWidget(self.refresh_btn)

        button_layout.addStretch()

        form_layout.addRow(button_layout)

        form_group.setLayout(form_layout)
        return form_group

    def create_statistics_display(self):
        """Create statistics display panel"""
        stats_group = QGroupBox("PM Completion Statistics")
        stats_layout = QHBoxLayout()

        # Total completions
        self.total_completions_label = QLabel("Total Completions: Loading...")
        stats_layout.addWidget(self.total_completions_label)

        # Monthly completions
        self.monthly_completions_label = QLabel("Monthly: -")
        stats_layout.addWidget(self.monthly_completions_label)

        # Annual completions
        self.annual_completions_label = QLabel("Annual: -")
        stats_layout.addWidget(self.annual_completions_label)

        # This week completions
        self.weekly_completions_label = QLabel("This Week: -")
        stats_layout.addWidget(self.weekly_completions_label)

        stats_layout.addStretch()
        stats_group.setLayout(stats_layout)

        # Load statistics
        self.update_statistics()

        return stats_group

    def create_recent_completions_table(self):
        """Create the recent completions table"""
        recent_group = QGroupBox("Recent PM Completions (Last 500)")
        layout = QVBoxLayout()

        # Table
        self.completions_table = QTableWidget()
        self.completions_table.setColumnCount(5)
        self.completions_table.setHorizontalHeaderLabels([
            'Date', 'BFM Number', 'PM Type', 'Technician', 'Hours'
        ])
        self.completions_table.setAlternatingRowColors(True)
        self.completions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.completions_table.setSelectionMode(QTableWidget.SingleSelection)
        self.completions_table.setSortingEnabled(True)

        # Set column widths
        header = self.completions_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        layout.addWidget(self.completions_table)
        recent_group.setLayout(layout)

        return recent_group

    def load_technicians(self):
        """Load technicians list from database"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute("""
                SELECT full_name FROM users
                WHERE role = 'Technician'
                ORDER BY full_name
            """)

            rows = cursor.fetchall()
            self.technicians = [row['full_name'] for row in rows]

            print(f"Loaded {len(self.technicians)} technicians from database")

            # Fallback if no technicians found
            if not self.technicians:
                print("WARNING: No technicians found in database, using fallback list")
                self.technicians = [
                    "Mark Michaels", "Jerone Bosarge", "Jon Hymel", "Nick Whisenant",
                    "James Dunnam", "Wayne Dunnam", "Nate Williams", "Rey Marikit",
                    "Ronald Houghs"
                ]

        except Exception as e:
            print(f"Error loading technicians: {e}")
            # Use fallback list
            self.technicians = [
                "Mark Michaels", "Jerone Bosarge", "Jon Hymel", "Nick Whisenant",
                "James Dunnam", "Wayne Dunnam", "Nate Williams", "Rey Marikit",
                "Ronald Houghs"
            ]

    def load_equipment_list(self):
        """Load equipment list for autocomplete"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT bfm_equipment_no FROM equipment
                ORDER BY bfm_equipment_no
            ''')

            self.equipment_list = [row['bfm_equipment_no'] for row in cursor.fetchall()]
            print(f"Loaded {len(self.equipment_list)} equipment items")

        except Exception as e:
            print(f"Error loading equipment list: {e}")
            self.equipment_list = []

    def update_equipment_suggestions(self, text):
        """Update equipment autocomplete suggestions"""
        if len(text) >= 2:
            try:
                cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
                cursor.execute('''
                    SELECT bfm_equipment_no FROM equipment
                    WHERE LOWER(bfm_equipment_no) LIKE %s OR LOWER(description) LIKE %s
                    ORDER BY bfm_equipment_no LIMIT 20
                ''', (f'%{text.lower()}%', f'%{text.lower()}%'))

                suggestions = [row['bfm_equipment_no'] for row in cursor.fetchall()]

                # Update combo box items
                self.bfm_input.clear()
                self.bfm_input.addItems(suggestions)
                self.bfm_input.setEditText(text)

            except Exception as e:
                print(f"Error updating equipment suggestions: {e}")

    def load_recent_completions(self):
        """Load and display recent PM completions"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT completion_date, bfm_equipment_no, pm_type, technician_name,
                    (labor_hours + labor_minutes/60.0) as total_hours
                FROM pm_completions
                ORDER BY completion_date DESC, id DESC LIMIT 500
            ''')

            completions = cursor.fetchall()

            # Clear existing rows
            self.completions_table.setRowCount(0)

            # Disable sorting while populating
            self.completions_table.setSortingEnabled(False)

            # Add completions to table
            self.completions_table.setRowCount(len(completions))
            for row, completion in enumerate(completions):
                date = completion['completion_date']
                bfm_no = completion['bfm_equipment_no']
                pm_type = completion['pm_type']
                tech = completion['technician_name']
                hours = completion['total_hours']
                self.completions_table.setItem(row, 0, QTableWidgetItem(str(date)))
                self.completions_table.setItem(row, 1, QTableWidgetItem(bfm_no))
                self.completions_table.setItem(row, 2, QTableWidgetItem(pm_type))
                self.completions_table.setItem(row, 3, QTableWidgetItem(tech))
                hours_str = f"{hours:.1f}h" if hours else "0.0h"
                self.completions_table.setItem(row, 4, QTableWidgetItem(hours_str))

            # Re-enable sorting
            self.completions_table.setSortingEnabled(True)

            # Update statistics
            self.update_statistics()

            print(f"Loaded {len(completions)} recent PM completions")

        except Exception as e:
            print(f"Error loading recent completions: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load recent completions: {str(e)}")

    def update_statistics(self):
        """Update completion statistics display"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Total completions
            cursor.execute('SELECT COUNT(*) as count FROM pm_completions')
            total = cursor.fetchone()['count']
            self.total_completions_label.setText(f"Total Completions: {total}")

            # Monthly completions
            cursor.execute('''
                SELECT COUNT(*) as count FROM pm_completions
                WHERE pm_type = 'Monthly'
            ''')
            monthly = cursor.fetchone()['count']
            self.monthly_completions_label.setText(f"Monthly: {monthly}")

            # Annual completions
            cursor.execute('''
                SELECT COUNT(*) as count FROM pm_completions
                WHERE pm_type = 'Annual'
            ''')
            annual = cursor.fetchone()['count']
            self.annual_completions_label.setText(f"Annual: {annual}")

            # This week completions
            week_start = self.get_week_start(datetime.now())
            week_end = week_start + timedelta(days=6)
            cursor.execute('''
                SELECT COUNT(*) as count FROM pm_completions
                WHERE completion_date BETWEEN %s AND %s
            ''', (week_start.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d')))
            weekly = cursor.fetchone()['count']
            self.weekly_completions_label.setText(f"This Week: {weekly}")

        except Exception as e:
            print(f"Error updating statistics: {e}")

    def get_week_start(self, date):
        """Get the Monday of the week for a given date"""
        # Monday is 0, Sunday is 6
        days_since_monday = date.weekday()
        week_start = date - timedelta(days=days_since_monday)
        return week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    def validate_pm_completion(self, cursor, bfm_no, pm_type, technician, completion_date):
        """Comprehensive validation to prevent duplicate PMs"""
        try:
            issues = []

            # Check 1: Same PM type completed recently for this equipment
            cursor.execute('''
                SELECT completion_date, technician_name, id
                FROM pm_completions
                WHERE bfm_equipment_no = %s AND pm_type = %s
                ORDER BY completion_date DESC LIMIT 1
            ''', (bfm_no, pm_type))

            recent_completion = cursor.fetchone()
            if recent_completion:
                last_completion_date, last_technician, completion_id = recent_completion
                try:
                    last_date = datetime.strptime(last_completion_date, '%Y-%m-%d')
                    current_date = datetime.strptime(completion_date, '%Y-%m-%d')
                    days_since = (current_date - last_date).days

                    # Different thresholds for different PM types
                    min_days = {
                        'Monthly': 25,
                        'Six Month': 150,
                        'Annual': 300
                    }

                    threshold = min_days.get(pm_type, 7)

                    if days_since < threshold:
                        issues.append(
                            f"WARNING: DUPLICATE DETECTED: {pm_type} PM for {bfm_no} was completed only {days_since} days ago\n"
                            f"   Previous completion: {last_completion_date} by {last_technician}\n"
                            f"   Minimum interval for {pm_type} PM: {threshold} days"
                        )

                except ValueError:
                    issues.append(f"WARNING: Date parsing issue with previous completion: {last_completion_date}")

            # Check 2: Same technician completing SAME PM TYPE on same equipment too frequently
            cursor.execute('''
                SELECT COUNT(*)
                FROM pm_completions
                WHERE bfm_equipment_no = %s
                AND technician_name = %s
                AND pm_type = %s
                AND completion_date::date >= %s::date - INTERVAL '7 days'
            ''', (bfm_no, technician, pm_type, completion_date))

            recent_count = cursor.fetchone()[0]
            if recent_count > 0:
                issues.append(
                    f"WARNING: Same technician ({technician}) completed {pm_type} PM on {bfm_no} within last 7 days"
                )

            # Check 3: Equipment exists and is active
            cursor.execute('SELECT status FROM equipment WHERE bfm_equipment_no = %s', (bfm_no,))
            equipment_status = cursor.fetchone()

            if not equipment_status:
                issues.append(f"CHECK: Equipment {bfm_no} not found in database")
            elif equipment_status[0] in ['Missing', 'Run to Failure'] and pm_type not in ['CANNOT FIND', 'Run to Failure']:
                issues.append(
                    f"WARNING: Equipment {bfm_no} has status '{equipment_status[0]}' - unusual for {pm_type} PM"
                )

            # Return validation result
            if issues:
                return {
                    'valid': False,
                    'message': f"Found {len(issues)} potential issue(s):\n\n" + "\n\n".join(issues)
                }
            else:
                return {'valid': True, 'message': 'Validation passed'}

        except Exception as e:
            traceback.print_exc()
            return {
                'valid': False,
                'message': f"Validation error: {str(e)}"
            }

    def process_normal_pm_completion(self, cursor, bfm_no, pm_type, technician, completion_date,
                                     labor_hours, labor_minutes, pm_due_date, special_equipment,
                                     notes, next_annual_pm):
        """Process normal PM completion with enhanced error handling"""
        try:
            # Insert completion record
            cursor.execute('''
                INSERT INTO pm_completions
                (bfm_equipment_no, pm_type, technician_name, completion_date,
                labor_hours, labor_minutes, pm_due_date, special_equipment,
                notes, next_annual_pm_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                bfm_no, pm_type, technician, completion_date,
                labor_hours, labor_minutes, pm_due_date, special_equipment,
                notes, next_annual_pm
            ))

            completion_id = cursor.fetchone()[0]
            if not completion_id:
                raise Exception("Failed to get completion record ID")

            # Update equipment PM dates based on PM type
            if pm_type == 'Monthly':
                if next_annual_pm:
                    cursor.execute('''
                        UPDATE equipment SET
                        last_monthly_pm = %s,
                        next_monthly_pm = %s::date + INTERVAL '30 days',
                        next_annual_pm = %s,
                        updated_date = CURRENT_TIMESTAMP
                        WHERE bfm_equipment_no = %s
                    ''', (completion_date, completion_date, next_annual_pm, bfm_no))
                else:
                    cursor.execute('''
                        UPDATE equipment SET
                        last_monthly_pm = %s,
                        next_monthly_pm = %s::date + INTERVAL '30 days',
                        updated_date = CURRENT_TIMESTAMP
                        WHERE bfm_equipment_no = %s
                    ''', (completion_date, completion_date, bfm_no))

            elif pm_type == 'Six Month':
                cursor.execute('''
                    UPDATE equipment SET
                    last_six_month_pm = %s,
                    next_six_month_pm = %s::date + INTERVAL '180 days',
                    updated_date = CURRENT_TIMESTAMP
                    WHERE bfm_equipment_no = %s
                ''', (completion_date, completion_date, bfm_no))

            elif pm_type == 'Annual':
                cursor.execute('''
                    UPDATE equipment SET
                    last_annual_pm = %s,
                    next_annual_pm = %s::date + INTERVAL '365 days',
                    updated_date = CURRENT_TIMESTAMP
                    WHERE bfm_equipment_no = %s
                ''', (completion_date, completion_date, bfm_no))

            # Verify equipment update worked
            affected_rows = cursor.rowcount
            if affected_rows != 1:
                raise Exception(f"Equipment update failed - affected {affected_rows} rows instead of 1")

            # Update weekly schedule status if exists
            cursor.execute('''
                UPDATE weekly_pm_schedules SET
                status = 'Completed',
                completion_date = %s,
                labor_hours = %s,
                notes = %s
                WHERE id = (
                    SELECT id FROM weekly_pm_schedules
                    WHERE bfm_equipment_no = %s AND pm_type = %s AND assigned_technician = %s
                    AND status = 'Scheduled'
                    ORDER BY scheduled_date
                    LIMIT 1
                )
            ''', (completion_date, labor_hours + (labor_minutes/60), notes,
                  bfm_no, pm_type, technician))

            print(f"CHECK: Normal PM completion processed successfully: {bfm_no} - {pm_type}")
            return True

        except Exception as e:
            print(f"CHECK: Error processing normal PM completion: {str(e)}")
            traceback.print_exc()
            return False

    def verify_pm_completion_saved(self, cursor, bfm_no, pm_type, technician, completion_date):
        """Verify that the PM completion was actually saved to the database"""
        try:
            cursor.execute('''
                SELECT id FROM pm_completions
                WHERE bfm_equipment_no = %s
                AND pm_type = %s
                AND technician_name = %s
                AND completion_date = %s
                ORDER BY id DESC LIMIT 1
            ''', (bfm_no, pm_type, technician, completion_date))

            result = cursor.fetchone()
            if result:
                return {
                    'verified': True,
                    'message': f'PM completion verified in database (ID: {result[0]})'
                }
            else:
                return {
                    'verified': False,
                    'message': 'PM completion not found in database after save attempt'
                }

        except Exception as e:
            return {
                'verified': False,
                'message': f'Verification error: {str(e)}'
            }

    def submit_pm_completion(self):
        """Enhanced PM completion with validation and verification - PREVENTS DUPLICATES"""
        try:
            # Validate required fields
            bfm_no = self.bfm_input.currentText().strip()
            if not bfm_no:
                QMessageBox.warning(self, "Validation Error", "Please enter BFM Equipment Number")
                self.bfm_input.setFocus()
                return

            pm_type = self.pm_type_combo.currentText()
            if not pm_type:
                QMessageBox.warning(self, "Validation Error", "Please select PM Type")
                self.pm_type_combo.setFocus()
                return

            technician = self.tech_combo.currentText()
            if not technician:
                QMessageBox.warning(self, "Validation Error", "Please select Technician")
                self.tech_combo.setFocus()
                return

            # Get form data
            labor_hours = self.labor_hours.value()
            labor_minutes = self.labor_minutes.value()
            pm_due_date = self.pm_due_date.text().strip()
            special_equipment = self.special_equipment.text().strip()
            notes = self.notes_input.toPlainText().strip()
            next_annual_pm = self.next_annual_pm.text().strip()

            # Use PM Due Date as completion date if provided, otherwise today's date
            if pm_due_date:
                completion_date = pm_due_date
            else:
                completion_date = datetime.now().strftime('%Y-%m-%d')

            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Ensure clean transaction state
            try:
                self.conn.rollback()
            except:
                pass

            # WARNING: ENHANCED VALIDATION - Check for recent duplicates
            validation_result = self.validate_pm_completion(cursor, bfm_no, pm_type,
                                                           technician, completion_date)
            if not validation_result['valid']:
                # Show detailed warning dialog
                reply = QMessageBox.question(
                    self,
                    "WARNING: Potential Duplicate PM Detected",
                    f"{validation_result['message']}\n\n"
                    f"Details:\n"
                    f"- Equipment: {bfm_no}\n"
                    f"- PM Type: {pm_type}\n"
                    f"- Technician: {technician}\n"
                    f"- Completion Date: {completion_date}\n\n"
                    f"Do you want to proceed anyway?\n\n"
                    f"Click 'No' to review and make changes.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.No:
                    try:
                        self.conn.rollback()
                    except:
                        pass
                    print("PM submission cancelled - potential duplicate detected")
                    return

            # Auto-calculate next annual PM date if blank
            if not next_annual_pm and pm_type in ['Monthly', 'Six Month', 'Annual']:
                try:
                    completion_dt = datetime.strptime(completion_date, '%Y-%m-%d')
                except ValueError:
                    completion_dt = datetime.now()

                # ONLY set annual PM date when completing an Annual PM
                if pm_type == 'Annual':
                    next_annual_dt = completion_dt + timedelta(days=365)

                    # Add equipment-specific offset to spread annual PMs
                    try:
                        numeric_part = re.findall(r'\d+', bfm_no)
                        if numeric_part:
                            last_digits = int(numeric_part[-1]) % 61
                            offset_days = last_digits - 30  # -30 to +30 days
                        else:
                            offset_days = (hash(bfm_no) % 61) - 30

                        next_annual_dt = next_annual_dt + timedelta(days=offset_days)
                    except Exception:
                        import random
                        offset_days = random.randint(-21, 21)
                        next_annual_dt = next_annual_dt + timedelta(days=offset_days)

                    next_annual_pm = next_annual_dt.strftime('%Y-%m-%d')
                    self.next_annual_pm.setText(next_annual_pm)

            # Process normal PM completion with TRANSACTION SAFETY
            try:
                success = self.process_normal_pm_completion(
                    cursor, bfm_no, pm_type, technician, completion_date,
                    labor_hours, labor_minutes, pm_due_date, special_equipment,
                    notes, next_annual_pm
                )

                if success:
                    # Commit transaction
                    self.conn.commit()

                    # WARNING: VERIFY the completion was saved correctly
                    verification_result = self.verify_pm_completion_saved(
                        cursor, bfm_no, pm_type, technician, completion_date
                    )

                    if verification_result['verified']:
                        QMessageBox.information(
                            self,
                            "Success",
                            f"PM completion recorded and verified!\n\n"
                            f"Equipment: {bfm_no}\n"
                            f"PM Type: {pm_type}\n"
                            f"Technician: {technician}\n"
                            f"Date: {completion_date}\n\n"
                            f"CHECK: Database verification passed"
                        )

                        # Clear form and refresh displays
                        self.clear_form()
                        self.load_recent_completions()

                        # Emit signal
                        self.pm_completed.emit(bfm_no, pm_type, technician)

                        print(f"CHECK: PM completed and verified: {bfm_no} - {pm_type} by {technician}")
                    else:
                        QMessageBox.warning(
                            self,
                            "Warning",
                            f"PM was saved but verification failed!\n\n"
                            f"{verification_result['message']}\n\n"
                            f"Please check the PM History to confirm the completion was recorded."
                        )
                        print(f"WARNING: PM saved but verification incomplete: {bfm_no}")
                else:
                    # Rollback on failure
                    self.conn.rollback()
                    QMessageBox.critical(self, "Error",
                                       "Failed to process PM completion. Transaction rolled back.")

            except Exception as e:
                # Rollback on exception
                self.conn.rollback()
                raise e

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to submit PM completion: {str(e)}")
            traceback.print_exc()

    def clear_form(self):
        """Clear all form fields"""
        self.bfm_input.setCurrentText("")
        self.pm_type_combo.setCurrentIndex(0)
        self.tech_combo.setCurrentIndex(0)
        self.labor_hours.setValue(0)
        self.labor_minutes.setValue(0)
        self.pm_due_date.clear()
        self.special_equipment.clear()
        self.notes_input.clear()
        self.next_annual_pm.clear()

        # Set focus to BFM input
        self.bfm_input.setFocus()

    def show_equipment_history(self):
        """Show PM history dialog for selected or entered equipment"""
        bfm_no = self.bfm_input.currentText().strip()

        if not bfm_no:
            # Show input dialog
            from PyQt5.QtWidgets import QInputDialog
            bfm_no, ok = QInputDialog.getText(
                self,
                "Equipment PM History",
                "Enter BFM Equipment Number:"
            )

            if not ok or not bfm_no.strip():
                return

            bfm_no = bfm_no.strip()

        # Show history dialog
        dialog = EquipmentPMHistoryDialog(self.conn, bfm_no, self)
        dialog.exec_()


# Example usage and testing
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    import psycopg2

    app = QApplication(sys.argv)

    # Database configuration
    DB_CONFIG = {
        'host': 'ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech',
        'port': 5432,
        'database': 'neondb',
        'user': 'neondb_owner',
        'password': 'npg_2Nm6hyPVWiIH',
        'sslmode': 'require'
    }

    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        print("Connected to database successfully")

        # Create and show the PM Completion tab
        pm_tab = PMCompletionTab(conn)
        pm_tab.setWindowTitle("PM Completion - PyQt5")
        pm_tab.resize(1200, 800)
        pm_tab.show()

        sys.exit(app.exec_())

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
