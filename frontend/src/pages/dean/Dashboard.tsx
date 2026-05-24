import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import DeanAssignments from './DeanAssignments';
import DeanAssignmentDetail from './DeanAssignmentDetail';
import GlassIcons from '../../components/GlassIcons/GlassIcons';
import MagicRings from '../../components/MagicRings';

import { EyeOutlined } from '@ant-design/icons';
import '../../styles/Dashboard.css';

const menuConfig = [
  { key: 'assignments', icon: <EyeOutlined />, label: '所有作业', color: 'blue', path: '/dean/assignments' },
];

const DeanDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedKey, setSelectedKey] = useState('assignments');

  useEffect(() => {
    const path = location.pathname;
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
          <span className="header-role">教学主任端</span>
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
              <Route index element={<Navigate to="assignments" replace />} />
              <Route path="assignments" element={<DeanAssignments />} />
              <Route path="assignments/:id" element={<DeanAssignmentDetail />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
};

export default DeanDashboard;
