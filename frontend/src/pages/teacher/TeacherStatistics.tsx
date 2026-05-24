import React, { useState, useEffect, useMemo } from 'react';
import { Select, Spin, Typography, Card, Empty, Button, message, Space, Divider, Table, Tag, Modal } from 'antd';
import { PieChartOutlined, BarChartOutlined, LineChartOutlined, DownloadOutlined, CloseOutlined } from '@ant-design/icons';
import api from '../../api/client';
import SimilarityCharts from '../../components/SimilarityCharts';

const { Text, Title } = Typography;

interface Assignment {
  id: number;
  title: string;
}

interface MatrixRow {
  student: string;
  [key: string]: any;
}

interface ComparisonPair {
  studentA: string;
  studentB: string;
  similarity: number;
}

const TeacherStatistics: React.FC = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selectedAssignment, setSelectedAssignment] = useState<number | null>(null);
  const [rawMatrix, setRawMatrix] = useState<MatrixRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [exportingGrades, setExportingGrades] = useState(false);
  const [selectedRange, setSelectedRange] = useState<string | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [detailData, setDetailData] = useState<ComparisonPair[]>([]);

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
    setSelectedRange(null);
    fetchMatrix(val);
  };

  const exportStudentGrades = async (format: 'csv' | 'json') => {
    setExportingGrades(true);
    try {
      const res = await api.get<{ filename: string; content: string }>(`/statistics/export/grades?format=${format}`);

      const blob = new Blob([res.data.content], {
        type: format === 'csv' ? 'text/csv;charset=utf-8-sig' : 'application/json'
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = res.data.filename;
      a.click();
      window.URL.revokeObjectURL(url);
      message.success(`成绩导出成功: ${res.data.filename}`);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '导出失败');
    } finally {
      setExportingGrades(false);
    }
  };

  const { stats, distribution } = useMemo(() => {
    if (!rawMatrix.length) {
      return {
        stats: { highCount: 0, mediumCount: 0, lowCount: 0, totalPairs: 0 },
        distribution: { ranges: [], counts: [] }
      };
    }

    const rangeCounts: { [key: string]: number } = {
      '0-10': 0, '11-20': 0, '21-30': 0, '31-40': 0, '41-50': 0,
      '51-60': 0, '61-70': 0, '71-80': 0, '81-90': 0, '91-100': 0
    };

    let highCount = 0, mediumCount = 0, lowCount = 0, totalPairs = 0;
    const students = rawMatrix.map(row => row.student);

    for (let i = 0; i < students.length; i++) {
      for (let j = i + 1; j < students.length; j++) {
        const row = rawMatrix.find(r => r.student === students[i]);
        if (!row) continue;

        const similarity = row[students[j]];
        if (similarity === null || similarity === undefined || typeof similarity !== 'number') continue;

        totalPairs++;
        if (similarity >= 80) highCount++;
        else if (similarity >= 50) mediumCount++;
        else lowCount++;

        let rangeKey = '';
        if (similarity <= 10) rangeKey = '0-10';
        else if (similarity <= 20) rangeKey = '11-20';
        else if (similarity <= 30) rangeKey = '21-30';
        else if (similarity <= 40) rangeKey = '31-40';
        else if (similarity <= 50) rangeKey = '41-50';
        else if (similarity <= 60) rangeKey = '51-60';
        else if (similarity <= 70) rangeKey = '61-70';
        else if (similarity <= 80) rangeKey = '71-80';
        else if (similarity <= 90) rangeKey = '81-90';
        else rangeKey = '91-100';

        if (rangeKey in rangeCounts) rangeCounts[rangeKey]++;
      }
    }

    return {
      stats: { highCount, mediumCount, lowCount, totalPairs },
      distribution: { ranges: Object.keys(rangeCounts), counts: Object.values(rangeCounts) }
    };
  }, [rawMatrix]);

  const getAllPairs = useMemo(() => {
    const pairs: ComparisonPair[] = [];
    const students = rawMatrix.map(row => row.student);

    for (let i = 0; i < students.length; i++) {
      for (let j = i + 1; j < students.length; j++) {
        const row = rawMatrix.find(r => r.student === students[i]);
        if (!row) continue;

        const similarity = row[students[j]];
        if (similarity === null || similarity === undefined || typeof similarity !== 'number') continue;

        pairs.push({
          studentA: students[i],
          studentB: students[j],
          similarity: similarity
        });
      }
    }

    return pairs.sort((a, b) => b.similarity - a.similarity);
  }, [rawMatrix]);

  const handleRangeClick = (range: string) => {
    setSelectedRange(range);
    let filteredPairs: ComparisonPair[] = [];

    if (range === 'high') {
      filteredPairs = getAllPairs.filter(p => p.similarity >= 80);
    } else if (range === 'medium') {
      filteredPairs = getAllPairs.filter(p => p.similarity >= 50 && p.similarity < 80);
    } else if (range === 'low') {
      filteredPairs = getAllPairs.filter(p => p.similarity < 50);
    } else {
      const rangeMap: { [key: string]: [number, number] } = {
        '0-10': [0, 10], '11-20': [11, 20], '21-30': [21, 30], '31-40': [31, 40],
        '41-50': [41, 50], '51-60': [51, 60], '61-70': [61, 70], '71-80': [71, 80],
        '81-90': [81, 90], '91-100': [91, 100]
      };
      const [min, max] = rangeMap[range] || [0, 0];
      filteredPairs = getAllPairs.filter(p => p.similarity >= min && p.similarity <= max);
    }

    setDetailData(filteredPairs);
    setDetailModalVisible(true);
  };

  const getRangeTitle = () => {
    if (selectedRange === 'high') return '高相似度配对详情 (≥80%)';
    if (selectedRange === 'medium') return '中等相似度配对详情 (50%-79%)';
    if (selectedRange === 'low') return '低相似度配对详情 (<50%)';
    return `${selectedRange} 区间配对详情`;
  };

  const getSimilarityColor = (score: number) => {
    if (score >= 80) return '#dc2626';
    if (score >= 50) return '#d97706';
    return '#059669';
  };

  const detailColumns = [
    {
      title: '学生 A',
      dataIndex: 'studentA',
      key: 'studentA',
      width: '30%',
      render: (text: string) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '学生 B',
      dataIndex: 'studentB',
      key: 'studentB',
      width: '30%',
      render: (text: string) => <Tag color="green">{text}</Tag>
    },
    {
      title: '相似度',
      dataIndex: 'similarity',
      key: 'similarity',
      width: '20%',
      sorter: (a: ComparisonPair, b: ComparisonPair) => a.similarity - b.similarity,
      render: (score: number) => (
        <Tag
          style={{
            background: `${getSimilarityColor(score)}20`,
            color: getSimilarityColor(score),
            border: `1px solid ${getSimilarityColor(score)}50`,
            fontWeight: 600,
            fontSize: 14,
            padding: '4px 12px'
          }}
        >
          {score.toFixed(1)}%
        </Tag>
      )
    },
    {
      title: '相似度等级',
      key: 'level',
      width: '20%',
      render: (_: any, record: ComparisonPair) => {
        if (record.similarity >= 80) return <Tag color="red">高度相似</Tag>;
        if (record.similarity >= 50) return <Tag color="orange">中度相似</Tag>;
        return <Tag color="green">低度相似</Tag>;
      }
    }
  ];

  return (
    <div className="page-fade-in">
      <Card className="content-card">
        <Title level={4} className="page-title">
          <LineChartOutlined className="page-title-icon" />
          数据统计
        </Title>
        <Text style={{ display: 'block', marginBottom: 16, color: '#64748b' }}>
          基于相似度矩阵数据的可视化统计分析，帮助教师快速了解作业抄袭情况。点击饼图或柱状图查看详细配对信息。
        </Text>

        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="选择作业"
            style={{ width: 300 }}
            onChange={handleAssignmentChange}
            value={selectedAssignment ?? undefined}
          >
            {assignments.map((a) => (
              <Select.Option key={a.id} value={a.id}>{a.title}</Select.Option>
            ))}
          </Select>
        </Space>

        {loading && (
          <div style={{ textAlign: 'center', marginTop: 40 }}>
            <Spin />
          </div>
        )}

        {!loading && rawMatrix.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
              <Card className="content-card" style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 48, height: 48, borderRadius: 12, backgroundColor: 'rgba(239,68,68,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <PieChartOutlined style={{ fontSize: 24, color: '#dc2626' }} />
                  </div>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>高相似度配对</Text>
                    <div style={{ fontSize: 24, fontWeight: 700, color: '#dc2626' }}>{stats.highCount}</div>
                  </div>
                </div>
              </Card>
              <Card className="content-card" style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 48, height: 48, borderRadius: 12, backgroundColor: 'rgba(251,191,36,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <BarChartOutlined style={{ fontSize: 24, color: '#d97706' }} />
                  </div>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>中等相似度配对</Text>
                    <div style={{ fontSize: 24, fontWeight: 700, color: '#d97706' }}>{stats.mediumCount}</div>
                  </div>
                </div>
              </Card>
              <Card className="content-card" style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 48, height: 48, borderRadius: 12, backgroundColor: 'rgba(16,185,129,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <LineChartOutlined style={{ fontSize: 24, color: '#059669' }} />
                  </div>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>低相似度配对</Text>
                    <div style={{ fontSize: 24, fontWeight: 700, color: '#059669' }}>{stats.lowCount}</div>
                  </div>
                </div>
              </Card>
            </div>

            <SimilarityCharts
              stats={stats}
              distribution={distribution}
              onRangeClick={handleRangeClick}
            />

            {selectedRange && (
              <Card className="content-card" style={{ marginTop: 24 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <Title level={5} style={{ margin: 0 }}>{getRangeTitle()}</Title>
                  <Button
                    type="text"
                    icon={<CloseOutlined />}
                    onClick={() => setSelectedRange(null)}
                  >
                    关闭
                  </Button>
                </div>
                <Table
                  columns={detailColumns}
                  dataSource={detailData}
                  rowKey={(record, index) => `${record.studentA}-${record.studentB}-${index}`}
                  pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                  size="middle"
                />
              </Card>
            )}
          </div>
        )}

        {!loading && rawMatrix.length === 0 && selectedAssignment && (
          <Empty
            description={<span style={{ color: '#64748b' }}>该作业暂无提交记录或相似度数据</span>}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ marginTop: 40 }}
          />
        )}

        <Modal
          title={getRangeTitle()}
          open={detailModalVisible}
          onCancel={() => setDetailModalVisible(false)}
          footer={[
            <Button key="close" onClick={() => setDetailModalVisible(false)}>
              关闭
            </Button>
          ]}
          width={800}
        >
          <Table
            columns={detailColumns}
            dataSource={detailData}
            rowKey={(record, index) => `${record.studentA}-${record.studentB}-${index}`}
            pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
            size="middle"
          />
        </Modal>

        <Divider style={{ margin: '24px 0' }} />

        <Card className="content-card" style={{ marginTop: 16 }}>
          <Title level={5} style={{ marginBottom: 16 }}>
            数据导出
          </Title>

          <Space wrap>
            <Button
              icon={<DownloadOutlined />}
              onClick={() => exportStudentGrades('csv')}
              loading={exportingGrades}
            >
              导出成绩CSV
            </Button>

            <Button
              icon={<DownloadOutlined />}
              onClick={() => exportStudentGrades('json')}
              loading={exportingGrades}
            >
              导出成绩JSON
            </Button>
          </Space>
        </Card>
      </Card>
    </div>
  );
};

export default TeacherStatistics;