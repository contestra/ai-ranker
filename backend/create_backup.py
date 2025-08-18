#!/usr/bin/env python
"""Create a backup of the SQLite database."""

import shutil
import os
from datetime import datetime
from pathlib import Path

def create_backup():
    # Create timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Paths
    source_db = 'ai_ranker.db'
    backup_dir = Path('backups')
    backup_file = backup_dir / f'db_backup_{timestamp}.sqlite'
    
    # Create backup directory if it doesn't exist
    backup_dir.mkdir(exist_ok=True)
    
    # Check if source database exists
    if not os.path.exists(source_db):
        print(f"Error: Database file '{source_db}' not found")
        return False
    
    # Create backup
    try:
        shutil.copy2(source_db, backup_file)
        print(f"[SUCCESS] Backup created successfully: {backup_file}")
        print(f"          Size: {os.path.getsize(backup_file):,} bytes")
        return True
    except Exception as e:
        print(f"[ERROR] Error creating backup: {e}")
        return False

if __name__ == "__main__":
    create_backup()