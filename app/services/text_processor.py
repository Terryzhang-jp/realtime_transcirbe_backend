import logging
import time
import traceback
import os
import google.generativeai as genai
from typing import Dict, Optional, Tuple, Any
import asyncio
from dotenv import load_dotenv

# 导入会话总结上下文服务
from app.services.summary_context import summary_context_service

# 加载环境变量
load_dotenv()

# 配置Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    logging.warning("未设置GEMINI_API_KEY，文本处理功能将不可用")
else:
    genai.configure(api_key=GEMINI_API_KEY)

class TextProcessor:
    """文本处理服务，用于文本refinement和翻译"""
    
    def __init__(self):
        """初始化文本处理服务"""
        self.logger = logging.getLogger("TextProcessor")
        self.logger.setLevel(logging.DEBUG)
        self.available = bool(GEMINI_API_KEY)
        
        # 配置Gemini模型
        if self.available:
            try:
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.logger.info("Gemini模型初始化成功")
            except Exception as e:
                self.available = False
                self.logger.error(f"Gemini模型初始化失败: {str(e)}")
                self.logger.error(traceback.format_exc())
        
    async def process_text(self, text: str, source_language: str = "zh", target_language: str = "en") -> Dict[str, str]:
        """处理文本，进行refinement和翻译
        
        Args:
            text: 原始文本
            source_language: 源语言代码
            target_language: 目标语言代码
            
        Returns:
            包含处理结果的字典: {refined_text, translation}
        """
        if not self.available:
            self.logger.warning("Gemini API未配置，无法处理文本")
            return {
                "refined_text": text,
                "translation": "",
                "success": False
            }
            
        if not text or not text.strip():
            self.logger.warning("输入文本为空，跳过处理")
            return {
                "refined_text": text,
                "translation": "",
                "success": False
            }
            
        try:
            self.logger.info(f"处理文本: '{text}'")
            start_time = time.time()
            
            # 创建异步任务
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._call_gemini, 
                text, 
                source_language, 
                target_language
            )
            
            process_time = time.time() - start_time
            self.logger.info(f"文本处理完成，耗时: {process_time:.2f}秒")
            
            return {
                **result,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"处理文本时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "refined_text": text,
                "translation": "",
                "success": False,
                "error": str(e)
            }
    
    def _call_gemini(self, text: str, source_language: str, target_language: str) -> Dict[str, str]:
        """调用Gemini API处理文本
        
        这是一个同步方法，会在异步循环中通过run_in_executor调用
        """
        language_names = {
            "zh": "中文",
            "en": "英文",
            "ja": "日文",
            "ko": "韩文",
            "es": "西班牙文",
            "fr": "法文",
            "de": "德文",
            "ru": "俄文"
        }
        
        source_lang_name = language_names.get(source_language, source_language)
        target_lang_name = language_names.get(target_language, target_language)
        
        # 检查是否有会话总结上下文
        context_prompt = ""
        using_context = False
        if summary_context_service.has_summary_context():
            context_prompt = f"""
会话上下文：
{summary_context_service.get_context_prompt()}

请根据上述会话上下文信息，更准确地理解和处理以下文本。确保修正和翻译与会话的主题、场景和关键点保持一致。
"""
            self.logger.info("已添加会话总结上下文到文本处理提示词中")
            using_context = True
        
        # 构建提示词
        prompt = f"""
{context_prompt}
原始文本 ({source_lang_name}): {text}

任务:
1. Refinement: 修正上述文本中的错别字和语法错误，保持原意。如果有会话上下文，请确保修正后的文本与整体会话内容保持一致。
2. 翻译: 将上述文本翻译成{target_lang_name}。如果有会话上下文，请确保翻译与会话的主题和关键点一致。

请使用以下JSON格式输出结果:
{{
  "refined_text": "修正后的文本",
  "translation": "翻译后的文本"
}}

只输出JSON格式的结果，不要添加任何其他解释或注释。
"""
        
        # 调用Gemini API
        response = self.model.generate_content(prompt)
        
        # 解析响应
        try:
            # 从响应中提取JSON
            response_text = response.text
            import json
            import re
            
            # 尝试提取JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response_text
            
            # 清理JSON字符串
            json_str = re.sub(r'```(json)?\s*', '', json_str)
            json_str = re.sub(r'\s*```', '', json_str)
            
            # 解析JSON
            result = json.loads(json_str)
            
            # 确保结果包含所需字段
            if "refined_text" not in result:
                result["refined_text"] = text
            if "translation" not in result:
                result["translation"] = ""
            
            # 添加是否使用上下文的标记
            result["context_enhanced"] = using_context
                
            return result
            
        except Exception as e:
            self.logger.error(f"解析Gemini响应时出错: {str(e)}")
            self.logger.error(f"原始响应: {response.text}")
            return {
                "refined_text": text,
                "translation": "",
                "context_enhanced": using_context
            }

# 创建单例实例
text_processor = TextProcessor()
