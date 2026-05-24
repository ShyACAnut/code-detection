import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Tag, Space, Typography, message, Badge, Empty } from 'antd';
import { BellOutlined, CheckOutlined, FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import '../../styles/global.css';

const { Title, Text } = Typography;

interface Notification {
  id: number;
  student_id: number;
  teacher_id: number;
  assignment_id: number;
  title: string;
  content: string;
  similarity_score: number | null;
  priority: string;
  is_read: boolean;
  created_at: string;
  teacher_name?: string;
}

const StudentNotifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const response = await api.get('/notifications');
      setNotifications(response.data);
    } catch (error) {
      message.error('获取通知列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsRead = async (id: number) => {
    try {
      await api.put(`/notifications/${id}`, { is_read: true });
      fetchNotifications();
    } catch (error) {
      message.error('更新状态失败');
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      const unreadIds = notifications.filter(n => !n.is_read).map(n => n.id);
      await Promise.all(
        unreadIds.map(id => api.put(`/notifications/${id}`, { is_read: true }))
      );
      message.success('全部标记为已读');
      fetchNotifications();
    } catch (error) {
      message.error('更新状态失败');
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'red';
      case 'low': return 'green';
      default: return 'orange';
    }
  };

  const getPriorityText = (priority: string) => {
    switch (priority) {
      case 'high': return '紧急';
      case 'low': return '低';
      default: return '普通';
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const columns = [
    {
      title: '状态',
      key: 'status',
      width: 80,
      render: (_: any, record: Notification) => (
        !record.is_read ? <Badge status="processing" /> : <CheckOutlined style={{ color: '#52c41a' }} />
      ),
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: Notification) => (
        <Text strong style={{ color: record.is_read ? '#666' : '#1e293b' }}>{text}</Text>
      ),
    },
    {
      title: '相似度',
      dataIndex: 'similarity_score',
      key: 'similarity_score',
      width: 100,
      render: (score: number | null) => score !== null ? (
        <Tag color={score >= 80 ? 'red' : score >= 50 ? 'orange' : 'green'}>
          {score.toFixed(1)}%
        </Tag>
      ) : '-',
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)}>{getPriorityText(priority)}</Tag>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: Notification) => (
        <Space>
          <Button
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => navigate(`/student/assignments/${record.assignment_id}`)}
          >
            查看作业
          </Button>
          {!record.is_read && (
            <Button
              size="small"
              type="link"
              onClick={() => handleMarkAsRead(record.id)}
            >
              已读
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="page-fade-in">
      <Card className="content-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={4} className="page-title" style={{ margin: 0 }}>
            <BellOutlined className="page-title-icon" />
            我的通知
            {unreadCount > 0 && (
              <Badge count={unreadCount} style={{ marginLeft: 8 }} />
            )}
          </Title>
          {unreadCount > 0 && (
            <Button
              icon={<CheckOutlined />}
              onClick={handleMarkAllAsRead}
              className="btn-ghost"
            >
              全部标记为已读
            </Button>
          )}
        </div>

        {notifications.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无通知"
          />
        ) : (
          <Table
            dataSource={notifications}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
            rowClassName={(record) => record.is_read ? 'read-notification' : 'unread-notification'}
          />
        )}
      </Card>

      <style>{`
        .unread-notification {
          background-color: #f0f9ff;
        }
        .unread-notification:hover {
          background-color: #e0f2fe !important;
        }
        .read-notification {
          background-color: #ffffff;
        }
      `}</style>
    </div>
  );
};

export default StudentNotifications;