import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Tag, Space, Typography, Progress, Empty, Row, Col, Statistic, message, Alert } from 'antd';
import { BookOutlined, CheckCircleOutlined, WarningOutlined, FileTextOutlined, PlayCircleOutlined } from '@ant-design/icons';
import api from '../../api/client';
import '../../styles/global.css';

const { Title, Text, Paragraph } = Typography;

interface EthicsCase {
  id: number;
  title: string;
  category: string;
  description: string;
  scenario: string;
  outcome: string;
  consequences: string;
  prevention: string;
  is_active: boolean;
  created_at: string;
}

interface LearningProgress {
  total_cases: number;
  completed_count: number;
  progress_percentage: number;
  completed_cases: number[];
}

const EthicsLearning: React.FC = () => {
  const [cases, setCases] = useState<EthicsCase[]>([]);
  const [progress, setProgress] = useState<LearningProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedCase, setSelectedCase] = useState<EthicsCase | null>(null);

  useEffect(() => {
    fetchCases();
    fetchProgress();
  }, []);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const response = await api.get('/ethics-cases/');
      setCases(response.data);
    } catch (error) {
      message.error('获取案例失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchProgress = async () => {
    try {
      const response = await api.get('/ethics-cases/learning/progress');
      setProgress(response.data);
    } catch (error) {
      console.error('获取学习进度失败', error);
    }
  };

  const handleViewDetail = (caseItem: EthicsCase) => {
    setSelectedCase(caseItem);
    setDetailModalOpen(true);
  };

  const handleMarkComplete = async (caseId: number) => {
    try {
      const response = await api.post(`/ethics-cases/${caseId}/complete`);
      if (response.data.message && response.data.message.includes('全部完成')) {
        message.success(response.data.message);
      } else {
        message.info(response.data.message || '已标记为完成');
      }
      fetchProgress();
      setDetailModalOpen(false);
      window.location.reload();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const getCategoryColor = (category: string) => {
    const colors: { [key: string]: string } = {
      'plagiarism': 'red',
      'fair_use': 'orange',
      'attribution': 'blue',
      'collaboration': 'green',
      'other': 'default',
    };
    return colors[category] || 'default';
  };

  const getCategoryText = (category: string) => {
    const texts: { [key: string]: string } = {
      'plagiarism': '抄袭',
      'fair_use': '合理使用',
      'attribution': '署名',
      'collaboration': '协作',
      'other': '其他',
    };
    return texts[category] || category;
  };

  const isCompleted = (caseId: number) => {
    return progress?.completed_cases.includes(caseId) || false;
  };

  const columns = [
    {
      title: '状态',
      key: 'status',
      width: 80,
      render: (_: any, record: EthicsCase) => (
        isCompleted(record.id) ? (
          <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
        ) : (
          <WarningOutlined style={{ color: '#faad14', fontSize: 20 }} />
        )
      ),
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string) => (
        <Tag color={getCategoryColor(category)}>{getCategoryText(category)}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: EthicsCase) => (
        <Space>
          <Button
            type="link"
            icon={<FileTextOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            查看详情
          </Button>
          {isCompleted(record.id) ? (
            <Tag color="success">已完成</Tag>
          ) : (
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => handleMarkComplete(record.id)}
            >
              完成学习
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3}>
          <BookOutlined /> 编程伦理学习
        </Title>
        <Text type="secondary">
          学习编程伦理和学术诚信案例，了解代码相似度检测的意义和学术规范。
        </Text>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="总案例数"
              value={progress?.total_cases || 0}
              prefix={<BookOutlined />}
              valueStyle={{ color: '#3b82f6' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="已完成"
              value={progress?.completed_count || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="学习进度"
              value={progress?.progress_percentage || 0}
              suffix="%"
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="案例列表">
        <Table
          columns={columns}
          dataSource={cases}
          rowKey="id"
          loading={loading}
          locale={{ emptyText: <Empty description="暂无案例" /> }}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={selectedCase?.title}
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            关闭
          </Button>,
          selectedCase && !isCompleted(selectedCase.id) && (
            <Button key="complete" type="primary" onClick={() => handleMarkComplete(selectedCase.id)}>
              完成学习
            </Button>
          ),
        ]}
        width={700}
      >
        {selectedCase && (
          <div>
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={24}>
                <Tag color={getCategoryColor(selectedCase.category)} style={{ fontSize: 14, padding: '4px 12px' }}>
                  {getCategoryText(selectedCase.category)}
                </Tag>
              </Col>
            </Row>

            <Card size="small" title="案例描述" style={{ marginBottom: 16 }}>
              <Paragraph>{selectedCase.description}</Paragraph>
            </Card>

            <Card size="small" title="场景" style={{ marginBottom: 16 }}>
              <Paragraph>{selectedCase.scenario}</Paragraph>
            </Card>

            <Card size="small" title="结果" style={{ marginBottom: 16 }}>
              <Paragraph>{selectedCase.outcome}</Paragraph>
            </Card>

            <Card size="small" title="后果" style={{ marginBottom: 16 }}>
              <Paragraph type="danger">{selectedCase.consequences}</Paragraph>
            </Card>

            <Card size="small" title="预防措施">
              <Paragraph type="success">{selectedCase.prevention}</Paragraph>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default EthicsLearning;