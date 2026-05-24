import React, { useState, useEffect, useMemo } from 'react';
import { Select, Table, Spin, Tag, Typography, Card, Slider, Empty } from 'antd';
import api from '../../api/client';
import { BarChartOutlined, FilterOutlined } from '@ant-design/icons';
import '../../styles/global.css';

const { Text, Title } = Typography;

const MAX_SUBS = 30;

interface Assignment {
  id: number;
  title: string;
}

interface MatrixRow {
  student: string;
  [key: string]: any;
}

const TeacherMatrix: React.FC = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selectedAssignment, setSelectedAssignment] = useState<number | null>(null);
  const [rawMatrix, setRawMatrix] = useState<MatrixRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [threshold, setThreshold] = useState(0);

  useEffect(() => {
    fetchAssignments();
  }, []);

  const fetchAssignments = async () => {
    const res = await api.get<Assignment[]>('/assignments');
    setAssignments(res.data);
  };

  const fetchMatrix = async (assignmentId: number) => {
    setLoading(true);
    try {
      const res = await api.get<MatrixRow[]>(`/assignments/${assignmentId}/matrix`);
      setRawMatrix(res.data || []);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleAssignmentChange = (val: number) => {
    setSelectedAssignment(val);
    fetchMatrix(val);
  };

  const { matrix, columns } = useMemo(() => {
    if (!rawMatrix.length) {
      return { matrix: [] as MatrixRow[], columns: [] as any[] };
    }

    const sorted = [...rawMatrix].sort((a, b) => a.student.localeCompare(b.student));
    const limited = sorted.slice(0, MAX_SUBS);
    const keys = Object.keys(limited[0]).filter((k) => k !== 'student');
    const colKeys = keys
      .filter((k) => k !== 'student')
      .sort((a, b) => a.localeCompare(b))
      .slice(0, MAX_SUBS);

    const filteredRows = limited.map((row) => {
      const out: MatrixRow = { student: row.student };
      for (const ck of colKeys) {
        const v = row[ck];
        if (ck === row.student) {
          out[ck] = v;
        } else if (v === null || v === undefined) {
          out[ck] = null;
        } else if (typeof v === 'number' && v >= threshold) {
          out[ck] = v;
        } else {
          out[ck] = null;
        }
      }
      return out;
    });

    const cols = [
      {
        title: '学生',
        dataIndex: 'student',
        key: 'student',
        fixed: 'left' as const,
        render: (text: string) => <span style={{ color: '#334155', fontWeight: 600 }}>{text}</span>
      },
      ...colKeys.map((k) => ({
        title: k,
        dataIndex: k,
        key: k,
        render: (v: number | null) => {
          if (v === null || v === undefined) return <Text type="secondary" style={{ color: '#94a3b8' }}>—</Text>;
          const bgColor = v >= 80 ? 'rgba(239,68,68,0.1)' : v >= 50 ? 'rgba(251,191,36,0.1)' : 'rgba(16,185,129,0.1)';
          const textColor = v >= 80 ? '#dc2626' : v >= 50 ? '#d97706' : '#059669';
          const borderColor = v >= 80 ? 'rgba(239,68,68,0.3)' : v >= 50 ? 'rgba(251,191,36,0.3)' : 'rgba(16,185,129,0.3)';
          return (
            <Tag style={{
              background: bgColor,
              color: textColor,
              border: `1px solid ${borderColor}`,
              fontWeight: 600,
              boxShadow: v >= 80 ? '0 0 8px rgba(239,68,68,0.2)' : 'none'
            }}>
              {Math.round(v)}%
            </Tag>
          );
        },
      })),
    ];

    return { matrix: filteredRows, columns: cols };
  }, [rawMatrix, threshold]);

  return (
    <div className="page-fade-in">
      <Card className="content-card">
        <Title level={4} className="page-title">
          <BarChartOutlined className="page-title-icon" />
          相似度矩阵
        </Title>
        <Text style={{ display: 'block', marginBottom: 16, color: '#64748b' }}>
          最多展示前 {MAX_SUBS} 个提交（按学生用户名升序）。滑块可隐藏低于阈值的单元格。
        </Text>
        <div style={{ margin: '16px 0', maxWidth: 480, background: '#f8fafc', padding: 16, borderRadius: 8, border: '1px solid #e2e8f0' }}>
          <div style={{ marginBottom: 8, color: '#334155' }}>
            <FilterOutlined style={{ marginRight: 4 }} />
            相似度显示阈值：{threshold}（仅显示 ≥ 阈值的格子）
          </div>
          <Slider 
            min={0} 
            max={100} 
            value={threshold} 
            onChange={setThreshold}
            trackStyle={{ backgroundColor: '#3b82f6' }}
            handleStyle={{ borderColor: '#3b82f6', backgroundColor: '#3b82f6' }}
            railStyle={{ backgroundColor: '#e2e8f0' }}
          />
        </div>
        <Select
          placeholder="选择作业"
          style={{ width: 300, marginBottom: 16 }}
          onChange={handleAssignmentChange}
          value={selectedAssignment ?? undefined}
        >
          {assignments.map((a) => (
            <Select.Option key={a.id} value={a.id}>
              {a.title}
            </Select.Option>
          ))}
        </Select>

        {loading && (
          <div style={{ textAlign: 'center', marginTop: 40 }}>
            <Spin />
          </div>
        )}
        {!loading && matrix.length > 0 && (
          <Table
            dataSource={matrix}
            columns={columns}
            rowKey="student"
            scroll={{ x: true }}
            pagination={false}
            className="dark-table"
          />
        )}
        {!loading && matrix.length === 0 && selectedAssignment && (
          <Empty
            description={<span style={{ color: '#64748b' }}>该作业暂无提交记录</span>}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ marginTop: 40 }}
          />
        )}
      </Card>
    </div>
  );
};

export default TeacherMatrix;
