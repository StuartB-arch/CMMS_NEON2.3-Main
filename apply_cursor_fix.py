#!/usr/bin/env python3
"""
Automatic Database Cursor Fix Script
Fixes all PyQt5 tab files to use RealDictCursor properly
"""

import os
import re
from pathlib import Path

# Files to fix
FILES_TO_FIX = [
    'equipment_tab_pyqt5.py',
    'pm_scheduling_tab_pyqt5.py',
    'pm_completion_tab_pyqt5.py',
    'cm_management_tab_pyqt5.py',
    'mro_stock_tab_pyqt5.py',
    'equipment_history_tab_pyqt5.py',
    'kpi_trend_analyzer_tab_pyqt5.py',
    'parts_integration_dialog_pyqt5.py',
    'user_management_dialog_pyqt5.py',
]

def fix_file(filepath):
    """Fix a single file by adding proper cursor factory"""

    print(f"Processing: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Check if already has the import
        if 'from psycopg2 import extras' not in content:
            # Find the right place to add it (after other psycopg2 imports)
            if 'import psycopg2' in content:
                # Add after the existing psycopg2 import
                content = re.sub(
                    r'(from psycopg2 import[^\n]+)',
                    r'\1\nfrom psycopg2 import extras',
                    content
                )
            else:
                # Add at the top after other imports
                content = re.sub(
                    r'(import [a-zA-Z_][a-zA-Z0-9_]*\n)',
                    r'\1from psycopg2 import extras\n',
                    content,
                    count=1
                )
            print(f"  ✓ Added psycopg2.extras import")

        # Replace all cursor() calls with cursor(cursor_factory=extras.RealDictCursor)
        replacement_count = 0

        # Pattern 1: self.conn.cursor()
        new_content = re.sub(
            r'self\.conn\.cursor\(\)',
            r'self.conn.cursor(cursor_factory=extras.RealDictCursor)',
            content
        )
        if new_content != content:
            replacement_count += new_content.count('cursor_factory=extras.RealDictCursor') - content.count('cursor_factory=extras.RealDictCursor')
            content = new_content

        # Pattern 2: conn.cursor() where conn is a variable
        new_content = re.sub(
            r'(\w+)\.cursor\(\)(?!.*cursor_factory)',
            r'\1.cursor(cursor_factory=extras.RealDictCursor)',
            content
        )
        if new_content != content:
            replacement_count += new_content.count('cursor_factory=extras.RealDictCursor') - content.count('cursor_factory=extras.RealDictCursor')
            content = new_content

        # Save the file
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Fixed cursor() calls")
            return True
        else:
            print(f"  - No changes needed")
            return False

    except FileNotFoundError:
        print(f"  ✗ File not found: {filepath}")
        return False
    except Exception as e:
        print(f"  ✗ Error processing file: {e}")
        return False

def main():
    """Main function"""
    print("=" * 70)
    print("PyQt5 Database Cursor Fix - Automatic Apply")
    print("=" * 70)
    print()

    current_dir = Path.cwd()
    fixed_count = 0

    for filename in FILES_TO_FIX:
        filepath = current_dir / filename
        if filepath.exists():
            if fix_file(str(filepath)):
                fixed_count += 1
        else:
            print(f"Skipping: {filename} (not found)")

    print()
    print("=" * 70)
    print(f"✓ Fixed {fixed_count} file(s)")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review the changes: git diff")
    print("2. Test the application: python3 AIT_CMMS_REV3_PyQt5.py")
    print("3. If all works, commit: git add -A && git commit -m 'Fix database cursor factory issues'")
    print()

if __name__ == '__main__':
    main()
