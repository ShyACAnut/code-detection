import React, { useState, useEffect } from 'react';
import { Select, Spin, Typography, Card, Empty, Button, message, Modal, Space, Table, Tag } from 'antd';
import { FileTextOutlined, UserOutlined, ClockCircleOutlined, CheckCircleOutlined, BarChartOutlined, LineChartOutlined, SendOutlined } from '@ant-design/icons';
import api from '../../api/client';

const { Text, Title } = Typography;

interface Student {
  id: number;
  username: string;
  email: string;
}

interface ReportData {
  basic_info: {
    student_name: string;
    total_submissions: number;
    completed_assignments: number;
    on_time_rate: number;
    high_risk_rate: number;
  };
  performance_summary: string;
  ai_analysis: string;
  detailed_records: Array<{
    assignment_name: string;
    submission_time: string;
    status: string;
    similarity: number;
  }>;
}

const TeacherReportGenerator: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<number | null>(null);
  const [showStudentModal, setShowStudentModal] = useState(false);
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [pushingReport, setPushingReport] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);

  useEffect(() => {
    fetchStudents();
  }, []);

  const fetchStudents = async () => {
    try {
      const res = await api.get<Student[]>('/statistics/students');
      setStudents(res.data);
    } catch (error) {
      console.error('获取学生列表失败:', error);
    }
  };

  const handleGenerateReport = async () => {
    if (!selectedStudent) {
      message.warning('请先选择学生');
      return;
    }

    setGeneratingReport(true);
    Modal.info({
      title: '正在生成分析报告',
      content: (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <LineChartOutlined style={{ fontSize: 48, color: '#3b82f6', marginBottom: 16 }} />
          <p style={{ color: '#64748b' }}>正在使用大模型分析学生作业数据...</p>
          <p style={{ color: '#94a3b8', fontSize: 20, marginTop: 8 }}>请稍候，这可能需要几分钟时间</p>
        </div>
      ),
      closable: false,
      maskClosable: false,
    });

    try {
      const res = await api.post<ReportData>(`/statistics/student/${selectedStudent}/report/ai`);
      setReportData(res.data);

      setTimeout(() => {
        Modal.destroyAll();
        Modal.success({
          title: '分析报告生成完成',
          content: (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <CheckCircleOutlined style={{ fontSize: 48, color: '#059669', marginBottom: 16 }} />
              <p style={{ color: '#64748b' }}>报告已成功生成！</p>
              <p style={{ color: '#94a3b8', fontSize: 20, marginTop: 8 }}>点击确定查看详细报告</p>
            </div>
          ),
          onOk: () => {
            setReportModalOpen(true);
          },
        });
      }, 500);

    } catch (error: any) {
      Modal.destroyAll();
      Modal.error({
        title: '生成报告失败',
        content: error.response?.data?.detail || '生成报告时发生错误',
      });
    } finally {
      setGeneratingReport(false);
    }
  };

  const handlePushReport = async () => {
    if (!selectedStudent) {
      message.warning('请先选择学生');
      return;
    }

    setPushingReport(true);
    try {
      await api.post(`/statistics/student/${selectedStudent}/report/push`);
      message.success('报告已成功推送给学生');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '推送失败');
    } finally {
      setPushingReport(false);
    }
  };

  const getSelectedStudentInfo = () => {
    return students.find(s => s.id === selectedStudent);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case '优秀': return 'green';
      case '良好': return 'blue';
      case '及格': return 'orange';
      case '待改进': return 'red';
      default: return 'gray';
    }
  };

  return (
    <div className="page-fade-in" style={{ fontSize: '20px' }}>
      <Card className="content-card">
        <Title level={4} className="page-title">
          <FileTextOutlined className="page-title-icon" />
          生成学生分析报告
        </Title>
        <Text style={{ display: 'block', marginBottom: 16, color: '#64748b' }}>
          选择学生生成详细的学习分析报告，报告由大模型智能分析生成。
        </Text>

        {/* 学生选择区域 */}
        <Card className="content-card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <UserOutlined style={{ fontSize: 24, color: '#64748b' }} />
            <div style={{ flex: 1 }}>
              <Text type="secondary" style={{ fontSize: 20 }}>选择学生</Text>
              <div style={{ marginTop: 8 }}>
                {selectedStudent ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: '#e0f2fe', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <UserOutlined style={{ fontSize: 20, color: '#0ea5e9' }} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600 }}>{getSelectedStudentInfo()?.username}</div>
                      <div style={{ fontSize: 20, color: '#64748b' }}>{getSelectedStudentInfo()?.email}</div>
                    </div>
                  </div>
                ) : (
                  <Text type="secondary">请选择要生成报告的学生</Text>
                )}
              </div>
            </div>
            <Button
              type="primary"
              onClick={() => setShowStudentModal(true)}
              disabled={students.length === 0}
            >
              选择学生
            </Button>
          </div>
        </Card>

        {/* 操作按钮 */}
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Space size="large">
            <Button
              type="primary"
              size="large"
              icon={<LineChartOutlined />}
              onClick={handleGenerateReport}
              loading={generatingReport}
              disabled={!selectedStudent}
              style={{ padding: '8px 32px', fontSize: 14 }}
            >
              生成分析报告
            </Button>
            <Button
              size="large"
              icon={<SendOutlined />}
              onClick={handlePushReport}
              loading={pushingReport}
              disabled={!selectedStudent}
              style={{ padding: '8px 32px', fontSize: 14 }}
            >
              推送报告给学生
            </Button>
          </Space>
          <p style={{ color: '#94a3b8', fontSize: 20, marginTop: 16 }}>
            报告由大模型智能分析生成，包含学生作业提交情况、相似度分析和改进建议
          </p>
        </div>
      </Card>

      {/* 学生选择弹窗 */}
      <Modal
        title="选择学生"
        open={showStudentModal}
        onCancel={() => setShowStudentModal(false)}
        footer={null}
        width={600}
      >
        <Table
          dataSource={students}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          onRow={(record) => ({
            onClick: () => {
              setSelectedStudent(record.id);
              setShowStudentModal(false);
            },
            style: { cursor: 'pointer' },
          })}
          columns={[
            {
              title: '用户名',
              dataIndex: 'username',
              key: 'username',
            },
            {
              title: '邮箱',
              dataIndex: 'email',
              key: 'email',
            },
            {
              title: '操作',
              key: 'action',
              render: () => <Text style={{ color: "#1890ff" }}>点击选择</Text>,
            },
          ]}
        />
      </Modal>

      {/* 报告预览弹窗 */}
      <Modal
        title={`学习报告详情 - ${reportData?.basic_info.student_name || ''}`}
        open={reportModalOpen}
        onCancel={() => setReportModalOpen(false)}
        footer={[
          <Button key="push" type="primary" icon={<SendOutlined />} onClick={handlePushReport} loading={pushingReport}>
            推送报告给学生
          </Button>,
          <Button key="close" onClick={() => setReportModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={800}
        bodyStyle={{ maxHeight: '70vh', overflow: 'auto' }}
      >
        {reportData && (
          <div className="report-container">
            {/* 基本信息 */}
            <Card className="report-section" style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                <div style={{ width: 48, height: 48, borderRadius: 24, backgroundColor: '#e0f2fe', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <UserOutlined style={{ fontSize: 24, color: '#0ea5e9' }} />
                </div>
                <div>
                  <Title level={5} style={{ marginBottom: 4 }}>{reportData.basic_info.student_name}</Title>
                  <Text type="secondary" style={{ fontSize: 20 }}>学习报告</Text>
                </div>
                <div style={{ marginLeft: 'auto' }}>
                  <ClockCircleOutlined style={{ color: '#64748b' }} />
                  <Text type="secondary" style={{ marginLeft: 8 }}>{new Date().toLocaleString()}</Text>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                <div className="stat-card">
                  <div className="stat-value">{reportData.basic_info.total_submissions}</div>
                  <div className="stat-label">总提交数</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{reportData.basic_info.completed_assignments}</div>
                  <div className="stat-label">完成作业数</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value highlight-green">{reportData.basic_info.on_time_rate}%</div>
                  <div className="stat-label">按时提交率</div>
                </div>
                <div className="stat-card">
                  <div className={`stat-value ${reportData.basic_info.high_risk_rate > 0 ? 'highlight-red' : 'highlight-green'}`}>
                    {reportData.basic_info.high_risk_rate}%
                  </div>
                  <div className="stat-label">高风险提交率</div>
                </div>
              </div>
            </Card>

            {/* 表现总结 */}
            <Card className="report-section" style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <CheckCircleOutlined style={{ fontSize: 20, color: '#059669' }} />
                <Title level={5}>表现总结</Title>
              </div>
              <div className="performance-badge" style={{ backgroundColor: '#dcfce7', padding: '12px 16px', borderRadius: 8, marginBottom: 12 }}>
                <Text strong style={{ color: '#059669' }}>{reportData.performance_summary}</Text>
              </div>
            </Card>

            {/* AI分析 */}
            <Card className="report-section" style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <LineChartOutlined style={{ fontSize: 20, color: '#8b5cf6' }} />
                <Title level={5}>AI分析报告</Title>
              </div>
              <div style={{ backgroundColor: '#faf5ff', padding: '16px', borderRadius: 8 }}>
                <Text style={{ lineHeight: 1.8, color: '#64748b' }}>{reportData.ai_analysis}</Text>
              </div>
            </Card>

            {/* 详细提交记录 */}
            <Card className="report-section">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                <BarChartOutlined style={{ fontSize: 20, color: '#3b82f6' }} />
                <Title level={5}>详细提交记录</Title>
              </div>
              <Table
                dataSource={reportData.detailed_records}
                rowKey={(record, index) => String(index)}
                pagination={false}
                columns={[
                  {
                    title: '作业名称',
                    dataIndex: 'assignment_name',
                    key: 'assignment_name',
                  },
                  {
                    title: '提交时间',
                    dataIndex: 'submission_time',
                    key: 'submission_time',
                  },
                  {
                    title: '状态',
                    dataIndex: 'status',
                    key: 'status',
                    render: (status: string) => (
                      <Tag color={getStatusColor(status)}>{status}</Tag>
                    ),
                  },
                  {
                    title: '相似度',
                    dataIndex: 'similarity',
                    key: 'similarity',
                    render: (similarity: number) => (
                      <span style={{ color: similarity >= 80 ? '#dc2626' : similarity >= 50 ? '#d97706' : '#059669' }}>
                        {similarity}%
                      </span>
                    ),
                  },
                ]}
              />
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TeacherReportGenerator;