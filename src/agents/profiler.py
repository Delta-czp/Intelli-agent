#!/usr/bin/env python3
"""
候选人画像构建智能体 - 基于提取的简历信息构建动态标签体系和候选人画像
"""

import asyncio
import json
from typing import List, Dict, Any
from autogen_agentchat.agents import AssistantAgent
from src.core.model_client import create_default_client
from src.core.prompts import profiling_agent_prompt
from src.core.state_models import ResumeData, CandidateProfile, State
from src.utils.log_utils import setup_logger

# 配置日志
logger = setup_logger(__name__)


class ProfilingAgent:
    """候选人画像构建智能体"""
    
    def __init__(self, model_client=None):
        """初始化画像构建智能体"""
        self.model_client = model_client or create_default_client()
        self.profiling_agent = AssistantAgent(
            name="profiling_agent",
            model_client=self.model_client,
            system_message=profiling_agent_prompt
        )

    async def build_candidate_profile(self, resume_data: ResumeData, job_requirements: str) -> CandidateProfile:
        """基于简历数据和岗位要求构建候选人画像"""
        try:
            # 构造画像构建任务
            profiling_task = f"""
            基于以下候选人简历信息和岗位要求，构建详细的候选人画像：

            候选人简历信息：
            {resume_data.model_dump_json(indent=2)}

            岗位要求：
            {job_requirements}

            请分析并生成以下信息：
            1. 核心能力
            2. 经验总结
            3. 技能匹配度（对岗位要求中各项技能的匹配分数，0-1之间）
            4. 文化匹配度（0-1之间的分数）
            5. 综合评分（0-1之间的分数）
            6. 主要优势
            7. 待改进点
            8. 推荐意见

            请返回JSON格式的数据。
            """
            
            # 执行画像构建任务
            response = await self.profiling_agent.run(task=profiling_task)
            
            # 解析响应
            profile_json = self._parse_json_response(response.messages[-1].content)
            
            # 创建CandidateProfile对象
            candidate_profile = CandidateProfile(
                resume_id=resume_data.resume_id,
                name=resume_data.name,
                core_competencies=profile_json.get("core_competencies", []),
                experience_summary=profile_json.get("experience_summary", ""),
                skill_alignment=profile_json.get("skill_alignment", {}),
                cultural_fit_score=profile_json.get("cultural_fit_score", 0.0),
                overall_score=profile_json.get("overall_score", 0.0),
                strengths=profile_json.get("strengths", []),
                weaknesses=profile_json.get("weaknesses", []),
                recommendations=profile_json.get("recommendations", [])
            )
            
            return candidate_profile
            
        except Exception as e:
            logger.error(f"候选人画像构建失败: {str(e)}")
            raise

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析LLM返回的JSON响应"""
        try:
            # 尝试直接解析JSON
            if response.strip().startswith("```"):
                # 提取代码块中的JSON
                start_idx = response.find("{")
                end_idx = response.rfind("}") + 1
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return json.loads(response)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试使用正则表达式提取
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # 返回默认值
                return {
                    "core_competencies": [],
                    "experience_summary": "",
                    "skill_alignment": {},
                    "cultural_fit_score": 0.0,
                    "overall_score": 0.0,
                    "strengths": [],
                    "weaknesses": [],
                    "recommendations": []
                }

    async def run(self, resume_data: ResumeData, job_requirements: str) -> CandidateProfile:
        """统一接口方法"""
        return await self.build_candidate_profile(resume_data, job_requirements)


async def profiling_node(state: State) -> State:
    """画像节点 - 构建候选人画像"""
    current_state = state['value']
    logger.info(f"执行画像构建节点")
    
    try:
        profiling_agent = ProfilingAgent()
        candidate_profiles = []
        
        # 为每个候选人构建画像
        for resume_data in current_state.extracted_data:
            profile = await profiling_agent.run(resume_data, current_state.user_request)
            candidate_profiles.append(profile)
        
        updated_state = current_state.copy(update={
            "current_step": "profiling",
            "candidate_profiles": candidate_profiles,
            "agent_logs": {**current_state.agent_logs, "profiling_agent": f"成功构建 {len(candidate_profiles)} 个候选人画像"}
        })
        
        state['value'] = updated_state
        return state
    except Exception as e:
        logger.error(f"画像节点执行失败: {str(e)}")
        updated_state = current_state.copy(update={
            "current_step": "failed",
            "error": current_state.error.copy(update={"profiling_node_error": str(e)}) if current_state.error else None
        })
        state['value'] = updated_state
        return state


async def main():
    """主测试函数"""
    # 创建画像构建智能体
    agent = ProfilingAgent()
    
    # 示例使用
    # resume_data = ResumeData(...)
    # profile = await agent.run(resume_data, "岗位要求...")
    # print(profile)


if __name__ == "__main__":
    asyncio.run(main())
