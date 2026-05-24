import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Button,
  Card,
  Descriptions,
  Divider,
  message,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  Modal,
} from 'antd';
import api from '../../api/client';
import dayjs from 'dayjs';
import { ArrowLeftOutlined, CodeOutlined, TeamOutlined } from '@ant-design/icons';
import '../../styles/Dashboard.css';

const { Text, Title } = Typography;

interface Assignment {
  id: number;
  title: string;
  description: string;
  language: string;
  deadline: string;
  created_at: string;
  created_by: number;
  creator_name?: string;
  submission_count?: number;
}

interface Submission {
  id: number;
  student_id: number;
  assignment_id: number;
  code: string;
  submitted_at: string;
  student_name: string;
}

interface ComparisonResult {
  id: number;
  submission_id: number;
  compared_with_id: number;
  similarity_score: number;
  filter_layer: string;
  details: string;
  created_at: string;
}

interface AnalysisTask {
  id: number;
  assignment_id: number;
  status: string;
  total_pairs: number;
  processed_pairs: number;
  error_message?: string | null;
}

function safeReason(details: string): string {
  try {
    const parsed = JSON.parse(details);
    return parsed?.similarity_analysis?.reason || '';
  } catch {
    return '';
  }
}

const DeanAssignmentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const assignmentId = Number(id);
  const navigate = useNavigate();

  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [results, setResults] = useState<ComparisonResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingResults, setLoadingResults] = useState(false);
  const [previewCode, setPreviewCode] = useState<string>('');
  const [previewTitle, setPreviewTitle] = useState<string>('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareA, setCompareA] = useState<Submission | null>(null);
  const [compareB, setCompareB] = useState<Submission | null>(null);

  const riskResults = results.filter((r) => r.similarity_score >= 80);

  const fetchAssignment = async () => {
    try {
      const res = await api.get(`/assignments/${assignmentId}`);
      setAssignment(res.data);
    } catch (error) {
      message.error('获取作业信息失败');
      console.error(error);
    }
  };

  const fetchSubmissions = async () => {
    try {
      const res = await api.get(`/assignments/${assignmentId}/submissions`);
      setSubmissions(res.data);
    } catch (error) {
      message.error('获取提交列表失败');
      console.error(error);
    }
  };

  const fetchResults = async () => {
    setLoadingResults(true);
    try {
      const res = await api.get(`/assignments/${assignmentId}/results`);
      setResults(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      message.error('获取检测结果失败');
      console.error(error);
    } finally {
      setLoadingResults(false);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchAssignment(), fetchSubmissions()]);
      await fetchResults();
      setLoading(false);
    };
    loadData();
  }, [assignmentId]);

  const showCodePreview = (code: string, studentName: string, submissionId: number) => {
    setPreviewCode(code);
    setPreviewTitle(`提交 #${submissionId} - ${studentName} 的代码`);
    setPreviewOpen(true);
  };

  const openCompare = (r: ComparisonResult) => {
    const a = submissions.find((s) => s.id === r.submission_id) || null;
    const b = submissions.find((s) => s.id === r.compared_with_id) || null;
    setCompareA(a);
    setCompareB(b);
    setCompareOpen(true);
  };

  const renderCodeWithHighlights = (code: string, peers: Set<string>) => {
    const lines = (code || '').split('\n');
    return (
      <pre style={{ maxHeight: 420, overflow: 'auto', padding: 10, margin: 0, backgroundColor: '#1e293b', borderRadius: '4px' }}>
        {lines.map((ln, idx) => {
          const k = ln.trim();
          const hit = k.length >= 6 && peers.has(k);
          return (
            <div key={idx} style={{ background: hit ? 'rgba(251, 191, 36, 0.15)' : 'transparent' }}>
              <span style={{ color: 'rgba(255,255,255,0.4)', width: 36, display: 'inline-block' }}>{idx + 1}</span>
              <span style={{ color: '#e2e8f0' }}>{ln || ' '}</span>
            </div>
          );
        })}
      </pre>
    );
  };

  const getLanguageColor = (lang: string) => {
    const colors: { [key: string]: string } = {
      python: 'rgba(59, 130, 246, 0.15)',
      java: 'rgba(251, 146, 60, 0.15)',
      javascript: 'rgba(251, 191, 36, 0.15)',
      c: 'rgba(16, 185, 129, 0.15)',
      cpp: 'rgba(6, 182, 212, 0.15)',
      csharp: 'rgba(168, 85, 247, 0.15)',
      go: 'rgba(20, 184, 166, 0.15)',
    };
    return colors[lang] || 'rgba(255, 255, 255, 0.05)';
  };

  const getLanguageTextColor = (lang: string) => {
    const colors: { [key: string]: string } = {
      python: '#3b82f6',
      java: '#fb923c',
      javascript: '#fbbf24',
      c: '#34d399',
      cpp: '#06b6d4',
      csharp: '#a855f7',
      go: '#14b8a6',
    };
    return colors[lang] || '#94a3b8';
  };

  const getLanguageBorderColor = (lang: string) => {
    const colors: { [key: string]: string } = {
      python: 'rgba(59, 130, 246, 0.3)',
      java: 'rgba(251, 146, 60, 0.3)',
      javascript: 'rgba(251, 191, 36, 0.3)',
      c: 'rgba(16, 185, 129, 0.3)',
      cpp: 'rgba(6, 182, 212, 0.3)',
      csharp: 'rgba(168, 85, 247, 0.3)',
      go: 'rgba(20, 184, 166, 0.3)',
    };
    return colors[lang] || 'rgba(255, 255, 255, 0.1)';
  };

  const columns = [
    {
      title: '提交ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
    },
    {
      title: '学生姓名',
      dataIndex: 'student_name',
      key: 'student_name',
      width: 140,
      render: (text: string) => <strong style={{ color: '#e2e8f0' }}>{text}</strong>,
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      render: (text: string) => <span style={{ color: '#94a3b8' }}>{dayjs(text).format('YYYY-MM-DD HH:mm:ss')}</span>,
      width: 180,
    },
    {
      title: '代码预览',
      dataIndex: 'code',
      key: 'code',
      render: (_: string, row: Submission) => {
        const codeStr = typeof row.code === 'string' ? row.code : JSON.stringify(row.code) || '';
        return (
          <Space>
            <Text code style={{ color: '#94a3b8', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}>{codeStr.slice(0, 80)}</Text>
            <Button
              size="small"
              onClick={() => showCodePreview(codeStr, row.student_name, row.id)}
              className="btn-ghost"
            >
              查看全文
            </Button>
          </Space>
        );
      },
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!assignment) {
    return <div style={{ color: '#1e293b' }}>作业不存在</div>;
  }

  return (
    <div>
      <Title level={4} className="page-title-light">作业详情</Title>
      
      <Space style={{ marginBottom: 16 }}>
        <Button 
          className="btn-primary-light"
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/dean/assignments')}
        >
          返回作业列表
        </Button>
        <Button onClick={fetchResults} loading={loadingResults} className="btn-primary-light">
          刷新检测结果
        </Button>
      </Space>

      <Card className="glass-surface-light">
        <Descriptions title="作业信息" bordered column={2}>
          <Descriptions.Item label="作业标题">{assignment.title}</Descriptions.Item>
          <Descriptions.Item label="创建者">
            <Tag color="purple" icon={<TeamOutlined />}>
              {assignment.creator_name || '未知'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="编程语言">
            <Tag color="blue" icon={<CodeOutlined />}>
              {assignment.language}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="提交人数">
            <Tag color="cyan">
              {assignment.submission_count || submissions.length} 人
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="截止时间">{dayjs(assignment.deadline).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{dayjs(assignment.created_at).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
          <Descriptions.Item label="作业描述" span={2}>{assignment.description || '无描述'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Title level={4} className="page-title-light" style={{ marginTop: 24 }}>提交情况统计</Title>
      <Card className="glass-surface-light">
        <Descriptions bordered column={3}>
          <Descriptions.Item label="总提交数">
            <Tag color="blue" style={{ fontSize: '14px', padding: '4px 12px' }}>
              {submissions.length} 次
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="提交学生数">
            <Tag color="green" style={{ fontSize: '14px', padding: '4px 12px' }}>
              {new Set(submissions.map(s => s.student_id)).size} 人
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="最近提交时间">
            {submissions.length > 0 
              ? (() => {
                  const sortedSubmissions = [...submissions].sort((a, b) => 
                    new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime()
                  );
                  return dayjs(sortedSubmissions[0].submitted_at).format('YYYY-MM-DD HH:mm:ss');
                })()
              : '暂无提交'
            }
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Title level={4} className="page-title-light" style={{ marginTop: 24 }}>提交列表</Title>
      <Card className="glass-surface-light">
        <Table
          dataSource={submissions}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          className="light-table"
        />
      </Card>

      {results.length > 0 && (
        <>
          <Title level={4} className="page-title-light" style={{ marginTop: 24 }}>高风险对（相似度 ≥ 80）({riskResults.length})</Title>
          <Card className="glass-surface-light">
            <Table
              dataSource={riskResults}
              rowKey="id"
              loading={loadingResults}
              pagination={{ pageSize: 10 }}
              locale={{ emptyText: '暂无高风险对' }}
              className="light-table"
              columns={[
                {
                  title: 'A提交',
                  dataIndex: 'submission_id',
                  key: 'submission_id',
                  width: 100,
                  render: (id: number) => {
                    const sub = submissions.find(s => s.id === id);
                    return <span style={{ color: '#1e293b' }}>{sub ? `${id} (${sub.student_name})` : id}</span>;
                  }
                },
                {
                  title: 'B提交',
                  dataIndex: 'compared_with_id',
                  key: 'compared_with_id',
                  width: 100,
                  render: (id: number) => {
                    const sub = submissions.find(s => s.id === id);
                    return <span style={{ color: '#1e293b' }}>{sub ? `${id} (${sub.student_name})` : id}</span>;
                  }
                },
                {
                  title: '相似度',
                  dataIndex: 'similarity_score',
                  key: 'similarity_score',
                  width: 120,
                  render: (s: number) => (
                    <span style={{ fontWeight: 600, color: s >= 80 ? '#dc2626' : '#22c55e' }}>{s}</span>
                  ),
                },
                {
                  title: '过滤层',
                  dataIndex: 'filter_layer',
                  key: 'filter_layer',
                  width: 140,
                  render: (text: string) => <span style={{ color: '#64748b' }}>{text}</span>,
                },
                {
                  title: '原因（摘要）',
                  dataIndex: 'details',
                  key: 'details',
                  render: (d: string) => {
                    const reason = safeReason(d);
                    return reason ? <span style={{ color: '#1e293b' }}>{reason}</span> : <span style={{ color: '#94a3b8' }}>-</span>;
                  },
                },
                {
                  title: '对比',
                  key: 'compare',
                  width: 120,
                  render: (_: any, r: ComparisonResult) => (
                    <Button size="small" onClick={() => openCompare(r)} className="btn-primary-light">
                      对照查看
                    </Button>
                  ),
                },
              ]}
            />
          </Card>

          <Title level={4} className="page-title-light" style={{ marginTop: 24 }}>全部比对结果（{results.length}）</Title>
          <Card className="glass-surface-light">
            <Table
              dataSource={results}
              rowKey="id"
              loading={loadingResults}
              pagination={{ pageSize: 10 }}
              className="light-table"
              columns={[
                {
                  title: 'A提交',
                  dataIndex: 'submission_id',
                  key: 'submission_id',
                  width: 100,
                  render: (id: number) => {
                    const sub = submissions.find(s => s.id === id);
                    return <span style={{ color: '#1e293b' }}>{sub ? `${id} (${sub.student_name})` : id}</span>;
                  }
                },
                {
                  title: 'B提交',
                  dataIndex: 'compared_with_id',
                  key: 'compared_with_id',
                  width: 100,
                  render: (id: number) => {
                    const sub = submissions.find(s => s.id === id);
                    return <span style={{ color: '#1e293b' }}>{sub ? `${id} (${sub.student_name})` : id}</span>;
                  }
                },
                {
                  title: '相似度',
                  dataIndex: 'similarity_score',
                  key: 'similarity_score',
                  width: 120,
                  render: (s: number) => (
                    <span style={{ fontWeight: 600, color: s >= 80 ? '#dc2626' : '#22c55e' }}>{s}</span>
                  ),
                },
                {
                  title: '过滤层',
                  dataIndex: 'filter_layer',
                  key: 'filter_layer',
                  width: 140,
                  render: (text: string) => <span style={{ color: '#64748b' }}>{text}</span>,
                },
                {
                  title: '原因（摘要）',
                  dataIndex: 'details',
                  key: 'details',
                  render: (d: string) => {
                    const reason = safeReason(d);
                    return reason ? <span style={{ color: '#1e293b' }}>{reason}</span> : <span style={{ color: '#94a3b8' }}>-</span>;
                  },
                },
                {
                  title: '对比',
                  key: 'compare',
                  width: 120,
                  render: (_: any, r: ComparisonResult) => (
                    <Button size="small" onClick={() => openCompare(r)} className="btn-primary-light">
                      对照查看
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </>
      )}

      <Modal
        title={previewTitle}
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        footer={null}
        width={800}
      >
        <pre style={{ 
          padding: '16px', 
          borderRadius: '4px',
          maxHeight: '500px',
          overflow: 'auto',
          fontFamily: 'Consolas, Monaco, "Courier New", monospace',
          backgroundColor: '#1e293b',
          color: '#e2e8f0'
        }}>
          {previewCode}
        </pre>
      </Modal>

      <Modal
        title="代码对照（高亮相同行）"
        open={compareOpen}
        onCancel={() => setCompareOpen(false)}
        footer={null}
        width={1200}
      >
        <Space align="start" size={12} style={{ width: '100%' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ marginBottom: 6, fontWeight: 600, color: '#1e293b' }}>
              A: 提交 #{compareA?.id} / 学生 {compareA?.student_name ?? '-'}
            </div>
            {renderCodeWithHighlights(
              compareA?.code || '',
              new Set((compareB?.code || '').split('\n').map((x) => x.trim()).filter((x) => x.length >= 6)),
            )}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ marginBottom: 6, fontWeight: 600, color: '#1e293b' }}>
              B: 提交 #{compareB?.id} / 学生 {compareB?.student_name ?? '-'}
            </div>
            {renderCodeWithHighlights(
              compareB?.code || '',
              new Set((compareA?.code || '').split('\n').map((x) => x.trim()).filter((x) => x.length >= 6)),
            )}
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default DeanAssignmentDetail;
