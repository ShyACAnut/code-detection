import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Card, Drawer, message, Modal, Select, Space, Spin, Table, Tag, Typography, Empty } from 'antd';
import api from '../../api/client';
import dayjs from 'dayjs';
import {
  FileTextOutlined,
  FilterOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  EditOutlined,
} from '@ant-design/icons';
import '../../styles/global.css';

const { Text, Title } = Typography;

interface SubmissionScore {
  id?: number;
  submission_id: number;
  overall_score: number;
  teacher_comments?: string;
  teacher_name?: string;
  created_at?: string;
  updated_at?: string;
}

interface Submission {
  id: number;
  student_id: number;
  assignment_id: number;
  assignment_title: string;
  code: string;
  submitted_at: string;
  analysis_status?: string;
  highest_similarity?: number | null;
  analysis_reason?: string | null;
  score?: SubmissionScore | null;
}

interface ComparisonResult {
  id: number;
  submission_id: number;
  compared_with_id?: number | null;
  peer_label?: string | null;
  similarity_score: number;
  filter_layer: string;
  details: string;
  created_at: string;
}

interface AssignmentBrief {
  id: number;
  title: string;
}

function safeReason(details: string): string {
  try {
    const parsed = JSON.parse(details);
    return parsed?.similarity_analysis?.reason || '';
  } catch {
    return '';
  }
}

const StatusTag: React.FC<{ status?: string }> = ({ status }) => {
  if (status === '已完成') {
    return (
      <Tag
        icon={<CheckCircleOutlined />}
        style={{
          background: '#d1fae5',
          color: '#065f46',
          border: '1px solid #a7f3d0',
        }}
      >
        已完成
      </Tag>
    );
  }
  if (status === '检测中') {
    return (
      <Tag
        icon={<ClockCircleOutlined />}
        style={{
          background: '#fef3c7',
          color: '#b45309',
          border: '1px solid #fde68a',
        }}
      >
        检测中
      </Tag>
    );
  }
  return (
    <Tag
      icon={<ExclamationCircleOutlined />}
      style={{
        background: '#f1f5f9',
        color: '#64748b',
        border: '1px solid #cbd5e1',
      }}
    >
      待检测
    </Tag>
  );
};

const SimilarityDisplay: React.FC<{ value?: number | null }> = ({ value }) => {
  if (value == null) return <span className="table-cell-secondary-light">-</span>;

  const roundedValue = Math.round(value);
  const isHigh = roundedValue >= 80;
  const isWarning = roundedValue >= 50 && roundedValue < 80;
  const color = isHigh ? '#f87171' : isWarning ? '#fbbf24' : '#34d399';
  const glow = isHigh ? '0 0 12px rgba(248,113,113,0.4)' : isWarning ? '0 0 10px rgba(251,191,36,0.3)' : 'none';

  return (
    <span
      className={isHigh ? 'similarity-high' : ''}
      style={{ color, fontWeight: 700, textShadow: glow }}
    >
      {roundedValue}%
    </span>
  );
};

const StudentSubmissions: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const assignmentIdParam = searchParams.get('assignment_id');
  const assignmentFilter = assignmentIdParam ? Number(assignmentIdParam) : undefined;

  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [activeSubmissionId, setActiveSubmissionId] = useState<number | null>(null);
  const [results, setResults] = useState<ComparisonResult[]>([]);
  const [assignments, setAssignments] = useState<AssignmentBrief[]>([]);
  const [scoreDetailModalOpen, setScoreDetailModalOpen] = useState(false);
  const [currentScoreDetail, setCurrentScoreDetail] = useState<SubmissionScore | null>(null);

  const fetchSubmissions = async () => {
    setLoading(true);
    try {
      const res = await api.get<Submission[]>('/submissions', {
        params: assignmentFilter != null && !Number.isNaN(assignmentFilter) ? { assignment_id: assignmentFilter } : undefined,
      });
      
      // 获取每个提交的评分信息
      const submissionsWithScores = await Promise.all(
        res.data.map(async (submission) => {
          try {
            const scoreRes = await api.get<SubmissionScore>(`/submissions/${submission.id}/score`);
            return { ...submission, score: scoreRes.data };
          } catch {
            return { ...submission, score: null };
          }
        })
      );
      
      setSubmissions(submissionsWithScores);
    } catch (e) {
      message.error('获取提交列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubmissions();
  }, [assignmentFilter]);

  useEffect(() => {
    api
      .get<AssignmentBrief[]>('/assignments/')
      .then((r) => setAssignments(r.data))
      .catch(() => setAssignments([]));
  }, []);

  const openResults = async (submissionId: number) => {
    setActiveSubmissionId(submissionId);
    setDrawerOpen(true);
    setDrawerLoading(true);
    try {
      const res = await api.get<ComparisonResult[]>(`/submissions/${submissionId}/results`);
      setResults(res.data);
    } catch (e: any) {
      message.error(e.response?.data?.detail || '获取比对结果失败');
      setResults([]);
    } finally {
      setDrawerLoading(false);
    }
  };

  const getSimilarityTag = (s: number) => {
    const roundedValue = Math.round(s);
    const isHigh = roundedValue >= 80;
    const isWarning = roundedValue >= 50 && roundedValue < 80;
    return (
      <Tag
        style={{
          background: isHigh ? '#fee2e2' : isWarning ? '#fef3c7' : '#d1fae5',
          color: isHigh ? '#991b1b' : isWarning ? '#b45309' : '#065f46',
          border: `1px solid ${isHigh ? '#fecaca' : isWarning ? '#fde68a' : '#a7f3d0'}`,
          fontWeight: 600,
        }}
      >
        {String(roundedValue)}
      </Tag>
    );
  };

  return (
    <div className="page-fade-in">
      <Card className="glass-surface-light">
        <Title level={4} className="page-title-light">
          <FileTextOutlined className="page-title-icon-light" />
          我的提交
        </Title>

        {/* Filter bar */}
        <div className="glass-filter-bar-light">
          <span className="filter-label-light">按作业筛选：</span>
          <Select
            style={{ minWidth: 280 }}
            placeholder="全部作业"
            allowClear
            value={assignmentFilter != null && !Number.isNaN(assignmentFilter) ? assignmentFilter : undefined}
            onChange={(v) => {
              if (v == null) {
                setSearchParams((prev) => {
                  const next = new URLSearchParams(prev);
                  next.delete('assignment_id');
                  return next;
                });
                return;
              }
              setSearchParams({ assignment_id: String(v) });
            }}
            options={assignments.map((a) => ({
              label: `${a.title} (#${a.id})`,
              value: a.id,
            }))}
          />
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', marginTop: 40 }}>
            <Spin />
          </div>
        ) : (
          <Table
            dataSource={submissions}
            rowKey="id"
            pagination={{ pageSize: 10 }}
            className="light-table optimized-light-table"
            locale={{
              emptyText: (
                <Empty
                  description={<span style={{ color: '#64748b' }}>
                    {assignmentFilter != null ? `当前筛选作业(#${assignmentFilter})暂无提交，可清空筛选查看全部` : '暂无提交记录'}
                  </span>}
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              ),
            }}
            columns={[
              {
                title: <span className="table-header-text-light">提交ID</span>,
                dataIndex: 'id',
                key: 'id',
                width: 90,
                render: (v: number) => <span className="table-cell-secondary-light">#{v}</span>,
              },
              {
                title: <span className="table-header-text-light">作业标题</span>,
                dataIndex: 'assignment_title',
                key: 'assignment_title',
                ellipsis: true,
                render: (text: string) => <span className="table-cell-primary-light">{text}</span>,
              },
              {
                title: <span className="table-header-text-light">提交时间</span>,
                dataIndex: 'submitted_at',
                key: 'submitted_at',
                width: 170,
                render: (t: string) => <span className="table-cell-secondary-light">{dayjs(t).format('YYYY-MM-DD HH:mm')}</span>,
              },
              {
                title: <span className="table-header-text-light">检测状态</span>,
                dataIndex: 'analysis_status',
                key: 'analysis_status',
                width: 130,
                render: (s?: string) => <StatusTag status={s} />,
              },
              {
                title: <span className="table-header-text-light">最高相似度</span>,
                key: 'highest_similarity',
                width: 120,
                render: (_: any, record: Submission) => <SimilarityDisplay value={record.highest_similarity} />,
              },
              {
                title: <span className="table-header-text-light">评分</span>,
                key: 'score',
                width: 120,
                render: (_: any, record: Submission) => {
                  if (record.score) {
                    const scoreColor = record.score.overall_score >= 80 ? '#52c41a' : record.score.overall_score >= 60 ? '#faad14' : '#ff4d4f';
                    return <Tag color={scoreColor}>{record.score.overall_score}分</Tag>;
                  }
                  return <Tag color="default">未评分</Tag>;
                },
              },
              {
                title: <span className="table-header-text-light">结果摘要</span>,
                dataIndex: 'analysis_reason',
                key: 'analysis_reason',
                ellipsis: true,
                render: (v?: string) => (v ? <span className="table-cell-secondary-light">{v}</span> : <span className="table-cell-secondary-light">暂无</span>),
              },
              {
                title: <span className="table-header-text-light">代码预览</span>,
                dataIndex: 'code',
                key: 'code',
                render: (code: string) => (
                  <Text code className="code-preview-light">
                    {(code || '').slice(0, 80)}
                  </Text>
                ),
              },
              {
                title: <span className="table-header-text-light">操作</span>,
                key: 'action',
                width: 280,
                render: (_: any, record: Submission) => (
                  <Space>
                    <Button className="btn-primary-light" icon={<EyeOutlined />} onClick={() => openResults(record.id)}>
                      检测结果
                    </Button>
                    {record.score && (
                      <Button
                        className="btn-ghost-light"
                        onClick={() => {
                          setCurrentScoreDetail(record.score || null);
                          setScoreDetailModalOpen(true);
                        }}
                      >
                        评分详情
                      </Button>
                    )}
                    <Button
                      className="btn-ghost-light"
                      icon={<EditOutlined />}
                      onClick={() => navigate(`/student/submit/${record.assignment_id}`)}
                    >
                      修改
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
        )}
      </Card>

      {/* Results Drawer */}
      <Drawer
        title={<span style={{ color: '#1e293b' }}>检测结果 - 提交 #{activeSubmissionId ?? ''}</span>}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={900}
        className="light-drawer"
      >
        {drawerLoading ? (
          <div style={{ textAlign: 'center', marginTop: 40 }}>
            <Spin />
          </div>
        ) : (
          <Table
            dataSource={results}
            rowKey="id"
            pagination={{ pageSize: 10 }}
            className="light-table optimized-light-table"
            columns={[
              {
                title: <span className="table-header-text-light">本方提交</span>,
                dataIndex: 'submission_id',
                key: 'submission_id',
                width: 100,
                render: (v: number) => <span className="table-cell-secondary-light">#{v}</span>,
              },
              {
                title: <span className="table-header-text-light">比对对象</span>,
                key: 'peer',
                width: 140,
                render: (_: any, r: ComparisonResult) =>
                  r.peer_label ? (
                    <span className="table-cell-primary-light">{r.peer_label}</span>
                  ) : (
                    <span className="table-cell-secondary-light">{r.compared_with_id}</span>
                  ),
              },
              {
                title: <span className="table-header-text-light">相似度</span>,
                dataIndex: 'similarity_score',
                key: 'similarity_score',
                width: 120,
                render: (s: number) => getSimilarityTag(s),
              },
              {
                title: <span className="table-header-text-light">过滤层</span>,
                dataIndex: 'filter_layer',
                key: 'filter_layer',
                width: 140,
                render: (v: string) => <span className="table-cell-secondary-light">{v}</span>,
              },
              {
                title: <span className="table-header-text-light">原因（摘要）</span>,
                dataIndex: 'details',
                key: 'details',
                render: (d: string) => {
                  const reason = safeReason(d);
                  return reason ? (
                    <span className="table-cell-secondary-light">{reason}</span>
                  ) : (
                    <span className="table-cell-secondary-light">-</span>
                  );
                },
              },
              {
                title: <span className="table-header-text-light">时间</span>,
                dataIndex: 'created_at',
                key: 'created_at',
                width: 170,
                render: (t: string) => <span className="table-cell-secondary-light">{dayjs(t).format('YYYY-MM-DD HH:mm')}</span>,
              },
            ]}
          />
        )}
      </Drawer>

      <Modal
        title="评分详情"
        open={scoreDetailModalOpen}
        onCancel={() => setScoreDetailModalOpen(false)}
        footer={null}
        width={600}
      >
        {currentScoreDetail && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Text strong style={{ fontSize: 16 }}>总分：</Text>
              <Tag
                color={currentScoreDetail.overall_score >= 80 ? '#52c41a' : currentScoreDetail.overall_score >= 60 ? '#faad14' : '#ff4d4f'}
                style={{ fontSize: 18, padding: '4px 12px' }}
              >
                {currentScoreDetail.overall_score}分
              </Tag>
            </div>

            {currentScoreDetail.teacher_comments && (
              <div style={{ marginBottom: 16 }}>
                <Text strong>教师评语：</Text>
                <div
                  style={{
                    marginTop: 8,
                    padding: 12,
                    background: '#f5f5f5',
                    borderRadius: 4,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {currentScoreDetail.teacher_comments}
                </div>
              </div>
            )}

            {currentScoreDetail.teacher_name && (
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary">评分教师：{currentScoreDetail.teacher_name}</Text>
              </div>
            )}

            {currentScoreDetail.created_at && (
              <div>
                <Text type="secondary">评分时间：{dayjs(currentScoreDetail.created_at).format('YYYY-MM-DD HH:mm')}</Text>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default StudentSubmissions;
