import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Alert, Form, Select, Button, message, Spin, Typography, Space, Tag, Upload, Divider, Card } from 'antd';
import { UploadOutlined, FileTextOutlined, CalendarOutlined, CodeOutlined, ArrowLeftOutlined, CheckCircleOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import api from '../../api/client';
import { getLatestSubmission, submitAssignmentFile } from '../../api/submissions';
import dayjs from 'dayjs';
import '../../styles/global.css';

const { Text, Title } = Typography;
const { Option } = Select;

interface Assignment {
  id: number;
  title: string;
  description: string;
  language: string;
  deadline: string;
}

const SubmitAssignment: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileUploading, setFileUploading] = useState(false);
  const [lastSubmittedCode, setLastSubmittedCode] = useState<string>('');
  const [lastSubmittedAt, setLastSubmittedAt] = useState<string>('');
  const [latestSubmissionId, setLatestSubmissionId] = useState<number | null>(null);
  const [lastSuccessInfo, setLastSuccessInfo] = useState<{
    version: string;
    submittedAt: string;
    fileName: string;
    lineCount: number;
  } | null>(null);

  useEffect(() => {
    if (!id) return;
    const fetchAssignment = async () => {
      setLoading(true);
      try {
        const response = await api.get<Assignment>(`/assignments/${id}`);
        setAssignment(response.data);
        setLanguage(response.data.language);
        try {
          const latest = await getLatestSubmission(Number(id));
          setLastSubmittedCode(latest.data.code || '');
          setLastSubmittedAt(latest.data.submitted_at || '');
          setLatestSubmissionId(latest.data.id || null);
          setLastSuccessInfo({
            version: `v${latest.data.id}`,
            submittedAt: latest.data.submitted_at,
            fileName: latest.data.file_path ? String(latest.data.file_path).split(/[\\/]/).pop() || '已提交文件' : '文本提交',
            lineCount: (latest.data.code || '').split('\n').length,
          });
        } catch {
          setLastSubmittedCode('');
          setLastSubmittedAt('');
        }
      } catch (error) {
        message.error('获取作业信息失败');
        navigate('/student/assignments');
      } finally {
        setLoading(false);
      }
    };
    fetchAssignment();
  }, [id, navigate]);

  const handleSubmit = async () => {
    if (!code.trim()) {
      message.warning('请输入代码内容');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/submissions', {
        assignment_id: Number(id),
        code: code,
      });
      const latest = await getLatestSubmission(Number(id));
      setLastSubmittedCode(latest.data.code || '');
      setLastSubmittedAt(latest.data.submitted_at || '');
      setLatestSubmissionId(latest.data.id || null);
      setLastSuccessInfo({
        version: `v${latest.data.id}`,
        submittedAt: latest.data.submitted_at,
        fileName: '文本提交',
        lineCount: (latest.data.code || '').split('\n').length,
      });
      message.success('作业提交成功');
      setTimeout(() => {
        navigate('/student/assignments');
      }, 1500);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '提交失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileSubmit = async () => {
    if (!id || !selectedFile) return;
    setFileUploading(true);
    try {
      const res = await submitAssignmentFile(Number(id), selectedFile);
      setCode(res.data.code || '');
      setLastSubmittedCode(res.data.code || '');
      setLastSubmittedAt(res.data.submitted_at || '');
      setLatestSubmissionId(res.data.id || null);
      setLastSuccessInfo({
        version: `v${res.data.id}`,
        submittedAt: res.data.submitted_at,
        fileName: selectedFile.name || '代码文件',
        lineCount: (res.data.code || '').split('\n').length,
      });
      setSelectedFile(null);
      message.success('作业提交成功');
      setTimeout(() => {
        navigate('/student/assignments');
      }, 1500);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '文件提交失败');
    } finally {
      setFileUploading(false);
    }
  };

  const handleUnifiedSubmit = async () => {
    if (selectedFile) {
      await handleFileSubmit();
      return;
    }
    await handleSubmit();
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', marginTop: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!assignment) {
    return <div style={{ color: '#e2e8f0' }}>作业不存在</div>;
  }

  const isDeadlinePassed = dayjs().isAfter(dayjs(assignment.deadline));
  const monacoLangMap: { [key: string]: string } = {
    python: 'python',
    java: 'java',
    go: 'go',
    javascript: 'javascript',
    c: 'c',
    cpp: 'cpp',
    csharp: 'csharp'
  };
  const monacoLang = monacoLangMap[language] || 'python';
  const now = dayjs();
  const deadline = dayjs(assignment.deadline);
  const diffMs = deadline.diff(now);
  const remainHours = Math.max(0, Math.floor(diffMs / (1000 * 60 * 60)));
  const remainDays = Math.floor(remainHours / 24);
  const riskSoon = !isDeadlinePassed && remainHours <= 24;

  const getLanguageColor = (lang: string) => {
    const colors: { [key: string]: string } = {
      python: 'blue',
      java: 'orange',
      javascript: 'gold',
      c: 'green',
      cpp: 'cyan',
      csharp: 'purple',
      go: 'cyan',
    };
    return colors[lang] || 'default';
  };

  const getLanguageTagStyle = (lang: string) => {
    if (lang === 'python') {
      return { background: 'rgba(59,130,246,0.15)', color: '#60a5fa', border: '1px solid rgba(59,130,246,0.3)' };
    }
    if (lang === 'java') {
      return { background: 'rgba(249,115,22,0.15)', color: '#fb923c', border: '1px solid rgba(249,115,22,0.3)' };
    }
    return { background: 'rgba(148,163,184,0.1)', color: '#94a3b8', border: '1px solid rgba(148,163,184,0.2)' };
  };

  return (
    <div className="page-fade-in">
      <Title level={4} className="page-title-light">
        <FileTextOutlined className="page-title-icon-light" />
        提交作业：{assignment.title}
      </Title>
        <Space orientation="vertical" size="large" style={{ width: '100%' }}>
          {lastSuccessInfo && (
            <Alert
              type="success"
              showIcon
              icon={<CheckCircleOutlined />}
              message={`最近一次提交成功于 ${dayjs(lastSuccessInfo.submittedAt).format('YYYY-MM-DD HH:mm:ss')}`}
              description={`版本号 ${lastSuccessInfo.version} | 文件名 ${lastSuccessInfo.fileName} | 代码行数 ${lastSuccessInfo.lineCount}`}
            />
          )}
          <div>
            <Text strong style={{ color: '#334155' }}>作业描述：</Text>
            <Text style={{ color: '#64748b' }}>{assignment.description}</Text>
          </div>
          <div>
            <Text strong style={{ color: '#334155' }}>编程语言：</Text>
            <Tag style={getLanguageTagStyle(assignment.language)} icon={<CodeOutlined />}>
              {assignment.language}
            </Tag>
          </div>
          <div>
            <Text strong style={{ color: '#334155' }}>截止时间：</Text>
            <Text style={{ color: isDeadlinePassed ? '#dc2626' : '#64748b' }}>
              <CalendarOutlined style={{ marginRight: 4 }} />
              {dayjs(assignment.deadline).format('YYYY-MM-DD HH:mm')}
              {isDeadlinePassed && ' (已截止)'}
            </Text>
            <div style={{ marginTop: 6 }}>
              {isDeadlinePassed ? (
                <Tag style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #fecaca' }}>
                  已截止，禁止提交
                </Tag>
              ) : riskSoon ? (
                <Tag style={{ background: '#fef3c7', color: '#b45309', border: '1px solid #fde68a' }}>
                  距离截止约 {remainHours} 小时（高风险）
                </Tag>
              ) : (
                <Tag style={{ background: '#d1fae5', color: '#065f46', border: '1px solid #a7f3d0' }}>
                  距离截止约 {remainDays} 天 {remainHours % 24} 小时
                </Tag>
              )}
            </div>
          </div>

          <Divider style={{ borderColor: '#e2e8f0' }} />

          <Form layout="vertical">
            <Form.Item label={<span style={{ color: '#334155' }}>上传代码文件</span>}>
              <Upload
                maxCount={1}
                beforeUpload={(file) => {
                  setSelectedFile(file);
                  return false;
                }}
                onRemove={() => {
                  setSelectedFile(null);
                  return true;
                }}
                fileList={selectedFile ? [selectedFile as any] : []}
                disabled={isDeadlinePassed || fileUploading}
              >
                <Button icon={<UploadOutlined />} disabled={isDeadlinePassed || fileUploading} className="btn-primary">
                  选择代码文件
                </Button>
              </Upload>
              <div style={{ marginTop: 8 }}>
                <Text type="secondary" style={{ color: '#94a3b8' }}>
                  {selectedFile ? `已选择: ${selectedFile.name}` : '尚未选择文件'}
                </Text>
              </div>
            </Form.Item>
            {lastSubmittedCode && (
              <Form.Item label={<span style={{ color: '#e2e8f0' }}>上次提交内容（只读）</span>}>
                <div style={{ border: '1px solid rgba(255,255,255,0.1)', padding: 12, borderRadius: 6, background: 'rgba(0,0,0,0.2)' }}>
                  <Text style={{ color: '#94a3b8' }}>
                    上次提交时间: {lastSubmittedAt ? dayjs(lastSubmittedAt).format('YYYY-MM-DD HH:mm:ss') : '-'} {latestSubmissionId ? `| 版本 v${latestSubmissionId}` : ''}
                  </Text>
                  <pre style={{ marginTop: 8, maxHeight: 200, overflow: 'auto', color: '#1e293b', background: '#f1f5f9', padding: 8, borderRadius: 4, border: '1px solid #e2e8f0' }}>{lastSubmittedCode}</pre>
                </div>
              </Form.Item>
            )}
            <Form.Item label={<span style={{ color: '#334155' }}>编辑器语言（可选）</span>}>
              <Select value={language} onChange={setLanguage} style={{ width: 200 }}>
                <Option value="python">Python</Option>
                <Option value="java">Java</Option>
                <Option value="go">Go</Option>
                <Option value="javascript">JavaScript</Option>
              </Select>
            </Form.Item>
            <Form.Item label={<span style={{ color: '#334155' }}>代码内容</span>} required>
              <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, overflow: 'hidden' }}>
                <Editor
                  height="380px"
                  language={monacoLang}
                  theme="vs-dark"
                  value={code}
                  onChange={(v) => setCode(v ?? '')}
                  options={{ minimap: { enabled: true }, fontSize: 14, wordWrap: 'on' }}
                />
              </div>
            </Form.Item>
            <Form.Item>
              <Space>
                <Button
                  onClick={handleUnifiedSubmit}
                  loading={fileUploading || submitting}
                  disabled={isDeadlinePassed || (!selectedFile && !code.trim())}
                  className="btn-primary"
                >
                  提交作业
                </Button>
                <Button onClick={() => navigate('/student/assignments')} icon={<ArrowLeftOutlined />} className="btn-ghost">
                  返回列表
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Space>
    </div>
  );
};

export default SubmitAssignment;
