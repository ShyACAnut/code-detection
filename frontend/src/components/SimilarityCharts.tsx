import ReactECharts from 'echarts-for-react';
import { Card, Row, Col, Statistic } from 'antd';
import { PieChartOutlined, BarChartOutlined } from '@ant-design/icons';

interface SimilarityStats {
  highCount: number;      // 高相似度 (>=80%)
  mediumCount: number;    // 中等相似度 (50%-79%)
  lowCount: number;       // 低相似度 (<50%)
  totalPairs: number;
}

interface PlagiarismDistribution {
  ranges: string[];
  counts: number[];
}

interface SimilarityChartsProps {
  stats: SimilarityStats;
  distribution: PlagiarismDistribution;
  onRangeClick?: (range: string) => void;
}

export const SimilarityCharts: React.FC<SimilarityChartsProps> = ({ stats, distribution, onRangeClick }) => {
  const handlePieClick = (params: any) => {
    if (onRangeClick) {
      const name = params.name as string;
      let range = '';
      if (name.includes('高相似')) {
        range = 'high';
      } else if (name.includes('中相似')) {
        range = 'medium';
      } else if (name.includes('低相似')) {
        range = 'low';
      }
      onRangeClick(range);
    }
  };

  const pieOption = {
    title: {
      text: '相似度分布（点击查看详情）',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
        color: '#334155'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'middle',
      textStyle: {
        color: '#64748b'
      }
    },
    color: ['#dc2626', '#d97706', '#059669'],
    series: [
      {
        name: '相似度',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '55%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          fontSize: 12
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.2)'
          }
        },
        data: [
          { value: stats.highCount, name: '高相似 (≥80%)' },
          { value: stats.mediumCount, name: '中相似 (50%-79%)' },
          { value: stats.lowCount, name: '低相似 (<50%)' }
        ]
      }
    ]
  };

  const onEvents = {
    click: handlePieClick
  };

  const barOption = {
    title: {
      text: '相似度区间分布（点击查看详情）',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
        color: '#334155'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: '{b}: {c} 对'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: distribution.ranges,
      axisLabel: {
        color: '#64748b',
        rotate: 30
      },
      axisLine: {
        lineStyle: {
          color: '#e2e8f0'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '配对数',
      nameTextStyle: {
        color: '#64748b'
      },
      axisLabel: {
        color: '#64748b'
      },
      axisLine: {
        lineStyle: {
          color: '#e2e8f0'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#f1f5f9'
        }
      }
    },
    series: [
      {
        name: '配对数',
        type: 'bar',
        barWidth: '50%',
        data: distribution.counts,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#60a5fa' }
            ]
          }
        },
        emphasis: {
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: '#2563eb' },
                { offset: 1, color: '#3b82f6' }
              ]
            }
          }
        },
        label: {
          show: true,
          position: 'top',
          color: '#64748b',
          fontSize: 12
        }
      }
    ]
  };

  const onBarEvents = {
    click: (params: any) => {
      if (onRangeClick) {
        onRangeClick(params.name as string);
      }
    }
  };

  const highPercentage = stats.totalPairs > 0 ? ((stats.highCount / stats.totalPairs) * 100).toFixed(1) : '0';
  const mediumPercentage = stats.totalPairs > 0 ? ((stats.mediumCount / stats.totalPairs) * 100).toFixed(1) : '0';
  const lowPercentage = stats.totalPairs > 0 ? ((stats.lowCount / stats.totalPairs) * 100).toFixed(1) : '0';

  return (
    <Row gutter={16}>
      <Col span={12}>
        <Card
          className="content-card"
          title={
            <span>
              <PieChartOutlined className="page-title-icon" />
              相似度饼图
            </span>
          }
        >
          <ReactECharts option={pieOption} style={{ height: 300 }} onEvents={onEvents} />
          <div style={{ marginTop: 16, display: 'flex', justifyContent: 'space-around' }}>
            <Statistic
              title="高相似"
              value={stats.highCount}
              suffix={`对 (${highPercentage}%)`}
              valueStyle={{ color: '#dc2626' }}
            />
            <Statistic
              title="中相似"
              value={stats.mediumCount}
              suffix={`对 (${mediumPercentage}%)`}
              valueStyle={{ color: '#d97706' }}
            />
            <Statistic
              title="低相似"
              value={stats.lowCount}
              suffix={`对 (${lowPercentage}%)`}
              valueStyle={{ color: '#059669' }}
            />
          </div>
        </Card>
      </Col>
      <Col span={12}>
        <Card
          className="content-card"
          title={
            <span>
              <BarChartOutlined className="page-title-icon" />
              抄袭分布柱状图
            </span>
          }
        >
          <ReactECharts option={barOption} style={{ height: 300 }} onEvents={onBarEvents} />
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Statistic
              title="总配对数"
              value={stats.totalPairs}
              valueStyle={{ color: '#3b82f6' }}
            />
          </div>
        </Card>
      </Col>
    </Row>
  );
};

export default SimilarityCharts;