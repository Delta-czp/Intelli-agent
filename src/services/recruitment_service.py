#!/usr/bin/env python3
"""
招聘服务 - 提供招聘相关的API和服务功能
"""

import asyncio
from typing import List, Dict, Any
from fastapi import UploadFile, File, HTTPException
from src.agents.orchestrator import RecruitmentAgentOrchestrator
from src.core.state_models import RecruitmentAgentState, BackToFrontData
from src.utils.log_utils import setup_logger
from asyncio import Queue

# 配置日志
logger = setup_logger(__name__)


class RecruitmentService:
    """招聘服务类"""
    
    def __init__(self):
        """初始化招聘服务"""
        self.upload_dir = "uploads"
        self.state_queues = {}  # 存储不同任务的状态队列
    
    async def upload_resumes(self, files: List[UploadFile]) -> List[str]:
        """上传简历文件"""
        file_paths = []
        for file in files:
            # 验证文件类型
            if not file.filename.lower().endswith(('.pdf', '.doc', '.docx')):
                raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.filename}")
            
            # 保存文件
            import os
            import uuid
            os.makedirs(self.upload_dir, exist_ok=True)
            
            file_id = str(uuid.uuid4())
            file_extension = os.path.splitext(file.filename)[1]
            file_path = f"{self.upload_dir}/{file_id}{file_extension}"
            
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            file_paths.append(file_path)
            logger.info(f"已上传简历: {file_path}")
        
        return file_paths
    
    async def start_recruitment_process(self, job_description: str, resume_paths: List[str], task_id: str) -> Dict[str, Any]:
        """启动招聘流程"""
        try:
            # 创建状态队列用于实时通信
            state_queue = Queue()
            self.state_queues[task_id] = state_queue
            
            # 创建招聘智能体编排器
            orchestrator = RecruitmentAgentOrchestrator(state_queue)
            
            # 异步启动招聘流程
            asyncio.create_task(
                orchestrator.run(job_description, resume_paths)
            )
            
            return {
                "task_id": task_id,
                "status": "started",
                "message": "招聘流程已启动"
            }
        except Exception as e:
            logger.error(f"启动招聘流程失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"启动招聘流程失败: {str(e)}")
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        if task_id not in self.state_queues:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        queue = self.state_queues[task_id]
        status_updates = []
        
        # 获取队列中的所有状态更新
        while not queue.empty():
            try:
                update: BackToFrontData = await queue.get()
                status_updates.append({
                    "step": update.step,
                    "state": update.state,
                    "data": update.data,
                    "timestamp": asyncio.get_event_loop().time()
                })
            except:
                break
        
        return {
            "task_id": task_id,
            "updates": status_updates
        }
    
    async def get_final_results(self, task_id: str) -> Dict[str, Any]:
        """获取最终结果"""
        # 这里应该从数据库或缓存中获取最终结果
        # 为了简化，暂时返回示例结果
        return {
            "task_id": task_id,
            "results": "招聘流程已完成，详细结果待实现...",
            "status": "completed"
        }


# 全局招聘服务实例
recruitment_service = RecruitmentService()