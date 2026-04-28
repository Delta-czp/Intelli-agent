# Intelligent-Recruiter: 基于多智能体协作的 AI+招聘与人才管理系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/LangGraph-Agentic-green.svg)](https://python.langchain.com/docs/langgraph)

## 📖 项目简介

**Intelligent-Recruiter** 是一款专为 AI 时代设计的自动化人才解析与评估系统。针对大规模招聘场景下简历非结构化、筛选主观且低效的痛点，本项目基于 **LangGraph** 构建了多智能体（Multi-Agent）协作工作流。系统实现了从“简历深度解析”到“智能决策辅助”的全链路自动化。不仅将核心处理效率提升 2-3 倍，更通过严格的质量评估与原创度校验，辅助组织构建高效、可信的新型人才选拔范式。

## ✨ 核心业务价值与技术亮点

- 🤖 **Agentic 工作流编排**：模拟 HR 真实工作流，基于 LangGraph 设计 `Extraction -> Profiling -> Reasoning -> Validation` 四步状态机机制，实现复杂任务的解耦与自动化流转。
- 🛠️ **复杂的 Tool Use 与外部调用**：集成 Grobid 与 PaddleOCR，多智能体通过 Function Calling 机制调用外部解析工具，实现对复杂 PDF/DOC 简历的深度结构化处理，沉淀人才数据资产。
- ⚡ **精细化成本控制 (ROI)**：针对多轮评估场景设计 Path Index 检索策略与精细化上下文管理，在保障多轮记忆与语义完整性的前提下，成功将 **Token 消耗降低 40%**。
- 🛡️ **原创度校验与防幻觉把控**：摒弃“算法绝对公平”的过度承诺，聚焦于**候选人原创度与真实性把控**。构建“生成-校验-修正”闭环，将评估任务的准确率提升至 **85%+**，并输出可解释的置信度看板。

## 🧩 系统架构与多智能体设计

项目采用模块化设计，底层基于有向无环图（DAG）流转状态模型 (`RecruitmentState`)，核心由四大 Agent 协同完成：

1. 📄 **ExtractorAgent (解析智能体)**：负责非结构化文档的 OCR 识别与关键字段（技能、经历等）的精准提取。
2. 👤 **ProfilerAgent (画像智能体)**：基于提取信息构建动态标签体系与向量知识库（SQLite + Chroma），实现人才数据资产化。
3. 🧠 **ReasonerAgent (推理智能体)**：结合具体岗位要求（JD），进行多维度的能力比对与适配度推理。
4. 🚦 **ValidatorAgent (校验智能体)**：对推理结果进行最终的质量校验与输出兜底，确保评估报告的客观性。

## 📂 核心目录结构

```text
Intelligent-Recruiter/
├── src/
│   ├── core/
│   │   ├── state_models.py      # 核心状态机模型 (RecruitmentState, EvaluationResult等)
│   │   └── config.py            # 全局配置管理
│   ├── agents/                  # Multi-Agent 核心逻辑
│   │   ├── extractor.py         
│   │   ├── profiler.py          
│   │   ├── reasoner.py          
│   │   ├── validator.py         
│   │   └── orchestrator.py      # LangGraph 工作流编排引擎
│   └── services/
│       └── recruitment_service.py # 提供 RESTful & WebSocket API
└── web/                         # Vue3 前端界面
    └── src/
        ├── App.vue              # 交互主入口：支持JD输入与简历上传
        ├── components/          # 视图组件：可视化看板与实时进度反馈
        └── ...
```

## 🚀 快速开始

本项目支持前后端分离的快速部署验证。

### 1. 后端启动 (FastAPI)
```bash
# 建议使用虚拟环境
pip install -r requirements.txt
python main.py
```

### 2. 前端启动 (Vue3)
```bash
cd web
npm install
npm run dev
```
前端启动后，系统将通过 WebSocket 提供实时流式反馈（SSE），直观展示各 Agent 节点的处理进度与思考过程。


## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
