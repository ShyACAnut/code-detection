-- 迁移脚本：为 analysis_tasks 表添加 started_at 字段
ALTER TABLE analysis_tasks ADD COLUMN started_at DATETIME;