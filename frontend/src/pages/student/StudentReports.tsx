import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  List, 
  Button, 
  Space, 
  Tag, 
  message,
  Modal,
  Descriptions,
  Alert,
  Badge,
  Card
} from 'antd';
import { 
  FileTextOutlined, 
  EyeOutlined, 
  CheckCircleOutlined,
  ArrowLeftOutlined
} from '@ant-design/icons';
import api from '../../api/client';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import '../../styles/global.css';

const { Title, Text } = Typography;

interface LearningReport {
  id: number;
  teacher_name: string;
  report_content: any;
  is_read: boolean;
  created_at: string;
  updated_at: string;
}

const StudentReports: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [reports, setReports] = useState<LearningReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [reportModalVisible, setReportModalVisible] = useState(false);
  const [selectedReport, setSelectedReport] = useState<LearningReport | null>(null);

  useEffect(() => {
    if (user && user.role === 'student') {
      fetchReports();
    }
  }, [user]);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const res = await api.get('/statistics/student/reports');
      setReports(res.data);
    } catch (error) {
      message.error('获取学习报告失败');
    } finally {
      setLoading(false);
    }
  };

  const viewReport = async (report: LearningReport) => {
    setSelectedReport(report);
    setReportModalVisible(true);
    
    if (!report.is_read) {
      try {
        await api.put(`/statistics/student/reports/${report.id}/read`);
        setReports(prev => prev.map(r => 
          r.id === report.id ? { ...r, is_read: true } : r
        ));
      } catch (error) {
        console.error('标记报告为已读失败');
      }
    }
  };

  const getUnreadCount = () => {
    return reports.filter(report => !report.is_read).length;
  };

  return (
    <div className="page-fade-in">
      <Card className="glass-surface-light">
        <Space style={{ marginBottom: 16 }}>
          <Button onClick={() => navigate('/student')} icon={<ArrowLeftOutlined />} className="btn-ghost-light">
            返回首页
          </Button>
          <Title level={4} className="page-title-light" style={{ margin: 0 }}>
            <FileTextOutlined className="page-title-icon-light" />
            我的学习报告
            {getUnreadCount() > 0 && (
              <Badge 
                count={getUnreadCount()} 
                style={{ marginLeft: 8, backgroundColor: '#dc2626' }}
              />
            )}
          </Title>
        </Space>

        <List
          loading={loading}
          dataSource={reports}
          renderItem={(report) => (
            <List.Item
              actions={[
                <Button 
                  key="view" 
                  type="link" 
                  icon={<EyeOutlined />}
                  onClick={() => viewReport(report)}
                  style={{ color: '#3b82f6' }}
                >
                  查看详情
                </Button>
              ]}
            >
              <List.Item.Meta
                avatar={
                  <div style={{ 
                    width: 40, 
                    height: 40, 
                    borderRadius: '50%', 
                    backgroundColor: report.is_read ? '#22c55e' : '#3b82f6',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white'
                  }}>
                    {report.is_read ? <CheckCircleOutlined /> : <FileTextOutlined />}
                  </div>
                }
                title={
                  <Space>
                    <Text strong style={{ color: '#1e293b' }}>来自 {report.teacher_name} 老师的学习报告</Text>
                    {report.is_read ? (
                      <Tag color="green">已读</Tag>
                    ) : (
                      <Tag color="blue">未读</Tag>
                    )}
                  </Space>
                }
                description={
                  <Space orientation="vertical" size={0}>
                    <Text type="secondary" style={{ color: '#64748b' }}>
                      生成时间: {dayjs(report.created_at).format('YYYY-MM-DD HH:mm:ss')}
                    </Text>
                    <Text type="secondary" style={{ color: '#64748b' }}>
                      总提交数: {report.report_content?.student_info?.total_submissions || 0}
                    </Text>
                  </Space>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: '暂无学习报告' }}
        />
      </Card>

      {/* 报告详情模态框 */}
      <Modal
        title={<span style={{ color: '#1e293b' }}>学习报告详情 - {selectedReport?.teacher_name}老师</span>}
        open={reportModalVisible}
        onCancel={() => setReportModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setReportModalVisible(false)} className="btn-ghost-light">
            关闭
          </Button>
        ]}
      >
        {selectedReport && (
          <div style={{ color: '#1e293b' }}>
            <Descriptions title="基本信息" bordered column={2} labelStyle={{ color: '#64748b' }} contentStyle={{ color: '#1e293b' }}>
              <Descriptions.Item label="生成教师">{selectedReport.teacher_name}</Descriptions.Item>
              <Descriptions.Item label="生成时间">
                {dayjs(selectedReport.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="总提交数">
                {selectedReport.report_content?.student_info?.total_submissions || 0}
              </Descriptions.Item>
              <Descriptions.Item label="完成作业数">
                {selectedReport.report_content?.student_info?.total_assignments || 0}
              </Descriptions.Item>
              <Descriptions.Item label="按时提交率">
                {selectedReport.report_content?.performance_summary?.on_time_rate || 0}%
              </Descriptions.Item>
              <Descriptions.Item label="高风险提交率">
                {selectedReport.report_content?.performance_summary?.high_risk_rate || 0}%
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 16 }}>
              <Text strong style={{ color: '#334155' }}>表现总结:</Text>
              <Alert 
                message={(selectedReport.report_content?.performance_summary?.on_time_rate || 0) >= 80 ? '表现良好' : '需要改进'}
                description={`按时提交率: ${selectedReport.report_content?.performance_summary?.on_time_rate || 0}%, 高风险提交率: ${selectedReport.report_content?.performance_summary?.high_risk_rate || 0}%`}
                type={(selectedReport.report_content?.performance_summary?.on_time_rate || 0) >= 80 ? 'success' : 'warning'}
                style={{ marginTop: 8 }}
              />
            </div>

            <div style={{ marginTop: 16 }}>
              <Text strong style={{ color: '#334155' }}>AI分析报告:</Text>
              <Card size="small" className="glass-surface-light" style={{ marginTop: 8 }}>
                <p><strong style={{ color: '#1e293b' }}>总结:</strong> {selectedReport.report_content?.ai_analysis?.summary || '暂无分析内容'}</p>
                <p><strong style={{ color: '#1e293b' }}>优势:</strong> {selectedReport.report_content?.ai_analysis?.strengths?.join(', ') || '暂无'}</p>
                <p><strong style={{ color: '#1e293b' }}>改进建议:</strong> {selectedReport.report_content?.ai_analysis?.improvements?.join(', ') || '暂无'}</p>
                <p><strong style={{ color: '#1e293b' }}>学习建议:</strong> {selectedReport.report_content?.ai_analysis?.recommendations?.join(', ') || '暂无'}</p>
              </Card>
            </div>

            <div style={{ marginTop: 16 }}>
              <Text strong style={{ color: '#334155' }}>详细提交记录:</Text>
              <List
                size="small"
                dataSource={selectedReport.report_content?.submission_details || []}
                renderItem={(item: any) => (
                  <List.Item>
                    <div>
                      <Text strong style={{ color: '#1e293b' }}>{item.assignment_title || '未知作业'}</Text>
                      <br />
                      <Text type="secondary" style={{ color: '#64748b' }}>
                        语言: {item.language || '未知'} | 
                        提交时间: {item.submitted_at ? dayjs(item.submitted_at).format('YYYY-MM-DD HH:mm') : '未知'} | 
                        是否按时: {item.is_on_time ? '是' : '否'}
                      </Text>
                    </div>
                  </List.Item>
                )}
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default StudentReports;
