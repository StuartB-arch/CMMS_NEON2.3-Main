#!/bin/bash
# Batch fix for database pool usage in all tab files

# Backup all files first
for file in pm_completion_tab_pyqt5.py pm_scheduling_tab_pyqt5.py equipment_tab_pyqt5.py \
             equipment_history_tab_pyqt5.py mro_stock_tab_pyqt5.py; do
    if [ -f "$file" ]; then
        cp "$file" "${file}.backup_$(date +%Y%m%d_%H%M%S)"
        echo "Backed up $file"
    fi
done

# For now, let's create a minimal compatibility layer by adding a connection property
# This allows the tabs to work with db_pool while maintaining backward compatibility

echo "Batch fix script ready. Files backed up."
echo "Manual fixes still needed for proper connection pooling."
