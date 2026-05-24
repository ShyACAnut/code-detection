import React from 'react';
import { Link } from 'react-router-dom';
import { Result, Button } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import '../styles/global.css';

const Unauthorized: React.FC = () => {
  return (
    <div className="login-container">
      <Result
        status="403"
        icon={<LockOutlined style={{ fontSize: 80, color: '#667eea' }} />}
        title={<span style={{ fontSize: 24, fontWeight: 600, color: '#333' }}>403 - 无权限访问</span>}
        subTitle={<span style={{ fontSize: 16, color: '#666' }}>抱歉，您没有权限查看此页面</span>}
        extra={
          <Link to="/">
            <Button type="primary" size="large" className="btn-primary">
              返回首页
            </Button>
          </Link>
        }
      />
    </div>
  );
};

export default Unauthorized;