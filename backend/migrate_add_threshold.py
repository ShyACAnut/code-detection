"""
数据库迁移脚本 - 添加 detection_threshold 列
=============================================

该脚本用于为 assignments 表添加缺失的 detection_threshold 列。
"""

import sqlite3

def migrate_database():
    # 连接到SQLite数据库
    conn = sqlite3.connect('d:/aicode_/code_detection.db')
    cursor = conn.cursor()
    
    try:
        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(assignments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'detection_threshold' not in columns:
            # 添加 detection_threshold 列，默认值为 80.0
            cursor.execute("""
                ALTER TABLE assignments 
                ADD COLUMN detection_threshold REAL DEFAULT 80.0
            """)
            print("[OK] 成功添加 detection_threshold 列")
            
            # 更新现有记录的默认值
            cursor.execute("""
                UPDATE assignments 
                SET detection_threshold = 80.0 
                WHERE detection_threshold IS NULL
            """)
            print("[OK] 成功更新现有记录的默认值")
            
            conn.commit()
            print("[OK] 数据库迁移完成")
        else:
            print("[OK] detection_threshold 列已存在，无需迁移")
            
    except Exception as e:
        print(f"[ERROR] 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
