import asyncio
import os
from fastapi import FastAPI, WebSocket, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
import uuid
from src.agents.orchestrator import RecruitmentAgentOrchestrator
from src.core.state_models import BackToFrontData
from src.knowledge.knowledge_router import router as knowledge_router
from src.utils.log_utils import setup_logger
from asyncio import Queue
import json
from src.services.recruitment_service import recruitment_service

# 配置日志
logger = setup_logger(__name__)

# 创建FastAPI应用
app = FastAPI(title="Recruitment Agent API", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载知识库路由
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["knowledge"])

class RecruitmentRequest(BaseModel):
    job_description: str
    max_candidates: int = 50

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket端点，用于实时传输任务状态"""
    await websocket.accept()
    
    # 从招聘服务获取状态队列
    if task_id not in recruitment_service.state_queues:
        recruitment_service.state_queues[task_id] = Queue()
    
    queue = recruitment_service.state_queues[task_id]
    
    # 启动一个后台任务来监听队列并发送消息到websocket
    async def listen_to_queue():
        while True:
            try:
                # 从队列中获取状态更新
                update: BackToFrontData = await queue.get()
                
                # 发送状态更新到websocket
                await websocket.send_text(update.model_dump_json())
            except Exception as e:
                logger.error(f"WebSocket发送错误: {e}")
                break
    
    # 运行监听任务
    listen_task = asyncio.create_task(listen_to_queue())
    
    try:
        # 保持WebSocket连接打开
        while True:
            data = await websocket.receive_text()
            # 可以在这里处理从前端发来的消息
            logger.info(f"收到WebSocket消息: {data}")
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        listen_task.cancel()

@app.post("/api/upload-resumes")
async def upload_resumes(files: List[UploadFile] = File(...)):
    """上传简历文件"""
    try:
        file_paths = await recruitment_service.upload_resumes(files)
        return {"file_paths": file_paths, "count": len(file_paths)}
    except Exception as e:
        logger.error(f"上传简历失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传简历失败: {str(e)}")

@app.post("/api/start-recruitment")
async def start_recruitment(request: RecruitmentRequest, background_tasks: BackgroundTasks):
    """启动招聘任务"""
    task_id = str(uuid.uuid4())
    
    # 这里我们假设简历已经上传，实际应用中需要管理上传的简历
    # 为了演示，我们使用模拟的简历路径
    resume_paths = []  # 实际应用中这里应该是上传的简历路径
    
    # 启动招聘流程
    result = await recruitment_service.start_recruitment_process(
        request.job_description, 
        resume_paths, 
        task_id
    )
    
    return result

@app.post("/api/start-recruitment-with-files")
async def start_recruitment_with_files(job_description: str, resume_paths: List[str], background_tasks: BackgroundTasks):
    """使用指定文件路径启动招聘任务"""
    task_id = str(uuid.uuid4())
    
    # 启动招聘流程
    result = await recruitment_service.start_recruitment_process(
        job_description, 
        resume_paths, 
        task_id
    )
    
    return result

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """获取任务状态"""
    return await recruitment_service.get_task_status(task_id)

@app.get("/api/results/{task_id}")
async def get_results(task_id: str):
    """获取任务结果"""
    return await recruitment_service.get_final_results(task_id)

# 挂载静态文件
current_dir = os.path.dirname(__file__)
web_dir = os.path.join(current_dir, "web/dist")
if os.path.exists(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="static")
else:
    logger.warning(f"Web目录不存在: {web_dir}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)