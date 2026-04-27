import sys
import os

from sqlalchemy import Null
from sqlalchemy.sql.functions import current_date
# 将项目根目录添加到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from src.core.state_models import RecruitmentAgentState, ExecutionState, NodeError
from src.agents.extractor import extraction_node
from src.agents.profiler import profiling_node
from src.agents.reasoner import reasoning_node
from src.agents.validator import validation_node
from typing import Dict, Any
from src.core.state_models import BackToFrontData
from src.core.state_models import State, ConfigSchema


import asyncio


class RecruitmentAgentOrchestrator:
    def __init__(self, state_queue):
        self.state_queue = state_queue
        self.graph = self._build_graph()

    async def handle_error_node(self, state: State) -> str:
        """错误处理节点"""
        current_state = state["value"]
        current_state.current_step = ExecutionState.FAILED
        print(f"Workflow failed at {current_state.current_step}: {current_state.error}")
        return {"value": current_state}

    def condition_handler(self, state: State) -> bool:
        """条件处理函数"""
        # 如果state.get("error") is not None那么就返回到handle_error_node
        current_state = state["value"]
        err = current_state.error
        current_step = current_state.current_step
        if err.extraction_node_error is None and current_step == ExecutionState.EXTRACTING:
            return "profiling_node"
        elif err.profiling_node_error is None and current_step == ExecutionState.PROFILING:
            return "reasoning_node"
        elif err.reasoning_node_error is None and current_step == ExecutionState.REASONING:
            return "validation_node"
        elif err.validation_node_error is None and current_step == ExecutionState.VALIDATING:
            return END
        else:
            return "handle_error_node"


    def _build_graph(self):
        """构建并编译LangGraph工作流"""
        builder = StateGraph(State, context_schema=ConfigSchema)
        
        # 添加节点
        builder.add_node("extraction_node", extraction_node)
        builder.add_node("profiling_node", profiling_node)
        builder.add_node("reasoning_node", reasoning_node)
        builder.add_node("validation_node", validation_node)
        builder.add_node("handle_error_node", self.handle_error_node)

        builder.set_entry_point("extraction_node")
        
        # 定义工作流路径
        builder.add_edge(START, "extraction_node")
        builder.add_conditional_edges("extraction_node", self.condition_handler)
        builder.add_conditional_edges("profiling_node", self.condition_handler)
        builder.add_conditional_edges("reasoning_node", self.condition_handler)
        builder.add_conditional_edges("validation_node", self.condition_handler)
        builder.add_edge("handle_error_node", END)
        
        return builder.compile()
    

    
    async def run(self, user_request: str, resume_list: list, max_candidates: int = 50):
        """执行完整工作流"""
        # 初始化状态
        # await self.state_queue.put(BackToFrontData(step="start",state="processing",data=None))
        print("Starting recruitment workflow...")
        initial_state = RecruitmentAgentState(
            user_request=user_request,
            resume_list=resume_list,
            max_candidates=max_candidates,
            error=NodeError(),
            config={}  # 可以传入各种配置
        )

        # 运行图
        await self.graph.ainvoke({"state_queue": self.state_queue, "value": initial_state})
        await self.state_queue.put(BackToFrontData(step=ExecutionState.FINISHED, state="finished", data=None))

    
if __name__ == "__main__":
    # from IPython.display import Image, display

    # # Attempt to visualize the graph as a Mermaid diagram
    # try:
    #     display(Image(graph.get_graph().draw_mermaid_png()))
    # except Exception:
    #     # Handle cases where visualization fails (e.g., missing dependencies)
    #     pass
    orchestrator = RecruitmentAgentOrchestrator()
    orchestrator.run("寻找高级Python开发工程师", ["resume1.pdf", "resume2.pdf"])