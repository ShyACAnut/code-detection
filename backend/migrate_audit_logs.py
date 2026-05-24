"""
数据库迁移脚本 - 为 audit_logs 表添加缺失的列
=============================================

该脚本用于为 audit_logs 表添加缺失的 ip_address 和 user_agent 列。
"""

import sqlite3
import os

def migrate_database():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_detection.db")
    print(f"[INFO] 使用数据库路径: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(audit_logs)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"[INFO] 当前 audit_logs 表的列: {columns}")

        if 'ip_address' not in columns:
            cursor.execute("""
                ALTER TABLE audit_logs
                ADD COLUMN ip_address TEXT
            """)
            print("[OK] 成功添加 ip_address 列")
        else:
            print("[INFO] ip_address 列已存在")

        if 'user_agent' not in columns:
            cursor.execute("""
                ALTER TABLE audit_logs
                ADD COLUMN user_agent TEXT
            """)
            print("[OK] 成功添加 user_agent 列")
        else:
            print("[INFO] user_agent 列已存在")

        conn.commit()
        print("[OK] 数据库迁移完成")

    except Exception as e:
        print(f"[ERROR] 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()