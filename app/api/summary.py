"""
会话总结API端点
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

from app.services.summary_service import summary_service
from app.services.summary_context import summary_context_service

# 创建API路由
router = APIRouter()

# 定义请求模型
class TranscriptionItem(BaseModel):
    text: str
    timestamp: str

class SummaryRequest(BaseModel):
    transcriptions: List[TranscriptionItem]

class SummaryContextRequest(BaseModel):
    scene: str
    topic: str
    keyPoints: List[str]
    summary: str

# 定义响应模型
class SummaryResponse(BaseModel):
    scene: str
    topic: str
    keyPoints: List[str]
    summary: str

class StatusResponse(BaseModel):
    status: str
    message: str

@router.post("/summary", response_model=SummaryResponse)
async def generate_summary(request: SummaryRequest):
    """
    生成会话总结
    
    接收转写文本列表，返回会话的场景、主题、关键点和总结
    """
    try:
        # 转换请求数据格式
        transcriptions = [
            {"text": item.text, "timestamp": item.timestamp}
            for item in request.transcriptions
        ]
        
        # 调用总结服务
        summary_result = await summary_service.generate_summary(transcriptions)
        
        # 返回结果
        return SummaryResponse(
            scene=summary_result["scene"],
            topic=summary_result["topic"],
            keyPoints=summary_result["keyPoints"],
            summary=summary_result["summary"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成总结时出错: {str(e)}")

@router.post("/summary/context", response_model=StatusResponse)
async def set_summary_context(request: SummaryContextRequest):
    """
    设置会话总结上下文
    
    接收会话总结信息，用于增强文本优化和翻译功能
    """
    try:
        # 将请求数据传递给上下文服务
        success = summary_context_service.set_context({
            "scene": request.scene,
            "topic": request.topic,
            "keyPoints": request.keyPoints,
            "summary": request.summary
        })
        
        if success:
            return StatusResponse(
                status="success",
                message="会话总结上下文设置成功"
            )
        else:
            return StatusResponse(
                status="error",
                message="设置会话总结上下文失败"
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置总结上下文时出错: {str(e)}") 