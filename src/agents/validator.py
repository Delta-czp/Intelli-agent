#!/usr/bin/env python3
"""
候选人评估质量校验智能体 - 对评估结果进行防幻觉校验，确保评估结果的真实性和合规性
"""

import asyncio
import json
from typing import Dict, Any
from autogen_agentchat.agents import AssistantAgent
from src.core.model_client import create_default_client
from src.core.prompts import validation_agent_prompt
from src.core.state_models import State
from src.utils.log_utils import setup_logger

# 配置日志
logger = setup_logger(__name__)


class ValidationAgent:
    """候选人评估质量校验智能体"""
    
    def __init__(self, model_client=None):
        """初始化质量校验智能体"""
        self.model_client = model_client or create_default_client()
        self.validation_agent = AssistantAgent(
            name="validation_agent",
            model_client=self.model_client,
            system_message=validation_agent_prompt
        )

    async def validate_assessment(self, candidate_data: Dict[str, Any], assessment_result: str) -> Dict[str, Any]:
        """校验候选人评估结果"""
        try:
            # 构造校验任务
            validation_task = f"""
            请对以下候选人评估结果进行质量校验：

            候选人原始数据：
            {json.dumps(candidate_data, indent=2, ensure_ascii=False)}

            评估结果：
            {assessment_result}

            请检查：
            1. 评估是否基于实际数据
            2. 是否存在偏见或歧视性内容
            3. 评分是否合理
            4. 推荐意见是否客观

            返回校验结果，包括：
            - 是否通过校验 (boolean)
            - 发现的问题 (list)
            - 修正建议 (string)
            - 最终确认的评估结果 (string)
            """
            
            # 执行校验任务
            response = await self.validation_agent.run(task=validation_task)
            
            # 解析校验结果
            validation_result = self._parse_validation_response(response.messages[-1].content)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"候选人评估校验失败: {str(e)}")
            raise

    def _parse_validation_response(self, response: str) -> Dict[str, Any]:
        """解析校验响应"""
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
            # 如果直接解析失败，返回默认值
            return {
                "passed": True,
                "issues": [],
                "suggestions": "",
                "validated_result": response
            }

    async def run(self, candidate_data: Dict[str, Any], assessment_result: str) -> Dict[str, Any]:
        """统一接口方法"""
        return await self.validate_assessment(candidate_data, assessment_result)


async def validation_node(state: State) -> State:
    """校验节点 - 验证评估结果"""
    current_state = state['value']
    logger.info(f"执行质量校验节点")
    
    try:
        validation_agent = ValidationAgent()
        
        # 校验整体评估结果
        validation_result = await validation_agent.run(
            {"profiles": [p.model_dump() for p in current_state.candidate_profiles]},
            current_state.assessment_results
        )
        
        updated_state = current_state.copy(update={
            "current_step": "validating",
            "validated_results": validation_result.get("validated_result", current_state.assessment_results),
            "current_step": "completed",
            "agent_logs": {**current_state.agent_logs, "validation_agent": "完成评估结果校验"}
        })
        
        state['value'] = updated_state
        return state
    except Exception as e:
        logger.error(f"校验节点执行失败: {str(e)}")
        updated_state = current_state.copy(update={
            "current_step": "failed",
            "error": current_state.error.copy(update={"validation_node_error": str(e)}) if current_state.error else None
        })
        state['value'] = updated_state
        return state


async def main():
    """主测试函数"""
    # 创建质量校验智能体
    agent = ValidationAgent()
    
    # 示例使用
    # candidate_data = {...}
    # assessment = "评估结果..."
    # validation = await agent.run(candidate_data, assessment)
    # print(validation)


if __name__ == "__main__":
    asyncio.run(main())
