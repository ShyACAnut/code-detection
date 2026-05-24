import React, { useEffect, useState } from 'react';
import { Button, Card, Statistic, Row, Col, Table, Form, Input, InputNumber, message, Popconfirm, Space, Typography, Divider } from 'antd';
import { Routes, Route, useNavigate, Navigate, useLocation } from 'react-router-dom';
import { LogoutOutlined, UserOutlined, SettingOutlined, BarChartOutlined, FolderOpenOutlined, FileSearchOutlined } from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../api/client';
import GlassIcons from '../../components/GlassIcons/GlassIcons';
import MagicRings from '../../components/MagicRings';
import CodeLibrary from './CodeLibrary';
import AuditLogs from './AuditLogs';
import SystemSettings from './SystemSettings';

import '../../styles/Dashboard.css';

const { Title } = Typography;

interface AdminUser {
  id: number;
  username: string;
  email: string;
  role: string;
  created_at: string;
}

interface Stats {
  user_count: number;
  assignment_count: number;
  submission_count: number;
  comparison_count: number;
  avg_similarity: number | null;
}

interface SystemConfig {
  similarity_threshold: number;
  llm_model_name: string;
  updated_at?: string;
}

const menuConfig = [
  { key: 'stats', icon: <BarChartOutlined />, label: '统计', color: 'blue', path: '/admin' },
  { key: 'users', icon: <UserOutlined />, label: '用户', color: 'purple', path: '/admin/users' },
  { key: 'library', icon: <FolderOpenOutlined />, label: '代码库', color: 'green', path: '/admin/library' },
  { key: 'logs', icon: <FileSearchOutlined />, label: '审计日志', color: 'cyan', path: '/admin/logs' },
  { key: 'settings', icon: <SettingOutlined />, label: '系统配置', color: 'orange', path: '/admin/settings' },
];

const AdminStats: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Stats>('/admin/stats')
      .then((r) => setStats(r.data))
      .catch(() => message.error('加载统计失败'))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !stats) return <Card loading={loading} className="glass-surface-light">加载中…</Card>;

  return (
    <Card className="glass-surface-light" style={{ borderRadius: '12px', padding: '24px' }}>
      <Title level={4} style={{ color: '#1e293b', marginBottom: '24px' }}>
        <BarChartOutlined style={{ marginRight: '8px', color: '#3b82f6' }} />
        系统概览
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
              <UserOutlined style={{ color: '#667eea', fontSize: '18px', marginRight: '8px' }} />
              <span style={{ color: '#64748b', fontSize: '13px' }}>用户数</span>
            </div>
            <span style={{ color: '#1e293b', fontSize: '28px', fontWeight: 700 }}>{stats.user_count}</span>
          </div>
        </Col>
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
              <FileSearchOutlined style={{ color: '#f59e0b', fontSize: '18px', marginRight: '8px' }} />
              <span style={{ color: '#64748b', fontSize: '13px' }}>作业数</span>
            </div>
            <span style={{ color: '#1e293b', fontSize: '28px', fontWeight: 700 }}>{stats.assignment_count}</span>
          </div>
        </Col>
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
              <FolderOpenOutlined style={{ color: '#10b981', fontSize: '18px', marginRight: '8px' }} />
              <span style={{ color: '#64748b', fontSize: '13px' }}>提交数</span>
            </div>
            <span style={{ color: '#1e293b', fontSize: '28px', fontWeight: 700 }}>{stats.submission_count}</span>
          </div>
        </Col>
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
              <SettingOutlined style={{ color: '#ef4444', fontSize: '18px', marginRight: '8px' }} />
              <span style={{ color: '#64748b', fontSize: '13px' }}>比对记录数</span>
            </div>
            <span style={{ color: '#1e293b', fontSize: '28px', fontWeight: 700 }}>{stats.comparison_count.toLocaleString()}</span>
          </div>
        </Col>
      </Row>
      <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ color: '#64748b', fontSize: '13px' }}>平均相似度（有效分数）</span>
        </div>
        <span style={{ color: '#1e293b', fontSize: '28px', fontWeight: 700 }}>
          {stats.avg_similarity != null ? stats.avg_similarity.toFixed(2) : '—'}
        </span>
      </div>
    </Card>
  );
};

const AdminUsers: React.FC = () => {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .get<AdminUser[]>('/admin/users')
      .then((r) => setUsers(r.data))
      .catch(() => message.error('加载用户失败'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const resetPwd = async (id: number) => {
    const pwd = window.prompt('输入新密码（至少 6 位）');
    if (!pwd || pwd.length < 6) {
      message.warning('已取消或密码过短');
      return;
    }
    try {
      await api.post(`/admin/users/${id}/reset-password`, { new_password: pwd });
      message.success('密码已重置');
    } catch (e: any) {
      message.error(e.response?.data?.detail || '失败');
    }
  };

  const remove = async (id: number) => {
    try {
      await api.delete(`/admin/users/${id}`);
      message.success('已删除');
      load();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '删除失败');
    }
  };

  return (
    <div>
      <Title level={4} className="page-title-light">用户管理</Title>
      <Table
        loading={loading}
        rowKey="id"
        dataSource={users}
        pagination={{ pageSize: 12 }}
        className="light-table"
        columns={[
          { title: 'ID', dataIndex: 'id', width: 80 },
          { title: '用户名', dataIndex: 'username' },
          { title: '邮箱', dataIndex: 'email' },
          { title: '角色', dataIndex: 'role', width: 100 },
          {
            title: '操作',
            key: 'act',
            width: 220,
            render: (_, u: AdminUser) => (
              <Space>
                <Button size="small" className="btn-primary-light" onClick={() => resetPwd(u.id)}>
                  重置密码
                </Button>
                <Popconfirm title="确定删除该用户？" onConfirm={() => remove(u.id)}>
                  <Button size="small" danger>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
    </div>
  );
};

const AdminSettings: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api
      .get<SystemConfig>('/admin/config')
      .then((r) => {
        form.setFieldsValue(r.data);
      })
      .catch(() => message.error('加载配置失败'));
  }, [form]);

  const onFinish = async (values: SystemConfig) => {
    setLoading(true);
    try {
      await api.put('/admin/config', values);
      message.success('已保存');
    } catch (e: any) {
      message.error(e.response?.data?.detail || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Title level={4} className="page-title-light">系统配置</Title>
      <div style={{ maxWidth: 480 }}>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="similarity_threshold" label="相似度阈值（0–100）" rules={[{ required: true }]}>
            <InputNumber min={0} max={100} style={{ width: '100%' }} className="light-input" />
          </Form.Item>
          <Form.Item name="llm_model_name" label="LLM 模型名" rules={[{ required: true }]}>
            <Input className="light-input" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} className="btn-primary-light">
              保存
            </Button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
};

const AdminDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedKey, setSelectedKey] = useState('stats');

  useEffect(() => {
    const path = location.pathname;
    if (path === '/admin' || path === '/admin/') {
      setSelectedKey('stats');
      return;
    }
    const matched = menuConfig.find((item) => path.includes(item.key));
    if (matched) setSelectedKey(matched.key);
  }, [location]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const glassItems = menuConfig.map((item) => ({
    icon: item.icon,
    color: item.color,
    label: item.label,
    customClass: selectedKey === item.key ? 'active' : '',
    onClick: () => navigate(item.path),
  }));

  return (
    <div className="dashboard-container">
      <div className="light-gradient-bg">
        <MagicRings
          color="#3b82f6"
          colorTwo="#8b5cf6"
          ringCount={4}
          speed={0.5}
          attenuation={15}
          lineThickness={1.5}
          baseRadius={0.5}
          radiusStep={0.15}
          scaleRate={0.1}
          opacity={0.5}
          blur={2}
          noiseAmount={0.05}
          rotation={0}
          ringGap={1.3}
          followMouse={true}
          mouseInfluence={0.1}
          hoverScale={1.05}
          parallax={0.02}
          clickBurst={false}
        />
      </div>

      {/* 顶部玻璃拟态头部 */}
      <header className="glass-header-light">
        {/* 左侧标题 */}
        <div className="header-left-full">
          <span className="header-brand">CodeDetect</span>
          <span className="header-dot">·</span>
          <span className="header-role">管理后台</span>
          <span className="header-divider">|</span>
          <span className="header-tech">基于 LangChain / LangGraph / FastAPI 的代码相似度检测系统</span>
        </div>

        {/* 右侧：用户信息 + 退出登录 */}
        <div className="header-right">
          <div className="user-info-no-bg">{user?.username}</div>
          <button className="logout-btn-dark" onClick={handleLogout}>
            退出登录
          </button>
        </div>
      </header>

      {/* 主体：侧边栏 + 内容区 */}
      <div className="dashboard-inner-light">
        {/* 左侧玻璃侧边栏（带3D图标） */}
        <aside className="glass-sidebar-light">
          <div className="sidebar-icons-wrapper">
            <GlassIcons items={glassItems} />
          </div>
        </aside>

        {/* 右侧内容区 —— 与 Header 完全齐平 */}
        <main className="content-area">
          <div className="content-card">
            <Routes>
              <Route index element={<AdminStats />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="library" element={<CodeLibrary />} />
              <Route path="logs" element={<AuditLogs />} />
              <Route path="settings" element={<SystemSettings />} />
              <Route path="*" element={<Navigate to="/admin" replace />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;