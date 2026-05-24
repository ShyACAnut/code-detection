#!/usr/bin/env python3
"""
数据库合并脚本
=============

将消融实验相关的表从一个数据库迁移到另一个数据库。

用法：
python merge_databases.py

说明：
- 源数据库：d:\aicode_\aicode\code_detection.db（包含消融实验表）
- 目标数据库：d:\aicode_\aicode\backend\code_detection.db（包含用户数据）
"""

import sqlite3
import os

def merge_databases():
    # 定义数据库路径
    source_db_path = r"d:\aicode_\aicode\code_detection.db"
    target_db_path = r"d:\aicode_\aicode\backend\code_detection.db"
    
    print("="*60)
    print("数据库合并脚本")
    print("="*60)
    print(f"源数据库: {source_db_path}")
    print(f"目标数据库: {target_db_path}")
    print()
    
    # 检查源数据库是否存在
    if not os.path.exists(source_db_path):
        print(f"❌ 源数据库不存在: {source_db_path}")
        return False
    
    # 检查目标数据库是否存在
    if not os.path.exists(target_db_path):
        print(f"❌ 目标数据库不存在: {target_db_path}")
        return False
    
    # 连接到源数据库
    source_conn = sqlite3.connect(source_db_path)
    source_cursor = source_conn.cursor()
    
    # 连接到目标数据库
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()
    
    try:
        # 获取源数据库中的表
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        source_tables = [row[0] for row in source_cursor.fetchall()]
        print(f"📋 源数据库中的表: {source_tables}")
        
        # 获取目标数据库中的表
        target_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        target_tables = [row[0] for row in target_cursor.fetchall()]
        print(f"📋 目标数据库中的表: {target_tables}")
        print()
        
        # 定义需要迁移的消融实验相关表
        ablation_tables = ['ablation_batch_tasks', 'ablation_task_details']
        
        for table_name in ablation_tables:
            if table_name not in source_tables:
                print(f"⏭️ 跳过: {table_name} (源数据库中不存在)")
                continue
            
            if table_name in target_tables:
                print(f"⚠️ 目标数据库已存在 {table_name} 表")
                # 删除目标数据库中的旧表
                target_cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                target_conn.commit()
                print(f"   已删除旧表")
            
            # 获取源表的创建语句
            source_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            create_sql = source_cursor.fetchone()[0]
            print(f"📤 创建表: {table_name}")
            target_cursor.execute(create_sql)
            target_conn.commit()
            
            # 获取源表的所有数据
            source_cursor.execute(f"SELECT * FROM {table_name}")
            rows = source_cursor.fetchall()
            
            if rows:
                # 获取列数
                col_count = len(source_cursor.description)
                placeholders = ','.join(['?' for _ in range(col_count)])
                
                # 插入数据
                target_cursor.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", rows)
                target_conn.commit()
                print(f"   已迁移 {len(rows)} 条记录")
            else:
                print(f"   表为空，无需迁移数据")
        
        # 迁移索引
        print()
        print("🔄 迁移索引...")
        source_cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index'")
        indexes = source_cursor.fetchall()
        
        for idx_name, idx_sql in indexes:
            if 'ablation' in idx_name.lower():
                try:
                    target_cursor.execute(idx_sql)
                    target_conn.commit()
                    print(f"   创建索引: {idx_name}")
                except Exception as e:
                    print(f"   ⚠️ 索引 {idx_name} 创建失败: {e}")
        
        print()
        print("✅ 数据库合并完成！")
        
        # 验证迁移结果
        print()
        print("🔍 验证迁移结果:")
        target_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = sorted([row[0] for row in target_cursor.fetchall()])
        print(f"   目标数据库所有表: {all_tables}")
        
        for table_name in ablation_tables:
            target_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = target_cursor.fetchone()[0]
            print(f"   {table_name}: {count} 条记录")
        
        return True
        
    except Exception as e:
        print(f"❌ 合并失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        source_conn.close()
        target_conn.close()

if __name__ == "__main__":
    success = merge_databases()
    
    if success:
        print()
        print("🎉 迁移成功！")
        print("请确保数据库配置使用目标数据库路径：")
        print("  SQLALCHEMY_DATABASE_URL = 'sqlite:///./code_detection.db'")
    else:
        print()
        print("❌ 迁移失败，请检查错误信息")