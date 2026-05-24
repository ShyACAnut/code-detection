import React, { useState, useEffect } from 'react';
import { Form, Input, DatePicker, Select, Button, Table, message, Space, Popconfirm, Tag, Typography, Divider, Card } from 'antd';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import dayjs from 'dayjs';
import { FileAddOutlined, FileTextOutlined, CalendarOutlined, CodeOutlined, DeleteOutlined, EyeOutlined, PlayCircleOutlined } from '@ant-design/icons';
import '../../styles/global.css';

const { TextArea } = Input;
const { Option } = Select;
const { Title } = Typography;

interface Assignment {
  id: number;
  title: string;
  description: string;
  language: string;
  deadline: string;
  created_at: string;
  detection_threshold?: number;
}

const TeacherAssignments: React.FC = () => {
  const [form] = Form.useForm();
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchAnalyzing, setBatchAnalyzing] = useState(false);
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

  const onFinish = async (values: any) => {
    setSubmitting(true);
    try {
      const payload = {
        title: values.title,
        description: values.description,
        language: values.language,
        deadline: values.deadline.toISOString(),
        function_requirements: values.functionRequirements,
        scoring_guideline: values.scoringGuideline,
        detection_threshold: values.detectionThreshold || 80,
      };
      await api.post('/assignments', payload);
      message.success('作业创建成功');
      form.resetFields();
      fetchAssignments();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '创建失败');
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assignments/${id}`);
      message.success('删除成功');
      fetchAssignments();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  const viewSubmissions = (assignmentId: number) => {
    navigate(`/teacher/assignments/${assignmentId}`);
  };

  const handleBatchAnalyze = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要检测的作业');
      return;
    }
    setBatchAnalyzing(true);
    try {
      navigate('/teacher/batch-analyze', {
        state: { selectedAssignmentIds: selectedRowKeys }
      });
    } catch (error) {
      message.error('跳转失败');
      console.error(error);
    } finally {
      setBatchAnalyzing(false);
    }
  };

  const goToAnalyzePage = (assignmentId: number) => {
    navigate(`/teacher/assignments/${assignmentId}`);
  };

  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
  };

  const getLanguageTagStyle = (lang: string) => {
    if (lang === 'python') {
      return { background: '#dbeafe', color: '#1d4ed8', border: '1px solid #93c5fd' };
    }
    if (lang === 'java') {
      return { background: '#ffedd5', color: '#c2410c', border: '1px solid #fed7aa' };
    }
    if (lang === 'go') {
      return { background: '#ccfbf1', color: '#0d9488', border: '1px solid #99f6e4' };
    }
    return { background: '#f1f5f9', color: '#475569', border: '1px solid #cbd5e1' };
  };

  const columns = [
    {
      title: <span className="table-header-text-light">标题</span>,
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <span className="table-cell-primary-light">{text}</span>,
    },
    {
      title: <span className="table-header-text-light">语言</span>,
      dataIndex: 'language',
      key: 'language',
      render: (lang: string) => (
        <Tag style={getLanguageTagStyle(lang)} icon={<CodeOutlined />}>
          {lang}
        </Tag>
      ),
    },
    {
      title: <span className="table-header-text-light">检测阈值</span>,
      dataIndex: 'detection_threshold',
      key: 'detection_threshold',
      render: (threshold: number) => (
        <span className="table-cell-secondary-light">
          {threshold || 80}%
        </span>
      ),
    },
    {
      title: <span className="table-header-text-light">截止时间</span>,
      dataIndex: 'deadline',
      key: 'deadline',
      render: (text: string) => (
        <span className="table-cell-secondary-light">
          <CalendarOutlined style={{ marginRight: 4 }} />
          {dayjs(text).format('YYYY-MM-DD HH:mm')}
        </span>
      ),
    },
    {
      title: <span className="table-header-text-light">创建时间</span>,
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => (
        <span className="table-cell-secondary-light">
          {dayjs(text).format('YYYY-MM-DD HH:mm')}
        </span>
      ),
    },
    {
      title: <span className="table-header-text-light">操作</span>,
      key: 'action',
      render: (_: any, record: Assignment) => (
        <Space>
          <Button
            type="link"
            onClick={() => viewSubmissions(record.id)}
            icon={<EyeOutlined />}
            style={{ color: '#3b82f6' }}
          >
            查看提交
          </Button>
          <Button
            type="link"
            onClick={() => goToAnalyzePage(record.id)}
            icon={<PlayCircleOutlined />}
            style={{ color: '#22c55e' }}
          >
            立即检测
          </Button>
          <Popconfirm
            title="确定删除该作业吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="page-fade-in">
      <Card className="glass-surface-light">
        <Title level={4} className="page-title-light">
          <FileAddOutlined className="page-title-icon-light" />
          创建新作业
        </Title>
        <Form
          form={form}
          onFinish={onFinish}
          layout="vertical"
          style={{ maxWidth: 600 }}
        >
          <Form.Item
            name="title"
            label={<span style={{ color: '#334155' }}>作业标题</span>}
            rules={[{ required: true, message: '请输入作业标题' }]}
          >
            <Input placeholder="例如：第三次作业 - 排序算法" />
          </Form.Item>

          <Form.Item name="description" label={<span style={{ color: '#334155' }}>作业描述</span>}>
            <TextArea rows={4} placeholder="描述作业要求、注意事项等" />
          </Form.Item>

          <Form.Item
            name="language"
            label={<span style={{ color: '#334155' }}>编程语言</span>}
            rules={[{ required: true, message: '请选择编程语言' }]}
          >
            <Select placeholder="请选择">
              <Option value="python">Python</Option>
              <Option value="java">Java</Option>
              <Option value="javascript">JavaScript</Option>
              <Option value="c">C</Option>
              <Option value="cpp">C/C++</Option>
              <Option value="csharp">C#</Option>
              <Option value="go">Go</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="deadline"
            label={<span style={{ color: '#334155' }}>截止时间</span>}
            rules={[{ required: true, message: '请选择截止时间' }]}
          >
            <DatePicker
              showTime
              format="YYYY-MM-DD HH:mm:ss"
              style={{ width: '100%' }}
              placeholder="选择日期和时间"
            />
          </Form.Item>

          <Form.Item name="functionRequirements" label={<span style={{ color: '#334155' }}>功能需求</span>}>
            <TextArea 
              rows={4} 
              placeholder="详细描述需要实现的功能，例如：实现排序算法，包括冒泡排序、快速排序等" 
            />
          </Form.Item>

          <Form.Item name="scoringGuideline" label={<span style={{ color: '#334155' }}>评分指南</span>}>
            <TextArea 
              rows={4} 
              placeholder="说明评分标准，例如：功能实现占 70%，代码风格占 20%，创新性占 10%" 
            />
          </Form.Item>

          <Form.Item 
            name="detectionThreshold" 
            label={<span style={{ color: '#334155' }}>检测阈值 (%)</span>}
            initialValue={80}
          >
            <Input 
              type="number" 
              min={0} 
              max={100} 
              placeholder="默认80%" 
              style={{ width: 150 }}
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting} className="btn-primary-light">
              创建作业
            </Button>
          </Form.Item>
        </Form>

        <Divider style={{ borderColor: '#e2e8f0' }} />

        <Title level={4} className="page-title-light">
          <FileTextOutlined className="page-title-icon-light" />
          已发布作业
        </Title>

        {selectedRowKeys.length > 0 && (
          <div style={{ marginBottom: 16, padding: '12px 16px', backgroundColor: 'rgba(59,130,246,0.1)', borderRadius: 8, border: '1px solid rgba(59,130,246,0.2)' }}>
            <Space>
              <span style={{ color: '#1e293b', fontWeight: 500 }}>已选择 {selectedRowKeys.length} 个作业</span>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleBatchAnalyze}
                loading={batchAnalyzing}
                className="btn-primary-light"
              >
                批量检测选中作业
              </Button>
              <Button onClick={() => setSelectedRowKeys([])} className="btn-ghost-light">
                取消选择
              </Button>
            </Space>
          </div>
        )}

        <Table
          dataSource={assignments}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          rowSelection={rowSelection}
          className="light-table optimized-light-table"
        />
      </Card>
    </div>
  );
};

export default TeacherAssignments;
