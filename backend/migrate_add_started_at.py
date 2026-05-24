import sqlite3

# 连接数据库
conn = sqlite3.connect('d:/aicode_/aicode/backend/code_detection.db')
cursor = conn.cursor()

try:
    # 添加 started_at 字段
    cursor.execute('ALTER TABLE analysis_tasks ADD COLUMN started_at DATETIME')
    print("Migration completed successfully: added started_at column")
    conn.commit()
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Column 'started_at' already exists, skipping migration")
    else:
        raise
finally:
    conn.close()