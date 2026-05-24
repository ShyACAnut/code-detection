import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Divider,
  Form,
  Input,
  InputNumber,
  message,
  Progress,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  Modal,
} from 'antd';
import api from '../../api/client';
import dayjs from 'dayjs';
import CodeCompare from '../../components/CodeCompare/CodeCompare';

const { Text } = Typography;
const { TextArea } = Input;

interface Assignment {
  id: number;
  title: string;
  description: string;
  language: string;
  deadline: string;
  created_at: string;
  created_by: number;
}

interface Submission {
  id: number;
  student_id: number;
  assignment_id: number;
  code: string;
  submitted_at: string;
  student_name: string;
}

interface SubmissionScore {
  id?: number;
  submission_id: number;
  overall_score: number;
  teacher_comments?: string;
  teacher_name?: string;
  created_at?: string;
  updated_at?: string;
}

interface ComparisonResult {
  id: number;
  submission_id: number;
  submission_username?: string;
  compared_with_id: number;
  compared_with_username?: string;
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

interface DetectionEvidence {
  id: number;
  comparison_result_id: number;
  submission_id: number;
  compared_with_id: number;
  language: string;
  syntax_score: number;
  semantic_score: number;
  final_score: number;
  model_name: string;
  evidence_payload: string;
}

function safeReason(details: string): string {
  try {
    const parsed = JSON.parse(details);
    return parsed?.similarity_analysis?.reason || '';
  } catch {
    return '';
  }
}

const TeacherAssignmentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const assignmentId = Number(id);
  const navigate = useNavigate();

  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [results, setResults] = useState<ComparisonResult[]>([]);
  const [scores, setScores] = useState<Map<number, SubmissionScore>>(new Map());

  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [loadingResults, setLoadingResults] = useState(false);
  const [taskId, setTaskId] = useState<number | null>(null);
  const [task, setTask] = useState<AnalysisTask | null>(null);
  const [previewCode, setPreviewCode] = useState<string>('');
  const [previewTitle, setPreviewTitle] = useState<string>('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareA, setCompareA] = useState<Submission | null>(null);
  const [compareB, setCompareB] = useState<Submission | null>(null);
  const [compareEvidence, setCompareEvidence] = useState<DetectionEvidence | null>(null);

  const [scoreModalOpen, setScoreModalOpen] = useState(false);
  const [currentScoreSubmission, setCurrentScoreSubmission] = useState<Submission | null>(null);
  const [scoreForm] = Form.useForm();
  const [savingScore, setSavingScore] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const riskResults = useMemo(() => results.filter((r) => r.similarity_score >= 80), [results]);

  const fetchAll = async () => {
    if (!assignmentId) return;
    setLoading(true);
    try {
      const [aRes, sRes, rRes] = await Promise.all([
        api.get(`/assignments/${assignmentId}`),
        api.get(`/assignments/${assignmentId}/submissions`),
        api.get(`/assignments/${assignmentId}/results`).catch(() => ({ data: [] })),
      ]);
      setAssignment(aRes.data);
      setSubmissions(sRes.data);
      setResults(Array.isArray(rRes.data) ? rRes.data : []);
      
      // 获取评分信息
      try {
        const scoresRes = await api.get(`/assignments/${assignmentId}/scores`);
        if (Array.isArray(scoresRes.data)) {
          const scoreMap = new Map<number, SubmissionScore>();
          scoresRes.data.forEach((item: any) => {
            if (item.score) {
              scoreMap.set(item.submission_id, item.score);
            }
          });
          setScores(scoreMap);
        }
      } catch {
        // ignore scores if not available
      }
      
      try {
        const tRes = await api.get<AnalysisTask>(`/analysis_tasks/latest/${assignmentId}`);
        if (['pending', 'running'].includes(tRes.data.status)) {
          setTask(tRes.data);
          setTaskId(tRes.data.id);
          setAnalyzing(true);
        }
      } catch {
        // no task
      }
    } catch (e) {
      message.error('获取作业详情或提交列表失败');
      navigate('/teacher/assignments');
    } finally {
      setLoading(false);
    }
  };

  const openScoreModal = (submission: Submission) => {
    setCurrentScoreSubmission(submission);
    const existingScore = scores.get(submission.id);
    scoreForm.setFieldsValue({
      overallScore: existingScore?.overall_score || 0,
      teacherComments: existingScore?.teacher_comments || '',
    });
    setScoreModalOpen(true);
  };

  const saveScore = async () => {
    if (!currentScoreSubmission) return;
    setSavingScore(true);
    try {
      const values = await scoreForm.validateFields();
      await api.post(`/submissions/${currentScoreSubmission.id}/score`, {
        overall_score: values.overallScore,
        teacher_comments: values.teacherComments,
      });
      
      // 更新评分信息
      const newScores = new Map(scores);
      const tRes = await api.get(`/submissions/${currentScoreSubmission.id}/score`);
      newScores.set(currentScoreSubmission.id, tRes.data);
      setScores(newScores);
      
      message.success('评分保存成功');
      setScoreModalOpen(false);
    } catch (e: any) {
      message.error(e.response?.data?.detail || '保存评分失败');
    } finally {
      setSavingScore(false);
    }
  };

  const fetchResults = async () => {
    if (!assignmentId) return;
    setLoadingResults(true);
    try {
      const rRes = await api.get(`/assignments/${assignmentId}/results`);
      setResults(rRes.data);
    } catch (e: any) {
      message.error(e.response?.data?.detail || '获取检测结果失败');
    } finally {
      setLoadingResults(false);
    }
  };

  useEffect(() => {
    fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assignmentId]);

  const stopPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!taskId) return;

    const tick = async () => {
      try {
        const r = await api.get<AnalysisTask>(`/analysis_tasks/${taskId}`);
        setTask(r.data);
        if (r.data.status === 'completed') {
          stopPoll();
          setAnalyzing(false);
          setTaskId(null);
          message.success('批量检测完成');
          await fetchResults();
        } else if (r.data.status === 'failed' || r.data.status === 'cancelled') {
          stopPoll();
          setAnalyzing(false);
          setTaskId(null);
          if (r.data.status === 'cancelled') {
            message.info('分析任务已取消');
          } else {
            message.error(r.data.error_message || '分析失败');
          }
        }
      } catch (e: any) {
        stopPoll();
        setAnalyzing(false);
        setTaskId(null);
        setTask(null);
        message.error(e.response?.data?.detail || '查询任务失败');
      }
    };

    tick();
    pollRef.current = setInterval(tick, 3000);
    return () => stopPoll();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 轮询仅依赖 taskId
  }, [taskId, stopPoll]);

  const runAnalyze = async () => {
    if (!assignmentId) return;
    if (submissions.length < 2) {
      message.warning('至少需要 2 份提交才能批量检测');
      return;
    }
    setTask(null);
    setAnalyzing(true);
    try {
      const res = await api.post<{ task_id: number }>(`/assignments/${assignmentId}/analyze`);
      setTaskId(res.data.task_id);
    } catch (e: any) {
      setAnalyzing(false);
      message.error(e.response?.data?.detail || '无法启动分析任务');
    }
  };

  const cancelAnalyze = async () => {
    if (!taskId) return;
    try {
      await api.post(`/analysis_tasks/${taskId}/cancel`);
      message.info('任务已取消');
      setAnalyzing(false);
      setTaskId(null);
      stopPoll();
      if (task) setTask({ ...task, status: 'cancelled', error_message: '已由教师手动取消' });
    } catch (e: any) {
      message.error(e.response?.data?.detail || '取消失败');
    }
  };

  const humanizeTaskError = (err?: string | null) => {
    const t = (err || '').toLowerCase();
    if (!t) return '任务执行失败，请稍后重试。';
    if (t.includes('pandoc')) return '导出失败：未安装或无法调用 pandoc。请安装 pandoc，或先仅运行检测。';
    if (t.includes('need at least 2 submissions')) return '样本不足：至少需要 2 份提交才能检测。';
    if (t.includes('timeout')) return '模型请求超时：请稍后重试。';
    if (t.includes('429')) return '模型调用频率受限（429）：请稍后再试。';
    return err || '任务执行失败。';
  };

  const openCompare = (r: ComparisonResult) => {
    const a = submissions.find((s) => s.id === r.submission_id) || null;
    const b = submissions.find((s) => s.id === r.compared_with_id) || null;
    setCompareA(a);
    setCompareB(b);
    api
      .get<DetectionEvidence[]>(`/assignments/${assignmentId}/evidences`)
      .then((res) => {
        const hit = (res.data || []).find((e) => e.comparison_result_id === r.id) || null;
        setCompareEvidence(hit);
      })
      .catch(() => setCompareEvidence(null));
    setCompareOpen(true);
  };

  const renderCodeWithHighlights = (code: string, peers: Set<string>) => {
    const lines = (code || '').split('\n');
    return (
      <pre style={{ maxHeight: 420, overflow: 'auto', background: '#fafafa', padding: 10, margin: 0 }}>
        {lines.map((ln, idx) => {
          const k = ln.trim();
          const hit = k.length >= 6 && peers.has(k);
          return (
            <div key={idx} style={{ background: hit ? '#fff1b8' : 'transparent' }}>
              <span style={{ color: '#999', width: 36, display: 'inline-block' }}>{idx + 1}</span>
              {ln || ' '}
            </div>
          );
        })}
      </pre>
    );
  };

  const runLangGraphWorkflow = async (exportFormat?: string | null) => {
    if (!assignmentId) return;
    if (submissions.length < 2) {
      message.warning('至少需要 2 份提交才能运行工作流');
      return;
    }
    setAnalyzing(true);
    try {
      const url =
        exportFormat != null && exportFormat !== ''
          ? `/assignments/${assignmentId}/workflow?export_format=${encodeURIComponent(exportFormat)}`
          : `/assignments/${assignmentId}/workflow`;
      const res = await api.post(url);
      const d = res.data;
      message.success(
        `工作流完成：比对 ${d.comparisons_created ?? '-'} 对，报告约 ${d.report_markdown_chars ?? 0} 字符`,
      );
      if (d.exported_file_path) {
        message.info(`服务端已生成文件：${d.exported_file_path}（也可使用下方导出按钮下载）`);
      }
      await fetchResults();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '工作流执行失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const exportReport = async (format: 'pdf' | 'docx' | 'md') => {
    if (!assignmentId) return;
    try {
      const url = `/assignments/${assignmentId}/report?format=${format}`;
      const res = await api.post(url, undefined, { responseType: format === 'md' ? 'text' : 'blob' });

      if (format === 'md') {
        const blob = new Blob([res.data], { type: 'text/markdown;charset=utf-8' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `assignment_${assignmentId}_report.md`;
        a.click();
        URL.revokeObjectURL(a.href);
        return;
      }

      const contentType: string =
        (res.headers['content-type'] as string) ||
        (format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
      const blob = new Blob([res.data], { type: contentType });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `assignment_${assignmentId}_report.${format}`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e: any) {
      let detail: string = '导出报告失败';
      const raw = e.response?.data;
      if (raw && typeof raw === 'object' && 'detail' in raw) {
        detail = String((raw as { detail?: unknown }).detail ?? detail);
      } else if (raw instanceof Blob) {
        try {
          const t = await raw.text();
          const j = JSON.parse(t) as { detail?: string };
          if (j.detail) detail = j.detail;
        } catch {
          /* ignore */
        }
      }
      message.error(detail);
      if (format !== 'md') {
        message.info('若未安装 pandoc，请使用「导出 Markdown」或安装 pandoc 后重试。');
      }
    }
  };

  const progressPct =
    task && task.total_pairs > 0
      ? Math.min(100, Math.round((task.processed_pairs / task.total_pairs) * 100))
      : analyzing
      ? 0
      : 0;

  if (loading) {
    return (
      <div style={{ textAlign: 'center', marginTop: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!assignment) return <div>作业不存在</div>;

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button onClick={() => navigate('/teacher/assignments')}>返回作业列表</Button>
        <Button type="primary" onClick={runAnalyze} loading={analyzing} disabled={submissions.length < 2}>
          一键批量检测（异步）
        </Button>
        <Button onClick={cancelAnalyze} danger disabled={!analyzing || !taskId}>
          取消任务
        </Button>
        <Button onClick={() => runLangGraphWorkflow(null)} loading={analyzing} disabled={submissions.length < 2}>
          LangGraph 工作流（检测+报告）
        </Button>
        <Button onClick={() => runLangGraphWorkflow('pdf')} loading={analyzing} disabled={submissions.length < 2}>
          工作流并导出 PDF（服务端）
        </Button>
        <Button onClick={fetchResults} loading={loadingResults}>
          刷新检测结果
        </Button>
        <Button onClick={() => exportReport('pdf')} disabled={results.length === 0}>
          导出PDF报告
        </Button>
        <Button onClick={() => exportReport('docx')} disabled={results.length === 0}>
          导出Word报告
        </Button>
        <Button onClick={() => exportReport('md')} disabled={results.length === 0}>
          导出Markdown
        </Button>
      </Space>

      {analyzing && task && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Progress percent={progressPct} status={task.status === 'failed' ? 'exception' : 'active'} />
          <div style={{ marginTop: 8 }}>
            <Text type="secondary">
              状态：{task.status} — 已处理 {task.processed_pairs} / {task.total_pairs} 对
            </Text>
          </div>
          {(task.status === 'failed' || task.status === 'cancelled') && (
            <Alert
              style={{ marginTop: 12 }}
              type={task.status === 'cancelled' ? 'warning' : 'error'}
              showIcon
              message={task.status === 'cancelled' ? '任务已取消' : '分析失败'}
              description={humanizeTaskError(task.error_message)}
              action={
                task.status === 'failed' ? <Button size="small" onClick={runAnalyze}>重试</Button> : undefined
              }
            />
          )}
        </Card>
      )}

      <Card title="作业信息" style={{ marginBottom: 16 }}>
        <Descriptions column={1} bordered>
          <Descriptions.Item label="标题">{assignment.title}</Descriptions.Item>
          <Descriptions.Item label="语言">
            <Tag color={assignment.language === 'python' ? 'blue' : 'orange'}>{assignment.language}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="截止时间">{dayjs(assignment.deadline).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
          <Descriptions.Item label="描述">{assignment.description}</Descriptions.Item>
          {(assignment as any).function_requirements && (
            <Descriptions.Item label="功能需求">{(assignment as any).function_requirements}</Descriptions.Item>
          )}
          {(assignment as any).scoring_guideline && (
            <Descriptions.Item label="评分指南">{(assignment as any).scoring_guideline}</Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title={`提交列表（${submissions.length}）`} style={{ marginBottom: 16 }}>
        <Table
          dataSource={submissions}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          columns={[
            { title: '提交ID', dataIndex: 'id', key: 'id', width: 100 },
            { title: '学生姓名', dataIndex: 'student_name', key: 'student_name', width: 140 },
            {
              title: '提交时间',
              dataIndex: 'submitted_at',
              key: 'submitted_at',
              render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm'),
              width: 180,
            },
            {
              title: '评分',
              dataIndex: 'score',
              key: 'score',
              width: 120,
              render: (_: any, row: Submission) => {
                const score = scores.get(row.id);
                if (score) {
                  const color = score.overall_score >= 80 ? '#52c41a' : score.overall_score >= 60 ? '#faad14' : '#ff4d4f';
                  return <Tag color={color}>{score.overall_score}分</Tag>;
                }
                return <Tag color="default">未评分</Tag>;
              },
            },
            {
              title: '代码预览',
              dataIndex: 'code',
              key: 'code',
              render: (_: string, row: Submission) => {
                const codeStr = typeof row.code === 'string' ? row.code : JSON.stringify(row.code) || '';
                return (
                  <Space>
                    <Text code>{codeStr.slice(0, 80)}</Text>
                    <Button
                      size="small"
                      onClick={() => {
                        setPreviewTitle(`提交 #${row.id} - ${row.student_name}`);
                        setPreviewCode(codeStr);
                        setPreviewOpen(true);
                      }}
                    >
                      查看全文
                    </Button>
                  </Space>
                );
              },
            },
            {
              title: '操作',
              key: 'action',
              width: 120,
              render: (_: any, row: Submission) => {
                return (
                  <Button size="small" type="primary" onClick={() => openScoreModal(row)}>
                    {scores.has(row.id) ? '修改评分' : '评分'}
                  </Button>
                );
              },
            },
          ]}
        />
      </Card>
      <Modal
        title={previewTitle || '代码内容'}
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        footer={null}
        width={900}
      >
        <pre style={{ maxHeight: 520, overflow: 'auto', background: '#fafafa', padding: 12 }}>
          {previewCode || '(空)'}
        </pre>
      </Modal>

      <Card title={`高风险对（相似度 ≥ 80）(${riskResults.length})`}>
        <Table
          dataSource={riskResults}
          rowKey="id"
          loading={loadingResults}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无高风险对（或尚未检测）' }}
          columns={[
            {
              title: 'A提交',
              dataIndex: 'submission_username',
              key: 'submission_username',
              width: 140,
              render: (text: string, record: any) => <span>{text} (#{record.submission_id})</span>
            },
            {
              title: 'B提交',
              dataIndex: 'compared_with_username',
              key: 'compared_with_username',
              width: 140,
              render: (text: string, record: any) => <span>{text} (#{record.compared_with_id})</span>
            },
            {
              title: '相似度',
              dataIndex: 'similarity_score',
              key: 'similarity_score',
              width: 120,
              render: (s: number) => (
                <span style={{ fontWeight: 600, color: s >= 80 ? '#d32f2f' : '#388e3c' }}>{s}</span>
              ),
            },
            { title: '过滤层', dataIndex: 'filter_layer', key: 'filter_layer', width: 140 },
            {
              title: '原因（摘要）',
              dataIndex: 'details',
              key: 'details',
              render: (d: string) => {
                const reason = safeReason(d);
                return reason ? <span>{reason}</span> : <span style={{ color: '#999' }}>-</span>;
              },
            },
            {
              title: '对比',
              key: 'compare',
              width: 120,
              render: (_: any, r: ComparisonResult) => (
                <Button size="small" onClick={() => openCompare(r)}>
                  对照查看
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Card title={`全部比对结果（${results.length}，按相似度降序）`} style={{ marginTop: 16 }}>
        <Divider />
        <Table
          dataSource={results}
          rowKey="id"
          loading={loadingResults}
          pagination={{ pageSize: 10 }}
          columns={[
            {
              title: 'A提交',
              dataIndex: 'submission_username',
              key: 'submission_username',
              width: 140,
              render: (text: string, record: any) => <span>{text} (#{record.submission_id})</span>
            },
            {
              title: 'B提交',
              dataIndex: 'compared_with_username',
              key: 'compared_with_username',
              width: 140,
              render: (text: string, record: any) => <span>{text} (#{record.compared_with_id})</span>
            },
            {
              title: '相似度',
              dataIndex: 'similarity_score',
              key: 'similarity_score',
              width: 120,
              render: (s: number) => (
                <span style={{ fontWeight: 600, color: s >= 80 ? '#d32f2f' : '#388e3c' }}>{s}</span>
              ),
            },
            { title: '过滤层', dataIndex: 'filter_layer', key: 'filter_layer', width: 140 },
            {
              title: '原因（摘要）',
              dataIndex: 'details',
              key: 'details',
              render: (d: string) => {
                const reason = safeReason(d);
                return reason ? <span>{reason}</span> : <span style={{ color: '#999' }}>-</span>;
              },
            },
            {
              title: '对比',
              key: 'compare',
              width: 120,
              render: (_: any, r: ComparisonResult) => (
                <Button size="small" onClick={() => openCompare(r)}>
                  对照查看
                </Button>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        title="代码逐行对比"
        open={compareOpen}
        onCancel={() => setCompareOpen(false)}
        footer={null}
        width={1300}
        bodyStyle={{ maxHeight: '80vh', overflow: 'auto' }}
      >
        {compareA && compareB && (
          <CodeCompare
            codeA={compareA.code || ''}
            codeB={compareB.code || ''}
            titleA={`提交 #${compareA.id} - ${compareA.student_name}`}
            titleB={`提交 #${compareB.id} - ${compareB.student_name}`}
            similarityScore={compareEvidence?.final_score}
            syntaxScore={compareEvidence?.syntax_score}
            semanticScore={compareEvidence?.semantic_score}
          />
        )}
      </Modal>

      
      <Modal
        title={currentScoreSubmission ? (scores.has(currentScoreSubmission.id) ? '修改评分' : '评分') : '评分'}
        open={scoreModalOpen}
        onCancel={() => setScoreModalOpen(false)}
        onOk={saveScore}
        confirmLoading={savingScore}
        width={600}
      >
        {currentScoreSubmission && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>学生：</Text>
              <Text>{currentScoreSubmission.student_name}</Text>
              <br />
              <Text strong>提交时间：</Text>
              <Text>{dayjs(currentScoreSubmission.submitted_at).format('YYYY-MM-DD HH:mm')}</Text>
            </div>
            
            {assignment && (
              <div style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                {(assignment as any).function_requirements && (
                <div>
                  <Text strong>功能需求：</Text>
                  <Text>{(assignment as any).function_requirements}</Text>
                </div>
              )}
              {(assignment as any).scoring_guideline && (
                <div style={{ marginTop: 8 }}>
                  <Text strong>评分指南：</Text>
                  <Text>{(assignment as any).scoring_guideline}</Text>
                </div>
              )}
              </div>
            )}
            
            <Form form={scoreForm} layout="vertical">
              <Form.Item
                name="overallScore"
                label="评分（0-100）"
                rules={[{ required: true, message: '请输入评分' }]}
              >
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="teacherComments"
                label="教师评语"
              >
                <TextArea rows={4} placeholder="请输入教师评语" />
              </Form.Item>
            </Form>
          </div>
        )}
      </Modal>

    </div>

  );

};

export default TeacherAssignmentDetail;
