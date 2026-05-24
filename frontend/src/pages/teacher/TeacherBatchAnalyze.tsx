import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Select, Button, message, Alert, Card, Typography, Space, List, Tag, Progress, Spin, Upload, Table, Tooltip } from 'antd';
import { PlayCircleOutlined, ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined, UploadOutlined, FileTextOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import api from '../../api/client';
import '../../styles/global.css';

const { Option } = Select;
const { Title, Text } = Typography;

interface Assignment {
  id: number;
  title: string;
  language: string;
  submission_count: number;
}

interface AnalysisTask {
  id: number;
  assignment_id: number;
  status: string;
  total_pairs: number;
  processed_pairs: number;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  updated_at: string;
}

interface ComparisonResultItem {
  submission_a_id: number;
  submission_b_id: number;
  similarity_score: number;
  reason?: string;
}

interface TaskProgress {
  task_id: number;
  assignment_id: number;
  status: string;
  total_pairs: number;
  processed_pairs: number;
  results: ComparisonResultItem[];
}

const TeacherBatchAnalyze: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selectedAssignments, setSelectedAssignments] = useState<number[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [tasks, setTasks] = useState<{ [key: number]: AnalysisTask }>({});
  const [taskProgress, setTaskProgress] = useState<{ [key: number]: TaskProgress }>({});
  const [uploadFile, setUploadFile] = useState<UploadFile | null>(null);
  const [uploading, setUploading] = useState(false);
  const [mode, setMode] = useState<'select' | 'upload'>('select');
  const [uploadedTaskId, setUploadedTaskId] = useState<number | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const pollingRef = useRef<{ [key: number]: NodeJS.Timeout }>({});
  const timeRef = useRef<NodeJS.Timeout | null>(null);

  const routeSelectedIds = location.state?.selectedAssignmentIds || [];

  useEffect(() => {
    fetchAssignments();

    if (routeSelectedIds.length > 0) {
      setSelectedAssignments(routeSelectedIds);
    }

    timeRef.current = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => {
      Object.values(pollingRef.current).forEach(timer => clearInterval(timer));
      if (timeRef.current) {
        clearInterval(timeRef.current);
      }
    };
  }, []);

  const fetchAssignments = async () => {
    try {
      const res = await api.get<Assignment[]>('/assignments');
      setAssignments(res.data);
    } catch {
      message.error('加载作业列表失败');
    }
  };

  const fetchTaskStatus = async (assignmentId: number) => {
    try {
      const res = await api.get<AnalysisTask[]>(`/analysis_tasks?assignment_id=${assignmentId}`);
      if (res.data.length > 0) {
        const latestTask = res.data[0];
        setTasks(prev => ({
          ...prev,
          [assignmentId]: latestTask
        }));
        return latestTask;
      }
    } catch (error) {
      console.error(`获取作业 ${assignmentId} 的任务状态失败:`, error);
    }
    return null;
  };

  const fetchTaskById = async (taskId: number) => {
    try {
      const res = await api.get<AnalysisTask>(`/analysis_tasks/${taskId}`);
      if (res.data) {
        // 添加时间调试日志
        console.log(`[任务 ${taskId}] 原始时间数据:`, {
          created_at: res.data.created_at,
          started_at: res.data.started_at,
          updated_at: res.data.updated_at
        });
        
        if (res.data.started_at) {
          const started = new Date(res.data.started_at);
          console.log(`[任务 ${taskId}] started_at 解析结果:`, {
            timestamp: started.getTime(),
            isoString: started.toISOString(),
            localString: started.toLocaleString('zh-CN')
          });
        }
        
        setTasks(prev => ({
          ...prev,
          [taskId]: res.data
        }));
        return res.data;
      }
    } catch (error) {
      console.error(`获取任务 ${taskId} 状态失败:`, error);
    }
    return null;
  };

  const fetchTaskProgress = async (taskId: number, key: number) => {
    try {
      const res = await api.get<TaskProgress>(`/analysis_tasks/${taskId}/progress`);
      setTaskProgress(prev => ({
        ...prev,
        [key]: res.data
      }));
      return res.data;
    } catch (error) {
      console.error(`获取任务进度失败:`, error);
      return null;
    }
  };

  const formatDuration = (startedAt: string | null | undefined): string => {
    if (!startedAt) {
      return '-';
    }
    // 确保正确解析UTC时间
    const started = new Date(startedAt);
    const now = new Date();
    
    // 如果解析失败，返回错误提示
    if (isNaN(started.getTime())) {
      return '-';
    }
    
    const diffMs = now.getTime() - started.getTime();
    
    const seconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}小时${minutes % 60}分钟${seconds % 60}秒`;
    } else if (minutes > 0) {
      return `${minutes}分钟${seconds % 60}秒`;
    } else {
      return `${seconds}秒`;
    }
  };

  const startPolling = (assignmentId: number, taskId: number) => {
    if (pollingRef.current[assignmentId]) {
      clearInterval(pollingRef.current[assignmentId]);
    }

    pollingRef.current[assignmentId] = setInterval(async () => {
      const task = await fetchTaskStatus(assignmentId);
      if (task) {
        const progress = await fetchTaskProgress(taskId, assignmentId);
        if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
          clearInterval(pollingRef.current[assignmentId]);
          delete pollingRef.current[assignmentId];
        }
      } else {
        clearInterval(pollingRef.current[assignmentId]);
        delete pollingRef.current[assignmentId];
      }
    }, 2000);
  };

  const startUploadPolling = (taskId: number) => {
    if (pollingRef.current[taskId]) {
      clearInterval(pollingRef.current[taskId]);
    }

    pollingRef.current[taskId] = setInterval(async () => {
      const task = await fetchTaskById(taskId);
      if (task) {
        const progress = await fetchTaskProgress(taskId, taskId);
        if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
          clearInterval(pollingRef.current[taskId]);
          delete pollingRef.current[taskId];
        }
      } else {
        clearInterval(pollingRef.current[taskId]);
        delete pollingRef.current[taskId];
      }
    }, 2000);
  };

  const handleFileUpload = async () => {
    if (!uploadFile) {
      message.warning('请先选择文件');
      return;
    }

    setUploading(true);

    const formData = new FormData();
    formData.append('file', uploadFile as any);

    try {
      const res = await api.post('/analysis_tasks/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      message.success('文件上传成功，检测任务已启动');
      const taskId = res.data.id;
      setTasks(prev => ({
        ...prev,
        [taskId]: res.data
      }));
      setUploadedTaskId(taskId);
      startUploadPolling(taskId);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const startBatchAnalyze = async () => {
    console.log('startBatchAnalyze called, selectedAssignments:', selectedAssignments);
    
    if (selectedAssignments.length === 0) {
      message.warning('请先选择要检测的作业');
      return;
    }

    setAnalyzing(true);

    try {
      for (const assignmentId of selectedAssignments) {
        try {
          console.log('Creating task for assignment:', assignmentId);
          const res = await api.post('/analysis_tasks', { assignment_id: assignmentId });
          console.log('Task created successfully:', res.data);
          message.success(`作业 ${assignmentId} 检测任务已启动`);

          const taskId = res.data.task_id || res.data.id;
          startPolling(assignmentId, taskId);

        } catch (error: any) {
          console.error('Failed to create task:', error);
          message.error(`作业 ${assignmentId} 检测任务启动失败: ${error.response?.data?.detail || '未知错误'}`);
        }
      }

      message.success('所有检测任务已启动，请稍后查看结果');

    } catch (error) {
      message.error('启动批量检测失败');
      console.error(error);
    } finally {
      setAnalyzing(false);
    }
  };

  const getTaskStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircleOutlined />;
      case 'failed': return <CloseCircleOutlined />;
      default: return null;
    }
  };

  const getProgressPercent = (task: AnalysisTask) => {
    if (!task || task.total_pairs === 0) return 0;
    return Math.min(100, Math.round((task.processed_pairs / task.total_pairs) * 100));
  };

  const getSimilarityColor = (score: number) => {
    if (score >= 80) return '#dc2626';
    if (score >= 60) return '#f59e0b';
    if (score >= 40) return '#3b82f6';
    return '#10b981';
  };

  const columns = [
    {
      title: '提交对',
      dataIndex: 'pair',
      key: 'pair',
      render: (_: any, record: ComparisonResultItem) => (
        <Text style={{ color: '#334155' }}>
          #{record.submission_a_id} vs #{record.submission_b_id}
        </Text>
      ),
    },
    {
      title: '相似度',
      dataIndex: 'similarity_score',
      key: 'similarity_score',
      render: (score: number) => (
        <Tag
          style={{
            background: `${getSimilarityColor(score)}20`,
            color: getSimilarityColor(score),
            border: `1px solid ${getSimilarityColor(score)}50`,
            fontWeight: 600,
          }}
        >
          {score.toFixed(1)}%
        </Tag>
      ),
    },
    {
      title: '分析原因',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
      render: (reason: string) => (
        <Tooltip title={reason}>
          <Text style={{ color: '#64748b', maxWidth: 400 }} ellipsis>
            {reason || '无'}
          </Text>
        </Tooltip>
      ),
    },
  ];

  return (
    <div className="page-fade-in">
      <Card className="content-card">
        <Title level={4} className="page-title">
          <PlayCircleOutlined className="page-title-icon" />
          批量检测作业
        </Title>

        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
          title="批量检测功能说明"
          description="支持两种检测模式：1) 选择已有作业进行检测；2) 上传 JSON 或 ZIP 文件导入代码后进行检测。检测过程中可实时查看进度和比对结果。"
        />

        <Space style={{ marginBottom: 24 }}>
          <Space.Compact>
            <Button
              type={mode === 'select' ? 'primary' : 'default'}
              onClick={() => {
                setMode('select');
              }}
            >
              选择作业检测
            </Button>
            <Button
              type={mode === 'upload' ? 'primary' : 'default'}
              onClick={() => {
                setMode('upload');
              }}
            >
              上传文件检测
            </Button>
          </Space.Compact>
        </Space>

        <Space orientation="vertical" size="large" style={{ width: '100%' }}>
          {mode === 'select' ? (
            <>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 8, color: '#334155' }}>
                  选择要检测的作业（可多选）
                </Text>
                <Select
                  mode="multiple"
                  placeholder="请选择作业"
                  style={{ width: '100%', maxWidth: 600 }}
                  value={selectedAssignments}
                  onChange={(vals) => {
                    console.log('Select changed, values:', vals);
                    setSelectedAssignments(vals);
                  }}
                  optionLabelProp="label"
                >
                  {assignments.map((assignment) => (
                    <Option key={assignment.id} value={assignment.id} label={assignment.title}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{assignment.title}</span>
                        <Space size="small">
                          <Tag
                            style={{
                              background: 'rgba(59,130,246,0.15)',
                              color: '#3b82f6',
                              border: '1px solid rgba(59,130,246,0.3)'
                            }}
                          >
                            {assignment.language}
                          </Tag>
                          <Tag
                            style={{
                              background: 'rgba(16,185,129,0.15)',
                              color: '#34d399',
                              border: '1px solid rgba(16,185,129,0.3)'
                            }}
                          >
                            {assignment.submission_count} 个提交
                          </Tag>
                        </Space>
                      </div>
                    </Option>
                  ))}
                </Select>
              </div>

              <Space>
                <Button
                  onClick={startBatchAnalyze}
                  loading={analyzing}
                  disabled={selectedAssignments.length === 0}
                  icon={<PlayCircleOutlined />}
                  className="btn-primary"
                >
                  开始批量检测
                </Button>
                <Button onClick={() => navigate('/teacher/assignments')} icon={<ArrowLeftOutlined />} className="btn-ghost">
                  返回作业列表
                </Button>
              </Space>
            </>
          ) : (
            <>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 8, color: '#334155' }}>
                  上传文件（JSON 或 ZIP）
                </Text>
                <Space orientation="vertical" size="middle">
                  <Upload
                    beforeUpload={(file) => {
                      const ext = file.name.split('.').pop()?.toLowerCase();
                      if (ext !== 'json' && ext !== 'zip') {
                        message.error('只支持 JSON 或 ZIP 文件');
                        return false;
                      }
                      setUploadFile(file as any);
                      return false;
                    }}
                    fileList={uploadFile ? [uploadFile] : []}
                    onRemove={() => setUploadFile(null)}
                    accept=".json,.zip"
                    maxCount={1}
                  >
                    <Button icon={<UploadOutlined />}>选择文件</Button>
                  </Upload>
                  <Alert
                    type="info"
                    showIcon
                    icon={<FileTextOutlined />}
                    title="文件格式说明"
                    description={
                      <div>
                        <div><b>JSON 文件格式：</b>包含代码对的数组，格式为 <code>{'[{"code_a": "...", "code_b": "..."}]'}</code></div>
                        <div style={{ marginTop: 8 }}><b>ZIP 文件格式：</b>包含多个代码文件，系统将自动配对进行比对</div>
                      </div>
                    }
                  />
                </Space>
              </div>

              <Space>
                <Button
                  onClick={handleFileUpload}
                  loading={uploading}
                  disabled={!uploadFile}
                  icon={<UploadOutlined />}
                  className="btn-primary"
                >
                  上传并开始检测
                </Button>
                <Button onClick={() => setMode('select')} icon={<ArrowLeftOutlined />} className="btn-ghost">
                  返回选择模式
                </Button>
              </Space>
            </>
          )}

          {uploadedTaskId && (
            <div style={{ marginTop: 24 }}>
              <Text strong style={{ display: 'block', marginBottom: 16, color: '#1e293b' }}>
                检测任务状态
              </Text>
              <div style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <Text strong style={{ color: '#334155' }}>独立文件检测任务</Text>
                  {tasks[uploadedTaskId] && (
                    <Tag
                      style={{
                        background: tasks[uploadedTaskId].status === 'completed' ? 'rgba(16,185,129,0.1)' :
                                   tasks[uploadedTaskId].status === 'running' ? 'rgba(59,130,246,0.1)' :
                                   tasks[uploadedTaskId].status === 'failed' ? 'rgba(239,68,68,0.1)' :
                                   '#f8fafc',
                        color: tasks[uploadedTaskId].status === 'completed' ? '#059669' :
                               tasks[uploadedTaskId].status === 'running' ? '#2563eb' :
                               tasks[uploadedTaskId].status === 'failed' ? '#dc2626' :
                               '#64748b',
                        border: `1px solid ${tasks[uploadedTaskId].status === 'completed' ? 'rgba(16,185,129,0.3)' :
                                   tasks[uploadedTaskId].status === 'running' ? 'rgba(59,130,246,0.3)' :
                                   tasks[uploadedTaskId].status === 'failed' ? 'rgba(239,68,68,0.3)' :
                                   '#e2e8f0'}`,
                      }}
                      icon={tasks[uploadedTaskId].status === 'completed' ? <CheckCircleOutlined /> :
                            tasks[uploadedTaskId].status === 'running' ? <Spin size="small" /> :
                            tasks[uploadedTaskId].status === 'failed' ? <CloseCircleOutlined /> : null}
                    >
                      {tasks[uploadedTaskId].status === 'completed' ? '已完成' :
                       tasks[uploadedTaskId].status === 'running' ? '进行中' :
                       tasks[uploadedTaskId].status === 'failed' ? '失败' :
                       tasks[uploadedTaskId].status === 'cancelled' ? '已取消' : '待开始'}
                    </Tag>
                  )}
                </div>

                {tasks[uploadedTaskId] ? (
                  <div>
                    <Progress
                      percent={tasks[uploadedTaskId].total_pairs > 0 ? 
                               Math.round((tasks[uploadedTaskId].processed_pairs / tasks[uploadedTaskId].total_pairs) * 100) : 0}
                      status={tasks[uploadedTaskId].status === 'failed' ? 'exception' : 'active'}
                      size="small"
                      strokeColor={{ '0%': '#3b82f6', '100%': '#8b5cf6' }}
                      trailColor="#e2e8f0"
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                      <Text type="secondary" style={{ fontSize: '12px', color: '#64748b' }}>
                        已处理 {tasks[uploadedTaskId].processed_pairs} / {tasks[uploadedTaskId].total_pairs} 对
                        {taskProgress[uploadedTaskId] && taskProgress[uploadedTaskId].results.length > 0 && ` (显示最近 ${taskProgress[uploadedTaskId].results.length} 条结果)`}
                      </Text>
                      <div style={{ display: 'flex', gap: 16 }}>
                        {tasks[uploadedTaskId].started_at && (
                          <Text type="secondary" style={{ fontSize: '12px', color: '#64748b' }}>
                            已检测: {formatDuration(tasks[uploadedTaskId].started_at)}
                          </Text>
                        )}
                        <Text type="secondary" style={{ fontSize: '12px', color: '#64748b' }}>
                          系统时间: {currentTime.toLocaleString('zh-CN')}
                        </Text>
                      </div>
                    </div>

                    {taskProgress[uploadedTaskId] && taskProgress[uploadedTaskId].results.length > 0 && (
                      <div style={{ marginTop: 16 }}>
                        <Text strong style={{ display: 'block', marginBottom: 8, color: '#334155', fontSize: 12 }}>
                          实时比对结果预览
                        </Text>
                        <Table
                          columns={columns}
                          dataSource={taskProgress[uploadedTaskId].results.slice(0, 10)}
                          rowKey={(record, index) => `${record.submission_a_id}-${record.submission_b_id}-${index}`}
                          size="small"
                          pagination={false}
                          scroll={{ y: 300 }}
                          style={{
                            background: '#f8fafc',
                            borderRadius: 8,
                            overflow: 'hidden',
                          }}
                        />
                      </div>
                    )}
                  </div>
                ) : (
                  <Text type="secondary" style={{ color: '#94a3b8' }}>等待开始检测...</Text>
                )}

                {tasks[uploadedTaskId] && tasks[uploadedTaskId].status === 'failed' && tasks[uploadedTaskId].error_message && (
                  <Alert
                    type="error"
                    showIcon
                    title="检测失败"
                    description={tasks[uploadedTaskId].error_message}
                    style={{ marginTop: 8 }}
                  />
                )}
              </div>
            </div>
          )}

          {selectedAssignments.length > 0 && (
            <div>
              <Text strong style={{ display: 'block', marginBottom: 16, color: '#1e293b' }}>
                检测任务状态
              </Text>
              <List
                dataSource={selectedAssignments}
                renderItem={(assignmentId) => {
                  const assignment = assignments.find(a => a.id === assignmentId);
                  const task = tasks[assignmentId];
                  const progress = taskProgress[assignmentId];

                  return (
                    <List.Item style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <div style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <Text strong style={{ color: '#334155' }}>{assignment?.title || `作业 #${assignmentId}`}</Text>
                          {task && (
                            <Tag
                              style={{
                                background: task.status === 'completed' ? 'rgba(16,185,129,0.1)' :
                                           task.status === 'running' ? 'rgba(59,130,246,0.1)' :
                                           task.status === 'failed' ? 'rgba(239,68,68,0.1)' :
                                           '#f8fafc',
                                color: task.status === 'completed' ? '#059669' :
                                       task.status === 'running' ? '#2563eb' :
                                       task.status === 'failed' ? '#dc2626' :
                                       '#64748b',
                                border: `1px solid ${task.status === 'completed' ? 'rgba(16,185,129,0.3)' :
                                           task.status === 'running' ? 'rgba(59,130,246,0.3)' :
                                           task.status === 'failed' ? 'rgba(239,68,68,0.3)' :
                                           '#e2e8f0'}`,
                              }}
                              icon={getTaskStatusIcon(task.status)}
                            >
                              {task.status === 'completed' ? '已完成' :
                               task.status === 'running' ? '进行中' :
                               task.status === 'failed' ? '失败' :
                               task.status === 'cancelled' ? '已取消' : '待开始'}
                            </Tag>
                          )}
                        </div>

                        {task ? (
                          <div>
                            <Progress
                              percent={getProgressPercent(task)}
                              status={task.status === 'failed' ? 'exception' : 'active'}
                              size="small"
                              strokeColor={{ '0%': '#3b82f6', '100%': '#8b5cf6' }}
                              trailColor="#e2e8f0"
                            />
                            <Text type="secondary" style={{ fontSize: '12px', color: '#64748b' }}>
                              已处理 {task.processed_pairs} / {task.total_pairs} 对
                              {progress && progress.results.length > 0 && ` (显示最近 ${progress.results.length} 条结果)`}
                            </Text>

                            {progress && progress.results.length > 0 && (
                              <div style={{ marginTop: 16 }}>
                                <Text strong style={{ display: 'block', marginBottom: 8, color: '#334155', fontSize: 12 }}>
                                  实时比对结果预览
                                </Text>
                                <Table
                                  columns={columns}
                                  dataSource={progress.results.slice(0, 10)}
                                  rowKey={(record, index) => `${record.submission_a_id}-${record.submission_b_id}-${index}`}
                                  size="small"
                                  pagination={false}
                                  scroll={{ y: 300 }}
                                  style={{
                                    background: '#f8fafc',
                                    borderRadius: 8,
                                    overflow: 'hidden',
                                  }}
                                />
                              </div>
                            )}
                          </div>
                        ) : (
                          <Text type="secondary" style={{ color: '#94a3b8' }}>等待开始检测...</Text>
                        )}

                        {task && task.status === 'completed' && (
                          <div style={{ marginTop: 8 }}>
                            <Button
                              size="small"
                              onClick={() => navigate(`/teacher/assignments/${assignmentId}`)}
                              className="btn-ghost"
                            >
                              查看完整检测结果
                            </Button>
                          </div>
                        )}

                        {task && task.status === 'failed' && task.error_message && (
                          <Alert
                            type="error"
                            showIcon
                            title="检测失败"
                            description={task.error_message}
                            style={{ marginTop: 8 }}
                          />
                        )}
                      </div>
                    </List.Item>
                  );
                }}
              />
            </div>
          )}
        </Space>
      </Card>
    </div>
  );
};

export default TeacherBatchAnalyze;