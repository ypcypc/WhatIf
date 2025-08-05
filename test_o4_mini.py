#!/usr/bin/env python3
"""
Test script for o4-mini model functionality
"""

import asyncio
import json
from openai import AsyncOpenAI
import os

async def test_o4_mini():
    """Test o4-mini with a simple Chinese text processing task."""
    
    # Initialize OpenAI client
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Simple test prompt in Chinese
    system_message = """你是一个故事生成助手。请将给出的中文文本转换为结构化的JSON格式，包含以下字段：
- script_units: 包含type（类型）和content（内容）的数组
- 每个单元的type可以是"narration"（叙述）或 "dialogue"（对话）
- 确保生成至少3个script_units"""

    user_message = """请将以下文本结构化：

好暗。乌漆麻黑的，什么都看不见。这里是哪里？不对，发生什么事了。印象中好像被人左一句贤者右一句大贤者耍弄……

想到这里，我的意识清醒过来。我的名字叫三上悟，三十七岁的好男人一个。在路上为了保护差点被随机杀人魔拿刀刺的学弟，结果被捅了。

很好，我还记得。没问题，目前似乎没什么好惊慌的。"""

    # Tool definition for structured output
    tools = [{
        "type": "function",
        "function": {
            "name": "generate_structured_script",
            "description": "Generate structured script from Chinese text",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_units": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["narration", "dialogue"]
                                },
                                "content": {
                                    "type": "string"
                                }
                            },
                            "required": ["type", "content"]
                        }
                    }
                },
                "required": ["script_units"]
            }
        }
    }]

    try:
        print("🧪 Testing o4-mini with simple Chinese text...")
        print(f"📝 Input length: {len(user_message)} characters")
        
        # Test both message structures for o4-mini
        print("🧪 Testing with separate system/user messages...")
        try:
            response = await client.chat.completions.create(
                model="o4-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "generate_structured_script"}},
                temperature=1.0,
                max_completion_tokens=4000
            )
            print("✅ Separate messages work")
        except Exception as e:
            print(f"❌ Separate messages failed: {e}")
            
            # Try combined message structure (as used in the real system)
            print("🧪 Testing with combined user message...")
            combined_message = f"# System Instructions\n{system_message}\n\n# User Request\n{user_message}"
            response = await client.chat.completions.create(
                model="o4-mini",
                messages=[
                    {"role": "user", "content": combined_message}
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "generate_structured_script"}},
                temperature=1.0,
                max_completion_tokens=4000
            )
        
        print("✅ API call successful")
        
        if response.choices and response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            raw_json = tool_call.function.arguments
            
            print(f"📊 Response length: {len(raw_json)} characters")
            print(f"🔍 Raw JSON: {raw_json}")
            
            try:
                result = json.loads(raw_json)
                script_units = result.get("script_units", [])
                
                print(f"✅ JSON parsed successfully")
                print(f"📊 Generated {len(script_units)} script units:")
                
                for i, unit in enumerate(script_units):
                    print(f"  {i+1}. [{unit.get('type', 'unknown')}] {unit.get('content', '')[:100]}")
                
                if len(script_units) == 0:
                    print("❌ ISSUE: Empty script_units array returned!")
                else:
                    print("✅ SUCCESS: Model generated content properly")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                
        else:
            print("❌ No tool calls in response")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_o4_mini())