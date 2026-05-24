import React, { useState } from 'react';
import { Card, Button, Select, Space, Typography, Row, Col, message, Divider, Tag, Progress, Alert, Input, Switch, Spin } from 'antd';
import { CodeOutlined, RocketOutlined, ClearOutlined, BarChartOutlined, CheckCircleOutlined, CloseCircleOutlined, ThunderboltOutlined, BulbOutlined, WarningOutlined } from '@ant-design/icons';
import api from '../api/client';
import './CodeAnalyzer.css';
import '../styles/global.css';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface AnalysisResult {
  similarity_analysis?: {
    score: number;
    reason: string;
    function_summary?: string;
  };
  metadata?: {
    language: string;
    ast_a_root_type: string;
    ast_b_root_type: string;
    filter_layer?: string;
  };
  error?: string;
  detected_language?: string;
  detected_language_a?: string;
  detected_language_b?: string;
}

interface LanguageDetectionResult {
  detected_language: string | null;
  confidence: number;
  reason: string;
}

const CodeAnalyzer: React.FC = () => {
  const [codeA, setCodeA] = useState<string>(
    `def sum_a(arr):\n    total = 0\n    for n in arr:\n        total += n\n    return total`,
  );
  const [codeB, setCodeB] = useState<string>(
    `def sum_b(lst):\n    result = 0\n    for item in lst:\n        result = result + item\n    return result`,
  );
  const [language, setLanguage] = useState<string>('python');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [autoDetect, setAutoDetect] = useState<boolean>(true);
  const [detectedLanguageA, setDetectedLanguageA] = useState<LanguageDetectionResult | null>(null);
  const [detectedLanguageB, setDetectedLanguageB] = useState<LanguageDetectionResult | null>(null);
  const [detectingLanguage, setDetectingLanguage] = useState<boolean>(false);

  const languageOptions = [
    { value: 'python', label: 'Python', color: 'blue' },
    { value: 'java', label: 'Java', color: 'orange' },
    { value: 'javascript', label: 'JavaScript', color: 'gold' },
    { value: 'c', label: 'C', color: 'cyan' },
    { value: 'cpp', label: 'C++', color: 'purple' },
    { value: 'csharp', label: 'C#', color: 'magenta' },
    { value: 'go', label: 'Go', color: 'cyan' },
  ];

  const detectLanguage = async (code: string, type: 'A' | 'B') => {
    if (!code.trim()) {
      if (type === 'A') {
        setDetectedLanguageA(null);
      } else {
        setDetectedLanguageB(null);
      }
      return;
    }

    setDetectingLanguage(true);
    try {
      const { data } = await api.post<LanguageDetectionResult>('/api/detect-language', { code });
      if (type === 'A') {
        setDetectedLanguageA(data);
      } else {
        setDetectedLanguageB(data);
      }
    } catch (error: any) {
      console.error('语言检测失败:', error);
    } finally {
      setDetectingLanguage(false);
    }
  };

  const handleCodeAChange = (value: string) => {
    setCodeA(value);
    detectLanguage(value, 'A');
  };

  const handleCodeBChange = (value: string) => {
    setCodeB(value);
    detectLanguage(value, 'B');
  };

  const handleAutoDetectChange = (checked: boolean) => {
    setAutoDetect(checked);
    if (checked) {
      if (detectedLanguageA?.detected_language) {
        setLanguage(detectedLanguageA.detected_language);
      }
    }
  };

  const analyzeCode = async () => {
    setAnalysisResult(null);
    setErrorMessage('');
    setIsLoading(true);

    try {
      const { data: result } = await api.post<AnalysisResult>('/api/analyze', {
        code_a: codeA,
        code_b: codeB,
        language: language,
      });
      setAnalysisResult(result);
      if (result.error) {
        message.warning(result.error);
      } else {
        message.success('分析完成！');
      }
    } catch (error: any) {
      const msg = error.response?.data?.detail || error.message || '未知错误';
      setErrorMessage(String(msg));
      setAnalysisResult(null);
      message.error(`分析失败: ${msg}`);
    } finally {
      setIsLoading(false);
    }
  };

  const resetAll = () => {
    setCodeA('');
    setCodeB('');
    setAnalysisResult(null);
    setErrorMessage('');
    setDetectedLanguageA(null);
    setDetectedLanguageB(null);
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#ff4d4f';
    if (score >= 60) return '#faad14';
    return '#52c41a';
  };

  const getScoreStatus = (score: number) => {
    if (score >= 80) return 'exception';
    if (score >= 60) return 'normal';
    return 'success';
  };

  const getSimilarityLevel = (score: number) => {
    if (score >= 80) return { text: '高度相似', color: 'red', icon: <CloseCircleOutlined /> };
    if (score >= 60) return { text: '中等相似', color: 'orange', icon: <ThunderboltOutlined /> };
    return { text: '低相似度', color: 'green', icon: <CheckCircleOutlined /> };
  };

  return (
    <div className="code-analyzer">
      <Card className="glass-surface-light">
        <Title level={4} className="page-title-light">
          <CodeOutlined className="page-title-icon-light" />
          代码相似度智能分析
          <Space style={{ marginLeft: 16 }}>
            <Tag color="blue" icon={<CodeOutlined />}>支持7种编程语言</Tag>
            <Tag color="green" icon={<CheckCircleOutlined />}>智能分析</Tag>
          </Space>
        </Title>
        <div className="control-panel">
          <Space wrap size="large">
            <Space>
              <Text strong>
                <BulbOutlined style={{ marginRight: 4, color: '#1890ff' }} />
                自动检测语言:
              </Text>
              <Switch
                checked={autoDetect}
                onChange={handleAutoDetectChange}
                checkedChildren="开启"
                unCheckedChildren="关闭"
              />
            </Space>
            {!autoDetect && (
              <Space>
                <Text strong>选择编程语言:</Text>
                <Select
                  value={language}
                  onChange={setLanguage}
                  style={{ width: 150 }}
                  size="large"
                >
                  {languageOptions.map(option => (
                    <Option key={option.value} value={option.value}>
                      <Tag color={option.color}>{option.label}</Tag>
                    </Option>
                  ))}
                </Select>
              </Space>
            )}
            <Button 
              type="primary" 
              size="large"
              icon={<RocketOutlined />}
              onClick={analyzeCode} 
              loading={isLoading}
            >
              开始智能分析
            </Button>
            <Button 
              size="large"
              icon={<ClearOutlined />}
              onClick={resetAll}
            >
              清空
            </Button>
          </Space>
        </div>

        {errorMessage && (
          <Alert
            title="分析错误"
            description={errorMessage}
            type="error"
            showIcon
            closable
            onClose={() => setErrorMessage('')}
            style={{ marginBottom: '1.5rem' }}
          />
        )}

        <div className="code-input-container">
          <div className="code-input">
            <h3>
              <CodeOutlined />
              代码片段 A
              {detectingLanguage && <Spin size="small" style={{ marginLeft: 8 }} />}
            </h3>
            <TextArea
              value={codeA}
              onChange={(e) => handleCodeAChange(e.target.value)}
              rows={15}
              placeholder={`请输入代码...`}
              spellCheck={false}
            />
            {autoDetect && detectedLanguageA && (
              <Alert
                title={
                  <Space>
                    <Text strong>检测到的语言:</Text>
                    {detectedLanguageA.detected_language ? (
                      <>
                        <Tag color={languageOptions.find(o => o.value === detectedLanguageA.detected_language)?.color || 'default'}>
                          {languageOptions.find(o => o.value === detectedLanguageA.detected_language)?.label || detectedLanguageA.detected_language}
                        </Tag>
                        <Text type="secondary">({(detectedLanguageA.confidence * 100).toFixed(1)}% 置信度)</Text>
                      </>
                    ) : (
                      <Text type="danger">
                        <WarningOutlined style={{ marginRight: 4 }} />
                        {detectedLanguageA.reason}
                      </Text>
                    )}
                  </Space>
                }
                type={detectedLanguageA.detected_language ? 'success' : 'warning'}
                showIcon
                style={{ marginTop: 8 }}
              />
            )}
            {!autoDetect && detectedLanguageA && detectedLanguageA.detected_language && (
              <Alert
                title={
                  <Space>
                    <Text strong>检测到的语言:</Text>
                    <Tag color={languageOptions.find(o => o.value === detectedLanguageA.detected_language)?.color || 'default'}>
                      {languageOptions.find(o => o.value === detectedLanguageA.detected_language)?.label || detectedLanguageA.detected_language}
                    </Tag>
                    {detectedLanguageA.detected_language !== language && (
                      <Text type="warning">
                        <WarningOutlined style={{ marginRight: 4 }} />
                        建议选择 {languageOptions.find(o => o.value === detectedLanguageA.detected_language)?.label}
                      </Text>
                    )}
                  </Space>
                }
                type={detectedLanguageA.detected_language === language ? 'success' : 'warning'}
                showIcon
                style={{ marginTop: 8 }}
              />
            )}
          </div>
          <div className="code-input">
            <h3>
              <CodeOutlined />
              代码片段 B
              {detectingLanguage && <Spin size="small" style={{ marginLeft: 8 }} />}
            </h3>
            <TextArea
              value={codeB}
              onChange={(e) => handleCodeBChange(e.target.value)}
              rows={15}
              placeholder={`请输入代码...`}
              spellCheck={false}
            />
            {autoDetect && detectedLanguageB && (
              <Alert
                title={
                  <Space>
                    <Text strong>检测到的语言:</Text>
                    {detectedLanguageB.detected_language ? (
                      <>
                        <Tag color={languageOptions.find(o => o.value === detectedLanguageB.detected_language)?.color || 'default'}>
                          {languageOptions.find(o => o.value === detectedLanguageB.detected_language)?.label || detectedLanguageB.detected_language}
                        </Tag>
                        <Text type="secondary">({(detectedLanguageB.confidence * 100).toFixed(1)}% 置信度)</Text>
                      </>
                    ) : (
                      <Text type="danger">
                        <WarningOutlined style={{ marginRight: 4 }} />
                        {detectedLanguageB.reason}
                      </Text>
                    )}
                  </Space>
                }
                type={detectedLanguageB.detected_language ? 'success' : 'warning'}
                showIcon
                style={{ marginTop: 8 }}
              />
            )}
            {!autoDetect && detectedLanguageB && detectedLanguageB.detected_language && (
              <Alert
                title={
                  <Space>
                    <Text strong>检测到的语言:</Text>
                    <Tag color={languageOptions.find(o => o.value === detectedLanguageB.detected_language)?.color || 'default'}>
                      {languageOptions.find(o => o.value === detectedLanguageB.detected_language)?.label || detectedLanguageB.detected_language}
                    </Tag>
                    {detectedLanguageB.detected_language !== language && (
                      <Text type="warning">
                        <WarningOutlined style={{ marginRight: 4 }} />
                        建议选择 {languageOptions.find(o => o.value === detectedLanguageB.detected_language)?.label}
                      </Text>
                    )}
                  </Space>
                }
                type={detectedLanguageB.detected_language === language ? 'success' : 'warning'}
                showIcon
                style={{ marginTop: 8 }}
              />
            )}
          </div>
        </div>

        {analysisResult && !analysisResult.error && analysisResult.similarity_analysis && (
          <div className="result-container" style={{ marginTop: 24 }}>
            <Title level={4} style={{ marginBottom: 16 }}>
              <BarChartOutlined />
              <Text strong>智能分析报告</Text>
              {analysisResult.detected_language && (
                <Tag color="blue" style={{ marginLeft: 8 }}>
                  检测语言: {languageOptions.find(o => o.value === analysisResult.detected_language)?.label || analysisResult.detected_language}
                </Tag>
              )}
            </Title>
            <div className="score-section">
              <Row gutter={[24, 24]} align="middle">
                <Col xs={24} md={8} style={{ textAlign: 'center' }}>
                  <Progress
                    type="circle"
                    percent={Math.round(analysisResult.similarity_analysis.score)}
                    strokeColor={getScoreColor(analysisResult.similarity_analysis.score)}
                    status={getScoreStatus(analysisResult.similarity_analysis.score)}
                    size={180}
                    format={(percent) => `${percent}`}
                  />
                </Col>
                <Col xs={24} md={16}>
                  <div className="score-info">
                    <Title level={3}>综合相似度评分</Title>
                    <Space size="large">
                      <Tag 
                        color={getSimilarityLevel(analysisResult.similarity_analysis.score).color}
                        icon={getSimilarityLevel(analysisResult.similarity_analysis.score).icon}
                        style={{ fontSize: '1rem', padding: '0.5rem 1rem' }}
                      >
                        {getSimilarityLevel(analysisResult.similarity_analysis.score).text}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: '1rem' }}>
                        {Math.round(analysisResult.similarity_analysis.score)}/100
                      </Text>
                    </Space>
                  </div>

                  <Divider />

                  <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
                    <Alert
                      title="分析依据"
                      description={analysisResult.similarity_analysis.reason}
                      type="info"
                      showIcon
                    />
                    {analysisResult.similarity_analysis.function_summary && (
                      <Alert
                        title="功能概括"
                        description={analysisResult.similarity_analysis.function_summary}
                        type="success"
                        showIcon
                      />
                    )}
                  </Space>
                </Col>
              </Row>
            </div>

            {analysisResult.metadata && (
              <div style={{ marginTop: 16 }}>
                <Title level={5}>
                  <ThunderboltOutlined />
                  <Text strong>分析详情</Text>
                </Title>
                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={12}>
                    <Space>
                      <Text type="secondary">分析语言:</Text>
                      <Tag color="blue">{analysisResult.metadata.language}</Tag>
                    </Space>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Space>
                      <Text type="secondary">AST A:</Text>
                      <Tag>{analysisResult.metadata.ast_a_root_type}</Tag>
                    </Space>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Space>
                      <Text type="secondary">AST B:</Text>
                      <Tag>{analysisResult.metadata.ast_b_root_type}</Tag>
                    </Space>
                  </Col>
                  {analysisResult.metadata.filter_layer && (
                    <Col xs={24} sm={12}>
                      <Space>
                        <Text type="secondary">过滤层:</Text>
                        <Tag color="purple">{analysisResult.metadata.filter_layer}</Tag>
                      </Space>
                    </Col>
                  )}
                </Row>
              </div>
            )}
          </div>
        )}

        {analysisResult && analysisResult.error && (
          <Alert
            title="分析错误"
            description={analysisResult.error}
            type="error"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>
    </div>
  );
};

export default CodeAnalyzer;