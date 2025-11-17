"""
Password Change Dialog - PyQt5 Implementation
Allows users to change their own passwords
Complete port from Tkinter to PyQt5
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QFormLayout, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from database_utils import db_pool, UserManager, AuditLogger


class PasswordChangeDialog(QDialog):
    """Dialog for users to change their own password"""

    password_changed = pyqtSignal(bool)  # Signal emitted when password is changed

    def __init__(self, current_user, username, parent=None):
        """
        Initialize Password Change Dialog

        Args:
            current_user: Current user's full name (for audit logging)
            username: Current user's username
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_user = current_user
        self.username = username

        self.setWindowTitle("Change Password")
        self.setFixedSize(450, 350)
        self.setModal(True)

        self.init_ui()
        self.center_on_parent()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Header Section
        header_frame = self.create_header()
        layout.addWidget(header_frame)

        # Form Section
        form_frame = self.create_form()
        layout.addWidget(form_frame)

        # Password Requirements
        requirements_frame = self.create_requirements()
        layout.addWidget(requirements_frame)

        # Buttons
        button_frame = self.create_buttons()
        layout.addWidget(button_frame)

        self.setLayout(layout)

        # Set keyboard shortcuts
        self.current_password_entry.setFocus()

    def create_header(self):
        """Create header section"""
        frame = QFrame()
        layout = QVBoxLayout()

        # Title
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label = QLabel("Change Your Password")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # User label
        user_font = QFont()
        user_font.setPointSize(10)
        user_label = QLabel(f"User: {self.username}")
        user_label.setFont(user_font)
        user_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(user_label)

        frame.setLayout(layout)
        return frame

    def create_form(self):
        """Create password entry form"""
        frame = QFrame()
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # Current Password
        self.current_password_entry = QLineEdit()
        self.current_password_entry.setEchoMode(QLineEdit.Password)
        self.current_password_entry.setMinimumWidth(250)
        form_layout.addRow("Current Password:", self.current_password_entry)

        # New Password
        self.new_password_entry = QLineEdit()
        self.new_password_entry.setEchoMode(QLineEdit.Password)
        self.new_password_entry.setMinimumWidth(250)
        form_layout.addRow("New Password:", self.new_password_entry)

        # Confirm New Password
        self.confirm_password_entry = QLineEdit()
        self.confirm_password_entry.setEchoMode(QLineEdit.Password)
        self.confirm_password_entry.setMinimumWidth(250)
        form_layout.addRow("Confirm New Password:", self.confirm_password_entry)

        frame.setLayout(form_layout)
        return frame

    def create_requirements(self):
        """Create password requirements section"""
        frame = QFrame()
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Title
        title_font = QFont()
        title_font.setPointSize(9)
        title_font.setBold(True)
        title_label = QLabel("Password Requirements:")
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Requirements
        req_font = QFont()
        req_font.setPointSize(8)

        req1_label = QLabel("• Minimum 4 characters")
        req1_label.setFont(req_font)
        req1_label.setStyleSheet("color: gray;")
        layout.addWidget(req1_label)

        req2_label = QLabel("• Avoid using common passwords")
        req2_label.setFont(req_font)
        req2_label.setStyleSheet("color: gray;")
        layout.addWidget(req2_label)

        frame.setLayout(layout)
        return frame

    def create_buttons(self):
        """Create button section"""
        frame = QFrame()
        layout = QHBoxLayout()

        # Change Password Button
        change_btn = QPushButton("Change Password")
        change_btn.setMinimumWidth(150)
        change_btn.clicked.connect(self.change_password)
        change_btn.setDefault(True)
        layout.addWidget(change_btn)

        # Cancel Button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(150)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        layout.addStretch()
        frame.setLayout(layout)
        return frame

    def center_on_parent(self):
        """Center dialog on parent window"""
        if self.parent():
            parent_geometry = self.parent().geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)

    def change_password(self):
        """Handle password change"""
        current_password = self.current_password_entry.text().strip()
        new_password = self.new_password_entry.text().strip()
        confirm_password = self.confirm_password_entry.text().strip()

        # Validate inputs
        if not current_password:
            QMessageBox.critical(self, "Validation Error", "Please enter your current password")
            self.current_password_entry.setFocus()
            return

        if not new_password:
            QMessageBox.critical(self, "Validation Error", "Please enter a new password")
            self.new_password_entry.setFocus()
            return

        if len(new_password) < 4:
            QMessageBox.critical(self, "Validation Error", "New password must be at least 4 characters long")
            self.new_password_entry.setFocus()
            return

        if new_password != confirm_password:
            QMessageBox.critical(self, "Validation Error", "New passwords do not match")
            self.confirm_password_entry.clear()
            self.confirm_password_entry.setFocus()
            return

        if current_password == new_password:
            QMessageBox.warning(self, "Validation Warning",
                               "New password must be different from current password")
            self.new_password_entry.setFocus()
            return

        # Attempt to change password
        try:
            with db_pool.get_cursor(commit=True) as cursor:
                success, message = UserManager.change_password(
                    cursor, self.username, current_password, new_password
                )

                if success:
                    # Log the password change to audit log
                    AuditLogger.log(
                        cursor,
                        self.current_user,
                        'UPDATE',
                        'users',
                        self.username,
                        notes="User changed their own password"
                    )

                    QMessageBox.information(self, "Success", message)
                    self.password_changed.emit(True)
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", message)
                    # Clear password fields if current password was wrong
                    if "incorrect" in message.lower():
                        self.current_password_entry.clear()
                        self.current_password_entry.setFocus()
                    self.password_changed.emit(False)

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to change password: {str(e)}")
            self.password_changed.emit(False)
            print(f"Password change error: {e}")

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.change_password()
        elif event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)


# Convenience function for compatibility
def show_password_change_dialog(parent, current_user, username):
    """
    Show password change dialog

    Args:
        parent: Parent widget
        current_user: Current user's full name (for audit logging)
        username: Current user's username

    Returns:
        Dialog instance
    """
    dialog = PasswordChangeDialog(current_user, username, parent)
    return dialog
