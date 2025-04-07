#!/usr/bin/env python
import os
import sys
import logging
from app.config import AVAILABLE_LANGUAGES, AVAILABLE_MODELS
from app.audio.audio_processor import AudioProcessor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("语言测试")

def main():
    """测试音频处理器支持的语言"""
    logger.info("====== 测试音频处理器支持的语言 ======")
    
    logger.info(f"配置文件中的可用语言: {AVAILABLE_LANGUAGES}")
    logger.info(f"配置文件中的可用模型: {AVAILABLE_MODELS}")
    
    # 测试不同语言
    for language in AVAILABLE_LANGUAGES:
        try:
            logger.info(f"尝试创建语言为 '{language}' 的处理器")
            processor = AudioProcessor(language=language, model_type="tiny")
            logger.info(f"成功创建语言为 '{language}' 的处理器")
            logger.info(f"处理器配置: language={processor.language}, model_type={processor.model_type}")
            logger.info("=" * 30)
        except Exception as e:
            logger.error(f"创建语言为 '{language}' 的处理器失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.info("=" * 30)

if __name__ == "__main__":
    main() 