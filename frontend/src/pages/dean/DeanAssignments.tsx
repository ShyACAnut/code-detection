import React, { useState, useEffect } from 'react';
import { Table, message, Space, Tag, Card, Typography, Divider, Statistic, Row, Col, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import dayjs from 'dayjs';
import { FileTextOutlined, CalendarOutlined, CodeOutlined, EyeOutlined, TeamOutlined, FileOutlined } from '@ant-design/icons';
import '../../styles/Dashboard.css';

const { Title } = Typography;

interface Assignment {
  id: number;
  title: string;
  description: string;
  language: string;
  deadline: string;
  created_at: string;
  created_by?: number;
  creator_name?: string;
  submission_count?: number;
}

const DeanAssignments: React.FC = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const fetchAssignments = async () => {
    setLoading(true);
    try {
      const res = await api.get('/assignments');
      setAssignments(res.data);
    } catch (error) {
      message.error('获取作业列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssignments();
  }, []);

  const viewSubmissions = (assignmentId: number) => {
    navigate(`/dean/assignments/${assignmentId}`);
  };

  const getLanguageColor = (lang: string) => {
    const colors: { [key: string]: string } = {
      python: '#dbeafe',
      java: '#ffedd5',
      javascript: '#fef3c7',
      c: '#d1fae5',
      cpp: '#cffafe',
      csharp: '#f5d0fe',
      go: '#ccfbf1',
    };
    return colors[lang] || '#f1f5f9';
  };

  const getLanguageTextColor = (lang: string) => {
    const colors: { [key: string]: string } = {
      python: '#1d4ed8',
      java: '#c2410c',
      javascript: '#b45309',
      c: '#065f46',
      cpp: '#0e7490',
      csharp: '#7c3aed',
      go: '#0d9488',
    };
    return colors[lang] || '#64748b';
  };

  const getLanguageBorderColor = (lang: string) => {
    const colors: { [key: string]: string } = {
      python: '#93c5fd',
      java: '#fed7aa',
      javascript: '#fde68a',
      c: '#a7f3d0',
      cpp: '#67e8f9',
      csharp: '#d8b4fe',
      go: '#99f6e4',
    };
    return colors[lang] || '#cbd5e1';
  };

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <strong style={{ color: '#1e293b' }}>{text}</strong>,
    },
    {
      title: '创建者',
      dataIndex: 'creator_name',
      key: 'creator_name',
      render: (text: string) => (
        <Tag 
          style={{ 
            background: '#f5d0fe',
            color: '#7c3aed',
            border: '1px solid #d8b4fe'
          }}
          icon={<TeamOutlined />}
        >
          {text || '未知'}
        </Tag>
      ),
    },
    {
      title: '语言',
      dataIndex: 'language',
      key: 'language',
      render: (lang: string) => (
        <Tag 
          style={{ 
            background: getLanguageColor(lang),
            color: getLanguageTextColor(lang),
            border: `1px solid ${getLanguageBorderColor(lang)}`
          }}
          icon={<CodeOutlined />}
        >
          {lang}
        </Tag>
      ),
    },
    {
      title: '提交数',
      dataIndex: 'submission_count',
      key: 'submission_count',
      render: (count: number) => (
        <Tag 
          style={{ 
            background: '#dbeafe',
            color: '#1d4ed8',
            border: '1px solid #93c5fd'
          }}
        >
          {count || 0} 人
        </Tag>
      ),
    },
    {
      title: '截止时间',
      dataIndex: 'deadline',
      key: 'deadline',
      render: (text: string) => (
        <span style={{ color: '#64748b' }}>
          <CalendarOutlined style={{ marginRight: 4 }} />
          {dayjs(text).format('YYYY-MM-DD HH:mm')}
        </span>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => (
        <span style={{ color: '#64748b' }}>
          {dayjs(text).format('YYYY-MM-DD HH:mm')}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Assignment) => (
        <Space>
          <Button 
          className="btn-link" 
          onClick={() => viewSubmissions(record.id)}
          icon={<EyeOutlined />}
        >
          查看提交
        </Button>
        </Space>
      ),
    },
  ];

  const getLanguageStats = () => {
    const stats: { [key: string]: number } = {};
    assignments.forEach(a => {
      stats[a.language] = (stats[a.language] || 0) + 1;
    });
    return stats;
  };

  const languageStats = getLanguageStats();

  return (
    <div>
      <Card className="glass-surface-light" style={{ borderRadius: '12px', padding: '24px', marginBottom: '24px' }}>
        <Title level={4} style={{ color: '#1e293b', marginBottom: '24px' }}>
          <TeamOutlined style={{ marginRight: '8px', color: '#3b82f6' }} />
          教学主任概览
        </Title>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6} md={6} lg={6}>
            <div style={{ 
              backgroundColor: '#ffffff', 
              borderRadius: '8px', 
              padding: '16px', 
              border: '1px solid #cbd5e1',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
              minHeight: '100px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                <FileOutlined style={{ color: '#667eea', fontSize: '18px', marginRight: '8px' }} />
                <span style={{ color: '#64748b', fontSize: '13px' }}>总作业数</span>
              </div>
              <span style={{ color: '#1e293b', fontSize: '28px', fontWeight: 700 }}>{assignments.length}</span>
            </div>
          </Col>
          {Object.entries(languageStats).slice(0, 3).map(([lang, count]) => (
            <Col xs={12} sm={6} md={6} lg={6} key={lang}>
              <div style={{ 
                backgroundColor: '#ffffff', 
                borderRadius: '8px', 
                padding: '16px', 
                border: '1px solid #cbd5e1',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
                minHeight: '100px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                  <CodeOutlined style={{ color: getLanguageTextColor(lang), fontSize: '18px', marginRight: '8px' }} />
                  <span style={{ color: '#64748b', fontSize: '13px' }}>{lang.toUpperCase()} 作业</span>
                </div>
                <span style={{ color: '#1e293b', fontSize: '28px', fontWeight: 700 }}>{count}</span>
              </div>
            </Col>
          ))}
        </Row>
      </Card>

      <Card className="glass-surface-light" style={{ borderRadius: '12px', padding: '24px' }}>
        <Title level={4} style={{ color: '#1e293b', marginBottom: '24px' }}>
          <FileTextOutlined style={{ marginRight: '8px', color: '#3b82f6' }} />
          所有已发布作业
        </Title>
        <Table
          dataSource={assignments}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          className="light-table"
        />
      </Card>
    </div>
  );
};

export default DeanAssignments;
