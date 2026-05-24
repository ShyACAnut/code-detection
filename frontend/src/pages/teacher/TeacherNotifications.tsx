import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message, Popconfirm, Badge, Alert } from 'antd';
import { BellOutlined, SendOutlined, DeleteOutlined, EyeOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import api from '../../api/client';
import '../../styles/global.css';

const { Title, Text } = Typography;
const { TextArea } = Input;
const { Option } = Select;

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
  student_name?: string;
  assignment_title?: string;
}

interface Student {
  id: number;
  username: string;
  email: string;
}

interface Assignment {
  id: number;
  title: string;
}

const TeacherNotifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState<Notification | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchNotifications();
    fetchStudents();
    fetchAssignments();
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

  const fetchStudents = async () => {
    try {
      const response = await api.get('/notifications/students');
      setStudents(response.data);
    } catch (error) {
      console.error('获取学生列表失败', error);
    }
  };

  const fetchAssignments = async () => {
    try {
      const response = await api.get('/assignments');
      setAssignments(response.data);
    } catch (error) {
      console.error('获取作业列表失败', error);
    }
  };

  const handleCreate = async (values: any) => {
    try {
      await api.post('/notifications', {
        student_id: values.student_id,
        assignment_id: values.assignment_id,
        title: values.title,
        content: values.content,
        similarity_score: values.similarity_score || null,
        priority: values.priority || 'normal',
      });
      message.success('通知发送成功');
      setCreateModalOpen(false);
      form.resetFields();
      fetchNotifications();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '发送失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/notifications/${id}`);
      message.success('删除成功');
      fetchNotifications();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  const handleViewDetail = (notification: Notification) => {
    setSelectedNotification(notification);
    setDetailModalOpen(true);
  };

  const handleMarkAsRead = async (id: number) => {
    try {
      await api.put(`/notifications/${id}`, { is_read: true });
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

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: Notification) => (
        <Space>
          {!record.is_read && <Badge status="error" />}
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: '学生',
      dataIndex: 'student_id',
      key: 'student_id',
      render: (id: number) => students.find(s => s.id === id)?.username || `学生 #${id}`,
    },
    {
      title: '作业',
      dataIndex: 'assignment_id',
      key: 'assignment_id',
      render: (id: number) => assignments.find(a => a.id === id)?.title || `作业 #${id}`,
    },
    {
      title: '相似度',
      dataIndex: 'similarity_score',
      key: 'similarity_score',
      render: (score: number | null) => score !== null ? `${score.toFixed(1)}%` : '-',
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)}>{getPriorityText(priority)}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_read',
      key: 'is_read',
      render: (isRead: boolean) => (
        <Tag color={isRead ? 'green' : 'default'}>
          {isRead ? '已读' : '未读'}
        </Tag>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Notification) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
            查看
          </Button>
          <Popconfirm
            title="确定删除此通知？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
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
            整改通知管理
          </Title>
          <Button
            type="primary"
            icon={<SendOutlined />}
            className="btn-primary"
            onClick={() => setCreateModalOpen(true)}
          >
            发送通知
          </Button>
        </div>

        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="整改通知功能"
          description="通过此功能，教师可以向学生发送代码整改通知，告知学生其代码存在相似度问题并要求整改。"
        />

        <Table
          dataSource={notifications}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />

        {/* 创建通知弹窗 */}
        <Modal
          title="发送整改通知"
          open={createModalOpen}
          onCancel={() => {
            setCreateModalOpen(false);
            form.resetFields();
          }}
          footer={null}
          width={600}
        >
          <Form form={form} layout="vertical" onFinish={handleCreate}>
            <Form.Item
              name="student_id"
              label="选择学生"
              rules={[{ required: true, message: '请选择学生' }]}
            >
              <Select placeholder="请选择学生">
                {students.map(student => (
                  <Option key={student.id} value={student.id}>
                    {student.username} ({student.email})
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="assignment_id"
              label="关联作业"
              rules={[{ required: true, message: '请选择作业' }]}
            >
              <Select placeholder="请选择作业">
                {assignments.map(assignment => (
                  <Option key={assignment.id} value={assignment.id}>
                    {assignment.title}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="title"
              label="通知标题"
              rules={[{ required: true, message: '请输入通知标题' }]}
            >
              <Input placeholder="如：作业整改通知" />
            </Form.Item>

            <Form.Item
              name="content"
              label="通知内容"
              rules={[{ required: true, message: '请输入通知内容' }]}
            >
              <TextArea rows={4} placeholder="请输入通知内容，说明整改要求..." />
            </Form.Item>

            <Form.Item name="similarity_score" label="相似度分数（可选）">
              <Input type="number" min={0} max={100} placeholder="如：85" />
            </Form.Item>

            <Form.Item name="priority" label="优先级" initialValue="normal">
              <Select>
                <Option value="low">低</Option>
                <Option value="normal">普通</Option>
                <Option value="high">紧急</Option>
              </Select>
            </Form.Item>

            <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
              <Space>
                <Button onClick={() => {
                  setCreateModalOpen(false);
                  form.resetFields();
                }}>
                  取消
                </Button>
                <Button type="primary" htmlType="submit" className="btn-primary">
                  发送通知
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>

        {/* 通知详情弹窗 */}
        <Modal
          title="通知详情"
          open={detailModalOpen}
          onCancel={() => {
            setDetailModalOpen(false);
            setSelectedNotification(null);
          }}
          footer={
            selectedNotification && !selectedNotification.is_read ? (
              <Button type="primary" onClick={() => handleMarkAsRead(selectedNotification.id)}>
                标记为已读
              </Button>
            ) : null
          }
          width={600}
        >
          {selectedNotification && (
            <div>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">标题：</Text>
                <Text strong style={{ marginLeft: 8 }}>{selectedNotification.title}</Text>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">学生：</Text>
                <Text style={{ marginLeft: 8 }}>
                  {students.find(s => s.id === selectedNotification.student_id)?.username || `学生 #${selectedNotification.student_id}`}
                </Text>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">作业：</Text>
                <Text style={{ marginLeft: 8 }}>
                  {assignments.find(a => a.id === selectedNotification.assignment_id)?.title || `作业 #${selectedNotification.assignment_id}`}
                </Text>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">相似度：</Text>
                <Text style={{ marginLeft: 8 }}>
                  {selectedNotification.similarity_score !== null ? `${selectedNotification.similarity_score.toFixed(1)}%` : '-'}
                </Text>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">优先级：</Text>
                <Tag color={getPriorityColor(selectedNotification.priority)} style={{ marginLeft: 8 }}>
                  {getPriorityText(selectedNotification.priority)}
                </Tag>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">状态：</Text>
                <Tag color={selectedNotification.is_read ? 'green' : 'default'} style={{ marginLeft: 8 }}>
                  {selectedNotification.is_read ? '已读' : '未读'}
                </Tag>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">时间：</Text>
                <Text style={{ marginLeft: 8 }}>{selectedNotification.created_at}</Text>
              </div>
              <div style={{ marginTop: 16, padding: 12, backgroundColor: '#f8fafc', borderRadius: 8 }}>
                <Text type="secondary">通知内容：</Text>
                <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{selectedNotification.content}</div>
              </div>
            </div>
          )}
        </Modal>
      </Card>
    </div>
  );
};

export default TeacherNotifications;