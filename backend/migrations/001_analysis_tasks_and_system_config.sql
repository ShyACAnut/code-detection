-- SQLite: 异步分析任务表 + 系统配置表
-- 若已使用 SQLAlchemy create_all 自动建表，可跳过；此脚本供手工迁移或审计使用。

CREATE TABLE IF NOT EXISTS analysis_tasks (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    total_pairs INTEGER DEFAULT 0,
    processed_pairs INTEGER DEFAULT 0,
    error_message TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY(assignment_id) REFERENCES assignments (id)
);

CREATE INDEX IF NOT EXISTS ix_analysis_tasks_assignment_id ON analysis_tasks (assignment_id);

CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER NOT NULL PRIMARY KEY,
    similarity_threshold FLOAT DEFAULT 80.0,
    llm_model_name VARCHAR DEFAULT 'glm-4.7',
    updated_at DATETIME
);

INSERT OR IGNORE INTO system_config (id, similarity_threshold, llm_model_name, updated_at)
VALUES (1, 80.0, 'glm-4.7', datetime('now'));
