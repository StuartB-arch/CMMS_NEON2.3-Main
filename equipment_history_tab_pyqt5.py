"""
Equipment History Tab - PyQt5 Implementation
Complete equipment maintenance history tracking and visualization

This module provides comprehensive equipment history tracking including:
- Complete PM and CM history timeline
- Visual timeline with color-coded events
- Event filtering by date range and type
- Statistics summary (total PMs/CMs, labor hours, costs)
- Equipment health scoring
- Event detail dialogs
- Export to PDF/CSV
- Interactive timeline visualization with tooltips
"""

from psycopg2 import extras
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QDialog, QFormLayout,
    QCheckBox, QMessageBox, QFileDialog, QGroupBox, QHeaderView,
    QTextEdit, QDialogButtonBox, QDateEdit, QSplitter, QFrame,
    QAbstractItemView, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QToolTip, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate, QRectF, QPointF
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainter
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import csv
import traceback


class TimelineEvent:
    """Represents a single event on the timeline"""

    def __init__(self, date, event_type, category, title, details, notes, color):
        """
        Initialize timeline event

        Args:
            date: Event date
            event_type: Type of event (PM, CM_OPEN, CM_CLOSE, PART, STATUS)
            category: Event category
            title: Event title
            details: Event details
            notes: Additional notes
            color: Display color (hex)
        """
        self.date = date
        self.event_type = event_type
        self.category = category
        self.title = title
        self.details = details
        self.notes = notes
        self.color = color


class TimelineGraphicsItem(QGraphicsRectItem):
    """Custom graphics item for timeline events with tooltips"""

    def __init__(self, event, x, y, width, height):
        """
        Initialize timeline graphics item

        Args:
            event: TimelineEvent object
            x, y: Position coordinates
            width, height: Item dimensions
        """
        super().__init__(x, y, width, height)
        self.event = event

        # Set appearance
        color = QColor(event.color)
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(120), 1))

        # Enable hover events
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        """Show tooltip on hover"""
        tooltip = f"<b>{self.event.title}</b><br>"
        tooltip += f"Date: {self.event.date}<br>"
        tooltip += f"Category: {self.event.category}<br>"
        tooltip += f"{self.event.details}"

        QToolTip.showText(event.screenPos(), tooltip)

        # Highlight on hover
        self.setBrush(QBrush(QColor(self.event.color).lighter(120)))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Reset appearance on hover leave"""
        self.setBrush(QBrush(QColor(self.event.color)))
        super().hoverLeaveEvent(event)


class TimelineWidget(QGraphicsView):
    """Timeline visualization widget showing maintenance events over time"""

    event_clicked = pyqtSignal(dict)  # Signal emitted when event is clicked

    def __init__(self, parent=None):
        """Initialize timeline widget"""
        super().__init__(parent)

        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Configure view
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.events = []

    def set_events(self, events: List[Dict]):
        """
        Set and display timeline events

        Args:
            events: List of event dictionaries
        """
        self.events = events
        self.draw_timeline()

    def draw_timeline(self):
        """Draw the timeline visualization"""
        self.scene.clear()

        if not self.events:
            # Show "No events" message
            text = self.scene.addText("No events to display")
            text.setPos(10, 10)
            return

        # Timeline parameters
        margin = 50
        timeline_width = max(800, self.width() - 2 * margin)
        event_height = 30
        vertical_spacing = 10

        # Find date range
        dates = [datetime.strptime(str(e['date']), '%Y-%m-%d') if isinstance(e['date'], str)
                else e['date'] for e in self.events]
        min_date = min(dates)
        max_date = max(dates)
        date_range = (max_date - min_date).days or 1

        # Draw timeline axis
        axis_y = margin
        self.scene.addLine(margin, axis_y, margin + timeline_width, axis_y,
                          QPen(Qt.black, 2))

        # Draw date labels
        num_labels = 5
        for i in range(num_labels):
            x = margin + (timeline_width * i / (num_labels - 1))
            label_date = min_date + timedelta(days=date_range * i / (num_labels - 1))

            # Tick mark
            self.scene.addLine(x, axis_y - 5, x, axis_y + 5, QPen(Qt.black, 1))

            # Date label
            text = self.scene.addText(label_date.strftime('%Y-%m-%d'))
            text.setPos(x - 30, axis_y + 10)
            font = QFont()
            font.setPointSize(8)
            text.setFont(font)

        # Draw events
        y_offset = axis_y + 60

        for event in self.events:
            event_date = datetime.strptime(str(event['date']), '%Y-%m-%d') if isinstance(event['date'], str) else event['date']

            # Calculate x position based on date
            days_from_start = (event_date - min_date).days
            x_pos = margin + (timeline_width * days_from_start / date_range)

            # Create event item
            event_obj = TimelineEvent(
                event['date'],
                event['type'],
                event['category'],
                event['title'],
                event['details'],
                event.get('notes', ''),
                event['color']
            )

            item = TimelineGraphicsItem(event_obj, x_pos - 5, y_offset, 10, event_height)
            self.scene.addItem(item)

            # Add event label
            label = self.scene.addText(event['title'])
            font = QFont()
            font.setPointSize(7)
            label.setFont(font)
            label.setPos(x_pos + 15, y_offset)

            # Connect line to axis
            self.scene.addLine(x_pos, axis_y, x_pos, y_offset,
                             QPen(QColor(event['color']).lighter(150), 1, Qt.DashLine))

            y_offset += event_height + vertical_spacing

        # Set scene rect
        self.scene.setSceneRect(0, 0, timeline_width + 2 * margin,
                               y_offset + margin)


class EventDetailDialog(QDialog):
    """Dialog showing complete details of a maintenance event"""

    def __init__(self, event_data: Dict, parent=None):
        """
        Initialize event detail dialog

        Args:
            event_data: Dictionary containing event information
            parent: Parent widget
        """
        super().__init__(parent)
        self.event_data = event_data

        self.setWindowTitle("Event Details")
        self.setModal(True)
        self.resize(600, 500)

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()

        # Event information
        info_group = QGroupBox("Event Information")
        info_layout = QFormLayout()

        # Create read-only fields
        date_field = QLineEdit(str(self.event_data.get('date', 'N/A')))
        date_field.setReadOnly(True)
        info_layout.addRow("Date:", date_field)

        type_field = QLineEdit(self.event_data.get('event_type', 'N/A'))
        type_field.setReadOnly(True)
        info_layout.addRow("Event Type:", type_field)

        if 'pm_type' in self.event_data:
            pm_type_field = QLineEdit(self.event_data.get('pm_type', 'N/A'))
            pm_type_field.setReadOnly(True)
            info_layout.addRow("PM Type:", pm_type_field)

        if 'cm_number' in self.event_data:
            cm_field = QLineEdit(str(self.event_data.get('cm_number', 'N/A')))
            cm_field.setReadOnly(True)
            info_layout.addRow("CM Number:", cm_field)

        if 'description' in self.event_data:
            desc_field = QLineEdit(self.event_data.get('description', 'N/A'))
            desc_field.setReadOnly(True)
            info_layout.addRow("Description:", desc_field)

        if 'technician' in self.event_data:
            tech_field = QLineEdit(self.event_data.get('technician', 'N/A'))
            tech_field.setReadOnly(True)
            info_layout.addRow("Technician:", tech_field)

        if 'labor_hours' in self.event_data:
            hours_field = QLineEdit(str(self.event_data.get('labor_hours', '0')))
            hours_field.setReadOnly(True)
            info_layout.addRow("Labor Hours:", hours_field)

        if 'priority' in self.event_data:
            priority_field = QLineEdit(self.event_data.get('priority', 'N/A'))
            priority_field.setReadOnly(True)
            info_layout.addRow("Priority:", priority_field)

        if 'status' in self.event_data:
            status_field = QLineEdit(self.event_data.get('status', 'N/A'))
            status_field.setReadOnly(True)
            info_layout.addRow("Status:", status_field)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Notes section
        if 'notes' in self.event_data and self.event_data['notes']:
            notes_group = QGroupBox("Notes")
            notes_layout = QVBoxLayout()

            notes_text = QTextEdit()
            notes_text.setPlainText(self.event_data['notes'])
            notes_text.setReadOnly(True)
            notes_text.setMaximumHeight(150)
            notes_layout.addWidget(notes_text)

            notes_group.setLayout(notes_layout)
            layout.addWidget(notes_group)

        # Parts information (if applicable)
        if 'part_number' in self.event_data:
            parts_group = QGroupBox("Parts Information")
            parts_layout = QFormLayout()

            part_num = QLineEdit(self.event_data.get('part_number', 'N/A'))
            part_num.setReadOnly(True)
            parts_layout.addRow("Part Number:", part_num)

            if 'model_number' in self.event_data:
                model_num = QLineEdit(self.event_data.get('model_number', 'N/A'))
                model_num.setReadOnly(True)
                parts_layout.addRow("Model Number:", model_num)

            parts_group.setLayout(parts_layout)
            layout.addWidget(parts_group)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)


class EquipmentHistoryTab(QWidget):
    """Equipment History Tab - Main widget for viewing equipment maintenance history"""

    status_updated = pyqtSignal(str)  # Signal to update status bar

    def __init__(self, conn, parent=None):
        """
        Initialize Equipment History Tab

        Args:
            conn: Database connection object
            parent: Parent widget
        """
        super().__init__(parent)
        self.conn = conn
        self.current_bfm = None
        self.all_events = []  # Store all events for filtering

        self.init_ui()
        self.load_equipment_list()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Equipment selection frame
        selection_frame = self.create_selection_frame()
        layout.addWidget(selection_frame)

        # Statistics frame
        stats_frame = self.create_statistics_frame()
        layout.addWidget(stats_frame)

        # Filter frame
        filter_frame = self.create_filter_frame()
        layout.addWidget(filter_frame)

        # Create splitter for timeline and table
        splitter = QSplitter(Qt.Vertical)

        # Timeline view
        timeline_group = QGroupBox("Timeline View")
        timeline_layout = QVBoxLayout()
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.setMinimumHeight(200)
        timeline_layout.addWidget(self.timeline_widget)
        timeline_group.setLayout(timeline_layout)
        splitter.addWidget(timeline_group)

        # Events table
        table_group = QGroupBox("Event History")
        table_layout = QVBoxLayout()
        self.create_events_table()
        table_layout.addWidget(self.events_table)
        table_group.setLayout(table_layout)
        splitter.addWidget(table_group)

        # Set initial splitter sizes
        splitter.setSizes([300, 400])

        layout.addWidget(splitter)

        # Export buttons
        export_frame = self.create_export_frame()
        layout.addWidget(export_frame)

        self.setLayout(layout)

    def create_selection_frame(self):
        """Create equipment selection frame"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout()

        # Label
        label = QLabel("Select Equipment:")
        label_font = QFont()
        label_font.setBold(True)
        label_font.setPointSize(10)
        label.setFont(label_font)
        layout.addWidget(label)

        # Equipment combo box
        self.equipment_combo = QComboBox()
        self.equipment_combo.setMinimumWidth(300)
        self.equipment_combo.currentTextChanged.connect(self.on_equipment_selected)
        layout.addWidget(self.equipment_combo)

        # Search field
        layout.addWidget(QLabel("Search:"))
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Enter BFM number or description...")
        self.search_field.textChanged.connect(self.filter_equipment_list)
        self.search_field.setMinimumWidth(250)
        layout.addWidget(self.search_field)

        # Refresh button
        refresh_btn = QPushButton("Refresh Equipment")
        refresh_btn.clicked.connect(self.load_equipment_list)
        layout.addWidget(refresh_btn)

        layout.addStretch()

        frame.setLayout(layout)
        return frame

    def create_statistics_frame(self):
        """Create statistics display frame"""
        frame = QGroupBox("Equipment Statistics")
        layout = QHBoxLayout()

        # Create statistics labels
        bold_font = QFont()
        bold_font.setBold(True)
        bold_font.setPointSize(10)

        self.stats_pm_label = QLabel("Total PMs: 0")
        self.stats_pm_label.setFont(bold_font)
        self.stats_pm_label.setStyleSheet("color: green;")
        layout.addWidget(self.stats_pm_label)

        self.stats_cm_label = QLabel("Total CMs: 0")
        self.stats_cm_label.setFont(bold_font)
        self.stats_cm_label.setStyleSheet("color: orange;")
        layout.addWidget(self.stats_cm_label)

        self.stats_hours_label = QLabel("Total Hours: 0.0")
        self.stats_hours_label.setFont(bold_font)
        self.stats_hours_label.setStyleSheet("color: blue;")
        layout.addWidget(self.stats_hours_label)

        self.stats_health_label = QLabel("Health Score: --")
        self.stats_health_label.setFont(bold_font)
        layout.addWidget(self.stats_health_label)

        self.stats_last_pm_label = QLabel("Last PM: --")
        self.stats_last_pm_label.setFont(bold_font)
        layout.addWidget(self.stats_last_pm_label)

        self.stats_last_cm_label = QLabel("Last CM: --")
        self.stats_last_cm_label.setFont(bold_font)
        layout.addWidget(self.stats_last_cm_label)

        layout.addStretch()

        frame.setLayout(layout)
        return frame

    def create_filter_frame(self):
        """Create filter controls frame"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout()

        # Date range filters
        layout.addWidget(QLabel("From:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.dateChanged.connect(self.apply_filters)
        layout.addWidget(self.start_date)

        layout.addWidget(QLabel("To:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.dateChanged.connect(self.apply_filters)
        layout.addWidget(self.end_date)

        # Event type filter
        layout.addWidget(QLabel("Event Type:"))
        self.event_type_combo = QComboBox()
        self.event_type_combo.addItems(["All Events", "PM Only", "CM Only", "Parts Only"])
        self.event_type_combo.currentTextChanged.connect(self.apply_filters)
        layout.addWidget(self.event_type_combo)

        # Quick date presets
        layout.addWidget(QLabel("Quick Select:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Last 30 Days", "Last 90 Days", "Last 6 Months",
                                   "Last Year", "Last 2 Years", "All Time"])
        self.preset_combo.currentTextChanged.connect(self.apply_date_preset)
        layout.addWidget(self.preset_combo)

        # Apply filters button
        apply_btn = QPushButton("Apply Filters")
        apply_btn.clicked.connect(self.apply_filters)
        layout.addWidget(apply_btn)

        # Reset filters button
        reset_btn = QPushButton("Reset Filters")
        reset_btn.clicked.connect(self.reset_filters)
        layout.addWidget(reset_btn)

        layout.addStretch()

        frame.setLayout(layout)
        return frame

    def create_events_table(self):
        """Create events table widget"""
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(8)
        self.events_table.setHorizontalHeaderLabels([
            "Date", "Event Type", "Description", "Technician",
            "Labor Hours", "Priority/Type", "Status", "Details"
        ])

        # Configure table
        self.events_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.events_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.events_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.events_table.setSortingEnabled(True)
        self.events_table.setAlternatingRowColors(True)

        # Set column widths
        header = self.events_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Event Type
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Description
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Technician
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Hours
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Priority/Type
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(7, QHeaderView.Fixed)             # Details button
        self.events_table.setColumnWidth(7, 80)

        # Double-click to view details
        self.events_table.cellDoubleClicked.connect(self.show_event_details)

    def create_export_frame(self):
        """Create export buttons frame"""
        frame = QFrame()
        layout = QHBoxLayout()

        # Export to CSV button
        csv_btn = QPushButton("Export to CSV")
        csv_btn.clicked.connect(self.export_to_csv)
        layout.addWidget(csv_btn)

        # Export to PDF button (placeholder for future implementation)
        pdf_btn = QPushButton("Export to PDF")
        pdf_btn.clicked.connect(self.export_to_pdf)
        layout.addWidget(pdf_btn)

        # View health report button
        health_btn = QPushButton("View Health Report")
        health_btn.clicked.connect(self.show_health_report)
        layout.addWidget(health_btn)

        layout.addStretch()

        frame.setLayout(layout)
        return frame

    def load_equipment_list(self):
        """Load list of equipment from database"""
        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute('''
                SELECT bfm_equipment_no, short_description, status
                FROM equipment
                ORDER BY bfm_equipment_no
            ''')

            self.equipment_combo.clear()
            self.equipment_list = []

            for row in cursor.fetchall():
                bfm_no = row['bfm_equipment_no']
                description = row['short_description'] or "No description"
                status = row['status'] or "Unknown"
                display_text = f"{bfm_no} - {description} ({status})"
                self.equipment_combo.addItem(display_text, bfm_no)
                self.equipment_list.append((bfm_no, description, status))

            self.conn.commit()
            self.status_updated.emit(f"Loaded {len(self.equipment_list)} equipment items")

        except Exception as e:
            QMessageBox.critical(self, "Database Error",
                               f"Error loading equipment list:\n{str(e)}")
            try:
                self.conn.rollback()
            except:
                pass

    def filter_equipment_list(self):
        """Filter equipment list based on search text"""
        search_text = self.search_field.text().lower()

        if not search_text:
            self.load_equipment_list()
            return

        self.equipment_combo.clear()

        for bfm_no, description, status in self.equipment_list:
            if (search_text in bfm_no.lower() or
                search_text in description.lower()):
                display_text = f"{bfm_no} - {description} ({status})"
                self.equipment_combo.addItem(display_text, bfm_no)

    def on_equipment_selected(self, text):
        """Handle equipment selection"""
        if not text:
            return

        bfm_no = self.equipment_combo.currentData()
        if bfm_no:
            self.current_bfm = bfm_no
            self.load_equipment_history()

    def load_equipment_history(self):
        """Load complete history for selected equipment"""
        if not self.current_bfm:
            return

        try:
            self.all_events = []

            # Get date range from filters
            start_date = self.start_date.date().toString("yyyy-MM-dd")
            end_date = self.end_date.date().toString("yyyy-MM-dd")

            # Get PM completions
            pm_events = self.get_pm_history(start_date, end_date)
            self.all_events.extend(pm_events)

            # Get CM records
            cm_events = self.get_cm_history(start_date, end_date)
            self.all_events.extend(cm_events)

            # Get parts requests
            parts_events = self.get_parts_history(start_date, end_date)
            self.all_events.extend(parts_events)

            # Sort events by date (most recent first)
            self.all_events.sort(key=lambda x: x.get('date', ''), reverse=True)

            # Apply filters and display
            self.apply_filters()

            # Update statistics
            self.update_statistics()

            self.conn.commit()
            self.status_updated.emit(f"Loaded {len(self.all_events)} events for {self.current_bfm}")

        except Exception as e:
            QMessageBox.critical(self, "Database Error",
                               f"Error loading equipment history:\n{str(e)}\n\n{traceback.format_exc()}")
            try:
                self.conn.rollback()
            except:
                pass

    def get_pm_history(self, start_date: str, end_date: str) -> List[Dict]:
        """Get PM completion history"""
        cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

        query = '''
            SELECT completion_date, pm_type, technician_name, labor_hours,
                   notes, special_equipment
            FROM pm_completions
            WHERE bfm_equipment_no = %s
            AND completion_date >= %s
            AND completion_date <= %s
            ORDER BY completion_date DESC
        '''

        cursor.execute(query, (self.current_bfm, start_date, end_date))

        results = []
        for row in cursor.fetchall():
            results.append({
                'date': row['completion_date'],
                'event_type': 'PM',
                'pm_type': row['pm_type'],
                'technician': row['technician_name'],
                'labor_hours': row['labor_hours'] or 0,
                'notes': row['notes'] or '',
                'special_equipment': row['special_equipment'] or '',
                'description': f"{row['pm_type']} PM Completion",
                'status': 'Completed',
                'color': '#4CAF50',  # Green
                'category': 'Preventive Maintenance',
                'title': f"{row['pm_type']} PM",
                'details': f"Technician: {row['technician_name']}, Hours: {row['labor_hours'] or 0}"
            })

        return results

    def get_cm_history(self, start_date: str, end_date: str) -> List[Dict]:
        """Get corrective maintenance history"""
        cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

        query = '''
            SELECT cm_number, reported_date, closed_date, description, priority,
                   status, assigned_technician, labor_hours, notes, root_cause,
                   corrective_action
            FROM corrective_maintenance
            WHERE bfm_equipment_no = %s
            AND reported_date >= %s
            AND reported_date <= %s
            ORDER BY reported_date DESC
        '''

        cursor.execute(query, (self.current_bfm, start_date, end_date))

        results = []
        for row in cursor.fetchall():
            # Determine color based on status
            status = row['status'] or 'Unknown'
            if status == 'Closed':
                color = '#4CAF50'  # Green
            elif status == 'In Progress':
                color = '#FF9800'  # Orange
            else:
                color = '#F44336'  # Red

            results.append({
                'date': row['reported_date'],
                'event_type': 'CM',
                'cm_number': row['cm_number'],
                'date_opened': row['reported_date'],
                'date_closed': row['closed_date'],
                'description': row['description'] or 'No description',
                'priority': row['priority'] or 'Normal',
                'status': status,
                'technician': row['assigned_technician'] or 'Unassigned',
                'labor_hours': row['labor_hours'] or 0,
                'notes': row['notes'] or '',
                'root_cause': row['root_cause'] or '',
                'corrective_action': row['corrective_action'] or '',
                'color': color,
                'category': 'Corrective Maintenance',
                'title': f"CM {row['cm_number']}",
                'details': f"Priority: {row['priority'] or 'Normal'}, Status: {status}"
            })

        return results

    def get_parts_history(self, start_date: str, end_date: str) -> List[Dict]:
        """Get parts usage history"""
        cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

        query = '''
            SELECT cpr.requested_date, cpr.part_number, cpr.model_number,
                   cpr.requested_by, cpr.notes, cm.cm_number
            FROM cm_parts_requests cpr
            JOIN corrective_maintenance cm ON cpr.cm_number = cm.cm_number
            WHERE cm.bfm_equipment_no = %s
            AND cpr.requested_date >= %s
            AND cpr.requested_date <= %s
            ORDER BY cpr.requested_date DESC
        '''

        cursor.execute(query, (self.current_bfm, start_date, end_date))

        results = []
        for row in cursor.fetchall():
            results.append({
                'date': row[0],
                'event_type': 'PART',
                'part_number': row[1],
                'model_number': row[2],
                'technician': row[3],
                'notes': row[4] or '',
                'cm_number': row[5],
                'description': f"Part Request: {row[1]}",
                'labor_hours': 0,
                'status': 'Requested',
                'color': '#2196F3',  # Blue
                'category': 'Parts Request',
                'title': f"Part: {row[1]}",
                'details': f"Model: {row[2]}, CM: {row[5]}"
            })

        return results

    def apply_filters(self):
        """Apply filters to event list"""
        if not self.all_events:
            self.display_events([])
            return

        # Get filter values
        event_type_filter = self.event_type_combo.currentText()

        # Filter events
        filtered_events = []
        for event in self.all_events:
            # Apply event type filter
            if event_type_filter == "PM Only" and event['event_type'] != 'PM':
                continue
            elif event_type_filter == "CM Only" and event['event_type'] != 'CM':
                continue
            elif event_type_filter == "Parts Only" and event['event_type'] != 'PART':
                continue

            filtered_events.append(event)

        # Display filtered events
        self.display_events(filtered_events)

    def apply_date_preset(self, preset):
        """Apply quick date preset"""
        end = QDate.currentDate()

        if preset == "Last 30 Days":
            start = end.addDays(-30)
        elif preset == "Last 90 Days":
            start = end.addDays(-90)
        elif preset == "Last 6 Months":
            start = end.addMonths(-6)
        elif preset == "Last Year":
            start = end.addYears(-1)
        elif preset == "Last 2 Years":
            start = end.addYears(-2)
        elif preset == "All Time":
            start = QDate(2000, 1, 1)
        else:
            return

        self.start_date.setDate(start)
        self.end_date.setDate(end)

        # Reload history with new date range
        if self.current_bfm:
            self.load_equipment_history()

    def reset_filters(self):
        """Reset all filters to defaults"""
        self.event_type_combo.setCurrentIndex(0)
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.end_date.setDate(QDate.currentDate())
        self.preset_combo.setCurrentIndex(3)  # Last Year

        if self.current_bfm:
            self.load_equipment_history()

    def display_events(self, events: List[Dict]):
        """Display events in table and timeline"""
        # Update table
        self.events_table.setRowCount(0)
        self.events_table.setSortingEnabled(False)

        for event in events:
            row = self.events_table.rowCount()
            self.events_table.insertRow(row)

            # Date
            self.events_table.setItem(row, 0, QTableWidgetItem(str(event.get('date', ''))))

            # Event Type
            type_item = QTableWidgetItem(event.get('event_type', ''))
            # Color-code by type
            if event['event_type'] == 'PM':
                type_item.setBackground(QColor('#E8F5E9'))  # Light green
            elif event['event_type'] == 'CM':
                type_item.setBackground(QColor('#FFF3E0'))  # Light orange
            elif event['event_type'] == 'PART':
                type_item.setBackground(QColor('#E3F2FD'))  # Light blue
            self.events_table.setItem(row, 1, type_item)

            # Description
            self.events_table.setItem(row, 2, QTableWidgetItem(event.get('description', '')))

            # Technician
            self.events_table.setItem(row, 3, QTableWidgetItem(event.get('technician', '')))

            # Labor Hours
            hours = str(event.get('labor_hours', 0))
            self.events_table.setItem(row, 4, QTableWidgetItem(hours))

            # Priority/Type
            if event['event_type'] == 'PM':
                detail = event.get('pm_type', '')
            elif event['event_type'] == 'CM':
                detail = event.get('priority', '')
            else:
                detail = event.get('part_number', '')
            self.events_table.setItem(row, 5, QTableWidgetItem(detail))

            # Status
            status_item = QTableWidgetItem(event.get('status', ''))
            # Color-code status
            status = event.get('status', '')
            if status in ['Completed', 'Closed']:
                status_item.setBackground(QColor('#C8E6C9'))  # Light green
            elif status == 'In Progress':
                status_item.setBackground(QColor('#FFE0B2'))  # Light orange
            elif status == 'Open':
                status_item.setBackground(QColor('#FFCDD2'))  # Light red
            self.events_table.setItem(row, 6, status_item)

            # Details button (stored as text, click handled by cellDoubleClicked)
            self.events_table.setItem(row, 7, QTableWidgetItem("Double-click"))

        self.events_table.setSortingEnabled(True)

        # Update timeline
        self.timeline_widget.set_events(events)

        self.status_updated.emit(f"Displaying {len(events)} events")

    def show_event_details(self, row, column):
        """Show detailed information for selected event"""
        if row < 0:
            return

        # Get event data from all_events based on row
        event_type = self.events_table.item(row, 1).text()
        event_date = self.events_table.item(row, 0).text()

        # Find matching event
        event_data = None
        for event in self.all_events:
            if (event.get('event_type') == event_type and
                str(event.get('date')) == event_date):
                event_data = event
                break

        if event_data:
            dialog = EventDetailDialog(event_data, self)
            dialog.exec_()

    def update_statistics(self):
        """Update statistics labels"""
        if not self.all_events:
            self.stats_pm_label.setText("Total PMs: 0")
            self.stats_cm_label.setText("Total CMs: 0")
            self.stats_hours_label.setText("Total Hours: 0.0")
            self.stats_last_pm_label.setText("Last PM: --")
            self.stats_last_cm_label.setText("Last CM: --")
            return

        # Count events by type
        pm_count = len([e for e in self.all_events if e['event_type'] == 'PM'])
        cm_count = len([e for e in self.all_events if e['event_type'] == 'CM'])

        # Calculate total labor hours
        total_hours = sum(float(e.get('labor_hours', 0)) for e in self.all_events)

        # Find last PM and CM dates
        pm_events = [e for e in self.all_events if e['event_type'] == 'PM']
        cm_events = [e for e in self.all_events if e['event_type'] == 'CM']

        last_pm = pm_events[0]['date'] if pm_events else '--'
        last_cm = cm_events[0]['date'] if cm_events else '--'

        # Update labels
        self.stats_pm_label.setText(f"Total PMs: {pm_count}")
        self.stats_cm_label.setText(f"Total CMs: {cm_count}")
        self.stats_hours_label.setText(f"Total Hours: {total_hours:.1f}")
        self.stats_last_pm_label.setText(f"Last PM: {last_pm}")
        self.stats_last_cm_label.setText(f"Last CM: {last_cm}")

        # Calculate and display health score
        self.calculate_health_score()

    def calculate_health_score(self):
        """Calculate equipment health score"""
        if not self.current_bfm:
            return

        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Get equipment info
            cursor.execute('''
                SELECT status, monthly_pm, annual_pm
                FROM equipment
                WHERE bfm_equipment_no = %s
            ''', (self.current_bfm,))

            equip_row = cursor.fetchone()
            if not equip_row:
                return

            status = equip_row[0]
            has_monthly = equip_row[1] == 'X'
            has_annual = equip_row[2] == 'X'

            # Calculate expected PMs in last 12 months
            one_year_ago = QDate.currentDate().addYears(-1).toString("yyyy-MM-dd")
            expected_pms = 0
            if has_monthly:
                expected_pms += 12
            if has_annual:
                expected_pms += 1

            # Count completed PMs
            cursor.execute('''
                SELECT COUNT(*)
                FROM pm_completions
                WHERE bfm_equipment_no = %s
                AND completion_date >= %s
            ''', (self.current_bfm, one_year_ago))

            completed_pms = cursor.fetchone()[0] or 0

            # Count CMs in last 12 months
            cursor.execute('''
                SELECT COUNT(*)
                FROM corrective_maintenance
                WHERE bfm_equipment_no = %s
                AND reported_date >= %s
            ''', (self.current_bfm, one_year_ago))

            cm_count = cursor.fetchone()[0] or 0

            # Calculate health score (0-100)
            score = 100

            # PM compliance
            if expected_pms > 0:
                pm_compliance = min(100, (completed_pms / expected_pms) * 100)
                score -= (100 - pm_compliance) * 0.3

            # CM frequency (more than 1 per month is concerning)
            cm_frequency = cm_count / 12
            if cm_frequency > 1:
                score -= min(20, (cm_frequency - 1) * 10)

            # Equipment status
            if status != 'Active':
                score -= 30

            score = max(0, int(score))

            # Update label with color coding
            self.stats_health_label.setText(f"Health Score: {score}/100")
            if score >= 80:
                self.stats_health_label.setStyleSheet("color: green; font-weight: bold;")
            elif score >= 60:
                self.stats_health_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.stats_health_label.setStyleSheet("color: red; font-weight: bold;")

            self.conn.commit()

        except Exception as e:
            print(f"Error calculating health score: {e}")
            try:
                self.conn.rollback()
            except:
                pass

    def show_health_report(self):
        """Show detailed health report dialog"""
        if not self.current_bfm:
            QMessageBox.warning(self, "No Equipment Selected",
                              "Please select an equipment item first.")
            return

        try:
            cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)

            # Get comprehensive health metrics
            one_year_ago = QDate.currentDate().addYears(-1).toString("yyyy-MM-dd")

            # Get equipment info
            cursor.execute('''
                SELECT status, monthly_pm, annual_pm, short_description
                FROM equipment
                WHERE bfm_equipment_no = %s
            ''', (self.current_bfm,))

            equip_row = cursor.fetchone()
            if not equip_row:
                return

            status, has_monthly, has_annual, description = equip_row

            # PM compliance
            expected_pms = 0
            if has_monthly == 'X':
                expected_pms += 12
            if has_annual == 'X':
                expected_pms += 1

            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(labor_hours), 0)
                FROM pm_completions
                WHERE bfm_equipment_no = %s
                AND completion_date >= %s
            ''', (self.current_bfm, one_year_ago))

            pm_row = cursor.fetchone()
            completed_pms = pm_row[0] or 0
            pm_hours = float(pm_row[1] or 0)

            # CM metrics
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(labor_hours), 0)
                FROM corrective_maintenance
                WHERE bfm_equipment_no = %s
                AND reported_date >= %s
            ''', (self.current_bfm, one_year_ago))

            cm_row = cursor.fetchone()
            cm_count = cm_row[0] or 0
            cm_hours = float(cm_row[1] or 0)

            # Parts count
            cursor.execute('''
                SELECT COUNT(*)
                FROM cm_parts_requests cpr
                JOIN corrective_maintenance cm ON cpr.cm_number = cm.cm_number
                WHERE cm.bfm_equipment_no = %s
                AND cpr.requested_date >= %s
            ''', (self.current_bfm, one_year_ago))

            parts_count = cursor.fetchone()[0] or 0

            # Calculate metrics
            pm_compliance = min(100, int((completed_pms / expected_pms) * 100)) if expected_pms > 0 else 100
            cm_frequency = round(cm_count / 12, 1)
            total_hours = pm_hours + cm_hours

            # Calculate health score
            score = 100
            score -= (100 - pm_compliance) * 0.3
            if cm_frequency > 1:
                score -= min(20, (cm_frequency - 1) * 10)
            if status != 'Active':
                score -= 30
            score = max(0, int(score))

            # Generate recommendations
            recommendations = []
            if pm_compliance < 80:
                recommendations.append("- Improve PM compliance - currently below 80%")
            if cm_frequency > 2:
                recommendations.append("- High CM frequency - investigate root causes")
            if parts_count > 20:
                recommendations.append("- High parts usage - review equipment reliability")
            if status != 'Active':
                recommendations.append(f"- Equipment status is '{status}' - review and update")
            if not recommendations:
                recommendations.append("- No issues detected. Equipment is performing well.")

            # Create report dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Health Report - {self.current_bfm}")
            dialog.resize(600, 500)

            layout = QVBoxLayout()

            # Header
            header = QLabel(f"Equipment Health Report")
            header_font = QFont()
            header_font.setBold(True)
            header_font.setPointSize(14)
            header.setFont(header_font)
            layout.addWidget(header)

            # Report text
            report_text = QTextEdit()
            report_text.setReadOnly(True)

            report = f"""
Equipment: {self.current_bfm}
Description: {description or 'N/A'}
Status: {status or 'Unknown'}

═══════════════════════════════════════════════════════════════

HEALTH SCORE: {score}/100
{'⬤ Excellent' if score >= 80 else '⬤ Good' if score >= 60 else '⬤ Needs Attention'}

═══════════════════════════════════════════════════════════════

METRICS (Last 12 Months):

Preventive Maintenance:
  • PM Compliance: {pm_compliance}%
  • Completed PMs: {completed_pms} of {expected_pms} expected
  • Total PM Hours: {pm_hours:.1f} hours

Corrective Maintenance:
  • CM Frequency: {cm_frequency} per month
  • Total CMs: {cm_count}
  • Total CM Hours: {cm_hours:.1f} hours

Parts & Costs:
  • Parts Requests: {parts_count}
  • Total Labor Hours: {total_hours:.1f} hours

═══════════════════════════════════════════════════════════════

RECOMMENDATIONS:

{chr(10).join(recommendations)}

═══════════════════════════════════════════════════════════════

Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            report_text.setPlainText(report)
            layout.addWidget(report_text)

            # Close button
            button_box = QDialogButtonBox(QDialogButtonBox.Close)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            dialog.setLayout(layout)
            dialog.exec_()

            self.conn.commit()

        except Exception as e:
            QMessageBox.critical(self, "Error",
                               f"Error generating health report:\n{str(e)}")
            try:
                self.conn.rollback()
            except:
                pass

    def export_to_csv(self):
        """Export event history to CSV file"""
        if not self.all_events:
            QMessageBox.warning(self, "No Data", "No events to export.")
            return

        # Get save file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to CSV",
            f"equipment_history_{self.current_bfm}_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow([
                    'Equipment', 'Date', 'Event Type', 'Description',
                    'Technician', 'Labor Hours', 'Priority/Type', 'Status', 'Notes'
                ])

                # Write data
                for event in self.all_events:
                    # Determine priority/type field
                    if event['event_type'] == 'PM':
                        priority_type = event.get('pm_type', '')
                    elif event['event_type'] == 'CM':
                        priority_type = event.get('priority', '')
                    else:
                        priority_type = event.get('part_number', '')

                    writer.writerow([
                        self.current_bfm,
                        event.get('date', ''),
                        event.get('event_type', ''),
                        event.get('description', ''),
                        event.get('technician', ''),
                        event.get('labor_hours', 0),
                        priority_type,
                        event.get('status', ''),
                        event.get('notes', '')
                    ])

            QMessageBox.information(self, "Success",
                                  f"Successfully exported {len(self.all_events)} events to:\n{file_path}")
            self.status_updated.emit(f"Exported {len(self.all_events)} events to CSV")

        except Exception as e:
            QMessageBox.critical(self, "Export Error",
                               f"Error exporting to CSV:\n{str(e)}")

    def export_to_pdf(self):
        """Export event history to PDF (placeholder)"""
        QMessageBox.information(self, "PDF Export",
                              "PDF export functionality will be implemented in a future update.\n\n"
                              "For now, please use CSV export and convert to PDF using external tools.")


if __name__ == '__main__':
    """Test the equipment history tab standalone"""
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import psycopg2

    app = QApplication(sys.argv)

    # Create test window
    window = QMainWindow()
    window.setWindowTitle("Equipment History Tab Test")
    window.resize(1400, 900)

    # Create test database connection (replace with your credentials)
    try:
        conn = psycopg2.connect(
            dbname="your_database",
            user="your_user",
            password="your_password",
            host="your_host",
            port="5432"
        )

        # Create and set tab
        tab = EquipmentHistoryTab(conn)
        window.setCentralWidget(tab)

        window.show()
        sys.exit(app.exec_())

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
