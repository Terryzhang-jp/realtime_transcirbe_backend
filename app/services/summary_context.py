"""
会话总结上下文服务

用于存储和管理会话总结上下文，为文本优化和翻译提供额外信息。
"""

import logging
from typing import Dict, Any, Optional

# 初始化日志
logger = logging.getLogger(__name__)

class SummaryContextService:
    """会话总结上下文服务，为文本处理提供额外上下文"""
    
    def __init__(self):
        """初始化会话总结上下文服务"""
        self.has_context = False
        self.context = {
            "scene": "",
            "topic": "",
            "keyPoints": [],
            "summary": ""
        }
        logger.info("已初始化会话总结上下文服务")
    
    def set_context(self, context_data: Dict[str, Any]) -> bool:
        """
        设置会话总结上下文
        
        Args:
            context_data: 包含场景、主题、关键点和总结的字典
            
        Returns:
            是否成功设置上下文
        """
        try:
            # 验证上下文数据
            if not all(key in context_data for key in ["scene", "topic", "keyPoints", "summary"]):
                logger.warning("上下文数据缺少必要字段")
                return False
                
            # 更新上下文
            self.context = {
                "scene": context_data.get("scene", ""),
                "topic": context_data.get("topic", ""),
                "keyPoints": context_data.get("keyPoints", []),
                "summary": context_data.get("summary", "")
            }
            
            # 设置上下文标志
            self.has_context = True
            
            logger.info(f"已设置会话总结上下文")
            logger.debug(f"上下文: {self.context}")
            
            return True
            
        except Exception as e:
            logger.error(f"设置会话总结上下文时出错: {str(e)}")
            return False
    
    def get_context(self) -> Dict[str, Any]:
        """获取当前会话总结上下文"""
        return self.context
    
    def has_summary_context(self) -> bool:
        """检查是否有会话总结上下文"""
        return self.has_context
    
    def get_context_prompt(self) -> Optional[str]:
        """
        获取格式化的上下文提示词
        
        Returns:
            格式化的提示词或None（如果没有上下文）
        """
        if not self.has_context:
            return None
            
        # 格式化关键点
        key_points_text = "\n".join([f"- {point}" for point in self.context["keyPoints"]])
        
        # 构建提示词
        prompt = f"""
会话上下文信息:
场景: {self.context["scene"]}
主题: {self.context["topic"]}
关键点:
{key_points_text}
整体总结: {self.context["summary"]}
        """
        
        return prompt.strip()
    
    def clear_context(self) -> None:
        """清除当前上下文"""
        self.has_context = False
        self.context = {
            "scene": "",
            "topic": "",
            "keyPoints": [],
            "summary": ""
        }
        logger.info("已清除会话总结上下文")


# 创建单例实例
summary_context_service = SummaryContextService() 