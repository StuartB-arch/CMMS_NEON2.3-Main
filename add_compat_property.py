#!/usr/bin/env python3
"""
Add compatibility property to tab files
"""

import re
import sys

def add_property_after_init(file_path):
    """Add @property conn compatibility method after __init__"""

    with open(file_path, 'r') as f:
        content = f.read()

    # Property to add
    property_code = '''
    @property
    def conn(self):
        """Compatibility property - returns a connection from pool for legacy code"""
        # This allows existing code using self.conn to work with connection pooling
        return self.db_pool.get_connection()
'''

    # Find the position after __init__ method
    # Look for the end of __init__ method (next method definition or class definition)
    pattern = r'(def __init__\(self[^)]*\):.*?)(    def [a-z_]+\(self|class [A-Z])'

    def replacer(match):
        init_method = match.group(1)
        next_item = match.group(2)
        return init_method + property_code + '\n' + next_item

    # Only add if not already present
    if '@property' not in content or 'def conn(self)' not in content:
        content = re.sub(pattern, replacer, content, count=1, flags=re.DOTALL)
        print(f"Added compatibility property to {file_path}")
    else:
        print(f"Compatibility property already exists in {file_path}")

    # Add db_pool import if not present
    if 'from database_utils import db_pool' not in content:
        # Find first import block
        lines = content.split('\n')
        import_insert_line = None
        for i, line in enumerate(lines):
            if line.startswith('from PyQt5') or line.startswith('import '):
                # Find end of import block
                for j in range(i, len(lines)):
                    if lines[j] and not lines[j].startswith(('from ', 'import ', ' ', '#')):
                        import_insert_line = j
                        break
                break

        if import_insert_line:
            lines.insert(import_insert_line, '\n# Import database utilities for connection pooling')
            lines.insert(import_insert_line + 1, 'from database_utils import db_pool as _db_pool_module\n')
            content = '\n'.join(lines)
            print(f"Added db_pool import to {file_path}")

    with open(file_path, 'w') as f:
        f.write(content)

if __name__ == '__main__':
    files = [
        'equipment_tab_pyqt5.py',
        'equipment_history_tab_pyqt5.py',
        'mro_stock_tab_pyqt5.py'
    ]

    for file in files:
        try:
            add_property_after_init(file)
        except Exception as e:
            print(f"Error processing {file}: {e}")
