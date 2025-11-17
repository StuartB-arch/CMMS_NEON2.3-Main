"""
PM Scheduling Tab - PyQt5 Implementation
Complete port from Tkinter to PyQt5

This module provides a complete PM Scheduling interface including:
- Week selector with available weeks
- Generate weekly PM schedule with advanced algorithm
- Technician exclusion (for vacation, sick, etc.)
- Technician-specific tabs showing assigned PMs
- PDF form generation with custom templates
- Excel export functionality
- Integration with PMSchedulingService for intelligent scheduling
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QDialog, QFormLayout,
    QCheckBox, QMessageBox, QFileDialog, QGroupBox, QHeaderView,
    QTextEdit, QListWidget, QDialogButtonBox, QScrollArea, QFrame,
    QAbstractItemView, QTabWidget, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
import pandas as pd
from datetime import datetime, timedelta
import traceback
from psycopg2 import extras
import os
import json

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Import PM Scheduling Service
# NOTE: PMSchedulingService should be imported from the main application
# It contains the complete scheduling logic with database operations
# If not available, it can be found in AIT_CMMS_REV3.py or pm_scheduler.py
try:
    from pm_scheduler import PMSchedulingService
except ImportError:
    # Fallback: assume it will be provided by the parent application
    PMSchedulingService = None


class PMSchedulingTab(QWidget):
    """PM Scheduling Tab Widget"""

    status_updated = pyqtSignal(str)  # Signal to update status bar

    def __init__(self, conn, technicians, parent=None):
        """
        Initialize PM Scheduling Tab

        Args:
            conn: Database connection object
            technicians: List of technician names
            parent: Parent widget
        """
        super().__init__(parent)
        self.conn = conn
        self.technicians = technicians
        self.weekly_pm_target = 130  # Target number of PMs per week

        # Initialize technician_tables early to prevent AttributeError
        self.technician_tables = {}
        self.technician_tabs = None

        # Calculate current week start (Monday)
        today = datetime.now()
        self.current_week_start = today - timedelta(days=today.weekday())

        self.init_ui()

        # Load the latest schedule after UI is initialized
        QTimer.singleShot(100, self.load_latest_weekly_schedule)

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Controls Frame
        controls_group = self.create_controls_group()
        layout.addWidget(controls_group)

        # Technician Exclusion Frame
        exclusion_group = self.create_exclusion_group()
        layout.addWidget(exclusion_group)

        # Schedule Display Frame
        schedule_group = self.create_schedule_group()
        layout.addWidget(schedule_group)

        self.setLayout(layout)

    def create_controls_group(self):
        """Create PM scheduling controls group box"""
        group = QGroupBox("PM Scheduling Controls")
        layout = QHBoxLayout()

        # Week selection label and combo
        week_label = QLabel("Week Starting:")
        layout.addWidget(week_label)

        self.week_combo = QComboBox()
        self.week_combo.setMinimumWidth(150)
        self.week_combo.currentTextChanged.connect(self.refresh_technician_schedules)
        layout.addWidget(self.week_combo)

        # Populate with available weeks
        self.populate_week_selector()

        # Generate button
        btn_generate = QPushButton("Generate Weekly Schedule")
        btn_generate.clicked.connect(self.generate_weekly_assignments)
        btn_generate.setStyleSheet("QPushButton { font-weight: bold; background-color: #4CAF50; color: white; }")
        layout.addWidget(btn_generate)

        # Print button
        btn_print = QPushButton("Print PM Forms")
        btn_print.clicked.connect(self.print_weekly_pm_forms)
        btn_print.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        layout.addWidget(btn_print)

        # Export button
        btn_export = QPushButton("Export Schedule")
        btn_export.clicked.connect(self.export_weekly_schedule)
        layout.addWidget(btn_export)

        # Monthly Summary Report button
        btn_monthly_report = QPushButton("Monthly Summary Report")
        btn_monthly_report.clicked.connect(self.generate_monthly_summary_report)
        btn_monthly_report.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
        layout.addWidget(btn_monthly_report)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_exclusion_group(self):
        """Create technician exclusion group box"""
        group = QGroupBox("Exclude Technicians from This Week's Schedule")
        layout = QVBoxLayout()

        # Instructions
        instructions = QLabel("Select technicians to exclude (e.g., vacation, out sick):")
        layout.addWidget(instructions)

        # List widget for technician selection
        self.excluded_technicians_listbox = QListWidget()
        self.excluded_technicians_listbox.setSelectionMode(QAbstractItemView.MultiSelection)
        self.excluded_technicians_listbox.setMaximumHeight(120)
        layout.addWidget(self.excluded_technicians_listbox)

        # Populate the listbox
        self.populate_technician_exclusion_list()

        # Clear button
        btn_clear = QPushButton("Clear All Exclusions")
        btn_clear.clicked.connect(self.clear_all_exclusions)
        layout.addWidget(btn_clear)

        group.setLayout(layout)
        return group

    def create_schedule_group(self):
        """Create schedule display group box with technician tabs"""
        group = QGroupBox("Weekly PM Schedule")
        layout = QVBoxLayout()

        # Create tab widget for technicians
        self.technician_tabs = QTabWidget()

        # Dictionary to hold table widgets for each technician
        self.technician_tables = {}

        # Create a tab for each technician
        for tech in self.technicians:
            # Create table widget for this technician
            table = QTableWidget()

            # Set up columns
            columns = ['BFM Equipment No.', 'Description', 'PM Type', 'Due Date', 'Status']
            table.setColumnCount(len(columns))
            table.setHorizontalHeaderLabels(columns)

            # Configure table properties
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.ExtendedSelection)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.setSortingEnabled(True)

            # Set column widths
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

            # Add to dictionary and tab widget
            self.technician_tables[tech] = table
            self.technician_tabs.addTab(table, tech)

        layout.addWidget(self.technician_tabs)
        group.setLayout(layout)
        return group

    def populate_week_selector(self):
        """Populate dropdown with weeks that have schedules"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT DISTINCT week_start_date
                FROM weekly_pm_schedules
                ORDER BY week_start_date DESC
            ''')
            available_weeks = [str(row['week_start_date']) for row in cursor.fetchall()]

            # Always include current week as an option
            current_week = self.current_week_start.strftime('%Y-%m-%d')
            if current_week not in available_weeks:
                available_weeks.append(current_week)
                available_weeks.sort(reverse=True)

            # Update combobox
            self.week_combo.clear()
            self.week_combo.addItems(available_weeks)

            # Set to most recent week with data, or current week if no data
            if available_weeks:
                self.week_combo.setCurrentIndex(0)

        except Exception as e:
            print(f"Error populating week selector: {e}")
            # Rollback failed transaction
            try:
                self.conn.rollback()
            except:
                pass
            QMessageBox.warning(self, "Warning", f"Error populating week selector: {str(e)}")

    def populate_technician_exclusion_list(self):
        """Populate the exclusion listbox with all technicians"""
        self.excluded_technicians_listbox.clear()
        for tech in self.technicians:
            self.excluded_technicians_listbox.addItem(tech)

    def clear_all_exclusions(self):
        """Clear all technician exclusions"""
        self.excluded_technicians_listbox.clearSelection()

    def get_excluded_technicians(self):
        """Get list of excluded technicians based on listbox selection"""
        excluded = []
        for item in self.excluded_technicians_listbox.selectedItems():
            excluded.append(item.text())
        return excluded

    def load_latest_weekly_schedule(self):
        """Load the most recent weekly schedule on startup"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Find the most recent week with scheduled PMs
            cursor.execute('''
                SELECT week_start_date
                FROM weekly_pm_schedules
                ORDER BY week_start_date DESC
                LIMIT 1
            ''')

            latest_week = cursor.fetchone()

            if latest_week:
                # Find the index of this week in the combo box
                week_start = str(latest_week['week_start_date'])
                index = self.week_combo.findText(week_start)
                if index >= 0:
                    self.week_combo.setCurrentIndex(index)
                self.refresh_technician_schedules()
                self.status_updated.emit(f"Loaded latest weekly schedule: {week_start}")
            else:
                self.status_updated.emit("No weekly schedules found")

        except Exception as e:
            print(f"Error loading latest weekly schedule: {e}")
            # Rollback failed transaction
            try:
                self.conn.rollback()
            except:
                pass

    def generate_weekly_assignments(self):
        """
        Generate weekly PM assignments using PMSchedulingService

        This method uses the PMSchedulingService which must be available either from:
        - pm_scheduler.py module (basic version)
        - Main application file (AIT_CMMS_REV3.py - full version with database operations)

        The full version includes database DELETE/INSERT operations and conflict checking.
        """
        try:
            # Check if PMSchedulingService is available
            if PMSchedulingService is None:
                QMessageBox.critical(
                    self,
                    "Import Error",
                    "PMSchedulingService is not available.\n\n"
                    "Please ensure the pm_scheduler module or main application "
                    "provides this class."
                )
                return

            # Validate that technicians are configured
            if not self.technicians or len(self.technicians) == 0:
                QMessageBox.critical(
                    self,
                    "Configuration Error",
                    "No technicians configured in the system.\n\n"
                    "Please contact your system administrator."
                )
                return

            # Get excluded technicians
            excluded_techs = self.get_excluded_technicians()

            # Filter technicians to exclude selected ones
            available_technicians = [tech for tech in self.technicians if tech not in excluded_techs]

            # Validate that at least one technician is available
            if len(available_technicians) == 0:
                QMessageBox.critical(
                    self,
                    "Configuration Error",
                    "All technicians are excluded from scheduling.\n\n"
                    "Please ensure at least one technician is available for PM assignment."
                )
                return

            # Show info if technicians are excluded
            if excluded_techs:
                excluded_names = ", ".join(excluded_techs)
                QMessageBox.information(
                    self,
                    "Technician Exclusions",
                    f"The following technician(s) will be excluded from this week's schedule:\n\n"
                    f"{excluded_names}\n\n"
                    f"PMs will be distributed among the remaining {len(available_technicians)} technician(s)."
                )

            # Create the PM scheduling service with filtered technicians
            pm_service = PMSchedulingService(self.conn, available_technicians, None)

            # Get the week start date
            week_start_str = self.week_combo.currentText()

            # Parse week start date
            try:
                week_start = datetime.strptime(week_start_str, '%Y-%m-%d')
            except:
                QMessageBox.warning(self, "Warning", "Invalid week start date format")
                return

            # Generate the schedule
            # NOTE: The full PMSchedulingService (from AIT_CMMS_REV3.py) takes week_start_str and returns Dict
            # The basic version (from pm_scheduler.py) takes datetime and returns List[PMAssignment]
            # Try the full version first (string parameter)
            try:
                result = pm_service.generate_weekly_schedule(week_start_str, self.weekly_pm_target)
            except TypeError:
                # Fallback to basic version (datetime parameter)
                result = pm_service.generate_weekly_schedule(week_start, self.weekly_pm_target)
                # Convert List[PMAssignment] to Dict format
                if isinstance(result, list):
                    result = {
                        'success': True,
                        'total_assignments': len(result),
                        'unique_assets': len(set(a.bfm_no for a in result)),
                        'assignments': result
                    }

            if result['success']:
                # Check if there's a special message (like no equipment or no assignments)
                if 'message' in result and result['total_assignments'] == 0:
                    QMessageBox.information(
                        self,
                        "Scheduling Complete",
                        f"{result['message']}\n\n"
                        f"Week: {week_start_str}"
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Scheduling Complete",
                        f"Generated {result['total_assignments']} PM assignments for week {week_start_str}\n\n"
                        f"Unique assets: {result['unique_assets']}\n\n"
                        f"This system prevents duplicate assignments!"
                    )

                # Refresh displays
                self.refresh_technician_schedules()
                self.status_updated.emit(f"Generated {result['total_assignments']} PM assignments")
            else:
                QMessageBox.critical(self, "Error", f"Failed to generate assignments: {result['error']}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate assignments: {str(e)}")
            traceback.print_exc()

    def refresh_technician_schedules(self):
        """Refresh all technician schedule displays"""
        week_start = self.week_combo.currentText()

        if not week_start:
            return

        # Guard against missing technician_tables during initialization
        if not self.technician_tables:
            return

        for technician, table in self.technician_tables.items():
            # Clear existing items
            table.setRowCount(0)
            table.setSortingEnabled(False)

            # Load scheduled PMs for this technician
            try:
                cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
                cursor.execute('''
                    SELECT ws.bfm_equipment_no, e.description, ws.pm_type, ws.scheduled_date, ws.status
                    FROM weekly_pm_schedules ws
                    JOIN equipment e ON ws.bfm_equipment_no = e.bfm_equipment_no
                    WHERE ws.assigned_technician = %s AND ws.week_start_date = %s
                    ORDER BY ws.scheduled_date
                ''', (technician, week_start))

                assignments = cursor.fetchall()

                # Populate table
                table.setRowCount(len(assignments))
                for row_idx, assignment in enumerate(assignments):
                    # assignment is now a dictionary from RealDictCursor
                    bfm_no = assignment['bfm_equipment_no']
                    description = assignment['description']
                    pm_type = assignment['pm_type']
                    scheduled_date = assignment['scheduled_date']
                    status = assignment['status']

                    # Create table items
                    table.setItem(row_idx, 0, QTableWidgetItem(str(bfm_no or '')))
                    table.setItem(row_idx, 1, QTableWidgetItem(str(description or '')))
                    table.setItem(row_idx, 2, QTableWidgetItem(str(pm_type or '')))
                    table.setItem(row_idx, 3, QTableWidgetItem(str(scheduled_date or '')))
                    table.setItem(row_idx, 4, QTableWidgetItem(str(status or '')))

            except Exception as e:
                print(f"Error loading schedule for {technician}: {e}")
                # Rollback failed transaction
                try:
                    self.conn.rollback()
                except:
                    pass

            table.setSortingEnabled(True)

    def print_weekly_pm_forms(self):
        """Generate and print PM forms for the week"""
        try:
            week_start = self.week_combo.currentText()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Create directory for PM forms
            forms_dir = f"PM_Forms_Week_{week_start}_{timestamp}"
            os.makedirs(forms_dir, exist_ok=True)

            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Generate forms for each technician
            forms_generated = 0
            for technician in self.technicians:
                cursor.execute('''
                    SELECT ws.bfm_equipment_no, e.sap_material_no, e.description, e.tool_id_drawing_no,
                        e.location, e.master_lin, ws.pm_type, ws.scheduled_date, ws.assigned_technician
                    FROM weekly_pm_schedules ws
                    JOIN equipment e ON ws.bfm_equipment_no = e.bfm_equipment_no
                    WHERE ws.assigned_technician = %s AND ws.week_start_date = %s
                    ORDER BY ws.scheduled_date
                ''', (technician, week_start))

                assignments = cursor.fetchall()

                if assignments:
                    # Create PDF for this technician
                    filename = os.path.join(forms_dir, f"{technician.replace(' ', '_')}_PM_Forms.pdf")
                    self.create_pm_forms_pdf(filename, technician, assignments)
                    forms_generated += 1

            if forms_generated > 0:
                QMessageBox.information(
                    self,
                    "Success",
                    f"PM forms generated for {forms_generated} technician(s) in directory:\n{forms_dir}"
                )
                self.status_updated.emit(f"PM forms generated for week {week_start}")
            else:
                QMessageBox.warning(
                    self,
                    "No Forms Generated",
                    f"No PM assignments found for week {week_start}"
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PM forms: {str(e)}")
            traceback.print_exc()

    def create_pm_forms_pdf(self, filename, technician, assignments):
        """Create PDF with PM forms for a technician - ENHANCED WITH CUSTOM TEMPLATES"""
        try:
            doc = SimpleDocTemplate(filename, pagesize=letter,
                                    rightMargin=36, leftMargin=36,
                                    topMargin=36, bottomMargin=36)

            styles = getSampleStyleSheet()
            story = []

            # Custom styles for better text wrapping
            cell_style = ParagraphStyle(
                'CellStyle',
                parent=styles['Normal'],
                fontSize=8,
                leading=10,
                wordWrap='LTR'
            )

            header_cell_style = ParagraphStyle(
                'HeaderCellStyle',
                parent=styles['Normal'],
                fontSize=9,
                fontName='Helvetica-Bold',
                leading=11,
                wordWrap='LTR'
            )

            company_style = ParagraphStyle(
                'CompanyStyle',
                parent=styles['Heading1'],
                fontSize=14,
                fontName='Helvetica-Bold',
                alignment=1,
                textColor=colors.darkblue
            )

            print(f"DEBUG: Creating PDF for {technician}")
            print(f"DEBUG: Total assignments: {len(assignments)}")

            for i, assignment in enumerate(assignments):
                print(f"DEBUG: Processing assignment {i}: {assignment}")

                # Safety check for assignment data - now a dictionary from RealDictCursor
                if not assignment:
                    print(f"DEBUG: Skipping invalid assignment {i}")
                    continue

                # Extract variables from assignment dictionary
                bfm_no = assignment.get('bfm_equipment_no') or ''
                sap_no = assignment.get('sap_material_no') or ''
                description = assignment.get('description') or ''
                tool_id = assignment.get('tool_id_drawing_no') or ''
                location = assignment.get('location') or ''
                master_lin = assignment.get('master_lin') or ''
                pm_type = assignment.get('pm_type') or 'Monthly'
                scheduled_date = assignment.get('scheduled_date') or ''
                assigned_tech = assignment.get('assigned_technician') or technician

                print(f"DEBUG: Processing {bfm_no} - {pm_type}")

                # =================== LOGO SECTION ===================
                # Dynamic logo path that works on any computer
                script_dir = os.path.dirname(os.path.abspath(__file__))
                logo_path = os.path.join(script_dir, "img", "ait_logo.png")

                try:
                    if os.path.exists(logo_path):
                        # Create centered logo
                        logo_image = Image(logo_path, width=4*inch, height=1.2*inch)

                        # Center the logo in a table
                        logo_data = [[logo_image]]
                        logo_table = Table(logo_data, colWidths=[7*inch])
                        logo_table.setStyle(TableStyle([
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('TOPPADDING', (0, 0), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                        ]))

                        story.append(logo_table)
                    else:
                        print(f"Logo file not found at: {logo_path}")
                        # Fallback to text if logo file not found
                        story.append(Paragraph("AIT - BUILDING THE FUTURE OF AEROSPACE", company_style))
                        story.append(Spacer(1, 15))

                except Exception as e:
                    print(f"Could not load logo: {e}")
                    # Fallback to text header
                    story.append(Paragraph("AIT - BUILDING THE FUTURE OF AEROSPACE", company_style))
                    story.append(Spacer(1, 15))

                # =================== FETCH CUSTOM PM TEMPLATE ===================
                # Retrieve custom template data BEFORE building the equipment table
                checklist_items = []
                estimated_hours = 1.0
                special_instructions = None
                safety_notes = None

                cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
                cursor.execute('''
                    SELECT checklist_items, estimated_hours, special_instructions, safety_notes
                    FROM pm_templates
                    WHERE bfm_equipment_no = %s AND pm_type = %s
                    ORDER BY updated_date DESC LIMIT 1
                ''', (bfm_no, pm_type))

                template_result = cursor.fetchone()

                if template_result and template_result[0]:
                    try:
                        checklist_items = json.loads(template_result[0])
                        estimated_hours = template_result[1] or 1.0
                        special_instructions = template_result[2]
                        safety_notes = template_result[3]
                        print(f"DEBUG: Using custom template for {bfm_no} - {pm_type} with {len(checklist_items)} items, {estimated_hours}h estimated")
                    except Exception as e:
                        print(f"DEBUG: Error loading custom template: {e}")
                        checklist_items = []

                # Use default checklist if no custom template
                if not checklist_items:
                    print(f"DEBUG: No custom template found for {bfm_no} - {pm_type}, using default checklist")
                    checklist_items = [
                        "Special Equipment Used (List):",
                        "Validate your maintenance with Date / Stamp / Hours",
                        "Refer to drawing when performing maintenance",
                        "Make sure all instruments are properly calibrated",
                        "Make sure tool is properly identified",
                        "Make sure all mobile mechanisms move fluidly",
                        "Visually inspect the welds",
                        "Take note of any anomaly or defect (create a CM if needed)",
                        "Check all screws. Tighten if needed.",
                        "Check the pins for wear",
                        "Make sure all tooling is secured to the equipment with cable",
                        "Ensure all tags (BFM and SAP) are applied and securely fastened",
                        "All documentation are picked up from work area",
                        "All parts and tools have been picked up",
                        "Workspace has been cleaned up",
                        "Dry runs have been performed (tests, restarts, etc.)",
                        "Ensure that AIT Sticker is applied"
                    ]

                # =================== EQUIPMENT INFORMATION TABLE ===================
                equipment_data = [
                    [
                        Paragraph('(SAP) Material Number:', header_cell_style),
                        Paragraph(str(sap_no), cell_style),
                        Paragraph('Tool ID / Drawing Number:', header_cell_style),
                        Paragraph(str(tool_id), cell_style)
                    ],
                    [
                        Paragraph('(BFM) Equipment Number:', header_cell_style),
                        Paragraph(str(bfm_no), cell_style),
                        Paragraph('Description of Equipment:', header_cell_style),
                        Paragraph(str(description), cell_style)
                    ],
                    [
                        Paragraph('Date of Last PM:', header_cell_style),
                        Paragraph('', cell_style),
                        Paragraph('Location of Equipment:', header_cell_style),
                        Paragraph(str(location), cell_style)
                    ],
                    [
                        Paragraph('Maintenance Technician:', header_cell_style),
                        Paragraph(str(assigned_tech), cell_style),
                        Paragraph('PM Cycle:', header_cell_style),
                        Paragraph(str(pm_type), cell_style)
                    ],
                    [
                        Paragraph('Estimated Hours:', header_cell_style),
                        Paragraph(f'{estimated_hours:.1f}h', cell_style),
                        Paragraph('Date of PM Completion:', header_cell_style),
                        Paragraph('', cell_style)
                    ],
                    [
                        Paragraph('Signature of Technician:', header_cell_style),
                        Paragraph('', cell_style),
                        Paragraph('', cell_style),
                        Paragraph('', cell_style)
                    ],
                    [
                        Paragraph('Safety: Always be aware of both Airbus and AIT safety policies and ensure safety policies are followed.', cell_style),
                        Paragraph('', cell_style),
                        Paragraph('', cell_style),
                        Paragraph('', cell_style)
                    ],
                    [
                        Paragraph(f'Printed: {datetime.now().strftime("%m/%d/%Y")}', cell_style),
                        '', '', ''
                    ]
                ]

                equipment_table = Table(equipment_data, colWidths=[1.8*inch, 1.7*inch, 1.8*inch, 1.7*inch])
                equipment_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('SPAN', (0, -2), (-1, -2)),  # Safety spans all columns
                    ('SPAN', (0, -1), (-1, -1)),  # Printed date spans all columns
                ]))

                story.append(equipment_table)
                story.append(Spacer(1, 15))

                # =================== PM CHECKLIST TABLE ===================
                checklist_data = [
                    [
                        Paragraph('', header_cell_style),
                        Paragraph('PM CHECKLIST:', header_cell_style),
                        Paragraph('', header_cell_style),
                        Paragraph('Complete', header_cell_style),
                        Paragraph('Labor Time', header_cell_style)
                    ]
                ]

                # Add checklist items
                for idx, item in enumerate(checklist_items, 1):
                    checklist_data.append([
                        Paragraph(str(idx), cell_style),
                        Paragraph(item, cell_style),
                        Paragraph('', cell_style),
                        Paragraph('', cell_style),
                        Paragraph('', cell_style)
                    ])

                checklist_table = Table(checklist_data, colWidths=[0.3*inch, 3.5*inch, 1.5*inch, 0.8*inch, 0.9*inch])
                checklist_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('SPAN', (1, 0), (2, 0)),  # PM CHECKLIST spans 2 columns
                ]))

                story.append(checklist_table)
                story.append(Spacer(1, 15))

                # =================== SPECIAL INSTRUCTIONS & SAFETY NOTES ===================
                # Add special instructions from custom template if available
                if special_instructions and special_instructions.strip():
                    instructions_style = ParagraphStyle(
                        'InstructionsStyle',
                        parent=styles['Normal'],
                        fontSize=9,
                        leading=11,
                        textColor=colors.darkblue,
                        fontName='Helvetica-Bold'
                    )
                    content_style = ParagraphStyle(
                        'ContentStyle',
                        parent=styles['Normal'],
                        fontSize=8,
                        leading=10
                    )

                    story.append(Paragraph("SPECIAL INSTRUCTIONS:", instructions_style))
                    story.append(Paragraph(special_instructions, content_style))
                    story.append(Spacer(1, 10))

                # Add safety notes from custom template if available
                if safety_notes and safety_notes.strip():
                    safety_style = ParagraphStyle(
                        'SafetyStyle',
                        parent=styles['Normal'],
                        fontSize=9,
                        leading=11,
                        textColor=colors.red,
                        fontName='Helvetica-Bold'
                    )
                    safety_content_style = ParagraphStyle(
                        'SafetyContentStyle',
                        parent=styles['Normal'],
                        fontSize=8,
                        leading=10,
                        textColor=colors.black
                    )

                    story.append(Paragraph("SAFETY NOTES:", safety_style))
                    story.append(Paragraph(safety_notes, safety_content_style))
                    story.append(Spacer(1, 10))

                # =================== COMPLETION INFORMATION TABLE ===================
                completion_data = [
                    [
                        Paragraph('Notes from Technician:', header_cell_style),
                        Paragraph('', cell_style),
                        Paragraph('Next Annual PM Date:', header_cell_style)
                    ],
                    [
                        Paragraph('', cell_style),
                        Paragraph('', cell_style),
                        Paragraph('', cell_style)
                    ],
                    [
                        Paragraph('All Data Entered Into System:', header_cell_style),
                        Paragraph('', cell_style),
                        Paragraph('Total Time', header_cell_style)
                    ],
                    [
                        Paragraph('Document Name', header_cell_style),
                        Paragraph('Revision', header_cell_style),
                        Paragraph('', cell_style)
                    ],
                    [
                        Paragraph('Preventive_Maintenance_Form', cell_style),
                        Paragraph('A2', cell_style),
                        Paragraph('', cell_style)
                    ]
                ]

                completion_table = Table(completion_data, colWidths=[2.8*inch, 2.2*inch, 2*inch])
                completion_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))

                story.append(completion_table)

                # Add page break after each PM form (except the last one)
                if i < len(assignments) - 1:
                    story.append(PageBreak())

            # Build PDF
            print(f"DEBUG: Building PDF with {len(story)} elements")
            doc.build(story)
            print(f"DEBUG: PDF created successfully: {filename}")

        except Exception as e:
            print(f"Error creating PM forms PDF: {e}")
            traceback.print_exc()
            raise

    def export_weekly_schedule(self):
        """Export weekly schedule to Excel"""
        try:
            week_start = self.week_combo.currentText()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_filename = f"Weekly_PM_Schedule_{week_start}_{timestamp}.xlsx"

            # Open file dialog
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Weekly Schedule",
                default_filename,
                "Excel Files (*.xlsx);;All Files (*)"
            )

            if not filename:
                return

            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT ws.assigned_technician, ws.bfm_equipment_no, e.description,
                       ws.pm_type, ws.scheduled_date, ws.status
                FROM weekly_pm_schedules ws
                JOIN equipment e ON ws.bfm_equipment_no = e.bfm_equipment_no
                WHERE ws.week_start_date = %s
                ORDER BY ws.assigned_technician, ws.scheduled_date
            ''', (week_start,))

            schedule_data = cursor.fetchall()

            if not schedule_data:
                QMessageBox.warning(
                    self,
                    "No Data",
                    f"No PM schedule data found for week {week_start}"
                )
                return

            # Create DataFrame
            df = pd.DataFrame(schedule_data, columns=[
                'Technician', 'BFM Equipment No', 'Description', 'PM Type', 'Scheduled Date', 'Status'
            ])

            # Export to Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Weekly Schedule', index=False)

                # Create summary sheet
                summary_data = []
                for tech in self.technicians:
                    tech_count = len(df[df['Technician'] == tech])
                    summary_data.append([tech, tech_count])

                summary_df = pd.DataFrame(summary_data, columns=['Technician', 'Assigned PMs'])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

            QMessageBox.information(
                self,
                "Success",
                f"Weekly schedule exported to:\n{filename}"
            )
            self.status_updated.emit(f"Exported weekly schedule to {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export weekly schedule: {str(e)}")
            traceback.print_exc()

    def generate_monthly_summary_report(self):
        """Generate and export monthly PM summary report to PDF"""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
            from PyQt5.QtCore import Qt
            from datetime import datetime

            # Create date selection dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Monthly PM Summary Report")
            dialog.setGeometry(100, 100, 400, 150)

            layout = QVBoxLayout()

            # Month selection
            month_layout = QHBoxLayout()
            month_layout.addWidget(QLabel("Select Month:"))
            month_combo = QComboBox()
            months = ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December']
            month_combo.addItems(months)
            current_month = datetime.now().month - 1
            month_combo.setCurrentIndex(current_month)
            month_layout.addWidget(month_combo)
            layout.addLayout(month_layout)

            # Year selection
            year_layout = QHBoxLayout()
            year_layout.addWidget(QLabel("Select Year:"))
            year_combo = QComboBox()
            current_year = datetime.now().year
            for year in range(current_year - 2, current_year + 1):
                year_combo.addItem(str(year))
            year_combo.setCurrentIndex(2)  # Current year
            year_layout.addWidget(year_combo)
            layout.addLayout(year_layout)

            # Buttons
            button_layout = QHBoxLayout()

            ok_button = QPushButton("Generate PDF")
            ok_button.clicked.connect(dialog.accept)
            button_layout.addWidget(ok_button)

            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_button)

            layout.addLayout(button_layout)
            layout.addStretch()

            dialog.setLayout(layout)

            if dialog.exec_() == QDialog.Accepted:
                selected_month = month_combo.currentIndex() + 1
                selected_year = int(year_combo.currentText())
                self.export_monthly_summary_pdf(selected_month, selected_year)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report: {str(e)}")
            traceback.print_exc()

    def export_monthly_summary_pdf(self, month: int, year: int):
        """Generate comprehensive monthly PM summary as PDF with all data"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            from datetime import datetime, timedelta
            import calendar

            # Create filename
            month_name = calendar.month_name[month]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_filename = f"AIT_Monthly_Report_{month_name}_{year}_{timestamp}.pdf"

            # Open file dialog
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Monthly Summary",
                default_filename,
                "PDF Files (*.pdf);;All Files (*)"
            )

            if not filename:
                return

            # Create PDF document
            doc = SimpleDocTemplate(filename, pagesize=letter,
                                  rightMargin=36, leftMargin=36,
                                  topMargin=50, bottomMargin=36)

            styles = getSampleStyleSheet()
            story = []

            # ==================== CUSTOM STYLES ====================
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a365d'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#2c5282'),
                spaceAfter=12,
                spaceBefore=12,
                fontName='Helvetica-Bold'
            )

            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#2d3748'),
                spaceAfter=6,
                fontName='Helvetica'
            )

            # ==================== TITLE PAGE ====================
            story.append(Paragraph("AIRBUS AIT", title_style))
            story.append(Paragraph("Monthly Maintenance Summary Report",
                                ParagraphStyle('Subtitle', parent=styles['Normal'],
                                           fontSize=16, alignment=TA_CENTER,
                                           textColor=colors.HexColor('#4a5568'))))
            story.append(Spacer(1, 20))

            # Report metadata box
            meta_data = [
                ['Report Period:', f'{month_name} {year}'],
                ['Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')],
                ['Report Type:', 'Comprehensive Monthly Summary']
            ]

            meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
            meta_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e2e8f0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))

            story.append(meta_table)
            story.append(Spacer(1, 30))

            # ==================== EXECUTIVE SUMMARY ====================
            story.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
            story.append(Spacer(1, 10))

            # Get PM summary data
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            start_date = f"{year}-{month:02d}-01"
            last_day = calendar.monthrange(year, month)[1]
            end_date = f"{year}-{month:02d}-{last_day}"

            cursor.execute('''
                SELECT
                    COUNT(*) as total_completions,
                    SUM(labor_hours + labor_minutes/60.0) as total_hours,
                    AVG(labor_hours + labor_minutes/60.0) as avg_hours
                FROM pm_completions
                WHERE completion_date::date BETWEEN %s::date AND %s::date
            ''', (start_date, end_date))

            pm_result = cursor.fetchone()
            pm_completions = pm_result['total_completions'] or 0
            pm_total_hours = pm_result['total_hours'] or 0.0
            pm_avg_hours = pm_result['avg_hours'] or 0.0

            # Get CM created this month
            cursor.execute('''
                SELECT COUNT(*) as count FROM corrective_maintenance
                WHERE created_date::date BETWEEN %s::date AND %s::date
            ''', (start_date, end_date))
            cms_created = cursor.fetchone()['count'] or 0

            # Get CM closed this month
            cursor.execute('''
                SELECT COUNT(*) as count FROM corrective_maintenance
                WHERE completion_date::date BETWEEN %s::date AND %s::date
                AND status IN ('Closed', 'Completed')
            ''', (start_date, end_date))
            cms_closed = cursor.fetchone()['count'] or 0

            # Summary highlights table
            summary_data = [
                ['METRIC', 'VALUE'],
                ['PM Completions', f'{pm_completions:,}'],
                ['Total PM Labor Hours', f'{pm_total_hours:.1f} hrs'],
                ['Average Time per PM', f'{pm_avg_hours:.1f} hrs'],
                ['CMs Created', f'{cms_created:,}'],
                ['CMs Closed', f'{cms_closed:,}']
            ]

            summary_table = Table(summary_data, colWidths=[3.5*inch, 2.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 11),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
            ]))

            story.append(summary_table)
            story.append(Spacer(1, 25))

            # ==================== CORRECTIVE MAINTENANCE DETAIL ====================
            story.append(Paragraph("CORRECTIVE MAINTENANCE ANALYSIS", heading_style))
            story.append(Spacer(1, 10))

            # Get CM breakdown data
            cursor.execute('''
                SELECT COUNT(*) as count FROM corrective_maintenance
                WHERE created_date::date BETWEEN %s::date AND %s::date
                AND completion_date::date BETWEEN %s::date AND %s::date
                AND status IN ('Closed', 'Completed')
            ''', (start_date, end_date, start_date, end_date))
            cms_created_and_closed = cursor.fetchone()['count'] or 0

            cursor.execute('''
                SELECT COUNT(*) as count FROM corrective_maintenance
                WHERE NOT (created_date::date BETWEEN %s::date AND %s::date)
                AND completion_date::date BETWEEN %s::date AND %s::date
                AND status IN ('Closed', 'Completed')
            ''', (start_date, end_date, start_date, end_date))
            cms_closed_from_before = cursor.fetchone()['count'] or 0

            cursor.execute("SELECT COUNT(*) as count FROM corrective_maintenance WHERE status = 'Open'")
            cms_open_current = cursor.fetchone()['count'] or 0

            # Get CM labor hours
            cursor.execute('''
                SELECT
                    SUM(labor_hours) as total_hours,
                    AVG(labor_hours) as avg_hours
                FROM corrective_maintenance
                WHERE completion_date::date BETWEEN %s::date AND %s::date
                AND status IN ('Closed', 'Completed')
            ''', (start_date, end_date))

            cm_hours_result = cursor.fetchone()
            cm_total_hours = cm_hours_result['total_hours'] or 0.0
            cm_avg_hours = cm_hours_result['avg_hours'] or 0.0

            # Get days to close
            cursor.execute('''
                SELECT
                    SUM(completion_date::date - created_date::date) as total_days_to_close,
                    AVG(completion_date::date - created_date::date) as avg_days_to_close
                FROM corrective_maintenance
                WHERE completion_date::date BETWEEN %s::date AND %s::date
                AND status IN ('Closed', 'Completed')
            ''', (start_date, end_date))

            closed_days_result = cursor.fetchone()
            cms_total_days_to_close = closed_days_result['total_days_to_close'] or 0
            cms_avg_days_to_close = closed_days_result['avg_days_to_close'] or 0.0

            # CM breakdown table
            cm_breakdown_data = [
                ['CATEGORY', 'VALUE'],
                ['CMs Created This Month', str(cms_created)],
                ['CMs Closed This Month', str(cms_closed)],
                ['  - Created & Closed Same Month', str(cms_created_and_closed)],
                [f'  - Carried Over from Prior Months', str(cms_closed_from_before)]
            ]

            if cms_closed > 0:
                cm_breakdown_data.extend([
                    ['  - Total Days to Close (All Closed CMs)', f'{int(cms_total_days_to_close)} days'],
                    ['  - Average Days to Close per CM', f'{cms_avg_days_to_close:.1f} days']
                ])

            cm_breakdown_data.extend([
                ['CM Total Labor Hours (Closed)', f'{cm_total_hours:.1f} hours'],
                ['CM Average Hours per Closure', f'{cm_avg_hours:.1f} hours'],
                ['Currently Open CMs', str(cms_open_current)]
            ])

            cm_table = Table(cm_breakdown_data, colWidths=[4.5*inch, 1.5*inch])
            cm_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BACKGROUND', (0, 1), (-1, 2), colors.white),
                ('BACKGROUND', (0, 3), (-1, -1), colors.HexColor('#f7fafc')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('LEFTPADDING', (0, 3), (0, 4), 24),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))

            story.append(cm_table)
            story.append(Spacer(1, 20))

            # ==================== OVERALL MAINTENANCE EFFICIENCY ====================
            story.append(Paragraph("OVERALL MAINTENANCE EFFICIENCY", heading_style))
            story.append(Spacer(1, 10))

            # Efficiency calculation
            TOTAL_TECHNICIANS = 9
            ANNUAL_HOURS_PER_TECHNICIAN = 1980
            MONTHLY_AVAILABLE_HOURS = (TOTAL_TECHNICIANS * ANNUAL_HOURS_PER_TECHNICIAN) / 12
            WEEKLY_AVAILABLE_HOURS = 342.69
            TARGET_EFFICIENCY_RATE = 80.0

            # Calculate total maintenance hours
            total_maintenance_hours = pm_total_hours + cm_total_hours
            efficiency_rate = (total_maintenance_hours / MONTHLY_AVAILABLE_HOURS) * 100 if MONTHLY_AVAILABLE_HOURS > 0 else 0.0

            # Determine status and color
            if efficiency_rate >= TARGET_EFFICIENCY_RATE:
                efficiency_status = "MEETS TARGET ✓"
                status_color = colors.HexColor('#22c55e')
            else:
                efficiency_status = "BELOW TARGET ✗"
                status_color = colors.HexColor('#ef4444')

            # Build efficiency data table
            efficiency_data = [
                ['METRIC', 'VALUE'],
                ['Total PM Hours', f'{pm_total_hours:.1f} hours'],
                ['Total CM Hours', f'{cm_total_hours:.1f} hours'],
                ['Total Maintenance Hours', f'{total_maintenance_hours:.1f} hours'],
                ['Monthly Available Hours', f'{MONTHLY_AVAILABLE_HOURS:.1f} hours'],
                ['Weekly Available Hours', f'{WEEKLY_AVAILABLE_HOURS:.2f} hours'],
                ['Overall Efficiency Rate', f'{efficiency_rate:.1f}%'],
                ['Target Efficiency Rate', f'{TARGET_EFFICIENCY_RATE:.1f}%'],
                ['Status', efficiency_status]
            ]

            efficiency_table = Table(efficiency_data, colWidths=[3*inch, 3*inch])
            efficiency_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor('#e0f2fe')),
                ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 6), (-1, 6), 11),
                ('BACKGROUND', (0, 8), (-1, 8), colors.HexColor('#f0fdf4') if efficiency_rate >= TARGET_EFFICIENCY_RATE else colors.HexColor('#fef2f2')),
                ('TEXTCOLOR', (1, 8), (1, 8), status_color),
                ('FONTNAME', (0, 8), (-1, 8), 'Helvetica-Bold'),
            ]))

            story.append(efficiency_table)
            story.append(Spacer(1, 20))

            # ==================== TECHNICIAN PERFORMANCE ====================
            story.append(Paragraph("TECHNICIAN PERFORMANCE", heading_style))
            story.append(Spacer(1, 10))

            # Get technician PM performance
            cursor.execute('''
                SELECT technician_name, COUNT(*) as count, SUM(labor_hours + labor_minutes/60.0) as total_hours
                FROM pm_completions
                WHERE completion_date::date BETWEEN %s::date AND %s::date
                GROUP BY technician_name
                ORDER BY count DESC
            ''', (start_date, end_date))

            tech_data = cursor.fetchall()

            if tech_data:
                tech_table_data = [['Technician', 'PMs Completed', 'Total Hours']]

                for row in tech_data:
                    tech_name = row['technician_name'] or 'Unknown'
                    count = row['count'] or 0
                    hours = row['total_hours'] or 0
                    tech_table_data.append([tech_name, str(count), f"{hours:.1f}"])

                tech_table = Table(tech_table_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
                tech_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(tech_table)
            else:
                story.append(Paragraph("No technician data available.", body_style))

            # Build and save PDF
            doc.build(story)

            QMessageBox.information(
                self,
                "Success",
                f"Monthly report generated successfully!\n\nSaved to:\n{filename}"
            )
            self.status_updated.emit(f"Monthly summary report generated: {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export PDF: {str(e)}")
            traceback.print_exc()

    def update_status(self, message):
        """Update status bar with message"""
        self.status_updated.emit(message)
