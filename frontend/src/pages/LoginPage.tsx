import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import MagicRings from '../components/MagicRings';
import CrackedIce from '../components/CrackedIce';
import '../styles/global.css';

const techItems = [
  'LANGCHAIN',
  'MCP',
  'LANGGRAPH',
  'FASTAPI',
  'GLM-4',
  'FAISS',
];

const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('登录成功');
      navigate('/');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '登录失败，请检查用户名和密码');
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
          <h2 className="login-title">代码相似性检测系统</h2>
          <Form onFinish={onFinish} layout="vertical">
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
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="密码"
                size="large"
                className="login-input"
              />
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
                登录
              </Button>
            </Form.Item>
          </Form>
          <div className="login-footer">
            还没有账号？ <Link to="/register">立即注册</Link>
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

export default LoginPage;
