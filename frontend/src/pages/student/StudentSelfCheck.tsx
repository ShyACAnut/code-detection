import React, { useState } from 'react';
import { Card, Form, Input, Button, message, Spin, Typography, Space, Tag, Alert, Divider } from 'antd';
import { UploadOutlined, FileTextOutlined, CheckCircleOutlined, SettingOutlined, DownloadOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import api from '../../api/client';
import '../../styles/global.css';

const { Text, Title } = Typography;
const { TextArea } = Input;

interface SelfCheckResult {
  similarity_score: number;
  compared_with_count: number;
  details: string;
  suggestions: string[];
}

const StudentSelfCheck: React.FC = () => {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<SelfCheckResult | null>(null);
  const [history, setHistory] = useState<SelfCheckResult[]>([]);

  const handleCheck = async () => {
    if (!code.trim()) {
      message.warning('请输入代码内容');
      return;
    }

    setChecking(true);
    try {
      const response = await api.post('/self-check', {
        code: code,
        language: language,
      });
      
      const data = response.data;
      const resultData: SelfCheckResult = {
        similarity_score: data.similarity_score || 0,
        compared_with_count: data.compared_with_count || 0,
        details: data.details || '',
        suggestions: data.suggestions || [],
      };
      
      setResult(resultData);
      setHistory(prev => [resultData, ...prev].slice(0, 5));
      message.success('自查完成');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '自查失败');
    } finally {
      setChecking(false);
    }
  };

  const handleDownloadReport = () => {
    if (!result) return;
    
    const report = `代码自查报告
================

检测时间: ${new Date().toLocaleString()}
编程语言: ${language}
代码行数: ${code.split('\n').length}

相似度检测结果:
- 最高相似度: ${result.similarity_score}%
- 比对数量: ${result.compared_with_count} 个提交

检测详情:
${result.details}

改进建议:
${result.suggestions.map((s, i) => `${i + 1}. ${s}`).join('\n')}
`;
    
    const blob = new Blob([report], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `self_check_report_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const getScoreLevel = (score: number) => {
    if (score >= 80) return { level: '高风险', color: 'red' };
    if (score >= 50) return { level: '中等', color: 'orange' };
    return { level: '低风险', color: 'green' };
  };

  const languages = [
    { value: 'python', label: 'Python' },
    { value: 'java', label: 'Java' },
    { value: 'javascript', label: 'JavaScript' },
    { value: 'go', label: 'Go' },
    { value: 'cpp', label: 'C/C++' },
    { value: 'c', label: 'C' },
    { value: 'csharp', label: 'C#' },
  ];

  return (
    <div className="page-fade-in">
      <Card className="content-card">
        <Title level={4} className="page-title">
          <FileTextOutlined className="page-title-icon" />
          代码自查
        </Title>
        
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
          message="代码自查功能说明"
          description="在此页面上传代码进行自查，系统将检测您的代码与已有提交的相似度，帮助您提前发现潜在的抄袭风险。请注意：自查结果仅供参考，正式提交后教师将进行全面检测。"
        />

        <Form layout="vertical" style={{ maxWidth: 1000 }}>
          <Form.Item 
            label={<span style={{ color: '#334155' }}>选择编程语言</span>}
          >
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              style={{ 
                width: '100%', 
                maxWidth: 200, 
                padding: '8px 12px',
                borderRadius: 8,
                border: '1px solid #e2e8f0',
                backgroundColor: 'white'
              }}
            >
              {languages.map((lang) => (
                <option key={lang.value} value={lang.value}>
                  {lang.label}
                </option>
              ))}
            </select>
          </Form.Item>

          <Form.Item label={<span style={{ color: '#334155' }}>输入代码内容</span>}>
            <div style={{ height: 300, border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden' }}>
              <Editor
                height="100%"
                language={language}
                theme="vs-light"
                value={code}
                onChange={(value) => setCode(value || '')}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
                }}
              />
            </div>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                onClick={handleCheck}
                loading={checking}
                icon={<CheckCircleOutlined />}
                className="btn-primary"
              >
                开始自查
              </Button>
              <Button
                onClick={() => setCode('')}
                className="btn-ghost"
              >
                清空代码
              </Button>
            </Space>
          </Form.Item>
        </Form>

        {/* 检测结果 */}
        {result && (
          <div style={{ marginTop: 24 }}>
            <Divider />
            <Title level={5} style={{ marginBottom: 16 }}>
              <SettingOutlined style={{ marginRight: 8 }} />
              自查结果
            </Title>
            
            <Card style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <Text strong style={{ fontSize: 16 }}>相似度评分</Text>
                </div>
                <Tag color={getScoreLevel(result.similarity_score).color} style={{ fontSize: 18, padding: '8px 16px' }}>
                  {result.similarity_score}% - {getScoreLevel(result.similarity_score).level}
                </Tag>
              </div>
              
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary">比对数量：</Text>
                <Text>{result.compared_with_count} 个已有提交</Text>
              </div>
              
              {result.details && (
                <div style={{ marginBottom: 16, padding: 12, backgroundColor: '#f8fafc', borderRadius: 8 }}>
                  <Text strong style={{ display: 'block', marginBottom: 8 }}>检测详情：</Text>
                  <Text>{result.details}</Text>
                </div>
              )}
              
              {result.suggestions.length > 0 && (
                <div>
                  <Text strong style={{ display: 'block', marginBottom: 8 }}>改进建议：</Text>
                  <ul style={{ paddingLeft: 20 }}>
                    {result.suggestions.map((suggestion, index) => (
                      <li key={index} style={{ marginBottom: 4, color: '#334155' }}>
                        {suggestion}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div style={{ marginTop: 16, textAlign: 'right' }}>
                <Button
                  onClick={handleDownloadReport}
                  icon={<DownloadOutlined />}
                  className="btn-ghost"
                >
                  下载自查报告
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* 历史记录 */}
        {history.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <Divider />
            <Title level={5}>自查历史</Title>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {history.map((item, index) => (
                <Card key={index} size="small" style={{ width: 200 }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: getScoreLevel(item.similarity_score).color }}>
                      {item.similarity_score}%
                    </div>
                    <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                      比对 {item.compared_with_count} 个提交
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default StudentSelfCheck;