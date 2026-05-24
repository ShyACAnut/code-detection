import React, { useEffect, useState } from 'react';
import { Table, Button, message, Space, Tag, Typography, Empty, Card } from 'antd';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import dayjs from 'dayjs';
import { FileTextOutlined, CalendarOutlined, CodeOutlined, EyeOutlined, SendOutlined } from '@ant-design/icons';
import '../../styles/global.css';

const { Title } = Typography;

interface Assignment {
  id: number;
  title: string;
  description: string;
  language: string;
  deadline: string;
  created_at: string;
}

const StudentAssignments: React.FC = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const fetchAssignments = async () => {
    setLoading(true);
    try {
      const response = await api.get('/assignments/');
      setAssignments(response.data);
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

  const handleSubmit = (assignmentId: number) => {
    navigate(`/student/submit/${assignmentId}`);
  };

  const handleViewDetail = (assignmentId: number) => {
    navigate(`/student/assignments/${assignmentId}`);
  };

  const getLanguageTag = (lang: string) => {
    const configs: { [key: string]: { bg: string; text: string; border: string } } = {
      python: { bg: '#dbeafe', text: '#1d4ed8', border: '#93c5fd' },
      java: { bg: '#ffedd5', text: '#c2410c', border: '#fed7aa' },
      javascript: { bg: '#fef9c3', text: '#a16207', border: '#fde047' },
      c: { bg: '#d1fae5', text: '#047857', border: '#a7f3d0' },
      cpp: { bg: '#cffafe', text: '#0e7490', border: '#a5f3fc' },
      csharp: { bg: '#ede9fe', text: '#6d28d9', border: '#ddd6fe' },
      go: { bg: '#ccfbf1', text: '#0d9488', border: '#99f6e4' },
    };
    const cfg = configs[lang] || { bg: '#f1f5f9', text: '#475569', border: '#cbd5e1' };
    return (
      <Tag
        style={{
          background: cfg.bg,
          color: cfg.text,
          border: `1px solid ${cfg.border}`,
          borderRadius: '8px',
          fontWeight: 500,
        }}
        icon={<CodeOutlined />}
      >
        {lang}
      </Tag>
    );
  };

  const columns = [
    {
      title: <span className="table-header-text-light">标题</span>,
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <span className="table-cell-primary-light">{text}</span>,
    },
    {
      title: <span className="table-header-text-light">描述</span>,
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => <span className="table-cell-secondary-light">{text}</span>,
    },
    {
      title: <span className="table-header-text-light">语言</span>,
      dataIndex: 'language',
      key: 'language',
      width: 120,
      render: (lang: string) => getLanguageTag(lang),
    },
    {
      title: <span className="table-header-text-light">截止时间</span>,
      dataIndex: 'deadline',
      key: 'deadline',
      width: 180,
      render: (text: string) => (
        <span className="table-cell-secondary-light">
          <CalendarOutlined style={{ marginRight: 6, opacity: 0.6 }} />
          {dayjs(text).format('YYYY-MM-DD HH:mm')}
        </span>
      ),
    },
    {
      title: <span className="table-header-text-light">操作</span>,
      key: 'action',
      width: 220,
      render: (_: any, record: Assignment) => (
        <Space>
          <Button
            className="btn-primary-light"
            icon={<SendOutlined />}
            onClick={() => handleSubmit(record.id)}
          >
            提交作业
          </Button>
          <Button
            className="btn-ghost-light"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record.id)}
          >
            详情
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="page-fade-in">
      <Card className="glass-surface-light">
        <Title level={4} className="page-title-light">
          <FileTextOutlined className="page-title-icon" />
          当前作业列表
        </Title>
        <Table
          dataSource={assignments}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          className="light-table optimized-light-table"
          locale={{
            emptyText: (
              <Empty
                description={<span style={{ color: '#64748b' }}>暂无作业</span>}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      </Card>
    </div>
  );
};

export default StudentAssignments;
