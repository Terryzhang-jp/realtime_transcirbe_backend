"""
会话总结API端点
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

from app.services.summary_service import summary_service

# 创建API路由
router = APIRouter()

# 定义请求模型
class TranscriptionItem(BaseModel):
    text: str
    timestamp: str

class SummaryRequest(BaseModel):
    transcriptions: List[TranscriptionItem]

# 定义响应模型
class SummaryResponse(BaseModel):
    scene: str
    topic: str
    keyPoints: List[str]
    summary: str

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