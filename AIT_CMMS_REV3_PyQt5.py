#!/usr/bin/env python3
"""
AIT Complete CMMS - PyQt5 Version (PRODUCTION READY)
Computerized Maintenance Management System converted from Tkinter to PyQt5

This is the COMPLETE main application file that integrates all PyQt5 tabs:
1. Equipment Management
2. PM Scheduling
3. PM Completion
4. Corrective Maintenance
5. MRO Stock Management
6. Equipment History
7. KPI Dashboard
8. KPI Trend Analyzer

Features:
- Role-based access control (Manager, Technician, Parts Coordinator)
- Database connection pooling
- Session management with audit logging
- Professional UI with unified color scheme
- Signal connections between tabs
- Menu bar with full functionality
- Status bar with live updates
- Window state management
- Comprehensive error handling

Author: CMMS Development Team
Version: 2.2 PyQt5
Date: 2025-11-15
"""

# ===== STANDARD LIBRARY IMPORTS =====
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, NamedTuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import sys
import os
import json
import re
import math
import random
import calendar
import shutil
import traceback

# ===== THIRD PARTY IMPORTS =====
import pandas as pd
import psycopg2
from psycopg2 import sql, extras

# ===== PYQT5 IMPORTS =====
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QMessageBox, QDialog,
    QLineEdit, QFormLayout, QStatusBar, QMenuBar, QMenu, QAction,
    QDialogButtonBox, QFrame, QSizePolicy, QSplashScreen, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSettings, QSize
from PyQt5.QtGui import QIcon, QFont, QCloseEvent, QPixmap, QPalette, QColor

# ===== REPORTLAB IMPORTS (with availability check) =====
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("WARNING: ReportLab not installed. PDF generation will not work.")

# ===== DATABASE UTILITY IMPORTS =====
from database_utils import (
    db_pool, UserManager, AuditLogger,
    OptimisticConcurrencyControl, TransactionManager
)

# ===== MODULE IMPORTS =====
from kpi_database_migration import migrate_kpi_database
from kpi_manager import KPIManager

# ===== TAB IMPORTS - ALL PYQT5 CONVERTED MODULES =====
try:
    from equipment_tab_pyqt5 import EquipmentTab
    EQUIPMENT_TAB_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Equipment Tab not available: {e}")
    EQUIPMENT_TAB_AVAILABLE = False

try:
    from pm_scheduling_tab_pyqt5 import PMSchedulingTab
    PM_SCHEDULING_TAB_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: PM Scheduling Tab not available: {e}")
    PM_SCHEDULING_TAB_AVAILABLE = False

try:
    from pm_completion_tab_pyqt5 import PMCompletionTab
    PM_COMPLETION_TAB_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: PM Completion Tab not available: {e}")
    PM_COMPLETION_TAB_AVAILABLE = False

try:
    from cm_management_tab_pyqt5 import CMManagementTab
    CM_MANAGEMENT_TAB_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: CM Management Tab not available: {e}")
    CM_MANAGEMENT_TAB_AVAILABLE = False

try:
    from mro_stock_tab_pyqt5 import MROStockTab
    MRO_STOCK_TAB_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: MRO Stock Tab not available: {e}")
    MRO_STOCK_TAB_AVAILABLE = False

try:
    from equipment_history_tab_pyqt5 import EquipmentHistoryTab
    EQUIPMENT_HISTORY_TAB_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Equipment History Tab not available: {e}")
    EQUIPMENT_HISTORY_TAB_AVAILABLE = False

try:
    from kpi_ui import KPIDashboard
    KPI_DASHBOARD_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: KPI Dashboard not available: {e}")
    KPI_DASHBOARD_AVAILABLE = False

try:
    from kpi_trend_analyzer_tab_pyqt5 import KPITrendAnalyzerTab
    KPI_TREND_ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: KPI Trend Analyzer Tab not available: {e}")
    KPI_TREND_ANALYZER_AVAILABLE = False

# ===== DIALOG IMPORTS =====
try:
    from user_management_dialog_pyqt5 import UserManagementDialog
    USER_MANAGEMENT_AVAILABLE = True
except ImportError:
    print("WARNING: User Management Dialog not available")
    USER_MANAGEMENT_AVAILABLE = False

try:
    from password_change_dialog_pyqt5 import PasswordChangeDialog
    PASSWORD_CHANGE_AVAILABLE = True
except ImportError:
    print("WARNING: Password Change Dialog not available")
    PASSWORD_CHANGE_AVAILABLE = False

# ===== INTEGRATION MODULES =====
try:
    from cm_parts_integration import CMPartsIntegration
    CM_PARTS_INTEGRATION_AVAILABLE = True
except ImportError:
    print("WARNING: CM Parts Integration not available")
    CM_PARTS_INTEGRATION_AVAILABLE = False


# ===== DATA CLASSES AND ENUMS =====

class PMType(Enum):
    MONTHLY = "Monthly"
    ANNUAL = "Annual"

class PMStatus(Enum):
    DUE = "due"
    NOT_DUE = "not_due"
    RECENTLY_COMPLETED = "recently_completed"
    CONFLICTED = "conflicted"

@dataclass
class Equipment:
    bfm_no: str
    description: str
    has_monthly: bool
    has_annual: bool
    last_monthly_date: Optional[str]
    last_annual_date: Optional[str]
    status: str
    priority: int = 99

@dataclass
class CompletionRecord:
    bfm_no: str
    pm_type: PMType
    completion_date: datetime
    technician: str

@dataclass
class PMAssignment:
    bfm_no: str
    pm_type: PMType
    description: str
    priority_score: int
    reason: str

class PMEligibilityResult(NamedTuple):
    status: PMStatus
    reason: str
    priority_score: int = 0
    days_overdue: int = 0


# ===== DATABASE UTILITY CLASSES =====

class DateParser:
    """Responsible for parsing and standardizing dates"""

    def __init__(self, conn):
        self.conn = conn

    def parse_flexible(self, date_string: Optional[str]) -> Optional[datetime]:
        """Parse date string with flexible format handling"""
        if not date_string:
            return None

        try:
            from database_utils import DateStandardizer
            standardizer = DateStandardizer(self.conn)
            parsed_date = standardizer.parse_date_flexible(date_string)
            if parsed_date:
                return datetime.strptime(parsed_date, '%Y-%m-%d')
        except Exception as e:
            print(f"Date parsing error for '{date_string}': {e}")

        return None


class DateStandardizer:
    """Utility class to standardize all dates in the CMMS database to YYYY-MM-DD format"""

    def __init__(self, conn):
        self.conn = conn
        self.date_patterns = [
            r'^\d{1,2}/\d{1,2}/\d{2}$',
            r'^\d{1,2}/\d{1,2}/\d{4}$',
            r'^\d{1,2}-\d{1,2}-\d{2}$',
            r'^\d{1,2}-\d{1,2}-\d{4}$',
            r'^\d{4}-\d{1,2}-\d{1,2}$',
        ]

    def parse_date_flexible(self, date_str: str) -> Optional[str]:
        """Parse date string in various formats and return YYYY-MM-DD format"""
        if not date_str or date_str.strip() == '':
            return None

        date_str = date_str.strip()

        # Try to parse different date formats
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m/%d/%y',
            '%m-%d-%Y',
            '%m-%d-%y',
            '%d/%m/%Y',
            '%d/%m/%y',
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None


# ===== LOGIN DIALOG =====

class LoginDialog(QDialog):
    """Professional login dialog with gradient background"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AIT CMMS - User Login")
        self.setFixedSize(550, 550)  # Significantly increased height for better visibility
        self.setModal(True)

        # Center the dialog
        self.center_on_screen()

        # Disable close button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        self.user_id = None
        self.user_name = None
        self.user_role = None
        self.session_id = None

        self.setup_ui()
        self.apply_stylesheet()

    def center_on_screen(self):
        """Center the dialog on the screen"""
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def apply_stylesheet(self):
        """Apply professional stylesheet with improved readability"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #34495e);
            }
            QLabel {
                color: white;
                font-size: 12pt;
            }
            QLineEdit {
                padding: 12px;
                border: 2px solid #3498db;
                border-radius: 5px;
                background: white;
                color: #2c3e50;
                font-size: 13pt;
            }
            QLineEdit:focus {
                border: 2px solid #2980b9;
                background-color: #ecf0f1;
            }
            QPushButton {
                padding: 12px 40px;
                border: none;
                border-radius: 5px;
                background-color: #3498db;
                color: white;
                font-size: 13pt;
                font-weight: bold;
                min-width: 120px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)

    def setup_ui(self):
        """Setup the login dialog UI"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)

        # Header with logo placeholder
        header_label = QLabel("🔧 AIT CMMS LOGIN")
        header_font = QFont("Arial", 24, QFont.Bold)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        subtitle_label = QLabel("Computerized Maintenance Management System")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #ecf0f1; font-size: 12pt;")
        layout.addWidget(subtitle_label)

        layout.addSpacing(20)

        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # Username label with larger font
        username_label = QLabel("Username:")
        username_label.setStyleSheet("color: white; font-size: 12pt; font-weight: bold;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setMinimumHeight(40)
        form_layout.addRow(username_label, self.username_input)

        # Password label with larger font
        password_label = QLabel("Password:")
        password_label.setStyleSheet("color: white; font-size: 12pt; font-weight: bold;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(40)
        form_layout.addRow(password_label, self.password_input)

        layout.addLayout(form_layout)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 11pt;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        login_button = QPushButton("Login")
        login_button.clicked.connect(self.handle_login)
        login_button.setMinimumWidth(150)
        login_button.setMinimumHeight(45)
        button_layout.addWidget(login_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect Enter key to login
        self.password_input.returnPressed.connect(self.handle_login)
        self.username_input.returnPressed.connect(self.handle_login)

    def handle_login(self):
        """Handle login attempt with enhanced error handling"""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.status_label.setText("Please enter both username and password")
            return

        try:
            with db_pool.get_cursor() as cursor:
                # Authenticate user - use correct method name
                user_data = UserManager.authenticate(cursor, username, password)

                if user_data:
                    self.user_id = user_data['id']  # Correct field name
                    self.user_name = user_data['username']  # Correct field name
                    self.user_role = user_data['role']

                    # Create session - use correct method name
                    self.session_id = UserManager.create_session(cursor, self.user_id, username)

                    print(f"Login successful: {self.user_name} ({self.user_role})")
                    self.accept()
                else:
                    self.status_label.setText("Invalid username or password")
                    self.password_input.clear()
                    self.password_input.setFocus()

        except Exception as e:
            self.status_label.setText(f"Login error: {str(e)}")
            print(f"Login error: {e}")
            traceback.print_exc()


# ===== MAIN APPLICATION CLASS =====

class AITCMMSSystemPyQt5(QMainWindow):
    """
    Main PyQt5 application class for AIT CMMS

    This is the COMPLETE production-ready main window that integrates all tabs
    and provides full CMMS functionality with role-based access control.
    """

    # Signals
    equipment_updated = pyqtSignal()
    pm_completed = pyqtSignal(str, str, str)  # bfm_no, pm_type, technician

    def __init__(self):
        super().__init__()

        # Database configuration
        self.DB_CONFIG = {
            'host': 'ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech',
            'port': 5432,
            'database': 'neondb',
            'user': 'neondb_owner',
            'password': 'npg_2Nm6hyPVWiIH',
            'sslmode': 'require'
        }

        self.conn = None
        self.session_start_time = datetime.now()
        self.session_id = None
        self.user_id = None
        self.user_name = None
        self.current_user_role = None
        self.technicians = []

        # Tab references
        self.tab_widget = None
        self.equipment_tab = None
        self.pm_scheduling_tab = None
        self.pm_completion_tab = None
        self.cm_management_tab = None
        self.mro_stock_tab = None
        self.equipment_history_tab = None
        self.kpi_dashboard_tab = None
        self.kpi_trend_tab = None

        # Settings for window state
        self.settings = QSettings('AIT', 'CMMS')

        # Initialize window
        self.setWindowTitle("AIT Complete CMMS - Computerized Maintenance Management System (PyQt5)")
        self.setMinimumSize(1400, 900)

        # Set window icon (if available)
        self.set_window_icon()

        # Initialize database connection pool
        print("Starting AIT CMMS Application (PyQt5)...")
        if not self.initialize_database_pool():
            sys.exit(1)

        # Initialize users table and run migrations
        if not self.init_users_table_before_login():
            sys.exit(1)

        # Show login dialog
        if not self.show_login_dialog():
            sys.exit(0)

        # Restore window state or maximize
        self.restore_window_state()

        # Load technicians from database
        self.load_technicians_from_database()

        # Initialize database tables
        self.init_database()

        # Setup UI
        self.setup_ui()

        # Apply professional styling
        self.apply_stylesheet()

        # PM Settings
        self.pm_frequencies = {
            'Monthly': 30,
            'Six Month': 180,
            'Annual': 365,
            'Run to Failure': 0,
            'CANNOT FIND': 0
        }
        self.weekly_pm_target = 130

        # Initialize data storage
        self.equipment_data = []
        self.current_week_start = self.get_week_start(datetime.now())

        # Connect closing signal
        self.closing_signal = False

        # Setup auto-save timer
        self.setup_auto_save()

        print(f"AIT Complete CMMS System (PyQt5) initialized successfully for {self.user_name} ({self.current_user_role})")
        self.update_status(f"Welcome, {self.user_name}! System ready.")

    def set_window_icon(self):
        """Set window icon if available"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "ait_logo.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"Could not load window icon: {e}")

    def initialize_database_pool(self) -> bool:
        """Initialize database connection pool"""
        try:
            db_pool.initialize(self.DB_CONFIG, min_conn=2, max_conn=20)
            print("Database connection pool initialized successfully")
            return True
        except Exception as e:
            QMessageBox.critical(
                self, "Database Error",
                f"Failed to initialize database connection:\n{str(e)}\n\n"
                f"Please check your internet connection and try again."
            )
            print(f"Database initialization error: {e}")
            traceback.print_exc()
            return False

    def init_users_table_before_login(self) -> bool:
        """Initialize KPI tables and verify database connectivity before login"""
        try:
            # Verify database connectivity
            with db_pool.get_cursor() as cursor:
                cursor.execute("SELECT 1")  # Simple connectivity test
                print("✓ Database connection successful")

                # Run KPI database migrations (function takes no arguments)
                print("Running KPI database migrations...")
                migrate_kpi_database()  # Call without arguments

            print("Database initialization successful")
            return True
        except Exception as e:
            QMessageBox.critical(
                self, "Database Error",
                f"Failed to initialize database:\n{str(e)}\n\n"
                f"Please check your database configuration and ensure:\n"
                f"1. Database is accessible\n"
                f"2. Users table exists\n"
                f"3. Neon database credentials are correct"
            )
            print(f"Database initialization error: {e}")
            traceback.print_exc()
            return False

    def show_login_dialog(self) -> bool:
        """Show login dialog and authenticate user"""
        login_dlg = LoginDialog(self)
        result = login_dlg.exec_()

        if result == QDialog.Accepted:
            self.user_id = login_dlg.user_id
            self.user_name = login_dlg.user_name
            self.current_user_role = login_dlg.user_role
            self.session_id = login_dlg.session_id
            return True

        return False

    def restore_window_state(self):
        """Restore window geometry and state"""
        try:
            # Restore geometry
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
            else:
                self.showMaximized()

            # Restore window state
            state = self.settings.value("windowState")
            if state:
                self.restoreState(state)
        except Exception as e:
            print(f"Could not restore window state: {e}")
            self.showMaximized()

    def save_window_state(self):
        """Save window geometry and state"""
        try:
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())
        except Exception as e:
            print(f"Could not save window state: {e}")

    def load_technicians_from_database(self):
        """Load technicians list from database"""
        try:
            with db_pool.get_cursor() as cursor:
                cursor.execute("""
                    SELECT full_name FROM users
                    WHERE role = 'Technician' AND is_active = TRUE
                    ORDER BY full_name
                """)
                self.technicians = [row['full_name'] for row in cursor.fetchall()]

            if not self.technicians:
                # Fallback list if no technicians in database
                self.technicians = [
                    "Mark Michaels", "Jerone Bosarge", "Jon Hymel",
                    "Nick Whisenant", "James Dunnam", "Wayne Dunnam",
                    "Nate Williams", "Rey Marikit", "Ronald Houghs"
                ]

            print(f"Loaded {len(self.technicians)} technicians from database")
        except Exception as e:
            print(f"Error loading technicians: {e}")
            # Use fallback list
            self.technicians = [
                "Mark Michaels", "Jerone Bosarge", "Jon Hymel",
                "Nick Whisenant", "James Dunnam", "Wayne Dunnam",
                "Nate Williams", "Rey Marikit", "Ronald Houghs"
            ]

    def init_database(self):
        """Initialize database connection and verify tables"""
        try:
            with db_pool.get_cursor() as cursor:
                # Verify critical tables exist
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name IN ('equipment', 'pm_completions',
                                      'corrective_maintenance', 'mro_inventory')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                print(f"Verified database tables: {', '.join(tables)}")
        except Exception as e:
            print(f"Database verification warning: {e}")

    def setup_ui(self):
        """Setup the main UI with all tabs"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(main_layout)

        # Create menu bar
        self.create_menu_bar()

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(False)
        self.tab_widget.setDocumentMode(True)
        main_layout.addWidget(self.tab_widget)

        # Create tabs based on user role
        self.create_tabs()

        # Create status bar
        self.create_status_bar()

        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def create_menu_bar(self):
        """Create the comprehensive menu bar"""
        menubar = self.menuBar()

        # Account menu
        account_menu = menubar.addMenu("&Account")

        if PASSWORD_CHANGE_AVAILABLE:
            change_password_action = QAction("Change Password", self)
            change_password_action.triggered.connect(self.open_change_password)
            change_password_action.setShortcut("Ctrl+P")
            account_menu.addAction(change_password_action)

        account_menu.addSeparator()

        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.logout)
        logout_action.setShortcut("Ctrl+L")
        account_menu.addAction(logout_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        if self.current_user_role == 'Manager' and USER_MANAGEMENT_AVAILABLE:
            user_mgmt_action = QAction("User Management", self)
            user_mgmt_action.triggered.connect(self.open_user_management)
            user_mgmt_action.setShortcut("Ctrl+U")
            tools_menu.addAction(user_mgmt_action)
            tools_menu.addSeparator()

        database_tools_action = QAction("Database Tools", self)
        database_tools_action.triggered.connect(self.open_database_tools)
        tools_menu.addAction(database_tools_action)

        backup_action = QAction("Backup && Restore", self)
        backup_action.triggered.connect(self.open_backup_restore)
        tools_menu.addAction(backup_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        refresh_action = QAction("Refresh Current Tab", self)
        refresh_action.triggered.connect(self.refresh_current_tab)
        refresh_action.setShortcut("F5")
        view_menu.addAction(refresh_action)

        view_menu.addSeparator()

        fullscreen_action = QAction("Toggle Fullscreen", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        fullscreen_action.setShortcut("F11")
        view_menu.addAction(fullscreen_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("About AIT CMMS", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        documentation_action = QAction("Documentation", self)
        documentation_action.triggered.connect(self.show_documentation)
        help_menu.addAction(documentation_action)

        help_menu.addSeparator()

        version_action = QAction("Version Information", self)
        version_action.triggered.connect(self.show_version_info)
        help_menu.addAction(version_action)

    def create_status_bar(self):
        """Create the comprehensive status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Create status labels
        self.status_message = QLabel(f"Ready - Logged in as: {self.user_name}")
        self.status_role = QLabel(f"Role: {self.current_user_role}")
        self.status_connection = QLabel("🟢 Connected")

        # Style the labels
        self.status_role.setStyleSheet("color: #2c3e50; font-weight: bold;")
        self.status_connection.setStyleSheet("color: #27ae60; font-weight: bold;")

        # Add to status bar
        self.status_bar.addWidget(self.status_message, 1)
        self.status_bar.addPermanentWidget(self.status_role)
        self.status_bar.addPermanentWidget(self.status_connection)

        # Update connection status periodically
        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.check_database_connection)
        self.connection_timer.start(30000)  # Check every 30 seconds

    def create_tabs(self):
        """Create tabs based on user role - COMPLETE IMPLEMENTATION"""
        print(f"Creating tabs for role: {self.current_user_role}")

        # Get database connection for tabs
        # IMPORTANT: The connection will be used by tabs to create cursors
        # Make sure tabs use cursor_factory=extras.RealDictCursor when creating cursors
        conn = db_pool.get_connection()

        if self.current_user_role == 'Manager':
            # MANAGER: Gets ALL tabs
            print("Creating Manager tabs (all 8 tabs)...")

            # 1. Equipment Management
            if EQUIPMENT_TAB_AVAILABLE:
                try:
                    self.equipment_tab = EquipmentTab(conn, self.technicians, self)
                    self.equipment_tab.status_updated.connect(self.update_status)
                    self.tab_widget.addTab(self.equipment_tab, "📋 Equipment")
                    print("  ✓ Equipment tab added")
                except Exception as e:
                    print(f"  ✗ Equipment tab error: {e}")
                    self.add_error_tab("Equipment Management", str(e))

            # 2. PM Scheduling
            if PM_SCHEDULING_TAB_AVAILABLE:
                try:
                    self.pm_scheduling_tab = PMSchedulingTab(conn, self.technicians, self)
                    self.pm_scheduling_tab.status_updated.connect(self.update_status)
                    self.tab_widget.addTab(self.pm_scheduling_tab, "📅 PM Scheduling")
                    print("  ✓ PM Scheduling tab added")
                except Exception as e:
                    print(f"  ✗ PM Scheduling tab error: {e}")
                    self.add_error_tab("PM Scheduling", str(e))

            # 3. PM Completion
            if PM_COMPLETION_TAB_AVAILABLE:
                try:
                    self.pm_completion_tab = PMCompletionTab(conn, self)
                    self.pm_completion_tab.pm_completed.connect(self.on_pm_completed)
                    self.tab_widget.addTab(self.pm_completion_tab, "✅ PM Completion")
                    print("  ✓ PM Completion tab added")
                except Exception as e:
                    print(f"  ✗ PM Completion tab error: {e}")
                    self.add_error_tab("PM Completion", str(e))

            # 4. Corrective Maintenance
            if CM_MANAGEMENT_TAB_AVAILABLE:
                try:
                    self.cm_management_tab = CMManagementTab(
                        conn, self.user_name, self.current_user_role,
                        self.technicians, self
                    )

                    # Set up parts integration if available
                    if CM_PARTS_INTEGRATION_AVAILABLE:
                        try:
                            parts_integration = CMPartsIntegration(self)
                            self.cm_management_tab.set_parts_integration(parts_integration)
                        except Exception as e:
                            print(f"  ⚠ Parts integration setup failed: {e}")

                    self.tab_widget.addTab(self.cm_management_tab, "🔧 CM Management")
                    print("  ✓ CM Management tab added")
                except Exception as e:
                    print(f"  ✗ CM Management tab error: {e}")
                    self.add_error_tab("CM Management", str(e))

            # 5. MRO Stock Management
            if MRO_STOCK_TAB_AVAILABLE:
                try:
                    self.mro_stock_tab = MROStockTab(conn, self.user_name, self)
                    self.tab_widget.addTab(self.mro_stock_tab, "📦 MRO Stock")
                    print("  ✓ MRO Stock tab added")
                except Exception as e:
                    print(f"  ✗ MRO Stock tab error: {e}")
                    self.add_error_tab("MRO Stock", str(e))

            # 6. Equipment History
            if EQUIPMENT_HISTORY_TAB_AVAILABLE:
                try:
                    self.equipment_history_tab = EquipmentHistoryTab(conn, self)
                    self.tab_widget.addTab(self.equipment_history_tab, "📊 Equipment History")
                    print("  ✓ Equipment History tab added")
                except Exception as e:
                    print(f"  ✗ Equipment History tab error: {e}")
                    self.add_error_tab("Equipment History", str(e))

            # 7. KPI Dashboard
            if KPI_DASHBOARD_AVAILABLE:
                try:
                    self.kpi_dashboard_tab = KPIDashboard(db_pool, self.user_name, self)
                    self.tab_widget.addTab(self.kpi_dashboard_tab, "📈 KPI Dashboard")
                    print("  ✓ KPI Dashboard tab added")
                except Exception as e:
                    print(f"  ✗ KPI Dashboard tab error: {e}")
                    self.add_error_tab("KPI Dashboard", str(e))

            # 8. KPI Trend Analyzer
            if KPI_TREND_ANALYZER_AVAILABLE:
                try:
                    self.kpi_trend_tab = KPITrendAnalyzerTab(db_pool, self)
                    self.tab_widget.addTab(self.kpi_trend_tab, "📉 KPI Trends")
                    print("  ✓ KPI Trends tab added")
                except Exception as e:
                    print(f"  ✗ KPI Trends tab error: {e}")
                    self.add_error_tab("KPI Trends", str(e))

        elif self.current_user_role == 'Technician':
            # TECHNICIAN: PM Completion, CM, Equipment (view-only), History
            print("Creating Technician tabs...")

            # PM Completion
            if PM_COMPLETION_TAB_AVAILABLE:
                try:
                    self.pm_completion_tab = PMCompletionTab(conn, self)
                    self.pm_completion_tab.pm_completed.connect(self.on_pm_completed)
                    self.tab_widget.addTab(self.pm_completion_tab, "✅ PM Completion")
                    print("  ✓ PM Completion tab added")
                except Exception as e:
                    print(f"  ✗ PM Completion tab error: {e}")

            # CM Management
            if CM_MANAGEMENT_TAB_AVAILABLE:
                try:
                    self.cm_management_tab = CMManagementTab(
                        conn, self.user_name, self.current_user_role,
                        self.technicians, self
                    )
                    self.tab_widget.addTab(self.cm_management_tab, "🔧 CM Management")
                    print("  ✓ CM Management tab added")
                except Exception as e:
                    print(f"  ✗ CM Management tab error: {e}")

            # Equipment (view-only)
            if EQUIPMENT_TAB_AVAILABLE:
                try:
                    self.equipment_tab = EquipmentTab(conn, self.technicians, self)
                    self.equipment_tab.status_updated.connect(self.update_status)
                    self.tab_widget.addTab(self.equipment_tab, "📋 Equipment (View)")
                    print("  ✓ Equipment tab added (view-only)")
                except Exception as e:
                    print(f"  ✗ Equipment tab error: {e}")

            # Equipment History
            if EQUIPMENT_HISTORY_TAB_AVAILABLE:
                try:
                    self.equipment_history_tab = EquipmentHistoryTab(conn, self)
                    self.tab_widget.addTab(self.equipment_history_tab, "📊 Equipment History")
                    print("  ✓ Equipment History tab added")
                except Exception as e:
                    print(f"  ✗ Equipment History tab error: {e}")

        elif self.current_user_role == 'Parts Coordinator':
            # PARTS COORDINATOR: PM Completion, CM, MRO Stock
            print("Creating Parts Coordinator tabs...")

            # PM Completion
            if PM_COMPLETION_TAB_AVAILABLE:
                try:
                    self.pm_completion_tab = PMCompletionTab(conn, self)
                    self.pm_completion_tab.pm_completed.connect(self.on_pm_completed)
                    self.tab_widget.addTab(self.pm_completion_tab, "✅ PM Completion")
                    print("  ✓ PM Completion tab added")
                except Exception as e:
                    print(f"  ✗ PM Completion tab error: {e}")

            # CM Management
            if CM_MANAGEMENT_TAB_AVAILABLE:
                try:
                    self.cm_management_tab = CMManagementTab(
                        conn, self.user_name, self.current_user_role,
                        self.technicians, self
                    )
                    self.tab_widget.addTab(self.cm_management_tab, "🔧 CM Management")
                    print("  ✓ CM Management tab added")
                except Exception as e:
                    print(f"  ✗ CM Management tab error: {e}")

            # MRO Stock
            if MRO_STOCK_TAB_AVAILABLE:
                try:
                    self.mro_stock_tab = MROStockTab(conn, self.user_name, self)
                    self.tab_widget.addTab(self.mro_stock_tab, "📦 MRO Stock")
                    print("  ✓ MRO Stock tab added")
                except Exception as e:
                    print(f"  ✗ MRO Stock tab error: {e}")

        else:
            # Unknown role - show error
            error_widget = QWidget()
            error_layout = QVBoxLayout()
            error_label = QLabel(f"Unknown user role: {self.current_user_role}")
            error_label.setAlignment(Qt.AlignCenter)
            error_layout.addWidget(error_label)
            error_widget.setLayout(error_layout)
            self.tab_widget.addTab(error_widget, "Error")

        print(f"Tab creation complete. Total tabs: {self.tab_widget.count()}")

    def add_error_tab(self, tab_name: str, error_message: str):
        """Add an error placeholder tab"""
        error_widget = QWidget()
        layout = QVBoxLayout()

        label = QLabel(f"{tab_name}\n\nError loading tab:\n{error_message}")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color: red; font-size: 12pt;")

        layout.addWidget(label)
        error_widget.setLayout(layout)

        self.tab_widget.addTab(error_widget, f"⚠ {tab_name}")

    def apply_stylesheet(self):
        """Apply professional stylesheet to entire application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
                margin-top: -1px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ecf0f1, stop:1 #bdc3c7);
                border: 1px solid #95a5a6;
                border-bottom-color: #bdc3c7;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 10px 20px;
                margin-right: 2px;
                font-weight: bold;
                color: #2c3e50;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                border-color: #2980b9;
                color: white;
                margin-top: 0px;
            }
            QTabBar::tab:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ecf0f1, stop:1 #95a5a6);
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QGroupBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                margin-top: 10px;
                font-weight: bold;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                background-color: white;
            }
            QStatusBar {
                background-color: #34495e;
                color: white;
            }
            QStatusBar QLabel {
                color: white;
            }
        """)

    def setup_auto_save(self):
        """Setup auto-save timer for session data"""
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save_session)
        self.auto_save_timer.start(300000)  # Every 5 minutes

    def auto_save_session(self):
        """Auto-save session data"""
        try:
            # Update session activity heartbeat
            if self.session_id:
                with db_pool.get_cursor() as cursor:
                    UserManager.update_session_activity(cursor, self.session_id)
        except Exception as e:
            print(f"Auto-save error: {e}")

    # ===== MENU ACTION HANDLERS =====

    def open_change_password(self):
        """Open change password dialog"""
        if PASSWORD_CHANGE_AVAILABLE:
            try:
                dialog = PasswordChangeDialog(self.user_id, self)
                dialog.exec_()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open password change dialog: {str(e)}")
        else:
            QMessageBox.information(self, "Not Available", "Password change dialog is not available")

    def open_user_management(self):
        """Open user management dialog (managers only)"""
        if USER_MANAGEMENT_AVAILABLE:
            try:
                dialog = UserManagementDialog(self.user_name, self)
                dialog.exec_()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open user management: {str(e)}")
        else:
            QMessageBox.information(self, "Not Available", "User management dialog is not available")

    def open_database_tools(self):
        """Open database tools dialog"""
        QMessageBox.information(
            self, "Database Tools",
            "Database tools dialog will be implemented.\n\n"
            "Planned features:\n"
            "- Database maintenance\n"
            "- Table optimization\n"
            "- Index management\n"
            "- Query analyzer"
        )

    def open_backup_restore(self):
        """Open backup and restore dialog"""
        QMessageBox.information(
            self, "Backup & Restore",
            "Backup and restore functionality will be implemented.\n\n"
            "Planned features:\n"
            "- Full database backup\n"
            "- Selective backup\n"
            "- Restore from backup\n"
            "- Scheduled backups"
        )

    def refresh_current_tab(self):
        """Refresh the currently active tab"""
        current_tab = self.tab_widget.currentWidget()

        # Try to call refresh method if available
        if hasattr(current_tab, 'refresh_equipment_list'):
            current_tab.refresh_equipment_list()
        elif hasattr(current_tab, 'load_recent_completions'):
            current_tab.load_recent_completions()
        elif hasattr(current_tab, 'load_data'):
            current_tab.load_data()
        elif hasattr(current_tab, 'refresh_dashboard'):
            current_tab.refresh_dashboard()

        self.update_status("Current tab refreshed")

    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>AIT Complete CMMS</h2>
        <h3>Computerized Maintenance Management System</h3>
        <p><b>Version:</b> 2.2 PyQt5 Edition</p>
        <p><b>Date:</b> November 2025</p>
        <br>
        <p>A comprehensive maintenance management system for aerospace manufacturing.</p>
        <br>
        <p><b>Features:</b></p>
        <ul>
        <li>Equipment Management</li>
        <li>Preventive Maintenance Scheduling</li>
        <li>PM Completion Tracking</li>
        <li>Corrective Maintenance</li>
        <li>MRO Stock Management</li>
        <li>Equipment History</li>
        <li>KPI Dashboard</li>
        <li>Trend Analysis</li>
        </ul>
        <br>
        <p><b>Developed by:</b> AIT CMMS Development Team</p>
        """

        QMessageBox.about(self, "About AIT CMMS", about_text)

    def show_documentation(self):
        """Show documentation"""
        QMessageBox.information(
            self, "Documentation",
            "Documentation is available in the following files:\n\n"
            "- EQUIPMENT_TAB_README.md\n"
            "- PM_SCHEDULING_TAB_README.md\n"
            "- PM_COMPLETION_TAB_README.md\n"
            "- START_HERE_PM_COMPLETION.md\n"
            "- INTEGRATION_GUIDE.md\n\n"
            "These files are located in the application directory."
        )

    def show_version_info(self):
        """Show detailed version information"""
        version_info = f"""
        <h3>Version Information</h3>
        <table>
        <tr><td><b>Application:</b></td><td>AIT CMMS PyQt5</td></tr>
        <tr><td><b>Version:</b></td><td>2.2</td></tr>
        <tr><td><b>Build Date:</b></td><td>2025-11-15</td></tr>
        <tr><td><b>Python:</b></td><td>{sys.version.split()[0]}</td></tr>
        <tr><td><b>PyQt5:</b></td><td>{Qt.PYQT_VERSION_STR}</td></tr>
        <tr><td><b>Database:</b></td><td>PostgreSQL (Neon)</td></tr>
        </table>
        <br>
        <p><b>Available Modules:</b></p>
        <ul>
        <li>{'✓' if EQUIPMENT_TAB_AVAILABLE else '✗'} Equipment Management</li>
        <li>{'✓' if PM_SCHEDULING_TAB_AVAILABLE else '✗'} PM Scheduling</li>
        <li>{'✓' if PM_COMPLETION_TAB_AVAILABLE else '✗'} PM Completion</li>
        <li>{'✓' if CM_MANAGEMENT_TAB_AVAILABLE else '✗'} CM Management</li>
        <li>{'✓' if MRO_STOCK_TAB_AVAILABLE else '✗'} MRO Stock</li>
        <li>{'✓' if EQUIPMENT_HISTORY_TAB_AVAILABLE else '✗'} Equipment History</li>
        <li>{'✓' if KPI_DASHBOARD_AVAILABLE else '✗'} KPI Dashboard</li>
        <li>{'✓' if KPI_TREND_ANALYZER_AVAILABLE else '✗'} KPI Trends</li>
        </ul>
        """

        QMessageBox.about(self, "Version Information", version_info)

    def logout(self):
        """Logout current user"""
        result = QMessageBox.question(
            self, "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result == QMessageBox.Yes:
            try:
                if self.session_id:
                    with db_pool.get_cursor() as cursor:
                        UserManager.end_session(cursor, self.session_id)
                        print(f"User session ended for {self.user_name}")
            except Exception as e:
                print(f"Error ending session: {e}")

            # Save window state
            self.save_window_state()

            # Close application
            self.close()

    # ===== SIGNAL HANDLERS =====

    def on_tab_changed(self, index):
        """Handle tab change event"""
        if index >= 0:
            tab_name = self.tab_widget.tabText(index)
            self.update_status(f"Switched to: {tab_name}")

    def on_pm_completed(self, bfm_no, pm_type, technician):
        """Handle PM completion signal"""
        self.update_status(f"PM Completed: {bfm_no} - {pm_type} by {technician}")

        # Refresh other tabs if needed
        if self.equipment_tab:
            try:
                self.equipment_tab.refresh_equipment_list()
            except:
                pass

    def update_status(self, message: str):
        """Update status bar with message"""
        # Guard against calls before status_message is initialized
        if hasattr(self, 'status_message') and self.status_message:
            self.status_message.setText(message)
        print(f"Status: {message}")

    def check_database_connection(self):
        """Check database connection status"""
        try:
            with db_pool.get_cursor() as cursor:
                cursor.execute("SELECT 1")
            self.status_connection.setText("🟢 Connected")
            self.status_connection.setStyleSheet("color: #27ae60; font-weight: bold;")
        except Exception as e:
            self.status_connection.setText("🔴 Disconnected")
            self.status_connection.setStyleSheet("color: #e74c3c; font-weight: bold;")
            print(f"Database connection check failed: {e}")

    # ===== UTILITY METHODS =====

    def get_week_start(self, date: datetime) -> datetime:
        """Get the start of the week (Monday) for a given date"""
        return date - timedelta(days=date.weekday())

    # ===== WINDOW EVENT HANDLERS =====

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event"""
        result = QMessageBox.question(
            self, "Confirm Exit",
            "Are you sure you want to close the application?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result == QMessageBox.Yes:
            try:
                # End user session
                if self.session_id:
                    with db_pool.get_cursor() as cursor:
                        UserManager.end_session(cursor, self.session_id)
                        print(f"User session ended for {self.user_name}")

                # Save window state
                self.save_window_state()

            except Exception as e:
                print(f"Error during cleanup: {e}")

            event.accept()
        else:
            event.ignore()


# ===== MAIN ENTRY POINT =====

def main():
    """Main entry point with splash screen"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look

    # Set application info
    app.setApplicationName("AIT CMMS")
    app.setOrganizationName("AIT")
    app.setApplicationVersion("2.2")

    # Set application font for better readability
    font = QFont("Arial", 10)
    app.setFont(font)

    # Show splash screen
    try:
        splash_pix = QPixmap(400, 300)
        splash_pix.fill(QColor('#2c3e50'))
        splash = QSplashScreen(splash_pix)
        splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

        # Add text to splash
        splash.showMessage(
            "AIT Complete CMMS\nLoading...",
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )
        splash.show()
        app.processEvents()

        # Simulate loading time
        QTimer.singleShot(1000, splash.close)
    except:
        # If splash fails, just continue
        pass

    # Create and show main window
    window = AITCMMSSystemPyQt5()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
