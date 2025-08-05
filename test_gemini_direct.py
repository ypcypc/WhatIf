#!/usr/bin/env python3
"""
直接测试Gemini API连接的脚本
用于诊断空响应问题

运行方式：
poetry run python test_gemini_direct.py
"""

import os
import sys
import json
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend_services"))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """加载配置文件"""
    config_path = project_root / "llm_config.json"
    if not config_path.exists():
        raise FileNotFoundError("llm_config.json not found")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

async def test_gemini_direct():
    """直接测试Gemini API"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
        from langchain_core.messages import HumanMessage
        
        # 加载配置
        config = load_config()
        api_key = config["api_keys"]["google_api_key"]
        
        if not api_key:
            raise ValueError("Google API key not found in config")
        
        logger.info("Testing Gemini API connection...")
        logger.info(f"API Key (masked): {api_key[:8]}...{api_key[-4:]}")
        
        # 配置安全设置
        safety_settings = {
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # 创建模型
        logger.info("Creating Gemini model with relaxed safety settings...")
        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.1,
            google_api_key=api_key,
            max_output_tokens=1000,
            safety_settings=safety_settings,
            verbose=True
        )
        
        # 测试简单消息
        test_messages = [
            "Hello, please respond with 'OK'",
            "What is 1+1?",
            "Generate a simple JSON: {\"test\": \"value\"}",
        ]
        
        for i, test_msg in enumerate(test_messages, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"TEST {i}: {test_msg}")
            logger.info('='*80)
            
            try:
                response = await model.ainvoke([HumanMessage(content=test_msg)])
                
                logger.info(f"Response object type: {type(response)}")
                logger.info(f"Response attributes: {dir(response)}")
                
                if hasattr(response, 'content'):
                    logger.info(f"Content type: {type(response.content)}")
                    logger.info(f"Content length: {len(response.content) if response.content else 0}")
                    logger.info(f"Content: '{response.content}'")
                
                if hasattr(response, 'response_metadata'):
                    logger.info(f"Response metadata: {response.response_metadata}")
                
                if hasattr(response, 'usage_metadata'):
                    logger.info(f"Usage metadata: {response.usage_metadata}")
                
                logger.info(f"Full response object: {response}")
                
                # 检查是否为空响应
                if not response.content:
                    logger.error("❌ EMPTY RESPONSE DETECTED!")
                else:
                    logger.info("✅ Response received successfully")
                    
            except Exception as e:
                logger.error(f"❌ Test {i} failed: {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                
                import traceback
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        import traceback
        logger.error(f"Setup traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_gemini_direct())