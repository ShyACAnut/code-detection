import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, Navigate, useLocation } from 'react-router-dom';
import TeacherAssignments from './TeacherAssignments';
import TeacherAssignmentDetail from './TeacherAssignmentDetail';
import TeacherBatchUpload from './TeacherBatchUpload';
import TeacherBatchAnalyze from './TeacherBatchAnalyze';
import TeacherStatistics from './TeacherStatistics';
import TeacherReportGenerator from './TeacherReportGenerator';
import TeacherNotifications from './TeacherNotifications';
import { useAuth } from '../../contexts/AuthContext';
import GlassIcons from '../../components/GlassIcons/GlassIcons';
import MagicRings from '../../components/MagicRings';

import {
  HomeOutlined,
  UploadOutlined,
  BarChartOutlined,
  PlayCircleOutlined,
  BellOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import '../../styles/Dashboard.css';

const menuConfig = [
  { key: 'assignments', icon: <HomeOutlined />, label: '作业管理', color: 'blue', path: '/teacher/assignments' },
  { key: 'batch', icon: <UploadOutlined />, label: '批量上传', color: 'purple', path: '/teacher/batch' },
  { key: 'batch-analyze', icon: <PlayCircleOutlined />, label: '批量检测', color: 'orange', path: '/teacher/batch-analyze' },
  { key: 'statistics', icon: <BarChartOutlined />, label: '数据统计', color: 'green', path: '/teacher/statistics' },
  { key: 'reports', icon: <FileTextOutlined />, label: '生成报告', color: 'indigo', path: '/teacher/reports' },
  { key: 'notifications', icon: <BellOutlined />, label: '整改通知', color: 'red', path: '/teacher/notifications' },
];

const TeacherDashboard: React.FC = () => {
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

      <header className="glass-header-light">
        <div className="header-left-full">
          <span className="header-brand">CodeDetect</span>
          <span className="header-dot">·</span>
          <span className="header-role">教师端</span>
          <span className="header-divider">|</span>
          <span className="header-tech">基于 LangChain / LangGraph / FastAPI 的代码相似度检测系统</span>
        </div>

        <div className="header-right">
          <div className="user-info-no-bg">{user?.username}</div>
          <button className="logout-btn-dark" onClick={handleLogout}>
            退出登录
          </button>
        </div>
      </header>

      <div className="dashboard-inner-light">
        <aside className="glass-sidebar-light">
          <div className="sidebar-icons-wrapper">
            <GlassIcons items={glassItems} />
          </div>
        </aside>

        <main className="content-area">
          <div className="content-card">
            <Routes>
              <Route index element={<Navigate to="assignments" replace />} />
              <Route path="assignments" element={<TeacherAssignments />} />
              <Route path="assignments/:id" element={<TeacherAssignmentDetail />} />
              <Route path="batch" element={<TeacherBatchUpload />} />
              <Route path="batch-analyze" element={<TeacherBatchAnalyze />} />
              <Route path="statistics" element={<TeacherStatistics />} />
              <Route path="reports" element={<TeacherReportGenerator />} />
              <Route path="notifications" element={<TeacherNotifications />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
};

export default TeacherDashboard;