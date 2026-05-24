import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, message, Select } from 'antd';
import api from '../api/client';
import { UserOutlined, LockOutlined, MailOutlined, TeamOutlined } from '@ant-design/icons';
import MagicRings from '../components/MagicRings';
import CrackedIce from '../components/CrackedIce';
import '../styles/global.css';

const { Option } = Select;

const techItems = [
  'LANGCHAIN',
  'MCP',
  'LANGGRAPH',
  'FASTAPI',
  'GLM-4',
  'FAISS',
];

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      await api.post('/auth/register', {
        username: values.username,
        email: values.email,
        password: values.password,
        role: values.role || 'student',
      });
      message.success('注册成功，请登录');
      navigate('/login');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '注册失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="rings-bg">
        <MagicRings
          color="#818cf8"
          colorTwo="#c4b5fd"
          ringCount={5}
          speed={0.4}
          attenuation={12}
          lineThickness={2}
          baseRadius={0.4}
          radiusStep={0.12}
          scaleRate={0.12}
          opacity={0.8}
          blur={1}
          noiseAmount={0.03}
          rotation={0}
          ringGap={1.2}
          followMouse={true}
          mouseInfluence={0.15}
          hoverScale={1.08}
          parallax={0.03}
          clickBurst={false}
        />
      </div>

      <div className="cracked-ice-layer">
        <CrackedIce />
      </div>

      <div className="vignette-overlay" />

      <div className="login-content">
        <header className="brand">CodeDetect</header>

        <main className="login-card cracked-glass">
          <div className="glass-shine" />
          <h2 className="login-title">用户注册</h2>
          <Form onFinish={onFinish} initialValues={{ role: 'student' }} layout="vertical">
            <Form.Item 
              name="username" 
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input 
                prefix={<UserOutlined />} 
                placeholder="用户名" 
                size="large" 
                className="login-input"
              />
            </Form.Item>
            <Form.Item 
              name="email" 
              rules={[{ required: true, type: 'email', message: '请输入有效的邮箱' }]}
            >
              <Input 
                prefix={<MailOutlined />} 
                placeholder="邮箱" 
                size="large" 
                className="login-input"
              />
            </Form.Item>
            <Form.Item 
              name="password" 
              rules={[{ required: true, message: '请输入密码', min: 6 }]}
            >
              <Input.Password 
                prefix={<LockOutlined />} 
                placeholder="密码（至少6位）" 
                size="large" 
                className="login-input"
              />
            </Form.Item>
            <Form.Item 
              name="role" 
              rules={[{ required: true }]}
            >
              <Select 
                placeholder="请选择角色" 
                size="large" 
                suffixIcon={<TeamOutlined />}
                className="login-input"
              >
                <Option value="student">学生</Option>
                <Option value="teacher">教师</Option>
                <Option value="dean">教学主任</Option>
                <Option value="admin">管理员</Option>
              </Select>
            </Form.Item>
            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={loading} 
                size="large" 
                block
                className="login-btn"
              >
                注册
              </Button>
            </Form.Item>
          </Form>
          <div className="login-footer">
            已有账号？ <Link to="/login">立即登录</Link>
          </div>
        </main>

        <footer className="tech-marquee">
          <div className="marquee-container">
            <div className="marquee-track">
              {[...techItems, ...techItems, ...techItems].map((item, index) => (
                <React.Fragment key={index}>
                  <span className="marquee-item">{item}</span>
                  <span className="marquee-dot">•</span>
                </React.Fragment>
              ))}
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default RegisterPage;