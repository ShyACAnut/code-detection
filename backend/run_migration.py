#!/usr/bin/env python3
"""
数据库迁移执行脚本
用于执行缺失的数据库迁移
"""

import os
import sqlite3

def run_migration():
    # 获取数据库路径
    db_path = os.path.join(os.path.dirname(__file__), '../code_detection.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"✅ 成功连接数据库: {db_path}")
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ablation_batch_tasks'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ ablation_batch_tasks 表已存在")
            
            # 检查 current_index 列是否存在
            cursor.execute("PRAGMA table_info(ablation_batch_tasks)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'current_index' in columns:
                print("✅ current_index 列已存在，无需迁移")
                conn.close()
                return True
            
            # 执行迁移 - 添加列
            print("🔧 正在添加 current_index 列...")
            cursor.execute("""
                ALTER TABLE ablation_batch_tasks
                ADD COLUMN IF NOT EXISTS current_index INTEGER DEFAULT 0
            """)
            
            conn.commit()
            print("✅ 迁移执行成功！")
            
            # 验证
            cursor.execute("PRAGMA table_info(ablation_batch_tasks)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'current_index' in columns:
                print("✅ 验证通过: current_index 列已添加")
            else:
                print("❌ 验证失败: current_index 列未添加")
                
        else:
            # 表不存在，创建完整表结构
            print("🔧 ablation_batch_tasks 表不存在，正在创建...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ablation_batch_tasks (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    mode VARCHAR NOT NULL,
                    total_pairs INTEGER NOT NULL,
                    current_index INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    completion_rate FLOAT DEFAULT 0.0,
                    summary_json TEXT,
                    status VARCHAR DEFAULT 'running',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_ablation_batch_tasks_user_id ON ablation_batch_tasks (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_ablation_batch_tasks_mode ON ablation_batch_tasks (mode)")
            
            conn.commit()
            print("✅ 表创建成功！")
            
            # 验证
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ablation_batch_tasks'")
            if cursor.fetchone():
                print("✅ 验证通过: ablation_batch_tasks 表已创建")
            else:
                print("❌ 验证失败: 表未创建")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 迁移执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*50)
    print("数据库迁移脚本")
    print("="*50)
    
    success = run_migration()
    
    if success:
        print("\n🎉 迁移完成！")
        print("现在可以重新启动服务器运行消融实验了。")
    else:
        print("\n❌ 迁移失败，请检查错误信息。")