import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Button, Tag, Spin, message, Typography, Space } from 'antd';
import api from '../../api/client';
import dayjs from 'dayjs';
import { FileTextOutlined, CalendarOutlined, CodeOutlined, ArrowLeftOutlined, UploadOutlined, FileSearchOutlined } from '@ant-design/icons';
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

const StudentAssignmentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const response = await api.get(`/assignments/${id}`);
        setAssignment(response.data);
      } catch (error) {
        message.error('获取作业详情失败');
        navigate('/student/assignments');
      } finally {
        setLoading(false);
      }
    };
    if (id) fetchDetail();
  }, [id, navigate]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '50px auto' }} />;
  if (!assignment) return <div>作业不存在</div>;

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

  return (
    <div className="page-fade-in">
      <Title level={4} className="page-title-light">
        <FileTextOutlined className="page-title-icon-light" />
        作业详情
      </Title>
        <Descriptions column={1} bordered>
          <Descriptions.Item label="标题" labelStyle={{ color: '#64748b' }} contentStyle={{ color: '#1e293b' }}>
            <strong style={{ color: '#1e293b' }}>{assignment.title}</strong>
          </Descriptions.Item>
          <Descriptions.Item label="描述" labelStyle={{ color: '#64748b' }} contentStyle={{ color: '#334155' }}>
            <span style={{ color: '#64748b' }}>{assignment.description}</span>
          </Descriptions.Item>
          <Descriptions.Item label="编程语言" labelStyle={{ color: '#64748b' }} contentStyle={{ color: '#334155' }}>
            <Tag color={getLanguageColor(assignment.language)} icon={<CodeOutlined />}>
              {assignment.language}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="截止时间" labelStyle={{ color: '#64748b' }} contentStyle={{ color: '#334155' }}>
            <span style={{ color: '#64748b' }}>
              <CalendarOutlined style={{ marginRight: 4 }} />
              {dayjs(assignment.deadline).format('YYYY-MM-DD HH:mm')}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间" labelStyle={{ color: '#64748b' }} contentStyle={{ color: '#334155' }}>
            <span style={{ color: '#64748b' }}>
              {dayjs(assignment.created_at).format('YYYY-MM-DD HH:mm')}
            </span>
          </Descriptions.Item>
        </Descriptions>
        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Space>
            <Button 
              type="primary" 
              onClick={() => navigate(`/student/submit/${assignment.id}`)}
              className="btn-primary-light"
              icon={<UploadOutlined />}
            >
              提交作业
            </Button>
            <Button 
              onClick={() => navigate(`/student/submissions?assignment_id=${assignment.id}`)}
              className="btn-ghost-light"
              icon={<FileSearchOutlined />}
            >
              我的提交（本作业）
            </Button>
            <Button 
              onClick={() => navigate('/student/assignments')}
              className="btn-ghost"
              icon={<ArrowLeftOutlined />}
            >
              返回列表
            </Button>
          </Space>
        </div>
    </div>
  );
};

export default StudentAssignmentDetail;