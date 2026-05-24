import React, { useState, useEffect } from 'react';
import { Card, Button, Table, Form, Input, message, Space, Tag, Typography, Modal, Upload, Alert } from 'antd';
import { UploadOutlined, FileTextOutlined, DashOutlined, DownloadOutlined, EyeOutlined } from '@ant-design/icons';
import api from '../../api/client';
import '../../styles/global.css';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface CodeLibraryItem {
  id: number;
  filename: string;
  language: string;
  file_size: number;
  uploaded_at: string;
  is_public: boolean;
}

const CodeLibrary: React.FC = () => {
  const [library, setLibrary] = useState<CodeLibraryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [previewTitle, setPreviewTitle] = useState('');
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  useEffect(() => {
    fetchLibrary();
  }, []);

  const fetchLibrary = async () => {
    setLoading(true);
    try {
      const response = await api.get('/admin/code-library');
      setLibrary(response.data);
    } catch (error) {
      message.error('加载代码库失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (file: any) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      await api.post('/admin/code-library/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      message.success('文件上传成功');
      fetchLibrary();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await api.delete(`/admin/code-library/${deleteId}`);
      message.success('删除成功');
      setLibrary(prev => prev.filter(item => item.id !== deleteId));
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败');
    } finally {
      setDeleteConfirmOpen(false);
      setDeleteId(null);
    }
  };

  const handlePreview = async (id: number) => {
    try {
      const response = await api.get(`/admin/code-library/${id}/content`);
      setPreviewContent(response.data.content);
      const item = library.find(i => i.id === id);
      setPreviewTitle(item?.filename || '代码预览');
      setPreviewOpen(true);
    } catch (error) {
      message.error('获取代码内容失败');
    }
  };

  const handleDownload = async (id: number) => {
    try {
      const response = await api.get(`/admin/code-library/${id}/download`, {
        responseType: 'blob',
      });
      const item = library.find(i => i.id === id);
      const blob = new Blob([response.data], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = item?.filename || `code_${id}.txt`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (error) {
      message.error('下载失败');
    }
  };

  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '语言',
      dataIndex: 'language',
      key: 'language',
      render: (lang: string) => (
        <Tag color={getLanguageColor(lang)}>{lang}</Tag>
      ),
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => formatFileSize(size),
    },
    {
      title: '状态',
      dataIndex: 'is_public',
      key: 'is_public',
      render: (isPublic: boolean) => (
        <Tag color={isPublic ? 'green' : 'default'}>
          {isPublic ? '公开' : '私有'}
        </Tag>
      ),
    },
    {
      title: '上传时间',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: CodeLibraryItem) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record.id)}
          >
            预览
          </Button>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record.id)}
          >
            下载
          </Button>
          <Button
            size="small"
            danger
            icon={<DashOutlined />}
            onClick={() => {
              setDeleteId(record.id);
              setDeleteConfirmOpen(true);
            }}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const getLanguageColor = (lang: string) => {
    const colors: { [key: string]: string } = {
      python: 'blue',
      java: 'orange',
      javascript: 'yellow',
      go: 'cyan',
      cpp: 'red',
      c: 'purple',
      csharp: 'purple',
    };
    return colors[lang] || 'default';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="page-fade-in">
      <Card className="content-card">
        <Title level={4} className="page-title">
          <FileTextOutlined className="page-title-icon" />
          代码库管理
        </Title>

        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
          message="代码库管理功能说明"
          description="管理系统代码库，用于代码相似度检测的比对参考。支持上传、查看、下载和删除操作。代码库中的代码将作为比对基准，帮助检测学生提交的相似度。"
        />

        <div style={{ marginBottom: 16 }}>
          <Upload
            accept=".py,.java,.js,.go,.cpp,.c,.cs"
            beforeUpload={(file) => {
              handleUpload(file);
              return false;
            }}
            fileList={[]}
          >
            <Button
              type="primary"
              loading={uploading}
              icon={<UploadOutlined />}
              className="btn-primary"
            >
              上传代码文件
            </Button>
          </Upload>
          <Text type="secondary" style={{ marginLeft: 12 }}>
            支持: .py .java .js .go .cpp .c .cs
          </Text>
        </div>

        <Table
          dataSource={library}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无代码库文件' }}
        />

        {/* 预览弹窗 */}
        <Modal
          title={previewTitle}
          open={previewOpen}
          onCancel={() => setPreviewOpen(false)}
          footer={null}
          width={900}
        >
          <pre style={{ maxHeight: 500, overflow: 'auto', background: '#f5f5f5', padding: 12 }}>
            {previewContent || '无内容'}
          </pre>
        </Modal>

        {/* 删除确认弹窗 */}
        <Modal
          title="确认删除"
          open={deleteConfirmOpen}
          onCancel={() => setDeleteConfirmOpen(false)}
          onOk={handleDelete}
          okText="确认删除"
          cancelText="取消"
          okType="danger"
        >
          <p>确定要删除该代码文件吗？此操作不可撤销。</p>
        </Modal>
      </Card>
    </div>
  );
};

export default CodeLibrary;