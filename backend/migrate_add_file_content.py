#!/usr/bin/env python3
"""
Database migration script
Add file_content and task_id columns for independent file detection
"""

import os
import sqlite3
import sys

def run_migration():
    db_path = os.path.join(os.path.dirname(__file__), '../code_detection.db')

    if not os.path.exists(db_path):
        print(f"ERROR: Database file not found: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"SUCCESS: Connected to database: {db_path}")

        cursor.execute("PRAGMA table_info(analysis_tasks)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'file_content' not in columns:
            print("MIGRATING: Adding file_content column to analysis_tasks...")
            cursor.execute("ALTER TABLE analysis_tasks ADD COLUMN file_content TEXT")
            print("DONE: file_content column added")
        else:
            print("SKIP: file_content column already exists")

        cursor.execute("PRAGMA table_info(comparison_results)")
        comp_columns = [col[1] for col in cursor.fetchall()]

        if 'task_id' not in comp_columns:
            print("MIGRATING: Adding task_id column to comparison_results...")
            cursor.execute("ALTER TABLE comparison_results ADD COLUMN task_id INTEGER")
            print("DONE: task_id column added")
        else:
            print("SKIP: task_id column already exists")

        print("MIGRATING: Creating index...")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_comparison_results_task_id ON comparison_results (task_id)")
        print("DONE: Index created")

        conn.commit()
        conn.close()
        print("SUCCESS: Migration completed!")
        return True

    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
