"""
LLM Configuration Management

Manages prompts, templates, parameters, and generation rules for LLM service.
Implements the improved content balance and dialogue strategies.
"""

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class DeviationLevel(str, Enum):
    """Deviation level classification."""
    LOW = "low"          # < 0.05
    MEDIUM = "medium"    # 0.05-0.3  
    HIGH = "high"        # 0.3-0.6
    CRITICAL = "critical" # > 0.6


@dataclass
class ContentRatio:
    """Content type ratio configuration."""
    narration_min: int
    narration_max: int
    dialogue_min: int
    dialogue_max: int
    interaction_min: int
    interaction_max: int
    
    @property
    def total_min(self) -> int:
        return self.narration_min + self.dialogue_min + self.interaction_min
    
    @property
    def total_max(self) -> int:
        return self.narration_max + self.dialogue_max + self.interaction_max


@dataclass
class GenerationConfig:
    """Generation parameters for different deviation levels."""
    temperature: float
    max_tokens: int
    content_ratio: ContentRatio
    dialogue_ratio_target: str  # e.g., "1:1", "1:1.5", "1:2"
    emphasis_instruction: str


class LLMConfig:
    """
    Centralized LLM configuration manager.
    
    Handles all prompt templates, generation parameters, and content rules
    based on the improved strategy for reducing narrator overuse.
    """
    
    def __init__(self):
        self._init_deviation_configs()
        self._init_prompt_templates()
        self._init_content_examples()
    
    def _init_deviation_configs(self):
        """Initialize generation configs for different deviation levels."""
        self.DEVIATION_CONFIGS = {
            DeviationLevel.LOW: GenerationConfig(
                temperature=0.6,
                max_tokens=8192,
                content_ratio=ContentRatio(
                    narration_min=6, narration_max=10,
                    dialogue_min=4, dialogue_max=8, 
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="2:1",
                emphasis_instruction="保持叙述为主，适量对话推进剧情。"
            ),
            DeviationLevel.MEDIUM: GenerationConfig(
                temperature=0.7,
                max_tokens=8192,
                content_ratio=ContentRatio(
                    narration_min=5, narration_max=8,
                    dialogue_min=6, dialogue_max=10,
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="1:1",
                emphasis_instruction="平衡叙述与对话，增加角色互动。"
            ),
            DeviationLevel.HIGH: GenerationConfig(
                temperature=0.8,
                max_tokens=8192,
                content_ratio=ContentRatio(
                    narration_min=4, narration_max=6,
                    dialogue_min=8, dialogue_max=12,
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="1:1.5",
                emphasis_instruction="重点通过角色对话推进剧情收束，减少冗长叙述。"
            ),
            DeviationLevel.CRITICAL: GenerationConfig(
                temperature=0.9,
                max_tokens=8192,
                content_ratio=ContentRatio(
                    narration_min=3, narration_max=5,
                    dialogue_min=10, dialogue_max=15,
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="1:2",
                emphasis_instruction="必须大量使用角色对话推动剧情回归主线，严格控制叙述篇幅。"
            )
        }
    
    def _init_prompt_templates(self):
        """Initialize prompt templates."""
        
        # Content ratio table for system prompt
        self.CONTENT_RATIO_TABLE = """
| unit_type  | min | max | 说明 |
|------------|-----|-----|------|
| narration  | {narration_min}   | {narration_max}   | 场景描写与氛围渲染，避免冗余 |
| dialogue   | {dialogue_min}   | {dialogue_max}   | 角色对话，包含内心独白转化的对话 |
| interaction| {interaction_min}   | {interaction_max}   | 玩家选择点，只能在结尾 |

**重要：本轮请保持叙述与对话数量比 ≈ {dialogue_ratio_target}**
"""
        
        # Good/bad examples for content types
        self.CONTENT_EXAMPLES = """
✅ **正确示例：**
- narration: "黄昏的校园被金色晚霞笼罩，空气中弥漫着淡淡的花香。"
- dialogue: 三上悟："这就是所谓的转生吗？变成史莱姆还真是意外啊。"
- dialogue: 三上悟（内心）："虽然外表变了，但思考能力似乎还在，这倒是个好消息。"

❌ **错误示例（会被拒绝）：**
- narration: "他思考着人生的意义，回忆起过去的种种经历，内心充满了复杂的情感...（无角色对话，过度冗长）"
"""
        
        # Core system prompt template
        self.SYSTEM_PROMPT_TEMPLATE = """你是一个专业的交互式小说生成器，专门创作忠实于原著的角色扮演故事。

## 当前生成约束

{content_ratio_table}

{emphasis_instruction}

{content_examples}

## 核心规则

1. **内心独白处理**：将角色的内心思考转换为"角色名（内心）：思考内容"的对话形式，但不得强行将旁白改成人物对话。

2. **对话优先策略**：在不违背原著的前提下，优先使用角色对话推进剧情，减少纯描述性旁白。

3. **结构化输出**：必须按照指定的JSON Schema输出，包含required_counts字段验证数量约束。

4. **偏离度控制**：根据当前偏离度({current_deviation:.1f}%)调整生成策略：
   - 偏离度低：可以适度探索，但保持主线
   - 偏离度高：必须通过角色行动和对话引导回归主线

5. **角色一致性**：严格保持角色性格、语言习惯和能力设定的一致性。

6. **【重要】必须生成interaction单元**：脚本必须以interaction类型的单元结尾，这是游戏继续的关键。

## 输出要求

使用structured output格式，包含：
- script_units: 按要求数量生成的脚本单元（必须以interaction单元结尾）
- required_counts: 各类型单元的实际数量（interaction必须为1）
- deviation_delta: 偏离度变化(-20到+20)
- affinity_changes: 角色好感度变化
- metadata: 生成元数据

**绝对要求**：脚本的最后一个单元必须是interaction类型，包含choice_id和default_reply字段。
"""
        
        # Function call schema template  
        self.FUNCTION_SCHEMA = {
            "name": "generate_story_script",
            "description": "Generate structured story script with content balance control",
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
                                    "enum": ["narration", "dialogue", "interaction"],
                                    "description": "脚本单元类型，interaction类型必须在最后"
                                },
                                "content": {"type": "string"},
                                "speaker": {"type": "string", "description": "Speaker name for dialogue, null for narration"},
                                "choice_id": {"type": "string", "description": "Choice ID for interaction units"},
                                "default_reply": {"type": "string", "description": "Default suggested response for interaction"},
                                "metadata": {"type": "object"}
                            },
                            "required": ["type", "content"]
                        }
                    },
                    "required_counts": {
                        "type": "object",
                        "properties": {
                            "narration": {"type": "integer"},
                            "dialogue": {"type": "integer"},
                            "interaction": {"type": "integer"}
                        },
                        "required": ["narration", "dialogue", "interaction"]
                    },
                    "deviation_delta": {
                        "type": "number",
                        "minimum": -20,
                        "maximum": 20,
                        "description": "Story deviation change"
                    },
                    "affinity_changes": {
                        "type": "object",
                        "description": "Character affinity changes"
                    },
                    "flags_updates": {
                        "type": "object",
                        "description": "Story flag updates"
                    },
                    "variables_updates": {
                        "type": "object", 
                        "description": "Game variable updates"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Generation metadata"
                    }
                },
                "required": ["script_units", "required_counts", "deviation_delta"]
            }
        }
    
    def _init_content_examples(self):
        """Initialize content type examples."""
        self.DIALOGUE_ENHANCEMENT_RULES = """
## 内心独白转换规则

将角色内心思考转换为对话形式，保持角色声音的真实性：

1. **直接内心独白**：
   - 原文："他想着这件事很奇怪"
   - 转换："角色名（内心）：'这件事真的很奇怪...'"

2. **情感反应**：
   - 原文："他感到很困惑"
   - 转换："角色名（内心）：'我怎么会变成这样？太困惑了。'"

3. **决策思考**：
   - 原文："他考虑着下一步该怎么办"
   - 转换："角色名（内心）：'接下来该怎么办呢？需要仔细考虑一下。'"

**注意**：不得强行将环境描写、动作叙述等改成对话。只转换真正的思考和情感表达。
"""
    
    def get_deviation_level(self, deviation: float) -> DeviationLevel:
        """Get deviation level based on score."""
        if deviation < 5.0:
            return DeviationLevel.LOW
        elif deviation <= 30.0:
            return DeviationLevel.MEDIUM
        elif deviation <= 60.0:
            return DeviationLevel.HIGH
        else:
            return DeviationLevel.CRITICAL
    
    def get_generation_config(self, deviation: float) -> GenerationConfig:
        """Get generation configuration for current deviation level."""
        level = self.get_deviation_level(deviation)
        return self.DEVIATION_CONFIGS[level]
    
    def build_system_prompt(self, 
                           deviation: float,
                           current_state: Dict[str, Any],
                           context_length: int) -> str:
        """Build complete system prompt for current context."""
        
        config = self.get_generation_config(deviation)
        
        # Format content ratio table
        content_ratio_table = self.CONTENT_RATIO_TABLE.format(
            narration_min=config.content_ratio.narration_min,
            narration_max=config.content_ratio.narration_max,
            dialogue_min=config.content_ratio.dialogue_min,
            dialogue_max=config.content_ratio.dialogue_max,
            interaction_min=config.content_ratio.interaction_min,
            interaction_max=config.content_ratio.interaction_max,
            dialogue_ratio_target=config.dialogue_ratio_target
        )
        
        return self.SYSTEM_PROMPT_TEMPLATE.format(
            content_ratio_table=content_ratio_table,
            emphasis_instruction=config.emphasis_instruction,
            content_examples=self.CONTENT_EXAMPLES,
            current_deviation=deviation
        )
    
    def get_required_counts(self, deviation: float) -> Dict[str, int]:
        """Get target counts for content types based on deviation."""
        config = self.get_generation_config(deviation)
        ratio = config.content_ratio
        
        # Use middle values as targets
        return {
            "narration": (ratio.narration_min + ratio.narration_max) // 2,
            "dialogue": (ratio.dialogue_min + ratio.dialogue_max) // 2,
            "interaction": ratio.interaction_min
        }
    
    def get_function_schema_with_counts(self, deviation: float) -> Dict[str, Any]:
        """Get function schema with current target counts."""
        schema = self.FUNCTION_SCHEMA.copy()
        target_counts = self.get_required_counts(deviation)
        
        # Add count validation to schema with strict interaction requirement
        schema["parameters"]["properties"]["required_counts"]["properties"] = {
            "narration": {
                "type": "integer",
                "minimum": target_counts["narration"] - 1,
                "maximum": target_counts["narration"] + 1
            },
            "dialogue": {
                "type": "integer", 
                "minimum": target_counts["dialogue"] - 1,
                "maximum": target_counts["dialogue"] + 1
            },
            "interaction": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1,
                "description": "必须为1，脚本必须包含一个interaction单元"
            }
        }
        
        # Add validation for script_units array to ensure last element is interaction
        schema["parameters"]["properties"]["script_units"]["description"] = "脚本单元数组，最后一个单元必须是interaction类型"
        
        return schema
    
    def should_adjust_temperature(self, 
                                 deviation: float,
                                 last_narration_count: int,
                                 last_dialogue_count: int) -> Tuple[bool, float]:
        """
        Determine if temperature should be adjusted based on content balance.
        
        Returns:
            (should_adjust, new_temperature)
        """
        config = self.get_generation_config(deviation)
        base_temp = config.temperature
        
        # Check if narration/dialogue ratio is too high
        if last_dialogue_count > 0:
            ratio = last_narration_count / last_dialogue_count
            if ratio > 1.5:  # Too much narration
                # Lower temperature to reduce "flowery" language
                new_temp = max(0.3, base_temp - 0.2)
                return True, new_temp
        
        return False, base_temp
    
    def build_game_state_details(
        self,
        current_state: Dict[str, Any],
        target_counts: Dict[str, int]
    ) -> str:
        """Build game state details section."""
        return f"""
当前游戏状态详情：
- 偏差值: {current_state.get('deviation', 0):.2f}%
- 角色好感度: {current_state.get('affinity', {})}
- 故事标记: {current_state.get('flags', {})}
- 游戏变量: {current_state.get('variables', {})}

目标内容配比：
- 叙述单元: {target_counts['narration']} 个
- 对话单元: {target_counts['dialogue']} 个  
- 交互单元: {target_counts['interaction']} 个

**重要提醒**：
1. 不得强行将旁白改成人物对话
2. 应该尽可能将人物的内心独白提取出来作为"角色名（内心）：思考内容"的对话形式
3. 严格按照required_counts字段的数量要求生成内容
4. 必须以interaction单元结尾，只生成一个interaction单元
5. 确保dialogue单元包含准确的speaker字段
"""
    
    def build_anchor_info_section(self, anchor_info: Optional[Dict[str, Any]]) -> str:
        """Build anchor information section."""
        if not anchor_info:
            return ""
        
        return f"""
当前锚点信息：
- 锚点ID: {anchor_info.get('anchor_id', 'unknown')}
- 锚点描述: {anchor_info.get('brief', '')}
- 锚点类型: {anchor_info.get('type', '')}
- 相关角色: {', '.join(anchor_info.get('characters', []))}
- 影响程度: {anchor_info.get('impact_score', 0)}

重要：最终的choice事件必须与锚点描述完全一致！
"""
    
    def build_user_message(
        self,
        context: str,
        prompt: str,
        anchor_info: Optional[Dict[str, Any]],
        current_state: Dict[str, Any],
        target_counts: Dict[str, int],
        config: GenerationConfig
    ) -> str:
        """Build complete user message for LLM generation."""
        anchor_info_text = self.build_anchor_info_section(anchor_info)
        
        return f"""
原文内容：
{context}

玩家选择：
{prompt}

{anchor_info_text}

请严格基于上述原文内容生成故事脚本。根据当前偏差值({current_state.get('deviation', 0):.2f}%)和配比要求：

内容生成指导：
- 严格按照目标配比生成：叙述{target_counts['narration']}个，对话{target_counts['dialogue']}个，交互{target_counts['interaction']}个
- 当前对话比率目标：{config.dialogue_ratio_target}
- {config.emphasis_instruction}

角色对话优化：
1. 将角色内心思考转换为对话形式："角色名（内心）：思考内容"
2. 不得强行将环境描写、动作叙述改成对话
3. 优先使用角色对话推进剧情，减少纯描述性旁白
4. 保持角色性格、语言习惯的一致性

偏差控制：
- 偏差值<5%：几乎完全按原文生成，只做必要的适配
- 偏差值5-30%：基于原文进行适度改编，保持主线剧情  
- 偏差值>30%：通过角色对话引导回归原文主线

输出要求：
1. 必须包含required_counts字段验证数量约束
2. **【绝对要求】脚本必须以interaction单元结尾**
3. 最终的interaction事件必须与锚点描述完全一致
4. 确保dialogue单元包含准确的speaker字段
5. interaction单元必须提供choice_id和default_reply字段

**重要提醒**：如果没有interaction单元，游戏将无法继续！
"""
    
    def build_enhanced_prompt_section(
        self,
        current_state: Dict[str, Any],
        target_counts: Dict[str, int],
        config: GenerationConfig
    ) -> str:
        """Build enhanced prompt section for services.py."""
        return f"""生成指导:
- 目标配比: 叙述{target_counts['narration']}个, 对话{target_counts['dialogue']}个, 交互{target_counts['interaction']}个
- 对话比率目标: {config.dialogue_ratio_target}
- {config.emphasis_instruction}
- 将角色内心思考转换为对话形式"""
    
    def get_summarization_prompt(self) -> str:
        """Get prompt template for conversation summarization."""
        return """
请简洁地总结以下对话内容，保留关键情节和角色发展：

{text}

总结：
"""
    
    def get_fallback_response(self, session_id: str, error: str) -> Dict[str, Any]:
        """Get fallback response when generation fails."""
        from .models import ScriptUnit, ScriptUnitType
        
        return {
            "script_units": [
                ScriptUnit(
                    type=ScriptUnitType.NARRATION,
                    content="故事暂时停顿了一下，等待着下一个转折点的到来。",
                    metadata={"fallback": True, "error": error}
                ),
                ScriptUnit(
                    type=ScriptUnitType.INTERACTION,
                    content="请选择你的下一步行动：",
                    choice_id="fallback_choice",
                    default_reply="继续",
                    metadata={"fallback": True}
                )
            ],
            "required_counts": {"narration": 1, "dialogue": 0, "interaction": 1},
            "deviation_delta": 0.0,
            "affinity_changes": {},
            "metadata": {
                "fallback": True,
                "error": error,
                "session_id": session_id
            }
        }


# Global configuration instance
llm_config = LLMConfig()