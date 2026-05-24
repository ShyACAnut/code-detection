import React, { useState, useEffect } from 'react';
import { Card, Form, Input, InputNumber, Button, message, Switch, Space, Typography, Divider, Alert, Tag } from 'antd';
import { SaveOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';
import api from '../../api/client';
import '../../styles/global.css';

const { Title, Text } = Typography;

interface SystemConfig {
  similarity_threshold: number;
  llm_model_name: string;
  syntax_weight: number;
  semantic_weight: number;
  max_file_size: number;
  auto_detection_enabled: boolean;
  notification_enabled: boolean;
  updated_at?: string;
}

const SystemSettings: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<SystemConfig>({
    similarity_threshold: 80,
    llm_model_name: 'glm-4.7',
    syntax_weight: 0.4,
    semantic_weight: 0.6,
    max_file_size: 10,
    auto_detection_enabled: true,
    notification_enabled: true,
  });
  const [form] = Form.useForm();

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const response = await api.get('/admin/config');
      setConfig({
        ...config,
        similarity_threshold: response.data.similarity_threshold || 80,
        llm_model_name: response.data.llm_model_name || 'glm-4.7',
        syntax_weight: response.data.syntax_weight || 0.4,
        semantic_weight: response.data.semantic_weight || 0.6,
        updated_at: response.data.updated_at,
      });
      form.setFieldsValue({
        similarity_threshold: response.data.similarity_threshold || 80,
        llm_model_name: response.data.llm_model_name || 'glm-4.7',
        syntax_weight: response.data.syntax_weight || 0.4,
        semantic_weight: response.data.semantic_weight || 0.6,
      });
    } catch (error) {
      message.error('获取配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: any) => {
    setSaving(true);
    try {
      // 验证权重和为1
      if (Math.abs((values.syntax_weight || 0) + (values.semantic_weight || 0) - 1) > 0.001) {
        message.error('语法权重和语义权重之和必须等于1');
        setSaving(false);
        return;
      }

      await api.put('/admin/config', {
        similarity_threshold: values.similarity_threshold,
        llm_model_name: values.llm_model_name,
        syntax_weight: values.syntax_weight,
        semantic_weight: values.semantic_weight,
      });

      // 保存其他配置（如果有的话）
      if (values.max_file_size !== undefined) {
        // 这可能需要额外的API端点
      }

      message.success('配置保存成功');
      fetchConfig();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    form.resetFields();
    form.setFieldsValue({
      similarity_threshold: 80,
      llm_model_name: 'glm-4.7',
      syntax_weight: 0.4,
      semantic_weight: 0.6,
    });
  };

  return (
    <div className="page-fade-in">
      <Card className="content-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={4} className="page-title" style={{ margin: 0 }}>
            <SettingOutlined className="page-title-icon" />
            系统参数配置
          </Title>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchConfig} loading={loading}>
              刷新
            </Button>
          </Space>
        </div>

        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
          message="配置说明"
          description="以下配置将影响整个系统的检测行为。请谨慎修改，修改后系统将自动应用新配置。"
        />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            similarity_threshold: config.similarity_threshold,
            llm_model_name: config.llm_model_name,
            syntax_weight: config.syntax_weight,
            semantic_weight: config.semantic_weight,
          }}
          style={{ maxWidth: 600 }}
        >
          <Divider>检测参数</Divider>

          <Form.Item
            name="similarity_threshold"
            label="默认检测阈值 (%)"
            extra="超过此阈值的提交将被标记为高风险"
          >
            <InputNumber min={0} max={100} style={{ width: 200 }} />
          </Form.Item>

          <Form.Item
            name="llm_model_name"
            label="LLM 模型名称"
            extra="用于语义分析的模型，如 glm-4.7、gpt-3.5-turbo 等"
          >
            <Input style={{ width: 300 }} placeholder="glm-4.7" />
          </Form.Item>

          <Divider>评分权重</Divider>

          <Form.Item
            name="syntax_weight"
            label="语法相似度权重"
            extra="语法相似度在最终评分中的占比"
          >
            <InputNumber min={0} max={1} step={0.1} style={{ width: 200 }} precision={2} />
          </Form.Item>

          <Form.Item
            name="semantic_weight"
            label="语义相似度权重"
            extra="语义相似度在最终评分中的占比"
          >
            <InputNumber min={0} max={1} step={0.1} style={{ width: 200 }} precision={2} />
          </Form.Item>

          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            message="权重说明"
            description={
              <span>
                语法权重和语义权重之和必须等于1。例如：语法0.4 + 语义0.6 = 1.0
                <br />
                <Text type="secondary">
                  语法检测：基于代码结构、关键字、变量名等表面特征
                </Text>
                <br />
                <Text type="secondary">
                  语义检测：基于代码含义、逻辑流程、功能实现等深层特征
                </Text>
              </span>
            }
          />

          <Divider>当前配置</Divider>

          <Card size="small" style={{ backgroundColor: '#f8fafc', marginBottom: 24 }}>
            <Space orientation="vertical">
              <div>
                <Text type="secondary">检测阈值：</Text>
                <Tag color="blue">{config.similarity_threshold}%</Tag>
              </div>
              <div>
                <Text type="secondary">LLM模型：</Text>
                <Tag color="green">{config.llm_model_name}</Tag>
              </div>
              <div>
                <Text type="secondary">权重配置：</Text>
                <Text>
                  语法 {config.syntax_weight} + 语义 {config.semantic_weight} = 1.0
                </Text>
              </div>
              {config.updated_at && (
                <div>
                  <Text type="secondary">最后更新：</Text>
                  <Text>{config.updated_at}</Text>
                </div>
              )}
            </Space>
          </Card>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                loading={saving}
                className="btn-primary"
              >
                保存配置
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleReset}
                className="btn-ghost"
              >
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default SystemSettings;