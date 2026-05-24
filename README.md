# AI Code Detection System

基于大语言模型和语法分析的代码相似性检测系统

## 项目简介

这是一个智能代码相似性检测系统，采用四层过滤策略结合LLM大模型进行深度语义分析，适用于教育场景下的作业抄袭检测。

## 技术栈

### 后端
- **FastAPI** - Web框架
- **SQLAlchemy** - ORM数据库
- **LangChain + ChatZhipuAI** - 大模型分析
- **FAISS** - 向量数据库
- **HuggingFace Embeddings** - 代码向量化

### 前端
- **React 19** + TypeScript
- **Ant Design 6** - UI组件库
- **Monaco Editor** - 代码编辑器
- **ECharts** - 数据可视化

## 核心功能

- 多语言代码相似性检测（Python, Java, JavaScript, C/C++, C#, Go）
- 四层过滤检测算法（向量检索 + 语法分析 + 语义分析 + 智能评分）
- 学生作业管理
- 教师批量分析
- 相似度矩阵可视化
- PDF报告生成
- 编程伦理学习模块

## 项目结构

```
aicode/
├── backend/              # 后端代码
│   ├── routers/         # API路由
│   ├── detectors/       # 检测器模块
│   ├── pipeline/        # 分析管道
│   ├── workflow/        # 工作流
│   └── ...
├── frontend/            # 前端代码
│   ├── pages/          # 页面组件
│   ├── components/     # 公共组件
│   └── ...
├── docs/               # 文档
└── images/             # 图片资源
```

## 安装与运行

### 后端
```bash
cd backend
pip install -r requirements.txt
python start_server.py
```

### 前端
```bash
cd frontend
npm install
npm start
```

## 使用说明

### 教师端
1. 创建作业
2. 批量上传学生代码
3. 发起相似性检测
4. 查看检测报告

### 学生端
1. 查看作业列表
2. 提交代码
3. 代码自查
4. 完成编程伦理学习

## 许可证

MIT License

## 作者

ShyACAnut
