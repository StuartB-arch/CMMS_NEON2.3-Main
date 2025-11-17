"""
User Management Dialog - PyQt5 Implementation
Allows managers to create, edit, and manage system users
Complete port from Tkinter to PyQt5
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QMessageBox, QHeaderView, QGroupBox,
    QFormLayout, QComboBox, QCheckBox, QTextEdit, QFrame,
    QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from psycopg2 import extras
from database_utils import db_pool, UserManager, AuditLogger


class UserManagementDialog(QDialog):
    """Dialog for managing users (Manager access only)"""

    user_updated = pyqtSignal()  # Signal emitted when user data changes

    def __init__(self, current_user, parent=None):
        """
        Initialize User Management Dialog

        Args:
            current_user: Current user's username (for audit logging)
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_user = current_user

        self.setWindowTitle("User Management")
        self.setMinimumSize(1000, 600)
        self.setModal(False)

        self.init_ui()
        self.load_users()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Header Section
        header_frame = self.create_header()
        layout.addWidget(header_frame)

        # User List Section
        list_group = self.create_user_list_section()
        layout.addWidget(list_group)

        # Close Button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def create_header(self):
        """Create header section with title and buttons"""
        frame = QFrame()
        layout = QHBoxLayout()

        # Title
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label = QLabel("User Management")
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        layout.addStretch()

        # Control Buttons
        add_btn = QPushButton("Add User")
        add_btn.clicked.connect(self.add_user)
        layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit User")
        edit_btn.clicked.connect(self.edit_user)
        layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete User")
        delete_btn.clicked.connect(self.delete_user)
        layout.addWidget(delete_btn)

        sessions_btn = QPushButton("View Sessions")
        sessions_btn.clicked.connect(self.view_sessions)
        layout.addWidget(sessions_btn)

        frame.setLayout(layout)
        return frame

    def create_user_list_section(self):
        """Create user list table section"""
        group = QGroupBox("System Users")
        layout = QVBoxLayout()

        # User Table
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(7)
        self.user_table.setHorizontalHeaderLabels([
            'ID', 'Username', 'Full Name', 'Role', 'Active', 'Last Login', 'Created'
        ])

        # Set column resize modes
        header = self.user_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        self.user_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.user_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.user_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.user_table.setAlternatingRowColors(True)

        layout.addWidget(self.user_table)
        group.setLayout(layout)
        return group

    def load_users(self):
        """Load all users from database"""
        try:
            # Clear existing items
            self.user_table.setRowCount(0)

            with db_pool.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, full_name, role, is_active,
                           last_login, created_date
                    FROM users
                    ORDER BY created_date DESC
                """)

                rows = cursor.fetchall()
                self.user_table.setRowCount(len(rows))

                for row_idx, row_data in enumerate(rows):
                    # ID
                    self.user_table.setItem(row_idx, 0, QTableWidgetItem(str(row_data['id'])))

                    # Username
                    self.user_table.setItem(row_idx, 1, QTableWidgetItem(str(row_data['username'])))

                    # Full Name
                    self.user_table.setItem(row_idx, 2, QTableWidgetItem(str(row_data['full_name'])))

                    # Role
                    self.user_table.setItem(row_idx, 3, QTableWidgetItem(str(row_data['role'])))

                    # Active
                    active_text = 'Yes' if row_data['is_active'] else 'No'
                    self.user_table.setItem(row_idx, 4, QTableWidgetItem(active_text))

                    # Last Login
                    last_login = str(row_data['last_login']) if row_data['last_login'] else 'Never'
                    self.user_table.setItem(row_idx, 5, QTableWidgetItem(last_login))

                    # Created
                    self.user_table.setItem(row_idx, 6, QTableWidgetItem(str(row_data['created_date'])))

            self.user_updated.emit()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load users: {str(e)}")

    def add_user(self):
        """Show dialog to add a new user"""
        dialog = AddUserDialog(self.current_user, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_users()

    def edit_user(self):
        """Edit selected user"""
        selected_items = self.user_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a user to edit")
            return

        row = selected_items[0].row()
        user_id = int(self.user_table.item(row, 0).text())

        # Fetch user details
        try:
            with db_pool.get_cursor() as cursor:
                cursor.execute("""
                    SELECT username, full_name, email, role, is_active, notes
                    FROM users
                    WHERE id = %s
                """, (user_id,))
                user = cursor.fetchone()

                if not user:
                    QMessageBox.critical(self, "Error", "User not found")
                    return

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load user: {str(e)}")
            return

        # Show edit dialog
        dialog = EditUserDialog(user_id, user, self.current_user, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_users()

    def delete_user(self):
        """Delete selected user"""
        selected_items = self.user_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a user to delete")
            return

        row = selected_items[0].row()
        user_id = int(self.user_table.item(row, 0).text())
        username = self.user_table.item(row, 1).text()
        role = self.user_table.item(row, 3).text()

        # Prevent self-deletion
        if username == self.current_user:
            QMessageBox.critical(self, "Error", "You cannot delete your own account")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete user '{username}' ({role})?\n\n"
            "This action cannot be undone and will:\n"
            "- Remove the user from the system\n"
            "- End any active sessions\n"
            "- Preserve audit trail entries\n\n"
            "Note: For safety, consider deactivating the user instead "
            "(via Edit User).",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            with db_pool.get_cursor() as cursor:
                # Log the deletion before deleting the user
                AuditLogger.log(cursor, self.current_user, 'DELETE', 'users', str(user_id),
                               notes=f"Deleted user: {username} ({role})")

                # Delete all sessions for this user first (to avoid foreign key constraint)
                cursor.execute("DELETE FROM user_sessions WHERE user_id = %s", (user_id,))

                # Now delete the user
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

                # Check if deletion was successful
                if cursor.rowcount == 0:
                    QMessageBox.critical(self, "Error", "User not found or already deleted")
                    return

            QMessageBox.information(self, "Success", f"User '{username}' has been deleted successfully")
            self.load_users()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete user: {str(e)}")

    def view_sessions(self):
        """View active user sessions"""
        dialog = SessionsViewDialog(self)
        dialog.exec_()


class AddUserDialog(QDialog):
    """Dialog for adding a new user"""

    def __init__(self, current_user, parent=None):
        """
        Initialize Add User Dialog

        Args:
            current_user: Current user's username (for audit logging)
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_user = current_user

        self.setWindowTitle("Add User")
        self.setMinimumSize(400, 400)
        self.setModal(True)

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()

        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Username
        self.username_entry = QLineEdit()
        form_layout.addRow("Username:", self.username_entry)

        # Full Name
        self.fullname_entry = QLineEdit()
        form_layout.addRow("Full Name:", self.fullname_entry)

        # Email
        self.email_entry = QLineEdit()
        form_layout.addRow("Email:", self.email_entry)

        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(['Manager', 'Technician'])
        self.role_combo.setCurrentText('Technician')
        form_layout.addRow("Role:", self.role_combo)

        # Password
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_entry)

        # Confirm Password
        self.confirm_entry = QLineEdit()
        self.confirm_entry.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Confirm Password:", self.confirm_entry)

        # Notes
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        form_layout.addRow("Notes:", self.notes_text)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_user)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def save_user(self):
        """Save new user to database"""
        username = self.username_entry.text().strip()
        fullname = self.fullname_entry.text().strip()
        email = self.email_entry.text().strip()
        role = self.role_combo.currentText()
        password = self.password_entry.text()
        confirm = self.confirm_entry.text()
        notes = self.notes_text.toPlainText().strip()

        # Validation
        if not username or not fullname or not password:
            QMessageBox.critical(self, "Error", "Username, full name, and password are required")
            return

        if password != confirm:
            QMessageBox.critical(self, "Error", "Passwords do not match")
            return

        if len(password) < 4:
            QMessageBox.critical(self, "Error", "Password must be at least 4 characters")
            return

        try:
            with db_pool.get_cursor() as cursor:
                # Check if username exists
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    QMessageBox.critical(self, "Error", "Username already exists")
                    return

                # Create user
                password_hash = UserManager.hash_password(password)
                cursor.execute("""
                    INSERT INTO users
                    (username, password_hash, full_name, email, role, created_by, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (username, password_hash, fullname, email, role, self.current_user, notes))

                # Log the action
                AuditLogger.log(cursor, self.current_user, 'INSERT', 'users', username,
                               notes=f"Created new {role} user: {fullname}")

            QMessageBox.information(self, "Success", f"User '{username}' created successfully")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create user: {str(e)}")


class EditUserDialog(QDialog):
    """Dialog for editing an existing user"""

    def __init__(self, user_id, user_data, current_user, parent=None):
        """
        Initialize Edit User Dialog

        Args:
            user_id: ID of user to edit
            user_data: Dictionary with user data
            current_user: Current user's username (for audit logging)
            parent: Parent widget
        """
        super().__init__(parent)
        self.user_id = user_id
        self.user_data = user_data
        self.current_user = current_user

        self.setWindowTitle("Edit User")
        self.setMinimumSize(400, 450)
        self.setModal(True)

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()

        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Username (read-only)
        username_label = QLabel(self.user_data['username'])
        username_font = QFont()
        username_font.setBold(True)
        username_label.setFont(username_font)
        form_layout.addRow("Username:", username_label)

        # Full Name
        self.fullname_entry = QLineEdit()
        self.fullname_entry.setText(self.user_data['full_name'])
        form_layout.addRow("Full Name:", self.fullname_entry)

        # Email
        self.email_entry = QLineEdit()
        self.email_entry.setText(self.user_data['email'] or '')
        form_layout.addRow("Email:", self.email_entry)

        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(['Manager', 'Technician'])
        self.role_combo.setCurrentText(self.user_data['role'])
        form_layout.addRow("Role:", self.role_combo)

        # Active
        self.active_checkbox = QCheckBox()
        self.active_checkbox.setChecked(self.user_data['is_active'])
        form_layout.addRow("Active:", self.active_checkbox)

        # New Password
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.Password)
        form_layout.addRow("New Password:", self.password_entry)

        hint_label = QLabel("(leave blank to keep current)")
        hint_font = QFont()
        hint_font.setPointSize(8)
        hint_label.setFont(hint_font)
        hint_label.setStyleSheet("color: gray;")
        form_layout.addRow("", hint_label)

        # Notes
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        self.notes_text.setPlainText(self.user_data['notes'] or '')
        form_layout.addRow("Notes:", self.notes_text)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_changes)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def save_changes(self):
        """Save changes to database"""
        try:
            with db_pool.get_cursor() as cursor:
                # Build update query
                updates = []
                params = []

                updates.append("full_name = %s")
                params.append(self.fullname_entry.text().strip())

                updates.append("email = %s")
                params.append(self.email_entry.text().strip())

                updates.append("role = %s")
                params.append(self.role_combo.currentText())

                updates.append("is_active = %s")
                params.append(self.active_checkbox.isChecked())

                updates.append("notes = %s")
                params.append(self.notes_text.toPlainText().strip())

                # Update password if provided
                new_password = self.password_entry.text()
                if new_password:
                    updates.append("password_hash = %s")
                    params.append(UserManager.hash_password(new_password))

                updates.append("updated_date = CURRENT_TIMESTAMP")
                params.append(self.user_id)

                query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
                cursor.execute(query, params)

                # Log the action
                AuditLogger.log(cursor, self.current_user, 'UPDATE', 'users', str(self.user_id),
                               notes=f"Updated user: {self.user_data['username']}")

            QMessageBox.information(self, "Success", "User updated successfully")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update user: {str(e)}")


class SessionsViewDialog(QDialog):
    """Dialog for viewing active user sessions"""

    def __init__(self, parent=None):
        """
        Initialize Sessions View Dialog

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.setWindowTitle("Active User Sessions")
        self.setMinimumSize(800, 400)
        self.setModal(True)

        self.init_ui()
        self.load_sessions()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()

        # Header
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header_label = QLabel("Active User Sessions")
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        # Sessions Table
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(6)
        self.sessions_table.setHorizontalHeaderLabels([
            'Session ID', 'User', 'Full Name', 'Role', 'Login Time', 'Last Activity'
        ])

        header = self.sessions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.sessions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sessions_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sessions_table.setAlternatingRowColors(True)

        layout.addWidget(self.sessions_table)

        # Close Button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def load_sessions(self):
        """Load active sessions from database"""
        try:
            with db_pool.get_cursor() as cursor:
                sessions = UserManager.get_active_sessions(cursor)

                self.sessions_table.setRowCount(len(sessions))
                for row_idx, session in enumerate(sessions):
                    self.sessions_table.setItem(row_idx, 0, QTableWidgetItem(str(session['id'])))
                    self.sessions_table.setItem(row_idx, 1, QTableWidgetItem(session['username']))
                    self.sessions_table.setItem(row_idx, 2, QTableWidgetItem(session['full_name']))
                    self.sessions_table.setItem(row_idx, 3, QTableWidgetItem(session['role']))
                    self.sessions_table.setItem(row_idx, 4, QTableWidgetItem(str(session['login_time'])))
                    self.sessions_table.setItem(row_idx, 5, QTableWidgetItem(str(session['last_activity'])))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load sessions: {str(e)}")


# Convenience function for compatibility
def show_user_management_dialog(current_user, parent=None):
    """
    Show user management dialog

    Args:
        current_user: Current user's username
        parent: Parent widget

    Returns:
        Dialog instance
    """
    dialog = UserManagementDialog(current_user, parent)
    return dialog
