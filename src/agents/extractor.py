#!/usr/bin/env python3
"""
简历解析智能体 - 负责从PDF、Word等文档中提取结构化简历信息
"""

import asyncio
import json
from typing import Dict, Any, List
from autogen_agentchat.agents import AssistantAgent
from src.core.model_client import create_default_client
from src.core.prompts import extraction_agent_prompt
from src.core.state_models import ResumeData, State
from src.plugins._ocr import OCREngine
from src.utils.log_utils import setup_logger

# 配置日志
logger = setup_logger(__name__)


class ExtractionAgent:
    """简历解析智能体"""
    
    def __init__(self, model_client=None):
        """初始化解析智能体"""
        self.model_client = model_client or create_default_client()
        self.extraction_agent = AssistantAgent(
            name="extraction_agent",
            model_client=self.model_client,
            system_message=extraction_agent_prompt
        )
        self.ocr_engine = OCREngine()

    async def extract_resume_data(self, resume_path: str) -> ResumeData:
        """从简历文件中提取结构化数据"""
        try:
            # 使用OCR引擎解析文档
            content = await self.ocr_engine.extract_text(resume_path)
            
            # 构造提取任务
            extraction_task = f"""
            请从以下简历内容中提取结构化信息：

            {content}

            提取以下字段：
            1. 姓名
            2. 邮箱
            3. 电话
            4. 教育经历（学校、专业、时间、学位）
            5. 工作经历（公司、职位、时间、主要职责）
            6. 技能列表
            7. 项目经历（项目名称、时间、技术栈、描述）
            8. 个人简介/求职意向

            请返回JSON格式的数据。
            """
            
            # 执行提取任务
            response = await self.extraction_agent.run(task=extraction_task)
            
            # 解析响应
            extracted_json = self._parse_json_response(response.messages[-1].content)
            
            # 创建ResumeData对象
            resume_data = ResumeData(
                resume_id=resume_path.split("/")[-1],  # 使用文件名作为ID
                name=extracted_json.get("name", ""),
                email=extracted_json.get("email", ""),
                phone=extracted_json.get("phone", ""),
                education=extracted_json.get("education", []),
                work_experience=extracted_json.get("work_experience", []),
                skills=extracted_json.get("skills", []),
                projects=extracted_json.get("projects", []),
                summary=extracted_json.get("summary", "")
            )
            
            return resume_data
            
        except Exception as e:
            logger.error(f"简历解析失败: {str(e)}")
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
                    "name": "",
                    "email": "",
                    "phone": "",
                    "education": [],
                    "work_experience": [],
                    "skills": [],
                    "projects": [],
                    "summary": ""
                }

    async def run(self, resume_path: str) -> ResumeData:
        """统一接口方法"""
        return await self.extract_resume_data(resume_path)


async def extraction_node(state: State) -> State:
    """提取节点 - 解析简历"""
    current_state = state['value']
    logger.info(f"执行简历解析节点，处理简历文件")
    
    try:
        extraction_agent = ExtractionAgent()
        extracted_data = []
        
        # 解析每个简历文件
        for resume_path in current_state.resume_list:
            resume_data = await extraction_agent.run(resume_path)
            extracted_data.append(resume_data)
        
        updated_state = current_state.copy(update={
            "current_step": "extracting",
            "extracted_data": extracted_data,
            "agent_logs": {**current_state.agent_logs, "extraction_agent": f"成功解析 {len(extracted_data)} 份简历"}
        })
        
        state['value'] = updated_state
        return state
    except Exception as e:
        logger.error(f"提取节点执行失败: {str(e)}")
        updated_state = current_state.copy(update={
            "current_step": "failed",
            "error": current_state.error.copy(update={"extraction_node_error": str(e)}) if current_state.error else None
        })
        state['value'] = updated_state
        return state


async def main():
    """主测试函数"""
    # 创建解析智能体
    agent = ExtractionAgent()
    
    # 示例使用
    # resume_data = await agent.run("path/to/resume.pdf")
    # print(resume_data)


if __name__ == "__main__":
    asyncio.run(main())
