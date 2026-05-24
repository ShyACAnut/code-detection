from database import get_db
from sqlalchemy import text

db = next(get_db())

# 检查列是否存在
result = db.execute(text("PRAGMA table_info(users)"))
columns = [row[1] for row in result]

print('当前users表字段:', columns)

# 添加新字段
if 'requires_ethics_learning' not in columns:
    db.execute(text('ALTER TABLE users ADD COLUMN requires_ethics_learning INTEGER DEFAULT 0'))
    print('已添加 requires_ethics_learning 字段')

if 'required_cases_count' not in columns:
    db.execute(text('ALTER TABLE users ADD COLUMN required_cases_count INTEGER DEFAULT 3'))
    print('已添加 required_cases_count 字段')

db.commit()
print('数据库更新完成')
