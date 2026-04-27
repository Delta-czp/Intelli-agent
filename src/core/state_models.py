from asyncio import Queue
from typing import List, Dict, Any, Optional,TypedDict
from pydantic import BaseModel, Field
from enum import Enum


class BackToFrontData(BaseModel):
    step: str
    state: str
    data: Any


class ExecutionState(str, Enum):
    """工作流执行状态枚举"""
    INITIALIZING = "initializing"
    EXTRACTING = "extracting"  # 简历解析
    PROFILING = "profiling"    # 画像构建
    REASONING = "reasoning"    # 推理评估
    VALIDATING = "validating"  # 质量校验
    COMPLETED = "completed"
    FAILED = "failed"
    FINISHED = "finished"

class ResumeData(BaseModel):
    """简历数据模型"""
    resume_id: str  # 简历唯一标识
    name: str       # 候选人姓名
    email: str      # 邮箱
    phone: str      # 电话
    education: List[Dict[str, str]]  # 教育经历
    work_experience: List[Dict[str, str]]  # 工作经历
    skills: List[str]  # 技能列表
    projects: List[Dict[str, str]]  # 项目经历
    summary: str  # 个人简介


class CandidateProfile(BaseModel):
    """候选人画像模型"""
    resume_id: str
    name: str
    core_competencies: List[str]  # 核心能力
    experience_summary: str  # 经验总结
    skill_alignment: Dict[str, float]  # 技能匹配度
    cultural_fit_score: float  # 文化匹配度
    overall_score: float  # 综合评分
    strengths: List[str]  # 优势
    weaknesses: List[str]  # 待改进点
    recommendations: List[str]  # 推荐意见

class NodeError(BaseModel):
    extraction_node_error: Optional[str] = Field(default=None, description="解析节点错误信息")
    profiling_node_error: Optional[str] = Field(default=None, description="画像节点错误信息")
    reasoning_node_error: Optional[str] = Field(default=None, description="推理节点错误信息")
    validation_node_error: Optional[str] = Field(default=None, description="校验节点错误信息")
    error: Optional[str] = Field(default=None, description="错误信息")

class RecruitmentAgentState(BaseModel):
    """招聘智能体工作流的全局状态对象"""
    # 用户输入
    frontend_data: Optional[BackToFrontData] = Field(default=None, description="前端展示数据")
    agent_logs: Dict[str, str] = Field(default_factory=dict, description="各智能体执行日志，key为智能体名称")
    user_request: str = Field(description="用户的原始输入请求，如岗位需求")
    max_candidates: int = Field(default=50, description="最大候选人数量")
    
    # 执行状态
    current_step: ExecutionState = Field(default=ExecutionState.INITIALIZING, description="当前执行步骤")
    error: Optional[NodeError] = Field(default=None, description="错误信息")
    
    # 数据流
    resume_list: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="解析后的简历列表")
    resume_contents: Optional[Dict[str, str]] = Field(default_factory=dict, description="简历内容字典, key: resume_id, value: 内容")
    extracted_data: Optional[List[ResumeData]] = Field(default_factory=list, description="提取后的简历数据列表")
    candidate_profiles: Optional[List[CandidateProfile]] = Field(default_factory=list, description="候选人画像列表")
    assessment_results: Optional[str] = Field(default=None, description="评估结果")
    final_recommendations: Optional[str] = Field(default=None, description="最终推荐意见")
    validated_results: Optional[str] = Field(default=None, description="验证后的结果")
    
    # 配置与上下文
    llm_provider: Any = Field(default=None, description="LLM提供者实例", exclude=True)  # 排除序列化
    config: Dict[str, Any] = Field(default_factory=dict, description="运行时配置")

class State(TypedDict):
    """LangGraph兼容的状态定义"""
    state_queue: Queue
    value: RecruitmentAgentState

class ConfigSchema(TypedDict):
    """LangGraph兼容的配置定义"""
    state_queue: Queue
    value: Dict[str, Any]
