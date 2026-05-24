import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import StudentAssignments from './StudentAssignments';
import StudentSubmissions from './StudentSubmissions';
import StudentAssignmentDetail from './StudentAssignmentDetail';
import SubmitAssignment from './SubmitAssignment';
import StudentReports from './StudentReports';
import StudentSelfCheck from './StudentSelfCheck';
import EthicsLearning from './EthicsLearning';
import StudentNotifications from './StudentNotifications';
import CodeAnalyzer from '../../components/CodeAnalyzer';
import GlassIcons from '../../components/GlassIcons/GlassIcons';
import MagicRings from '../../components/MagicRings';
import { Alert, Button } from 'antd';
import {
  HomeOutlined,
  FileTextOutlined,
  BarChartOutlined,
  CodeOutlined,
  CheckCircleOutlined,
  BookOutlined,
  BellOutlined,
} from '@ant-design/icons';
import api from '../../api/client';
import '../../styles/Dashboard.css';

interface EthicsStatus {
  requires_learning: boolean;
  required_count: number;
  completed_count: number;
  remaining_count: number;
}

const menuConfig = [
  { key: 'assignments', icon: <HomeOutlined />, label: '作业列表', color: 'blue', path: '/student/assignments' },
  { key: 'submissions', icon: <FileTextOutlined />, label: '我的提交', color: 'purple', path: '/student/submissions' },
  { key: 'notifications', icon: <BellOutlined />, label: '我的通知', color: 'red', path: '/student/notifications' },
  { key: 'reports', icon: <BarChartOutlined />, label: '学习报告', color: 'green', path: '/student/reports' },
  { key: 'analyze', icon: <CodeOutlined />, label: '代码分析', color: 'orange', path: '/student/analyze' },
  { key: 'self-check', icon: <CheckCircleOutlined />, label: '代码自查', color: 'cyan', path: '/student/self-check' },
  { key: 'ethics', icon: <BookOutlined />, label: '伦理学习', color: 'pink', path: '/student/ethics' },
];

const StudentDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedKey, setSelectedKey] = useState('assignments');
  const [ethicsStatus, setEthicsStatus] = useState<EthicsStatus | null>(null);

  useEffect(() => {
    const path = location.pathname;
    const matched = menuConfig.find((item) => path.includes(item.key));
    if (matched) setSelectedKey(matched.key);
  }, [location]);

  useEffect(() => {
    fetchEthicsStatus();
  }, []);

  const fetchEthicsStatus = async () => {
    try {
      const response = await api.get('/notifications/ethics/status');
      setEthicsStatus(response.data);
    } catch (error) {
      console.error('获取伦理学习状态失败', error);
    }
  };

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
          <span className="header-role">学生端</span>
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

      {ethicsStatus?.requires_learning && (
        <div style={{
          position: 'fixed',
          top: 70,
          left: 0,
          right: 0,
          zIndex: 1000,
          padding: '0 20px'
        }}>
          <Alert
            type="error"
            showIcon
            icon={<BookOutlined />}
            message={
              <span>
                <strong>您有未完成的伦理学习要求！</strong>
                <span style={{ marginLeft: 16 }}>
                  还需完成 <strong>{ethicsStatus.remaining_count}</strong> 个案例
                  （已学习 {ethicsStatus.completed_count}/{ethicsStatus.required_count}）
                </span>
              </span>
            }
            description={
              <span>
                由于您的代码相似度达到高风险或收到整改通知，您需要完成规定的伦理学习案例才能消除此警告。
                请点击{" "}
                <Button
                  type="link"
                  size="small"
                  onClick={() => navigate('/student/ethics')}
                  style={{ padding: 0, height: 'auto' }}
                >
                  这里前往伦理学习
                </Button>
                {" "}完成学习。
              </span>
            }
            closable
            style={{ marginBottom: 8 }}
            afterClose={() => setEthicsStatus(prev => prev ? { ...prev, requires_learning: false } : null)}
          />
        </div>
      )}

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
              <Route path="assignments" element={<StudentAssignments />} />
              <Route path="assignments/:id" element={<StudentAssignmentDetail />} />
              <Route path="submissions" element={<StudentSubmissions />} />
              <Route path="submit/:id" element={<SubmitAssignment />} />
              <Route path="notifications" element={<StudentNotifications />} />
              <Route path="reports" element={<StudentReports />} />
              <Route path="analyze" element={<CodeAnalyzer />} />
              <Route path="self-check" element={<StudentSelfCheck />} />
              <Route path="ethics" element={<EthicsLearning />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
};

export default StudentDashboard;