import React, { useState, useEffect } from 'react';
import { Card, Table, Form, Select, DatePicker, Button, Space, Tag, Typography, message, Input, Statistic, Row, Col } from 'antd';
import { FileTextOutlined, SearchOutlined, ReloadOutlined, DownloadOutlined, UserOutlined, SettingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import dayjs from 'dayjs';
import '../../styles/global.css';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface AuditLog {
  id: number;
  actor_user_id: number | null;
  action: string;
  target_type: string | null;
  target_id: number | null;
  detail: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  username?: string;
}

interface AuditStats {
  total_count: number;
  days: number;
  action_distribution: { [key: string]: number };
  top_users: { user_id: number; count: number }[];
}

const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [filters, setFilters] = useState({
    action: undefined as string | undefined,
    user_id: undefined as number | undefined,
    start_date: undefined as string | undefined,
    end_date: undefined as string | undefined,
  });

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [page, pageSize, filters]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params: any = {
        page,
        page_size: pageSize,
      };
      if (filters.action) params.action = filters.action;
      if (filters.user_id) params.user_id = filters.user_id;
      if (filters.start_date) params.start_date = filters.start_date;
      if (filters.end_date) params.end_date = filters.end_date;

      const response = await api.get('/audit-logs/', { params });
      setLogs(response.data);
      setTotal(response.data.length);
    } catch (error) {
      message.error('获取日志失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/audit-logs/stats/summary', {
        params: { days: 7 },
      });
      setStats(response.data);
    } catch (error) {
      console.error('获取统计失败', error);
    }
  };

  const handleSearch = (values: any) => {
    setFilters({
      action: values.action,
      user_id: values.user_id,
      start_date: values.dateRange?.[0]?.format('YYYY-MM-DD'),
      end_date: values.dateRange?.[1]?.format('YYYY-MM-DD'),
    });
    setPage(1);
  };

  const handleReset = () => {
    setFilters({
      action: undefined,
      user_id: undefined,
      start_date: undefined,
      end_date: undefined,
    });
    setPage(1);
  };

  const getActionColor = (action: string) => {
    if (action.includes('delete')) return 'red';
    if (action.includes('create') || action.includes('add')) return 'green';
    if (action.includes('update') || action.includes('edit')) return 'blue';
    if (action.includes('login')) return 'cyan';
    if (action.includes('logout')) return 'gray';
    if (action.includes('view') || action.includes('read')) return 'default';
    return 'orange';
  };

  const getActionText = (action: string) => {
    const actionMap: { [key: string]: string } = {
      'user.login': '用户登录',
      'user.logout': '用户登出',
      'user.create': '创建用户',
      'user.update': '更新用户',
      'user.delete': '删除用户',
      'assignment.create': '创建作业',
      'assignment.update': '更新作业',
      'assignment.delete': '删除作业',
      'submission.create': '提交作业',
      'submission.delete': '删除提交',
      'notification.send': '发送通知',
      'notification.read': '查看通知',
      'detection.run': '运行检测',
      'config.update': '更新配置',
    };
    return actionMap[action] || action;
  };

  const exportLogs = () => {
    const csvContent = [
      ['ID', '用户', '操作', '目标类型', '目标ID', '详情', 'IP地址', '时间'].join(','),
      ...logs.map(log => [
        log.id,
        log.username || log.actor_user_id || '-',
        log.action,
        log.target_type || '-',
        log.target_id || '-',
        (log.detail || '').replace(/,/g, ';'),
        log.ip_address || '-',
        log.created_at,
      ].join(',')),
    ].join('\n');

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `audit_logs_${dayjs().format('YYYY-MM-DD')}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      fixed: 'left' as const,
    },
    {
      title: '用户',
      dataIndex: 'actor_user_id',
      key: 'actor_user_id',
      width: 100,
      render: (id: number | null) => id ? `用户 #${id}` : '-',
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 140,
      render: (action: string) => (
        <Tag color={getActionColor(action)} style={{ fontSize: '14px', padding: '4px 10px' }}>
          {getActionText(action)}
        </Tag>
      ),
    },
    {
      title: '目标',
      key: 'target',
      width: 120,
      render: (_: any, record: AuditLog) => (
        record.target_type ? (
          <span style={{ fontSize: '14px' }}>
            {record.target_type} #{record.target_id}
          </span>
        ) : '-'
      ),
    },
    {
      title: '详情',
      dataIndex: 'detail',
      key: 'detail',
      ellipsis: true,
      width: 200,
      render: (detail: string | null) => (
        <span style={{ fontSize: '14px' }}>
          {detail || '-'}
        </span>
      ),
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      fixed: 'right' as const,
      render: (ip: string | null) => (
        <span style={{ fontSize: '14px' }}>
          {ip || '-'}
        </span>
      ),
    },
  ];

  return (
    <div className="page-fade-in">
      <Card className="content-card">
        <Title level={4} className="page-title">
          <FileTextOutlined className="page-title-icon" />
          审计日志
        </Title>

        {stats && (
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="7日内总操作数"
                  value={stats.total_count}
                  valueStyle={{ fontSize: 24 }}
                />
              </Card>
            </Col>
            <Col span={18}>
              <Card size="small" title="操作分布">
                <Space wrap>
                  {Object.entries(stats.action_distribution).slice(0, 6).map(([action, count]) => (
                    <Tag key={action} color={getActionColor(action)}>
                      {getActionText(action)}: {count}
                    </Tag>
                  ))}
                </Space>
              </Card>
            </Col>
          </Row>
        )}

        <Form layout="inline" onFinish={handleSearch} style={{ marginBottom: 16 }}>
          <Form.Item name="action" label="操作类型">
            <Select
              allowClear
              placeholder="选择操作"
              style={{ width: 150 }}
            >
              <Option value="user.login">用户登录</Option>
              <Option value="user.logout">用户登出</Option>
              <Option value="assignment.create">创建作业</Option>
              <Option value="assignment.update">更新作业</Option>
              <Option value="submission.create">提交作业</Option>
              <Option value="notification.send">发送通知</Option>
              <Option value="detection.run">运行检测</Option>
              <Option value="config.update">更新配置</Option>
            </Select>
          </Form.Item>

          <Form.Item name="dateRange" label="时间范围">
            <RangePicker />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>
                搜索
              </Button>
              <Button onClick={handleReset} icon={<ReloadOutlined />}>
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>

        <div style={{ marginBottom: 16, textAlign: 'right' }}>
          <Button icon={<DownloadOutlined />} onClick={exportLogs}>
            导出CSV
          </Button>
        </div>

        <Table
          dataSource={logs}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          scroll={{ x: 'max-content' }}
          style={{ fontSize: '14px' }}
        />
      </Card>
    </div>
  );
};

export default AuditLogs;