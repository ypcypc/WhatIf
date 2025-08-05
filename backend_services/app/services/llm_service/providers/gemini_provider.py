"""
Google Gemini Provider Implementation

Provides integration with Google Gemini models (Gemini 2.5 Pro, etc.)
"""

import os
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from .base import BaseLLMProvider, LLMProviderConfig, LLMProvider
from ..models import TurnEvent
from ..llm_settings import llm_settings
from backend_services.app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider implementation."""
    
    def _validate_config(self) -> None:
        """Validate Gemini-specific configuration."""
        if not self.config.api_key:
            # Try to get from settings or environment
            self.config.api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY")
        
        if not self.config.api_key:
            raise ValueError("Google API key not found. Please set GOOGLE_API_KEY.")
        
        # Validate model name
        valid_models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
        if self.config.model_name not in valid_models:
            logger.warning(f"Unknown Gemini model: {self.config.model_name}")
    
    def _initialize(self) -> None:
        """Initialize Gemini model."""
        self._create_model()
        logger.info(f"Initialized Gemini provider with model: {self.config.model_name}")
    
    def _create_model(self):
        """Create or recreate the Gemini model with current settings."""
        # 配置安全设置 - 放宽限制以避免空响应
        safety_settings = {
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        logger.info("Creating Gemini model with relaxed safety settings")
        logger.info(f"Safety settings: {safety_settings}")
        
        # Gemini 2.5 Flash 支持最多 65536 个输出令牌
        # 使用配置文件中设置的值，实现单一配置源管理
        max_output_tokens = self.config.max_tokens or 65536
        
        logger.info(f"Creating Gemini model with max_output_tokens: {max_output_tokens}")
        
        # 配置thinking_budget参数（如果设置的话）
        thinking_budget = self.config.thinking_budget
        logger.info(f"Using thinking_budget: {thinking_budget} tokens")
        
        self.model = ChatGoogleGenerativeAI(
            model=self.config.model_name,
            temperature=self.config.temperature,
            google_api_key=self.config.api_key,
            max_output_tokens=max_output_tokens,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            thinking_budget=thinking_budget,  # 添加thinking_budget参数
            convert_system_message_to_human=True,  # Gemini doesn't have system messages
            verbose=True,  # 启用详细模式
            safety_settings=safety_settings,  # 添加安全设置
        )
    
    def update_temperature(self, temperature: float) -> None:
        """Update temperature and recreate model."""
        super().update_temperature(temperature)
        self._create_model()
    
    async def generate_structured_script(
        self,
        prompt: str,
        context: str,
        current_state: Dict[str, Any],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
        anchor_info: Optional[Dict[str, Any]] = None,
        session_id: str = None,
        user_event: Optional[TurnEvent] = None,
        assistant_event: Optional[TurnEvent] = None,
        memory_context: str = ""
    ) -> Dict[str, Any]:
        """Generate structured story script using Gemini."""
        try:
            # Update temperature if different
            if temperature != self.config.temperature:
                self.update_temperature(temperature)
            
            # Get system prompt and user message from settings
            system_prompt = llm_settings.get_system_prompt(
                current_state.get('deviation', 0),
                current_state,
                len(context),
                session_id
            )
            
            # Get target counts for content generation
            target_counts = llm_settings.get_required_counts(
                current_state.get('deviation', 0),
                len(context)
            )
            
            # Get generation config
            config = llm_settings.get_generation_config(current_state.get('deviation', 0))
            
            # Build user message
            user_message = llm_settings.get_user_message(
                context=context,
                memory_context=memory_context,
                prompt=prompt,
                anchor_info=anchor_info,
                current_state=current_state,
                target_counts=target_counts,
                config=config,
                session_id=session_id
            )
            
            # Format instructions for JSON output
            format_instructions = self._get_json_format_instructions(target_counts)
            
            # Create messages for Gemini
            # Combine system and user messages since Gemini doesn't support system messages
            # 简化消息格式，避免过长的系统指令
            
            logger.info("Building combined message for Gemini...")
            logger.info(f"System prompt length: {len(system_prompt)}")
            logger.info(f"User message length: {len(user_message)}")
            logger.info(f"Format instructions length: {len(format_instructions)}")
            
            # 构建更简洁的消息
            combined_message = f"""请根据以下要求生成游戏脚本：

{user_message}

{format_instructions}"""
            
            logger.info(f"Final combined message length: {len(combined_message)}")
            logger.info(f"Combined message preview (first 1000 chars):\n{combined_message[:1000]}...")
            
            messages = [HumanMessage(content=combined_message)]
            logger.info(f"Message object created: {type(messages[0])}")
            logger.info(f"Message content length: {len(messages[0].content)}")
            
            # Log the generation request
            logger.info(f"Generating script for session {session_id} with {self.config.model_name}")
            logger.debug(f"Temperature: {temperature}, Deviation: {current_state.get('deviation', 0)}")
            
            # Log the request details before generation
            logger.info(f"Sending request to Gemini API:")
            logger.info(f"Model: {self.config.model_name}")
            logger.info(f"Temperature: {temperature}")
            logger.info(f"Max tokens: {self.config.max_tokens}")
            logger.info(f"Message length: {len(combined_message)} characters")
            logger.info(f"First 500 chars of message: {combined_message[:500]}...")
            
            # 验证当前模型的安全设置
            if hasattr(self.model, 'safety_settings'):
                logger.info(f"Active safety settings: {self.model.safety_settings}")
            else:
                logger.warning("No safety_settings attribute found on model!")
                
            # 记录实际的模型配置
            logger.info(f"Model configuration:")
            for attr in ['model', 'temperature', 'max_output_tokens', 'top_p', 'top_k']:
                if hasattr(self.model, attr):
                    logger.info(f"  {attr}: {getattr(self.model, attr)}")
            
            # 检查消息中可能触发过滤的关键词
            potentially_sensitive_keywords = ['龙', '邪恶', '利爪', '妖气', '暴风龙', '封印', '勇者']
            found_keywords = [kw for kw in potentially_sensitive_keywords if kw in combined_message]
            if found_keywords:
                logger.info(f"Potentially sensitive keywords found: {found_keywords}")
            else:
                logger.info("No obviously sensitive keywords detected")
            
            # Generate response with retry mechanism
            start_time = datetime.now()
            logger.info("Calling Gemini API...")
            
            max_retries = 3
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempt {attempt + 1}/{max_retries}")
                    response = await self.model.ainvoke(messages)
                    
                    # 详细分析响应对象
                    logger.info("=" * 80)
                    logger.info(f"ATTEMPT {attempt + 1} - DETAILED RESPONSE ANALYSIS:")
                    logger.info("=" * 80)
                    
                    # 检查响应基本信息
                    logger.info(f"Response object type: {type(response)}")
                    logger.info(f"Response content length: {len(response.content) if response.content else 0}")
                    logger.info(f"Response content: '{response.content}'")
                    
                    # 检查安全相关信息
                    if hasattr(response, 'response_metadata') and response.response_metadata:
                        metadata = response.response_metadata
                        logger.info(f"Response metadata: {metadata}")
                        
                        # 重点检查安全评级
                        if 'safety_ratings' in metadata:
                            logger.info(f"Safety ratings: {metadata['safety_ratings']}")
                        
                        if 'prompt_feedback' in metadata:
                            prompt_feedback = metadata['prompt_feedback']
                            logger.info(f"Prompt feedback: {prompt_feedback}")
                            
                            if 'block_reason' in prompt_feedback:
                                block_reason = prompt_feedback['block_reason']
                                logger.info(f"Block reason: {block_reason}")
                                if block_reason != 0:
                                    logger.error(f"REQUEST BLOCKED! Block reason: {block_reason}")
                        
                        if 'finish_reason' in metadata:
                            finish_reason = metadata['finish_reason']
                            logger.info(f"Finish reason: {finish_reason}")
                            if finish_reason != 'STOP':
                                logger.warning(f"Unusual finish reason: {finish_reason}")
                    
                    # 检查usage信息
                    if hasattr(response, 'usage_metadata') and response.usage_metadata:
                        logger.info(f"Usage metadata: {response.usage_metadata}")
                    
                    logger.info("=" * 80)
                    
                    # 检查响应是否为空
                    if not response.content:
                        logger.warning(f"Attempt {attempt + 1}: Empty response received")
                        
                        # 分析空响应的可能原因
                        if hasattr(response, 'response_metadata') and response.response_metadata:
                            metadata = response.response_metadata
                            finish_reason = metadata.get('finish_reason', '')
                            
                            if metadata.get('prompt_feedback', {}).get('block_reason', 0) != 0:
                                logger.error("Empty response due to content blocking!")
                            elif finish_reason == 'SAFETY':
                                logger.error("Empty response due to safety filtering!")
                            elif finish_reason == 'MAX_TOKENS':
                                logger.error("Empty response due to MAX_TOKENS - output was truncated!")
                                logger.error("This usually means the requested output is too long for the model")
                                # 记录当前的 max_output_tokens 设置
                                if hasattr(self.model, 'max_output_tokens'):
                                    logger.error(f"Current max_output_tokens: {self.model.max_output_tokens}")
                            else:
                                logger.error(f"Empty response for unknown reason! finish_reason: {finish_reason}")
                        
                        if attempt < max_retries - 1:
                            logger.info("Retrying due to empty response...")
                            continue
                        else:
                            logger.error("All attempts resulted in empty responses")
                    else:
                        logger.info(f"Attempt {attempt + 1}: Successful response received")
                        break
                        
                except Exception as e:
                    last_exception = e
                    logger.error(f"Attempt {attempt + 1} failed with exception: {type(e).__name__}: {e}")
                    
                    # 尝试从异常中提取更多信息
                    if hasattr(e, 'response') and e.response:
                        logger.error(f"Exception response object: {e.response}")
                    
                    # 检查是否是特定的Google API错误
                    if 'InternalServerError' in str(type(e)):
                        logger.error("This is a Google API internal server error (500)")
                        logger.error("This indicates a server-side issue, not a client problem")
                    
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt)  # 指数退避: 1s, 2s, 4s
                        logger.info(f"Waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error("All retry attempts failed")
                        raise e
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Gemini API call completed in {generation_time:.2f} seconds")
            
            # Debug response object structure
            logger.info("=" * 80)
            logger.info("GEMINI RESPONSE OBJECT ANALYSIS:")
            logger.info("=" * 80)
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response attributes: {dir(response)}")
            
            # Check all possible response attributes
            if hasattr(response, 'content'):
                logger.info(f"Response content length: {len(response.content) if response.content else 0}")
                logger.info(f"Response content type: {type(response.content)}")
                logger.info(f"Response content: '{response.content}'")
            
            if hasattr(response, 'response_metadata'):
                logger.info(f"Response metadata: {response.response_metadata}")
            
            if hasattr(response, 'usage_metadata'):
                logger.info(f"Usage metadata: {response.usage_metadata}")
            
            # Check for any additional response information
            logger.info(f"Full response object: {response}")
            logger.info("=" * 80)
            
            # Extract and parse JSON from response
            response_text = response.content if response.content else ""
            logger.info(f"Extracted response_text: '{response_text}'")
            
            result = self._parse_json_response(response_text, prompt, current_state)
            
            # Add metadata
            result['metadata'] = result.get('metadata', {})
            result['metadata'].update({
                'model': self.config.model_name,
                'temperature': temperature,
                'generation_time': generation_time,
                'session_id': session_id,
                'provider': 'gemini'
            })
            
            logger.info(f"Successfully generated script with {len(result.get('script_units', []))} units")
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
            
            # If we have a response_text variable, print it for debugging
            if 'response_text' in locals():
                logger.error("=" * 80)
                logger.error("GEMINI RESPONSE AT EXCEPTION TIME:")
                logger.error("=" * 80)
                logger.error(f"Response length: {len(response_text)} characters")
                logger.error(f"Full response text:\n{response_text}")
                logger.error("=" * 80)
            
            # Print full stack trace for debugging
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            
            return self._create_fallback_response(prompt, current_state)
    
    def _get_json_format_instructions(self, target_counts: Dict[str, int]) -> str:
        """Get JSON format instructions for Gemini."""
        return f"""
请生成一个严格符合以下JSON格式的响应：
{{
    "script_units": [
        {{
            "type": "narration|dialogue|interaction",
            "content": "单元内容",
            "speaker": "角色ID（对话时必须使用ID，如char_001）",
            "choice_id": "选择ID（交互时需要）",
            "default_reply": "默认回复（交互时需要）",
            "metadata": {{}}
        }}
    ],
    "required_counts": {{
        "narration": {target_counts.get('narration', 5)},
        "dialogue": {target_counts.get('dialogue', 5)},
        "interaction": 1
    }},
    "deviation_delta": -20到20的数字,
    "new_deviation": 0到100的数字,
    "deviation_reasoning": "偏离度评估理由",
    "affinity_changes": {{}},
    "flags_updates": {{}},
    "variables_updates": {{}},
    "metadata": {{}}
}}

重要：
1. 必须返回有效的JSON格式
2. 所有字符串都要正确转义
3. 数字不要加引号
4. 最后一个script_unit必须是interaction类型
5. 只返回JSON，不要包含其他文字说明
"""
    
    def _parse_json_response(self, response_text: str, prompt: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON from Gemini response."""
        try:
            logger.info("=" * 80)
            logger.info("JSON PARSING ANALYSIS:")
            logger.info("=" * 80)
            logger.info(f"Input response_text type: {type(response_text)}")
            logger.info(f"Input response_text length: {len(response_text) if response_text else 0}")
            logger.info(f"Response_text is None: {response_text is None}")
            logger.info(f"Response_text is empty string: {response_text == ''}")
            logger.info(f"Response_text repr: {repr(response_text)}")
            
            if not response_text:
                logger.error("Response text is None or empty - this indicates Gemini returned no content")
                raise ValueError("Empty response from Gemini API")
            
            # Try to find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            logger.info(f"JSON search results:")
            logger.info(f"  First '{{' found at position: {json_start}")
            logger.info(f"  Last '}}' found at position: {json_end - 1 if json_end > 0 else -1}")
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                logger.info(f"Extracted JSON string length: {len(json_str)}")
                logger.info(f"First 200 chars of JSON: {json_str[:200]}...")
                logger.info(f"Last 200 chars of JSON: ...{json_str[-200:]}")
                
                parsed_json = json.loads(json_str)
                logger.info("JSON parsing successful!")
                logger.info(f"Parsed JSON keys: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else 'Not a dict'}")
                return parsed_json
            else:
                logger.error("No valid JSON boundaries found in response")
                raise ValueError("No JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error("=" * 80)
            logger.error("COMPLETE GEMINI RESPONSE FOR DEBUGGING:")
            logger.error("=" * 80)
            logger.error(f"Response length: {len(response_text)} characters")
            logger.error(f"Full response text:\n{response_text}")
            logger.error("=" * 80)
            logger.error("JSON EXTRACTION ATTEMPT:")
            logger.error(f"JSON start position: {response_text.find('{')}")
            logger.error(f"JSON end position: {response_text.rfind('}')}")
            if response_text.find('{') != -1 and response_text.rfind('}') != -1:
                json_attempt = response_text[response_text.find('{'):response_text.rfind('}') + 1]
                logger.error(f"Extracted JSON attempt: {json_attempt}")
            logger.error("=" * 80)
            return self._create_fallback_response(prompt, current_state)
    
    async def generate_summary(self, text: str, max_length: int = 500) -> str:
        """Generate a summary using Gemini."""
        try:
            prompt = llm_settings.get_summarization_prompt().format(text=text)
            
            # 使用相同的安全设置
            safety_settings = {
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Create a low-temperature model for summaries
            summary_model = ChatGoogleGenerativeAI(
                model=self.config.model_name,
                temperature=0.3,
                google_api_key=self.config.api_key,
                max_output_tokens=max_length,
                safety_settings=safety_settings,
                verbose=True
            )
            
            response = await summary_model.ainvoke([
                HumanMessage(content=prompt)
            ])
            
            logger.info(f"Summary response content: '{response.content}'")
            return response.content.strip() if response.content else "[总结失败 - 空响应]"
            
        except Exception as e:
            logger.error(f"Gemini summarization failed: {e}")
            return f"[总结失败] {text[:max_length]}..."
    
    async def debug_content_test(self, test_content: str, test_name: str = "unnamed") -> Dict[str, Any]:
        """
        专门用于调试的内容测试函数
        测试不同类型的内容是否会触发500错误或安全过滤
        """
        logger.info(f"=" * 80)
        logger.info(f"DEBUG CONTENT TEST: {test_name}")
        logger.info(f"=" * 80)
        logger.info(f"Test content length: {len(test_content)} characters")
        logger.info(f"Test content: {test_content[:200]}...")
        
        try:
            response = await self.model.ainvoke([
                HumanMessage(content=test_content)
            ])
            
            # 详细分析测试响应
            logger.info(f"Test '{test_name}' - Response analysis:")
            logger.info(f"  Content length: {len(response.content) if response.content else 0}")
            logger.info(f"  Content: '{response.content}'")
            
            if hasattr(response, 'response_metadata') and response.response_metadata:
                metadata = response.response_metadata
                logger.info(f"  Metadata: {metadata}")
                
                if 'prompt_feedback' in metadata:
                    prompt_feedback = metadata['prompt_feedback']
                    block_reason = prompt_feedback.get('block_reason', 0)
                    logger.info(f"  Block reason: {block_reason}")
                    if block_reason != 0:
                        logger.error(f"  ❌ CONTENT BLOCKED! Block reason: {block_reason}")
                        return {"success": False, "reason": "content_blocked", "block_reason": block_reason}
                
                if 'finish_reason' in metadata:
                    finish_reason = metadata['finish_reason']
                    logger.info(f"  Finish reason: {finish_reason}")
                    if finish_reason == 'SAFETY':
                        logger.error(f"  ❌ SAFETY FILTERED!")
                        return {"success": False, "reason": "safety_filtered"}
            
            if response.content:
                logger.info(f"  ✅ Test '{test_name}' PASSED")
                return {"success": True, "response_length": len(response.content)}
            else:
                logger.error(f"  ❌ Test '{test_name}' returned empty response")
                return {"success": False, "reason": "empty_response"}
                
        except Exception as e:
            logger.error(f"  ❌ Test '{test_name}' failed with exception: {type(e).__name__}: {e}")
            return {"success": False, "reason": "exception", "error": str(e)}
    
    async def run_progressive_content_tests(self) -> Dict[str, Any]:
        """
        运行渐进式内容测试，找到触发问题的临界点
        """
        logger.info("🧪 STARTING PROGRESSIVE CONTENT TESTS")
        
        test_results = {}
        
        # 测试1：简单英文
        test_results["simple_english"] = await self.debug_content_test(
            "Hello, please respond with a simple JSON: {\"status\": \"ok\"}",
            "Simple English"
        )
        
        # 测试2：简单日文
        test_results["simple_japanese"] = await self.debug_content_test(
            "こんにちは。簡単なJSONで応答してください：{\"status\": \"ok\"}",
            "Simple Japanese"
        )
        
        # 测试3：短的转世史莱姆内容
        test_results["short_slime"] = await self.debug_content_test(
            "我变成了史莱姆。这个世界很神奇。请生成JSON：{\"story\": \"开始冒险\"}",
            "Short Slime Content"
        )
        
        # 测试4：包含"敏感"关键词的内容
        test_results["with_keywords"] = await self.debug_content_test(
            "龙很强大，有着邪恶的外表和利爪。但它其实很善良。请生成JSON：{\"character\": \"friendly dragon\"}",
            "Content with Sensitive Keywords"
        )
        
        # 测试5：中等长度的游戏内容
        medium_content = """
        这只龙似乎很喜欢人类。嘴巴上小喽啰、垃圾地叫，却不曾蓄意杀害前来挑衅的家伙。
        过去曾有一次，因为三百年前发生了某件事，所以他把城镇灭了。
        现在我们要成为朋友。请生成游戏脚本JSON格式：
        {"script_units": [{"type": "dialogue", "content": "我们做朋友吧"}]}
        """
        test_results["medium_game_content"] = await self.debug_content_test(
            medium_content.strip(),
            "Medium Game Content"
        )
        
        logger.info("🧪 PROGRESSIVE CONTENT TESTS COMPLETED")
        logger.info(f"Test results summary: {test_results}")
        
        return test_results

    async def generate_simplified_script(
        self,
        simplified_content: str,
        max_units: int = 3,
        target_length: int = 1000
    ) -> Dict[str, Any]:
        """
        生成简化版本的脚本，用于测试是否能避免500错误
        
        Args:
            simplified_content: 简化的输入内容
            max_units: 最大脚本单元数
            target_length: 目标长度（字符数）
        """
        logger.info("🧪 GENERATING SIMPLIFIED SCRIPT FOR TESTING")
        logger.info(f"Input length: {len(simplified_content)} characters")
        logger.info(f"Max units: {max_units}")
        logger.info(f"Target length: {target_length}")
        
        # 极简的JSON格式指令
        simple_format = f"""
请生成一个简单的JSON格式响应：
{{
    "script_units": [
        {{"type": "narration", "content": "故事内容"}},
        {{"type": "dialogue", "content": "对话内容", "speaker": "char_001"}},
        {{"type": "interaction", "content": "交互问题", "choice_id": "choice_1", "default_reply": "默认回复"}}
    ],
    "deviation_delta": 0,
    "new_deviation": 0
}}

请基于以下内容生成{max_units}个脚本单元（总长度约{target_length}字符）：
{simplified_content[:500]}...
"""
        
        try:
            response = await self.model.ainvoke([
                HumanMessage(content=simple_format)
            ])
            
            logger.info("Simplified generation completed")
            logger.info(f"Response length: {len(response.content) if response.content else 0}")
            
            if response.content:
                # 尝试解析JSON
                try:
                    import json
                    json_start = response.content.find('{')
                    json_end = response.content.rfind('}') + 1
                    
                    if json_start != -1 and json_end > json_start:
                        json_str = response.content[json_start:json_end]
                        result = json.loads(json_str)
                        logger.info("✅ Simplified generation successful!")
                        return result
                    else:
                        logger.warning("No JSON found in simplified response")
                        return {"error": "no_json", "raw_response": response.content}
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing failed: {e}")
                    return {"error": "json_parse_failed", "raw_response": response.content}
            else:
                logger.error("❌ Simplified generation returned empty response")
                return {"error": "empty_response"}
                
        except Exception as e:
            logger.error(f"❌ Simplified generation failed: {type(e).__name__}: {e}")
            return {"error": "exception", "details": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check Gemini API health status."""
        try:
            logger.info("Performing Gemini API health check...")
            
            # Try a simple generation
            test_message = "Say 'OK' if you're working."
            logger.info(f"Sending test message: {test_message}")
            
            response = await self.model.ainvoke([
                HumanMessage(content=test_message)
            ])
            
            logger.info(f"Health check response: {response}")
            logger.info(f"Health check response content: '{response.content}'")
            logger.info(f"Health check response length: {len(response.content) if response.content else 0}")
            
            return {
                "gemini_available": True,
                "model": self.config.model_name,
                "provider": "gemini",
                "status": "healthy",
                "response": response.content[:50] if response.content else "Empty response",
                "full_response_length": len(response.content) if response.content else 0
            }
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            logger.error(f"Health check exception type: {type(e).__name__}")
            
            # Import traceback for detailed error info
            import traceback
            logger.error(f"Health check full traceback:\n{traceback.format_exc()}")
            
            return {
                "gemini_available": False,
                "model": self.config.model_name,
                "provider": "gemini",
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "provider": "gemini",
            "model": self.config.model_name,
            "temperature_range": (0.0, 2.0),
            "supports_functions": False,  # Gemini uses JSON mode
            "max_tokens": self.config.max_tokens or 8192,
            "features": {
                "structured_output": True,
                "function_calling": False,
                "json_mode": True,
                "vision": True,
                "multimodal": True
            }
        }