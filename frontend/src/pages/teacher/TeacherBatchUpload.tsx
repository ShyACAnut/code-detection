import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Select, Upload, Button, message, Alert, Card, Typography, Space } from 'antd';
import { UploadOutlined, FileZipOutlined, InboxOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import api from '../../api/client';
import '../../styles/global.css';

const { Option } = Select;
const { Title, Text } = Typography;

interface Assignment {
  id: number;
  title: string;
}

const TeacherBatchUpload: React.FC = () => {
  const navigate = useNavigate();
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selectedAssignment, setSelectedAssignment] = useState<number | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchAssignments();
  }, []);

  const fetchAssignments = async () => {
    try {
      const res = await api.get<Assignment[]>('/assignments');
      setAssignments(res.data);
    } catch {
      message.error('加载作业列表失败');
    }
  };

  const handleUpload = async () => {
    if (!selectedAssignment) {
      message.warning('请先选择作业');
      return;
    }
    if (!file) {
      message.warning('请选择ZIP文件');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    try {
      const res = await api.post(`/assignments/${selectedAssignment}/import-zip`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      message.success(res.data.message || `已导入 ${res.data.files_imported} 个文件`);
      navigate(`/teacher/assignments/${selectedAssignment}`);
    } catch (e: any) {
      message.error(e.response?.data?.detail || '导入失败');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="page-fade-in">
      <Card className="content-card">
        <Title level={4} className="page-title">
          <FileZipOutlined className="page-title-icon" />
          批量导入 ZIP（写入作业提交）
        </Title>
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
          message="使用说明"
          description="请先创建作业，再选择 ZIP。系统会将压缩包内的代码文件按顺序分配给学生账号并写入 submissions，随后在作业详情页发起「一键批量检测」。支持的语言: Python(.py)、Java(.java)、Go(.go)、JavaScript(.js)、C(.c)、C++(.cpp/.cc/.cxx)、C#(.cs)"
        />
        <Space orientation="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ display: 'block', marginBottom: 8, color: '#334155' }}>
              选择作业
            </Text>
            <Select
              placeholder="请选择作业"
              style={{ width: '100%', maxWidth: 400 }}
              value={selectedAssignment ?? undefined}
              onChange={(val) => setSelectedAssignment(val)}
            >
              {assignments.map((a) => (
                <Option key={a.id} value={a.id}>
                  {a.title}
                </Option>
              ))}
            </Select>
          </div>
          <div>
            <Text strong style={{ display: 'block', marginBottom: 8, color: '#e2e8f0' }}>
              上传ZIP文件
            </Text>
            <Upload beforeUpload={(f) => { setFile(f); return false; }} accept=".zip">
              <Button icon={<UploadOutlined />} className="btn-primary">
                选择ZIP文件
              </Button>
            </Upload>
            {file && (
              <Text type="secondary" style={{ display: 'block', marginTop: 8, color: '#94a3b8' }}>
                已选择: {file.name}
              </Text>
            )}
          </div>
          <Space>
            <Button 
              onClick={handleUpload} 
              loading={uploading} 
              disabled={!selectedAssignment || !file}
              className="btn-primary"
            >
              导入并跳转到作业详情
            </Button>
            <Button onClick={() => navigate('/teacher/assignments')} icon={<ArrowLeftOutlined />} className="btn-ghost">
              返回作业列表
            </Button>
          </Space>
        </Space>
      </Card>
    </div>
  );
};

export default TeacherBatchUpload;
