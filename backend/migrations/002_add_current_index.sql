-- SQLite: 为 ablation_batch_tasks 表添加 current_index 列
-- 用于支持断点续测功能

ALTER TABLE ablation_batch_tasks
ADD COLUMN IF NOT EXISTS current_index INTEGER DEFAULT 0;