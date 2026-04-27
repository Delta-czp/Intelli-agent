#!/usr/bin/env python3
"""
候选人推理评估智能体 - 模拟HR逻辑进行多维度能力比对，生成结构化评估意见
"""

import asyncio
import json
from typing import List, Dict, Any
from autogen_agentchat.agents import AssistantAgent
from src.core.model_client import create_default_client
from src.core.prompts import reasoning_agent_prompt
from src.core.state_models import CandidateProfile, State
from src.utils.log_utils import setup_logger

# 配置日志
logger = setup_logger(__name__)


class ReasoningAgent:
    """候选人推理评估智能体"""
    
    def __init__(self, model_client=None):
        """初始化推理评估智能体"""
        self.model_client = model_client or create_default_client()
        self.reasoning_agent = AssistantAgent(
            name="reasoning_agent",
            model_client=self.model_client,
            system_message=reasoning_agent_prompt
        )

    async def evaluate_candidate(self, candidate_profile: CandidateProfile, job_requirements: str) -> str:
        """对候选人进行多维度评估"""
        try:
            # 构造评估任务
            evaluation_task = f"""
            基于以下候选人画像和岗位要求，进行多维度能力比对和综合评估：

            候选人画像：
            {candidate_profile.model_dump_json(indent=2)}

            岗位要求：
            {job_requirements}

            请从以下维度进行评估：
            1. 技术能力匹配度
            2. 经验适配性
            3. 文化契合度
            4. 发展潜力
            5. 综合评价

            请提供具体的评估理由和建议。
            """
            
            # 执行评估任务
            response = await self.reasoning_agent.run(task=evaluation_task)
            
            # 返回评估结果
            evaluation_result = response.messages[-1].content
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"候选人推理评估失败: {str(e)}")
            raise

    async def compare_candidates(self, profiles: List[CandidateProfile], job_requirements: str) -> str:
        """比较多个候选人"""
        try:
            # 构造比较任务
            profiles_json = [profile.model_dump() for profile in profiles]
            
            comparison_task = f"""
            基于以下候选人画像列表和岗位要求，进行横向比较分析：

            候选人画像列表：
            {json.dumps(profiles_json, indent=2, ensure_ascii=False)}

            岗位要求：
            {job_requirements}

            请提供：
            1. 各候选人的优劣势对比
            2. 推荐排序
            3. 录用建议
            """
            
            # 执行比较任务
            response = await self.reasoning_agent.run(task=comparison_task)
            
            # 返回比较结果
            comparison_result = response.messages[-1].content
            
            return comparison_result
            
        except Exception as e:
            logger.error(f"候选人比较评估失败: {str(e)}")
            raise

    async def run(self, candidate_profile: CandidateProfile, job_requirements: str) -> str:
        """统一接口方法"""
        return await self.evaluate_candidate(candidate_profile, job_requirements)


async def reasoning_node(state: State) -> State:
    """推理节点 - 评估候选人"""
    current_state = state['value']
    logger.info(f"执行推理评估节点")
    
    try:
        reasoning_agent = ReasoningAgent()
        assessment_results = []
        
        # 对每个候选人进行评估
        for profile in current_state.candidate_profiles:
            assessment = await reasoning_agent.run(profile, current_state.user_request)
            assessment_results.append(assessment)
        
        # 生成整体比较分析
        comparison_result = await reasoning_agent.compare_candidates(
            current_state.candidate_profiles, 
            current_state.user_request
        )
        
        updated_state = current_state.copy(update={
            "current_step": "reasoning",
            "assessment_results": comparison_result,
            "agent_logs": {**current_state.agent_logs, "reasoning_agent": "完成候选人评估和比较分析"}
        })
        
        state['value'] = updated_state
        return state
    except Exception as e:
        logger.error(f"推理节点执行失败: {str(e)}")
        updated_state = current_state.copy(update={
            "current_step": "failed",
            "error": current_state.error.copy(update={"reasoning_node_error": str(e)}) if current_state.error else None
        })
        state['value'] = updated_state
        return state


async def main():
    """主测试函数"""
    # 创建推理评估智能体
    agent = ReasoningAgent()
    
    # 示例使用
    # profile = CandidateProfile(...)
    # evaluation = await agent.run(profile, "岗位要求...")
    # print(evaluation)


if __name__ == "__main__":
    asyncio.run(main())
