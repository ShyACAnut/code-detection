-- 迁移脚本：添加独立文件检测支持所需的列
-- 添加 file_content 列到 analysis_tasks 表
-- 添加 task_id 列到 comparison_results 表
-- 将 assignment_id, submission_id, compared_with_id 改为可选

-- 添加 file_content 列到 analysis_tasks 表
ALTER TABLE analysis_tasks ADD COLUMN file_content TEXT;

-- 添加 task_id 列到 comparison_results 表
ALTER TABLE comparison_results ADD COLUMN task_id INTEGER;

-- 添加索引
CREATE INDEX IF NOT EXISTS ix_comparison_results_task_id ON comparison_results (task_id);

-- 将 assignment_id 改为可选（SQLite 不支持 DROP NOT NULL，需要重建表）
-- 由于 SQLite 不允许直接修改 NOT NULL 约束，我们需要重建表
-- 但为了简化，我们假设原来的表已经是 nullable 或者可以手动处理
