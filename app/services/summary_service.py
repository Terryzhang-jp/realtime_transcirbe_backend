"""
会话总结服务

使用Gemini-1.5-flash模型为转写文本生成会话总结，包括场景、主题、关键点和总结。
"""

import os
import logging
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置Google API密钥
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("未找到 GEMINI_API_KEY 环境变量。请在.env文件中设置它。")

# 配置genai
genai.configure(api_key=GEMINI_API_KEY)

# 初始化日志
logger = logging.getLogger(__name__)

# 摘要模型
MODEL_NAME = "gemini-1.5-flash"

class SessionSummaryService:
    """会话总结服务，使用Gemini生成摘要"""
    
    def __init__(self):
        """初始化会话总结服务"""
        self.model = genai.GenerativeModel(MODEL_NAME)
        logger.info(f"已初始化会话总结服务，使用模型: {MODEL_NAME}")
    
    async def generate_summary(self, transcriptions: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        生成会话总结
        
        Args:
            transcriptions: 转写结果列表，每个元素包含文本和时间戳
            
        Returns:
            包含场景、主题、关键点和总结的字典
        """
        try:
            # 记录请求
            logger.info(f"收到会话总结请求，包含 {len(transcriptions)} 条转写记录")
            
            # 检查是否有足够的内容进行总结
            if not transcriptions or len(transcriptions) < 2:
                logger.warning("转写内容太少，无法生成有意义的总结")
                return {
                    "scene": "内容不足",
                    "topic": "尚未确定",
                    "keyPoints": ["需要更多对话内容才能生成关键点"],
                    "summary": "请继续对话以生成更有意义的总结"
                }
            
            # 准备提示词
            prompt = self._prepare_prompt(transcriptions)
            
            # 调用Gemini模型
            response = self.model.generate_content(prompt)
            
            # 解析响应
            summary_result = self._parse_response(response.text)
            
            # 记录结果
            logger.info("成功生成会话总结")
            
            return summary_result
            
        except Exception as e:
            logger.error(f"生成会话总结时出错: {str(e)}")
            # 返回一个友好的错误响应
            return {
                "scene": "处理出错",
                "topic": "无法确定",
                "keyPoints": ["生成总结时发生错误"],
                "summary": f"抱歉，在处理您的请求时遇到了问题: {str(e)}"
            }
    
    def _prepare_prompt(self, transcriptions: List[Dict[str, str]]) -> str:
        """准备发送给Gemini的提示词"""
        
        # 将转写记录格式化为时间戳文本对
        transcript_text = "\n".join([
            f"[{self._format_timestamp(item['timestamp'])}] {item['text']}"
            for item in transcriptions
        ])
        
        # 构建提示词
        prompt = f"""
        以下是一段会话的转写记录，每条记录包含时间戳和文本内容：
        
        {transcript_text}
        
        请分析此会话并生成以下内容：
        1. 场景：描述这个会话发生的可能场景或环境
        2. 主题：概括会话的主要主题或目的
        3. 关键点：列出会话中讨论的3-5个主要关键点
        4. 总结：用简洁的语言总结整个会话的内容和结论
        
        请按以下JSON格式输出:
        ```json
        {{
          "scene": "场景描述",
          "topic": "主题概括",
          "keyPoints": ["关键点1", "关键点2", "关键点3"],
          "summary": "完整总结"
        }}
        ```
        
        用中文回答。确保输出是有效的JSON格式，不要添加其他内容。关键点请限制在5个以内。
        """
        
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """从Gemini响应中解析出结构化的总结信息"""
        try:
            # 尝试找到JSON部分
            import json
            import re
            
            # 寻找JSON块
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个响应
                json_str = response_text
            
            # 解析JSON
            result = json.loads(json_str)
            
            # 确保返回格式正确
            return {
                "scene": result.get("scene", "未提供"),
                "topic": result.get("topic", "未提供"),
                "keyPoints": result.get("keyPoints", []),
                "summary": result.get("summary", "未提供")
            }
            
        except Exception as e:
            logger.error(f"解析Gemini响应时出错: {str(e)}")
            logger.debug(f"原始响应: {response_text}")
            
            # 返回一个友好的错误响应
            return {
                "scene": "解析错误",
                "topic": "无法解析",
                "keyPoints": ["无法从模型响应中提取关键点"],
                "summary": f"解析模型响应时出错: {str(e)}"
            }
    
    def _format_timestamp(self, timestamp_str: str) -> str:
        """格式化ISO时间戳为更可读的形式"""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%H:%M:%S')
        except Exception:
            return timestamp_str


# 创建服务实例
summary_service = SessionSummaryService() 