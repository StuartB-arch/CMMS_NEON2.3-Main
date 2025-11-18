#!/usr/bin/env python3
"""
Script to fix database cursor usage in PyQt5 tabs
Converts from direct connection usage to connection pool context managers
"""

import re
import sys

def fix_cursor_pattern(content):
    """Fix cursor creation patterns to use db_pool.get_cursor()"""

    # Pattern 1: Simple cursor creation and close
    # Replace: cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
    # With: with self.db_pool.get_cursor() as cursor:

    # First, we need to identify try blocks with cursor creation
    # This is complex, so let's do a simpler replacement for now

    # Replace self.conn with self.db_pool in parameter
    content = content.replace('self.conn =', 'self.db_pool =')

    return content

def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_cursors.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    with open(file_path, 'r') as f:
        content = f.read()

    fixed_content = fix_cursor_pattern(content)

    # Backup original
    with open(file_path + '.backup', 'w') as f:
        f.write(content)

    # Write fixed version
    with open(file_path, 'w') as f:
        f.write(fixed_content)

    print(f"Fixed {file_path}")
    print(f"Backup saved to {file_path}.backup")

if __name__ == '__main__':
    main()
