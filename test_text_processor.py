import asyncio
import os
import sys
from app.services.text_processor import text_processor

async def test_text_processor():
    print("开始测试文本处理器...")
    
    # 检查Gemini API密钥是否已设置
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    print(f"Gemini API密钥是否已设置: {bool(gemini_api_key)}")
    print(f"文本处理器是否可用: {text_processor.available}")
    
    # 测试文本
    test_text = "我也不敢了。不然分不清在反打了。水水。"
    
    print(f"\n处理文本: '{test_text}'")
    result = await text_processor.process_text(
        text=test_text,
        source_language="zh",
        target_language="en"
    )
    
    print("\n处理结果:")
    print(f"优化文本: {result.get('refined_text', '无')}")
    print(f"翻译文本: {result.get('translation', '无')}")
    print(f"成功: {result.get('success', False)}")
    
    if not result.get('success', False):
        print(f"错误: {result.get('error', '未知错误')}")

if __name__ == "__main__":
    asyncio.run(test_text_processor()) 