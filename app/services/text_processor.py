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
        
    async def process_text(self, text: str, history: list = None, source_language: str = "zh", target_language: str = "en", keywords: list = None) -> Dict[str, str]:
        """处理文本，进行refinement和翻译
        
        Args:
            text: 原始文本
            history: 历史句子列表
            source_language: 源语言代码
            target_language: 目标语言代码
            keywords: 用户关注的关键词列表
            
        Returns:
            包含处理结果的字典: {refined_text, translation, is_keyword_match, is_continuation, continuation_reason}
        """
        if not self.available:
            self.logger.warning("Gemini API未配置，无法处理文本")
            return {
                "refined_text": text,
                "translation": "",
                "is_keyword_match": False,
                "is_continuation": False,
                "continuation_reason": "",
                "success": False
            }
            
        if not text or not text.strip():
            self.logger.warning("输入文本为空，跳过处理")
            return {
                "refined_text": text,
                "translation": "",
                "is_keyword_match": False,
                "is_continuation": False,
                "continuation_reason": "",
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
                history,
                source_language, 
                target_language,
                keywords
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
                "is_keyword_match": False,
                "is_continuation": False,
                "continuation_reason": "",
                "success": False,
                "error": str(e)
            }
    
    def _call_gemini(self, text: str, history: list = None, source_language: str = "zh", target_language: str = "en", keywords: list = None) -> Dict[str, str]:
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
            
        # 处理历史句子
        history_prompt = ""
        if history and len(history) > 0:
            history_prompt = "历史句子：\n"
            for i, h in enumerate(history):
                history_prompt += f"{i+1}. {h}\n"
            self.logger.info(f"添加了{len(history)}条历史句子到提示词中")

        # 处理关键词
        keywords_prompt = ""
        if keywords and len(keywords) > 0:
            # 首先进行简单的直接匹配检查
            direct_matches = []
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    direct_matches.append(keyword)
            
            if direct_matches:
                self.logger.info(f"检测到直接关键词匹配: {direct_matches}")
            
            keywords_prompt = "用户关注的关键词：\n"
            keywords_prompt += ", ".join(keywords) + "\n"
            self.logger.info(f"添加了用户关键词到提示词中: {keywords}")
        
        # 构建提示词
        prompt = f"""
                {context_prompt}
                {history_prompt}
                {keywords_prompt}
                当前文本 ({source_lang_name}): {text}

                任务:
                1. 关注度判断: 根据用户关注的关键词，以及根据历史文本作为背景连接当前文本判断当前文本是否包含用户关注的信息。检查当前文本是否包含或直接提到任何用户关注的关键词。如果文本中出现关键词的原形、变体或紧密相关的表达，或者上下文有关的表达均视为匹配。同时任何一个关键词匹配即返回true。
                2. 连贯性判断: 判断当前文本是否是对最近一句历史文本{history[-1]}的补充或继续，只考虑一个情况就是这一句是上一句的断句失败，按理应该是上一句,不考虑别的原因。如果是，请说明原因。
                3. Refinement: 如果是2是连贯的，则修正当前文本[{text}]中的错别字和语法错误，保持原意,并且结合最后一句历史文本{history[-1]}，一起返回。如果有会话上下文，请确保修正后的文本与整体会话内容保持一致。如果2不是连贯的，则只修正当前文本，返回当前文本
                4. 翻译: 如果2是连贯的，则将当前文本结合历史最后一句{history[-1]}翻译成{target_lang_name}。如果有会话上下文，请确保翻译与会话的主题和关键点一致。如果没有只翻译当前文本并且返回

                请使用以下JSON格式输出结果:
                {{
                "refined_text": "修正后的文本",
                "translation": "翻译后的文本",
                "is_keyword_match": true/false,
                "matched_keywords": ["匹配的关键词1", "匹配的关键词2"],
                "match_reason": "非常简要说明为什么判断为匹配或不匹配",
                "is_continuation": true/false,
                "continuation_reason": "如果是对上一句的继续，请非常简单解释原因"
                }}

                只输出JSON格式的结果，不要添加任何其他解释或注释。
                """
        
        # 记录完整提示词（用于调试）
        self.logger.debug(f"完整提示词: {prompt}")
        
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
            if "is_keyword_match" not in result:
                result["is_keyword_match"] = False
            if "matched_keywords" not in result:
                result["matched_keywords"] = []
            if "match_reason" not in result:
                result["match_reason"] = ""
            if "is_continuation" not in result:
                result["is_continuation"] = False
            if "continuation_reason" not in result:
                result["continuation_reason"] = ""
            
            # 如果直接匹配到关键词但模型未匹配，以直接匹配为准
            if "direct_matches" in locals() and direct_matches and not result["is_keyword_match"]:
                self.logger.info(f"直接匹配检测到关键词但模型未匹配，以直接匹配为准")
                result["is_keyword_match"] = True
                result["matched_keywords"] = direct_matches
                result["match_reason"] = "直接文本匹配检测到关键词"
            
            # 如果匹配到关键词，记录匹配原因
            if result["is_keyword_match"]:
                self.logger.info(f"关键词匹配成功: {result.get('matched_keywords', [])} - 原因: {result.get('match_reason', '未提供')}")
            
            # 添加是否使用上下文的标记
            result["context_enhanced"] = using_context
                
            return result
            
        except Exception as e:
            self.logger.error(f"解析Gemini响应时出错: {str(e)}")
            self.logger.error(f"原始响应: {response.text}")
            return {
                "refined_text": text,
                "translation": "",
                "is_keyword_match": False,
                "is_continuation": False,
                "continuation_reason": "",
                "context_enhanced": using_context
            }

# 创建单例实例
text_processor = TextProcessor()
