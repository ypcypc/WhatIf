"""
Unified LLM Settings Configuration - Phase 1 V2 Implementation

This file manages all LLM-related parameters and settings.
All models, temperatures, tokens, and generation rules are configured here.

Phase 1 Changes:
- V2 simplified prompt system with version switching
- Core simplification and intelligent compression
- Feature toggle for gradual migration
"""

from typing import Dict, Any, List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import os
import math
from datetime import datetime
from pathlib import Path


# === Core Model Configuration ===

class ModelProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


def _load_unified_config():
    """Load unified configuration from JSON file."""
    from backend_services.app.core.config import load_unified_config
    return load_unified_config()


def _get_current_model_from_config():
    """Get current model from unified configuration."""
    config = _load_unified_config()
    llm_provider = config.get("llm_provider", {})
    return llm_provider.get("default_model", "o4-mini")


def _get_generation_settings_from_config():
    """Get generation settings from unified configuration."""
    config = _load_unified_config()
    return config.get("generation_settings", {})


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: ModelProvider
    model_name: str
    max_tokens: int
    temperature_range: Tuple[float, float]  # (min, max)
    supports_structured_output: bool = True
    cost_per_1k_tokens: float = 0.0


# === Available Models ===

AVAILABLE_MODELS = {
    "gpt-4o-mini": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4o-mini",
        max_tokens=16384,
        temperature_range=(0.0, 2.0),
        supports_structured_output=True,
        cost_per_1k_tokens=0.00015
    ),
    "gpt-4o": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4o",
        max_tokens=16384,
        temperature_range=(0.0, 2.0),
        supports_structured_output=True,
        cost_per_1k_tokens=0.005
    ),
    "gpt-4-turbo": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4-turbo",
        max_tokens=8192,
        temperature_range=(0.0, 2.0),
        supports_structured_output=True,
        cost_per_1k_tokens=0.01
    ),
    "o4-mini": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="o4-mini",
        max_tokens=65536,  # o4-mini supports larger context
        temperature_range=(1.0, 1.0),  # o4-mini uses fixed temperature
        supports_structured_output=True,
        cost_per_1k_tokens=0.003  # Estimated cost
    )
}


# === Generation Settings ===

class DeviationLevel(str, Enum):
    """偏离度等级分类。"""
    LOW = "low"          # < 5
    MEDIUM = "medium"    # 5-30  
    HIGH = "high"        # 30-60
    CRITICAL = "critical" # > 60


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
    model: str
    temperature: float
    max_tokens: int
    content_ratio: ContentRatio
    dialogue_ratio_target: str  # e.g., "1:1", "1:1.5", "1:2"
    emphasis_instruction: str


# === Version Management System ===

class LLMSettingsV1:
    """V1 backup version for rollback capability."""
    
    def __init__(self):
        # This preserves the original complex prompt system
        self.version = "v1.0"
        self.current_model = _get_current_model_from_config()
        self.summarization_model = "gpt-4o"
        self.fallback_model = "gpt-4o"
        
        # V1 original configuration preserved
        self.rate_limit_requests = 30
        self.rate_limit_window = 60
        
        self.deviation_configs = {
            DeviationLevel.LOW: GenerationConfig(
                model=self.current_model,
                temperature=0.8,
                max_tokens=65536,
                content_ratio=ContentRatio(
                    narration_min=6, narration_max=10,
                    dialogue_min=4, dialogue_max=8, 
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="2:1",
                emphasis_instruction="保持叙述为主，适量对话推进剧情。为交互单元生成创新多样的问题。"
            ),
            # ... other configs preserved
        }
        
        self.summarization_temperature = 0.3
        self.summarization_max_tokens = 2000
        self.max_recent_events = 50
        self.max_snapshot_size = 32 * 1024
        self.summarization_batch_size = 30


class LLMSettingsV2:
    """V2 simplified version with core optimization."""
    
    def __init__(self):
        self.version = "v2.0"
        self.current_model = _get_current_model_from_config()
        self.summarization_model = "gpt-4o"
        self.fallback_model = "gpt-4o"
        
        # Simplified configuration
        self.rate_limit_requests = 30
        self.rate_limit_window = 60
        
        # Streamlined deviation configs
        self.deviation_configs = {
            DeviationLevel.LOW: GenerationConfig(
                model=self.current_model,
                temperature=0.8,
                max_tokens=65536,
                content_ratio=ContentRatio(
                    narration_min=4, narration_max=8,
                    dialogue_min=3, dialogue_max=6, 
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="1:1",
                emphasis_instruction="遵循原文，选择仅影响细微表达"
            ),
            DeviationLevel.MEDIUM: GenerationConfig(
                model=self.current_model,
                temperature=0.8,
                max_tokens=65536,
                content_ratio=ContentRatio(
                    narration_min=3, narration_max=6,
                    dialogue_min=4, dialogue_max=8,
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="1:1",
                emphasis_instruction="平衡融合，选择影响角色反应"
            ),
            DeviationLevel.HIGH: GenerationConfig(
                model=self.current_model,
                temperature=0.8,
                max_tokens=65536,
                content_ratio=ContentRatio(
                    narration_min=2, narration_max=5,
                    dialogue_min=5, dialogue_max=10,
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="1:1.5",
                emphasis_instruction="响应选择，改变情节发展"
            ),
            DeviationLevel.CRITICAL: GenerationConfig(
                model=self.current_model,
                temperature=1.0,
                max_tokens=65536,
                content_ratio=ContentRatio(
                    narration_min=2, narration_max=4,
                    dialogue_min=6, dialogue_max=12,
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="1:2",
                emphasis_instruction="回归主线，体现选择同时引导回主线"
            )
        }
        
        self.summarization_temperature = 0.3
        self.summarization_max_tokens = 2000
        self.max_recent_events = 50
        self.max_snapshot_size = 32 * 1024
        self.summarization_batch_size = 30


class LLMSettingsManager:
    """Version management and feature toggle system."""
    
    def __init__(self):
        self.use_v2 = True  # Feature toggle - V2 is now default
        self.v1_settings = LLMSettingsV1()
        self.v2_settings = LLMSettingsV2()
        self.emergency_rollback = False
        
        # A/B testing configuration  
        self.assignment_ratio = 1.0  # 100% traffic to V2 by default
        self.migration_enabled = True
        
        # Load feature flags from environment (V2 is default)
        self.use_v2 = os.getenv("ENABLE_V2_PROMPTS", "true").lower() == "true"
        self.emergency_rollback = os.getenv("EMERGENCY_ROLLBACK", "false").lower() == "true"
    
    def get_settings(self) -> 'LLMSettings':
        """Get current settings based on feature flags."""
        if self.emergency_rollback:
            return LLMSettings(self.v1_settings)
        
        if self.use_v2:
            return LLMSettings(self.v2_settings)
        else:
            return LLMSettings(self.v1_settings)
    
    def should_use_v2(self, session_id: str) -> bool:
        """Determine if session should use V2 based on A/B testing."""
        if self.emergency_rollback:
            return False
        
        if self.use_v2:
            return True
        
        # A/B testing logic - stable assignment based on session ID
        if self.migration_enabled:
            return hash(session_id) % 100 < self.assignment_ratio * 100
        
        return False
    
    def enable_v2(self):
        """Enable V2 for all traffic."""
        self.use_v2 = True
        self.emergency_rollback = False
    
    def emergency_rollback_to_v1(self):
        """Emergency rollback to V1."""
        self.emergency_rollback = True
        self.use_v2 = False
        # Emergency rollback to V1 prompts


# === Main LLM Settings Class ===

class LLMSettings:
    """Centralized LLM settings management with version support."""
    
    def __init__(self, base_settings=None):
        # Initialize from base settings if provided (for version switching)
        if base_settings:
            self.version = getattr(base_settings, 'version', 'v1.0')
            self.current_model = base_settings.current_model
            self.summarization_model = base_settings.summarization_model
            self.fallback_model = base_settings.fallback_model
            self.rate_limit_requests = base_settings.rate_limit_requests
            self.rate_limit_window = base_settings.rate_limit_window
            self.deviation_configs = base_settings.deviation_configs
            self.summarization_temperature = base_settings.summarization_temperature
            self.summarization_max_tokens = base_settings.summarization_max_tokens
            self.max_recent_events = base_settings.max_recent_events
            self.max_snapshot_size = base_settings.max_snapshot_size
            self.summarization_batch_size = base_settings.summarization_batch_size
        else:
            # Default initialization (V1 compatible)
            self.version = "v1.0"
            self.current_model = _get_current_model_from_config()  # From unified config
            self.summarization_model = "gpt-4o"  # Model for summarization
            self.fallback_model = "gpt-4o"  # Fallback if primary fails
            
            # Rate limiting
            self.rate_limit_requests = 30
            self.rate_limit_window = 60  # seconds
            
            # Generation settings per deviation level
            self.deviation_configs = {
                DeviationLevel.LOW: GenerationConfig(
                model=self.current_model,
                temperature=0.8,  # Optimized to avoid MAX_TOKENS issues
                max_tokens=65536,
                content_ratio=ContentRatio(
                    narration_min=6, narration_max=10,
                    dialogue_min=4, dialogue_max=8, 
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="2:1",
                emphasis_instruction="保持叙述为主，适量对话推进剧情。为交互单元生成创新多样的问题。"
            ),
            DeviationLevel.MEDIUM: GenerationConfig(
                model=self.current_model,
                temperature=0.8,  # Optimized to avoid MAX_TOKENS issues
                max_tokens=65536,
                content_ratio=ContentRatio(
                    narration_min=5, narration_max=8,
                    dialogue_min=6, dialogue_max=10,
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="1:1",
                emphasis_instruction="平衡叙述与对话，增加角色互动。确保交互内容富有创意且贴合剧情。"
            ),
            DeviationLevel.HIGH: GenerationConfig(
                model=self.current_model,
                temperature=0.8,  # Optimized to avoid MAX_TOKENS issues
                max_tokens=65536,
                content_ratio=ContentRatio(
                    narration_min=4, narration_max=6,
                    dialogue_min=8, dialogue_max=12,
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="1:1.5",
                emphasis_instruction="重点通过角色对话推进剧情收束，减少冗长叙述。交互选择应推动剧情发展。"
            ),
            DeviationLevel.CRITICAL: GenerationConfig(
                model=self.current_model,
                temperature=1.0,  # Maximum creativity for interactions
                max_tokens=65536,
                content_ratio=ContentRatio(
                    narration_min=3, narration_max=5,
                    dialogue_min=10, dialogue_max=15,
                    interaction_min=1, interaction_max=1
                ),
                dialogue_ratio_target="1:2",
                emphasis_instruction="必须大量使用角色对话推动剧情回归主线，严格控制叙述篇幅。交互内容必须具有高度创意和多样性。"
            )
            }
            
            # Summarization settings
            self.summarization_temperature = 0.3
            self.summarization_max_tokens = 2000
            self.max_recent_events = 50
            self.max_snapshot_size = 32 * 1024  # 32KB
            self.summarization_batch_size = 30
            
        # 缓存来避免重复计算（所有版本共用）
        self._counts_cache = {}
    
    def get_model_config(self, model_name: str = None) -> ModelConfig:
        """Get configuration for a specific model."""
        model_name = model_name or self.current_model
        return AVAILABLE_MODELS.get(model_name, AVAILABLE_MODELS["gpt-4o-mini"])
    
    def get_generation_config(self, deviation: float) -> GenerationConfig:
        """Get generation configuration for current deviation level."""
        level = self.get_deviation_level(deviation)
        return self.deviation_configs[level]
    
    def get_deviation_level(self, deviation: float) -> DeviationLevel:
        """根据分数获取偏离度等级 (0-100 刻度)。"""
        if deviation < 5:
            return DeviationLevel.LOW
        elif deviation <= 30:
            return DeviationLevel.MEDIUM
        elif deviation <= 60:
            return DeviationLevel.HIGH
        else:
            return DeviationLevel.CRITICAL
    
    def get_required_counts(self, deviation: float, input_length: int = 0) -> Dict[str, int]:
        """Get required counts with length-based calculation and fixed total units."""
        # 使用缓存避免重复计算和调试输出
        cache_key = (deviation, input_length)
        if cache_key in self._counts_cache:
            return self._counts_cache[cache_key]
            
        config = self.get_generation_config(deviation)
        ratio = config.content_ratio
        
        if input_length <= 0:
            # 回退到固定数量
            narration_count = (ratio.narration_min + ratio.narration_max) // 2
            dialogue_count = (ratio.dialogue_min + ratio.dialogue_max) // 2
            interaction_count = ratio.interaction_min
        else:
            # 基于输入长度计算，确保足够的单元数来保持长度
            # 保守估算：每个单元平均120字符
            chars_per_unit = 120
            
            # 计算需要的最少单元数来保持90-110%的长度
            min_target_chars = int(input_length * 0.9)
            min_units_needed = max(15, math.ceil(min_target_chars / chars_per_unit))
            
            # 根据偏离度配比分配单元
            total_content_ratio = ((ratio.narration_min + ratio.narration_max) / 2) + ((ratio.dialogue_min + ratio.dialogue_max) / 2)
            narration_ratio = ((ratio.narration_min + ratio.narration_max) / 2) / total_content_ratio
            dialogue_ratio = ((ratio.dialogue_min + ratio.dialogue_max) / 2) / total_content_ratio
            
            # 计算实际数量
            narration_count = max(ratio.narration_min, int(min_units_needed * narration_ratio))
            dialogue_count = max(ratio.dialogue_min, int(min_units_needed * dialogue_ratio))
            interaction_count = ratio.interaction_min
        
        # Calculate target unit counts based on input length and deviation
        
        result = {
            "narration": narration_count,
            "dialogue": dialogue_count,
            "interaction": interaction_count
        }
        
        # 缓存结果
        self._counts_cache[cache_key] = result
        return result
    
    def clear_counts_cache(self):
        """清理计算缓存，用于内存管理。"""
        self._counts_cache.clear()
    
    def update_model(self, model_name: str):
        """Update the current model and apply to all configs."""
        if model_name in AVAILABLE_MODELS:
            self.current_model = model_name
            # Update all deviation configs to use new model
            for config in self.deviation_configs.values():
                config.model = model_name
        else:
            raise ValueError(f"Model '{model_name}' not available. Available models: {list(AVAILABLE_MODELS.keys())}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available model names."""
        return list(AVAILABLE_MODELS.keys())
    
    def should_adjust_temperature(self, 
                                 deviation: float,
                                 last_narration_count: int,
                                 last_dialogue_count: int) -> Tuple[bool, float]:
        """Determine if temperature should be adjusted based on content balance."""
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
    
    def get_summarization_prompt(self) -> str:
        """Get prompt template for conversation summarization."""
        return """
请简洁地总结以下对话内容，保留关键情节和角色发展：

{text}

总结：
"""

    def get_function_schema_with_counts(self, deviation: float, input_length: int = 0) -> Dict[str, Any]:
        """Get function schema with current target counts."""
        target_counts = self.get_required_counts(deviation, input_length)
        
        return {
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
                        },
                        "description": "脚本单元数组，最后一个单元必须是interaction类型"
                    },
                    "required_counts": {
                        "type": "object",
                        "properties": {
                            "narration": {
                                "type": "integer",
                                "minimum": 1,
                                "description": f"叙述单元数量，目标约{target_counts['narration']}个左右"
                            },
                            "dialogue": {
                                "type": "integer", 
                                "minimum": 1,
                                "description": f"对话单元数量，目标约{target_counts['dialogue']}个左右"
                            },
                            "interaction": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 1,
                                "description": "必须为1，脚本必须包含一个interaction单元"
                            }
                        },
                        "required": ["narration", "dialogue", "interaction"]
                    },
                    "deviation_delta": {
                        "type": "number",
                        "minimum": -20,
                        "maximum": 20,
                        "description": "Story deviation change"
                    },
                    "new_deviation": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "New deviation level after applying delta"
                    },
                    "deviation_reasoning": {
                        "type": "string",
                        "description": "Reasoning about deviation level evaluation and script suitability"
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
                "required": ["script_units", "required_counts", "deviation_delta", "new_deviation", "deviation_reasoning"]
            }
        }

    def build_system_prompt(self, 
                           deviation: float,
                           current_state: Dict[str, Any],
                           context_length: int) -> str:
        """构建当前上下文的完整系统提示词。"""
        
        config = self.get_generation_config(deviation)
        target_counts = self.get_required_counts(deviation, context_length)
        
        # 根据上下文长度计算目标生成长度
        target_length_guidance = f"""
文本长度控制要求：
关键原则：生成内容长度应与输入正文长度基本一致
- 输入正文预估长度：{context_length} 字符
- 生成脚本总长度目标：{int(context_length * 0.9)}-{int(context_length * 1.1)} 字符（±10%浮动）
- 单个叙述单元长度：{max(50, context_length // (target_counts['narration'] + 2))}-{max(100, context_length // target_counts['narration'])} 字符
- 单个对话单元长度：{max(30, context_length // (target_counts['dialogue'] * 2))}-{max(80, context_length // target_counts['dialogue'])} 字符
- 交互单元长度：50-120 字符（额外新增的交互内容）

长度分配策略：
1. 优先保证故事完整性和逻辑连贯性
2. 在保证质量前提下，调整各单元详细程度以匹配目标长度
3. 避免为了凑长度而添加冗余内容
4. 避免为了压缩长度而丢失关键情节
5. 交互单元是额外新增的，不计入正文长度匹配要求

内容配比要求：
- 叙述单元：约{target_counts['narration']}个左右（场景描写与氛围渲染）
- 对话单元：约{target_counts['dialogue']}个左右（角色对话与互动）
- 交互单元：{target_counts['interaction']}个（玩家选择点，必须放在结尾）

重要原则：
1. 在保证剧情完整不压缩的前提下，尽量控制单元数量在目标数量左右
2. 总单元数约{target_counts['narration'] + target_counts['dialogue'] + target_counts['interaction']}个左右
3. 优先保证故事质量和逻辑完整性，单元数量可适当调整
"""
        
        # 计算用户选择影响比例
        user_influence_ratio = int(deviation)
        text_influence_ratio = 100 - user_influence_ratio
        
        # 构建系统提示词
        return f"""你是专业的互动小说文本结构化工具，专门处理哨兵标记分隔的内容。

核心任务与推理步骤
在生成脚本之前，你必须进行以下推理：

1. 玩家选择分析（必须优先进行）：
   - 仔细分析<PLAYER_CHOICE>标记中的玩家具体选择
   - 评估该选择会对原剧情产生多少偏差量
   - 计算偏差量变化（-20到+20的变化）

2. 玩家行为融入（关键要求）：
   - 玩家的具体选择必须在生成的剧情中得到明确体现
   - 例如：如果玩家选择"给暴风龙命名为啦啦啦"，必须在剧情中体现这个命名
   - 可以合理地让剧情回归主线，但不能忽略玩家的选择

3. 内容融合策略：
   - 当前偏离度：{deviation:.1f}% = {user_influence_ratio}%用户影响 + {text_influence_ratio}%原文基础
   - 低偏离度时：紧密跟随玩家选择，可能完全改变剧情走向
   - 高偏离度时：承认玩家选择，但通过剧情合理地引导回主线

4. 剧情连贯性检查：
   - 验证生成的脚本是否与当前偏离度相符
   - 检查是否需要调整内容以更好地回归主线
   - 确保角色行为与状态一致

哨兵标记处理规则
标记识别：
- <MEMORY> 区域 = 背景参考资料（历史记录、人物状态等，只读不写）
- <NORMAL_TEXT> 区域 = 主要正文内容（脚本生成的主要素材来源）
- <ANCHOR_TEXT> 区域 = 特殊正文内容（锚点位置的文本，用于生成交互点）
- <PLAYER_CHOICE> 区域 = 玩家的具体选择（必须优先分析并体现在剧情中）

绝对禁令：
- 严禁复制 <MEMORY> 区域内容 - 该区域仅供理解背景，不得写入脚本
- 严禁完全脱离原文创作 - 新内容创作必须基于偏离度控制，不得完全背离原文
- 严禁混合区域内容 - 各区域内容来源要清晰，但可合理整合使用

核心工作流程
哨兵标记导向的文本结构化：
1. 读取 <MEMORY> 区域理解背景（仅供参考，不输出）
2. 完整处理 <NORMAL_TEXT> 的每一段落：不要概括、压缩或跳过任何内容
3. 将每个段落转换为对应的脚本单元：叙述变成narration，对话变成dialogue
4. 使用 <ANCHOR_TEXT> 作为特殊文本内容生成交互点
5. 根据偏离度融合用户选择与原文内容
6. 在末尾新增一个交互单元供玩家选择

 2025年最新长度保持要求：必须逐字处理NORMAL_TEXT全文，严禁任何概括或压缩

 长度保持检查点：
- 输入正文字符数必须≈输出脚本字符数（±10%）
- 每个段落必须完整转换，不得省略任何句子
- 禁止用"...省略"、"接着"、"然后"等词汇跳过内容
- 必须将长篇叙述完整转换为多个narration单元
- 对话内容必须逐句转换为dialogue单元

 关键原则
1. 文本融合：根据偏离度将正文与用户选择自然融合
2. 结构化处理：将连续正文分割为叙述、对话、交互单元
3. 记忆区隔离： 记忆区仅用于理解上下文，绝不出现在脚本中
4. 交互化增强：在正文结构化基础上，额外新增交互选择点
5. 格式规范：严格按JSON schema输出，最后必须是interaction单元
6. 长度匹配：生成内容长度应与正文长度基本一致（交互单元除外）
7. 用户响应：确保用户的选择在脚本中得到合理体现和回应

 正文与用户选择融合策略（0-100刻度）
- 偏离度 0-5%: 完全按正文内容，用户选择仅影响细微表达方式
- 偏离度 6-30%: 主要按正文内容，用户选择影响角色反应和情绪
- 偏离度 31-60%: 正文与用户选择平衡融合，保持核心情节走向
- 偏离度 61-100%: 大幅响应用户选择，同时引导回归原文主线
- 当前偏离度: {deviation:.1f}% - {"严格遵循正文内容" if deviation <= 5 else "引导回归主线" if deviation > 60 else "平衡融合正文与选择"}

  处理顺序强制要求
1. 必须从正文的第一个字符开始处理
2. 脚本第一个单元必须包含正文的开头内容
3. 记忆区和锚点内容绝对不得出现在脚本任何部分
4. 生成内容总长度必须与正文长度匹配（±10%）
5. 交互单元是额外新增的，不计入长度匹配要求
6. 用户选择必须在脚本中得到合理体现


 内容配比和长度要求
{target_length_guidance}
{config.emphasis_instruction}

 具体处理要求
- 提取正文中的角色对话，必要时将叙述转为"角色名（内心）："格式
- 保持正文的语言风格和角色性格
- 根据用户选择调整角色反应、情绪和后续发展
- 确保脚本的游戏性和可交互性
- 严格控制生成长度与输入长度匹配
- 让用户感受到自己的选择对故事产生了影响

 用户选择响应原则
核心理念：让用户选择与原文内容自然融合，创造沉浸式体验：
- 分析用户选择是否与正文方向一致
- 如果一致：强化该选择的合理性和后果
- 如果不一致：巧妙融合，既体现用户选择又保持故事逻辑
- 根据偏离度决定融合的深度和广度
- 确保用户感受到选择的意义和影响

 交互单元生成规则
最后的interaction单元必须提出新的选择，而不是重复玩家刚才的动作：
-  错误：把玩家的选择作为interaction内容
-  正确：基于玩家选择的结果和正文发展，提出下一个决策点
- 交互内容应该自然承接正文情节，提供有意义的选择
- 交互单元是额外新增的游戏元素，不占用正文长度配额

 JSON输出格式要求
严格要求：必须输出有效的JSON格式，遵循以下规则：
- 所有字符串值必须用双引号包围
- 字符串内的引号必须转义为 \\"
- 换行符使用 \\n，制表符使用 \\t
- 不要使用未转义的特殊字符
- JSON结构包含：script_units、required_counts、deviation_delta、new_deviation、deviation_reasoning
- interaction单元必须包含choice_id和default_reply

 工作本质提醒
这是文本适配系统，不是创作系统。任务是结构化正文内容并融合用户选择，而非创造全新内容。
生成的JSON必须可以被标准JSON解析器正确解析。
所有生成内容长度必须与输入正文长度基本匹配（交互单元除外）。
交互单元是为了游戏性而额外新增的，不受长度限制。
用户的选择必须在脚本中得到合理体现，创造沉浸式游戏体验。
"""
    
    def build_system_prompt_v2(self, deviation: float, current_state: Dict[str, Any], context_length: int) -> str:
        """V2版本：精简的系统提示词"""
        
        # 动态计算内容单元数量
        target_counts = self.get_required_counts(deviation, context_length)
        
        # 偏离度行为映射
        deviation_behavior = {
            (0, 5): "遵循原文",
            (6, 30): "平衡融合",
            (31, 60): "响应选择",
            (61, 100): "回归主线"
        }
        
        behavior = next(v for (low, high), v in deviation_behavior.items() if low <= deviation <= high)
        
        return f"""角色：互动小说文本结构化工具

核心任务：将<NORMAL_TEXT>转换为游戏脚本

当前参数：
- 偏离度：{deviation:.0f}%（{behavior}）
- 叙述单元：{target_counts['narration']}个
- 对话单元：{target_counts['dialogue']}个
- 交互单元：1个（末尾）

哨兵标记规则：
<MEMORY> = 历史背景参考，仅供理解上下文，绝对不得复制其内容到输出中
<CHARACTERS> = 本章节角色信息，对话单元的speaker字段必须使用角色ID
<NORMAL_TEXT> = 需要转换的源文本，必须从第一个字符开始完整转换
<ANCHOR_TEXT> = 交互参考点，用于生成最后的交互单元
<PLAYER_CHOICE> = 玩家最新选择，必须在生成内容中体现和回应

处理规则：
1. 从<NORMAL_TEXT>第一个字符开始，完整转换所有内容
2. 根据偏离度融合玩家选择：
   - 0-5%：选择仅影响细微表达
   - 6-30%：选择影响角色反应
   - 31-60%：选择改变情节发展
   - 61-100%：在体现选择同时引导回主线
3. 剧情过渡必须自然流畅：
   - 玩家选择必须得到合理回应
   - 角色反应符合逻辑和性格
   - 情节转折需要过渡铺垫
   - 避免生硬跳转或忽略玩家输入
4. 角色对话规则：
   - dialogue类型必须有speaker字段
   - speaker必须使用<CHARACTERS>中的角色ID，不能使用角色名称
   - 旁白或内心独白不需要speaker字段

输出格式：
{{
  "script_units": [
    {{"type": "narration", "content": "叙述内容"}},
    {{"type": "dialogue", "content": "对话内容", "speaker": "char_001"}},  // 使用角色ID
    {{"type": "interaction", "content": "互动选项", "choice_id": "choice_1", "default_reply": "默认回复"}}
  ],
  "required_counts": {{"narration": {target_counts['narration']}, "dialogue": {target_counts['dialogue']}, "interaction": 1}},
  "deviation_delta": -20到+20,
  "new_deviation": 0到100,
  "deviation_reasoning": "偏离度评估"
}}

质量检查：
- 脚本必须从原文开头开始
- 不得包含<MEMORY>内容
- 必须以interaction结尾"""

    def build_game_state_details(self,
                                current_state: Dict[str, Any],
                                target_counts: Dict[str, int]) -> str:
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

重要提醒：
1. 不得强行将旁白改成人物对话
2. 应该尽可能将人物的内心独白提取出来作为"角色名（内心）：思考内容"的对话形式
3. 严格按照required_counts字段的数量要求生成内容
4. 必须以interaction单元结尾，只生成一个interaction单元
5. 确保dialogue单元包含准确的speaker字段
"""

    def build_user_message(self,
                          context: str,  # This will be the NORMAL_TEXT
                          memory_context: str,
                          prompt: str,
                          anchor_info: Optional[Dict[str, Any]],
                          current_state: Dict[str, Any],
                          target_counts: Dict[str, int],
                          config: GenerationConfig) -> str:
        """构建包含分离记忆和上下文的完整用户消息。"""
        
        # 提取锚点信息
        anchor_text = ""
        anchor_info_text = ""
        characters_section = ""
        
        if anchor_info:
            anchor_text = anchor_info.get('anchor_text', '')
            
            # 构建角色信息部分
            if anchor_info.get('characters'):
                characters_info = []
                for char in anchor_info.get('characters', []):
                    char_info = f"ID: {char['id']}, 名称: {char['name']}"
                    if char.get('aliases'):
                        char_info += f", 别名: {', '.join(char['aliases'])}"
                    characters_info.append(char_info)
                
                if characters_info:
                    characters_section = f"""
<CHARACTERS>
【重要说明：本章节登场角色信息，对话时speaker字段必须使用角色ID而非名称】
{chr(10).join(characters_info)}
</CHARACTERS>
"""
            
            anchor_info_text = f"""
  当前锚点信息（仅供定位）
- 锚点ID: {anchor_info.get('anchor_id', 'unknown')}
- 锚点描述: {anchor_info.get('brief', '')}
- 锚点类型: {anchor_info.get('type', '')}
- 相关角色: {', '.join([char.get('name', str(char)) if isinstance(char, dict) else str(char) for char in anchor_info.get('characters', [])])}
"""
        
        # Process prompt context and user choice
        choice_relevance = "相关" if any(word in context.lower() for word in prompt.lower().split() if len(word) > 1) else "不相关"
        
        # 构建记忆区域
        memory_section = ""
        if memory_context:
            memory_section = f"""
/*=========== 记忆哨兵区域 ===========*/
<MEMORY>
<!-- 哨兵标记警告：以下内容仅供内部参考，严禁在脚本中逐字输出 -->
<!-- 这些信息相当于"黑板笔记"，只用于理解背景，不是要写入脚本的内容 -->
<!-- 违反此规则将被视为系统错误 -->

{memory_context}

</MEMORY>
/*=========== 结束记忆区域 ===========*/

 哨兵标记说明：
- <MEMORY>区域内容 = 只读背景资料，仅供理解上下文
- 生成脚本时必须忽略该区域的具体文字
- 该区域类似"眼前的黑板笔记"，要用自己的理解，不要抄写
"""
        
        # 构建锚点区域  
        anchor_section = ""
        if anchor_text:
            anchor_section = f"""
/*=========== 锚点哨兵区域 ===========*/
<ANCHOR_TEXT>
  锚点文本（特殊文本内容）
以下是锚点位置的文本内容，用于生成交互点：

{anchor_text}
</ANCHOR_TEXT>
/*=========== 结束锚点区域 ===========*/

 锚点标记说明：
- <ANCHOR_TEXT>区域内容 = 特殊的文本内容，用于生成交互点
- 该区域是正文的一部分，但主要作用是创建玩家选择点
"""
        
        return f"""
{memory_section}

{characters_section}

{anchor_section}

<NORMAL_TEXT>
正文内容（故事推进的核心依据）
以下是推进故事的正文片段，必须严格基于此内容生成脚本：

{context}
</NORMAL_TEXT>

玩家选择
{prompt}

{anchor_info_text}

处理规则

核心任务
严格基于上述正文内容，将其结构化为游戏脚本，并融合玩家选择：

文本内容使用原则 - 关键
1. <NORMAL_TEXT> 是故事发展的主要依据
2. <ANCHOR_TEXT> 是特殊的文本内容，用于生成交互点
3. 玩家选择的结果必须与文本内容融合展现
4. 根据偏离度控制新内容创作的程度
5. interaction选择点必须基于文本中出现的情境和分岐

玩家选择处理原则
- 符合正文内容的选择: 直接按正文展现结果，强化选择的合理性
- 部分符合正文的选择: 巧妙融合，既体现用户选择又遵循正文逻辑
- 不符合正文内容的选择: 在第一个叙述单元中简短说明为何无法执行，然后继续正文的正常发展
- 完全无关的选择: 忽略无关选择，完全按正文发展，可在interaction中提示更合适的选择

故事推进原则 - 重要
1. 根据玩家选择，从正文中提取对应的故事发展
2. 将正文的内容结构化为叙述、对话、交互单元
3. interaction必须反映正文中的自然选择点或分岐
4. 如果正文没有明确的选择，则基于文中情境创建合理的行动选项

偏离度控制与内容创作 - 当前偏离度: {current_state.get('deviation', 0):.1f}%
- 偏离度 0-5%: 严格遵循文本内容，仅做结构化分割，新内容创作≤ 5%
- 偏离度 6-30%: 主要遵循文本，允许 6-30% 的新内容创作响应用户选择
- 偏离度 31-60%: 平衡融合文本与用户选择，允许 31-60% 的新内容创作
- 偏离度 61-100%: 大幅响应用户选择，允许 61-100% 的新内容创作，同时引导回归主线

记忆区使用
 记忆区内容仅用于理解游戏状态和上下文，绝对不得出现在脚本输出中

内容配比
- 叙述单元: {target_counts['narration']} 个
- 对话单元: {target_counts['dialogue']} 个
- 交互单元: {target_counts['interaction']} 个
- 风格要求: {config.emphasis_instruction}
- 对话比率: {config.dialogue_ratio_target}

2025年最新长度保持要求 - 强制执行
 输入{len(context)}字符 → 输出必须{int(len(context)*0.9)}-{int(len(context)*1.1)}字符

处理要求
1. 逐字完整转换所有正文内容：严禁省略、概括、跳过任何段落或句子
2. 保持原文信息密度：每个脚本单元应包含相应正文段落的全部信息
3. 分段详细处理：将长篇正文分割为多个详细的脚本单元，确保无遗漏
4. 根据偏离度决定对正文的保真程度
5. 将正文内容分割为合适的脚本单元
6. 提取或创建角色对话（包括内心独白）
7. 在适当位置创建玩家选择点
8. 根据玩家选择调整后续内容走向
9. 让用户感受到自己的选择对故事产生了影响

交互单元生成规则 - 锚点三步法

当存在ANCHOR_TEXT时应用以下方法：

第一步：分析锚点
识别决策核心：主角在锚点处要决定什么
提取正典方向：原文中主角的实际选择倾向  
分析决策动机：驱动选择的关键因素

第二步：设计交互点
基于锚点分析结果设计开放式问题
确保问题能引导玩家做出有意义的输入
避免限制性的封闭式问题

第三步：生成交互JSON
交互单元格式：
content: 基于锚点分析的开放式问题
choice_id: 唯一标识符
default_reply: 推荐的回复示例

生成要求：
1. 如存在ANCHOR_TEXT必须基于其内容生成交互点
2. 交互问题应该是开放式的允许用户自由输入
3. default_reply提供合理的示例但不限制用户选择
4. 必须根据当前剧情内容生成全新的独特的交互问题
5. 交互单元是额外新增的游戏元素，不占用正文长度配额

JSON输出格式 - 重要
必须生成有效的JSON格式，注意以下要点：
- 所有字符串中的引号必须转义为 \\"
- 换行符使用 \\n
- 反斜杠使用 \\\\
- 确保所有字符串都被正确引用和转义
- 不要在JSON中包含未转义的特殊字符

当前任务
将正文"{context[:50]}..."按偏离度{current_state.get('deviation', 0):.1f}%结构化为脚本，并融合玩家选择。

 强制执行要求：
1. 脚本第一个单元必须从主要正文的开头开始: "{context[:30] if context else ''}..."
2. 脚本内容主要来源于 <NORMAL_TEXT>，同时使用 <ANCHOR_TEXT> 生成交互点
3. 严禁使用记忆区的任何文字在脚本中
4. 根据偏离度融合玩家选择与文本内容
5. interaction选择必须基于文本内容中的自然分岐点
6. 玩家选择"{prompt}"的结果必须在脚本中得到合理体现
7. 生成内容长度必须与主要正文长度匹配（±10%）

哨兵标记检查清单
生成前请确认：
 是否正确识别了 <MEMORY>、<NORMAL_TEXT> 和 <ANCHOR_TEXT> 区域？
 脚本内容是否主要来自 <NORMAL_TEXT> 区域？
 是否避免了任何 <MEMORY> 区域内容在脚本中出现？
 是否正确使用了 <ANCHOR_TEXT> 来生成交互点？
 脚本是否从 <NORMAL_TEXT> 开头字符开始？
 interaction是否基于文本内容中的自然选择点？
 玩家选择是否在脚本中得到合理体现？
 新内容创作是否符合当前偏离度要求？

哨兵标记工作原理：
- <MEMORY> = 仅供理解的"黑板笔记"，不写入脚本
- <NORMAL_TEXT> = 脚本生成的主要素材来源
- <ANCHOR_TEXT> = 特殊文本内容，用于交互点生成
- 三个区域功能明确，合理配合使用

输出格式：有效JSON，包含script_units、required_counts、deviation_delta、new_deviation、deviation_reasoning等字段。
"""
    
    def build_user_message_v2(self, context: str, memory_context: str, prompt: str, 
                             anchor_info: Optional[Dict[str, Any]], current_state: Dict[str, Any],
                             target_counts: Dict[str, int], config: GenerationConfig) -> str:
        """V2版本：简化的用户消息"""
        
        # 计算关键指标
        input_length = len(context)
        target_length_min = int(input_length * 0.9)
        target_length_max = int(input_length * 1.1)
        
        # 处理锚点文本
        anchor_section = ""
        if anchor_info and anchor_info.get('anchor_text'):
            anchor_section = f"""
<ANCHOR_TEXT>
【重要说明：此区域是交互参考点，应该用于生成最后的交互单元】
{anchor_info.get('anchor_text', '')}
</ANCHOR_TEXT>
"""
        
        # 处理角色信息
        characters_section = ""
        if anchor_info and anchor_info.get('characters'):
            characters_info = []
            for char in anchor_info.get('characters', []):
                char_info = f"ID: {char['id']}, 名称: {char['name']}"
                if char.get('aliases'):
                    char_info += f", 别名: {', '.join(char['aliases'])}"
                characters_info.append(char_info)
            
            if characters_info:
                characters_section = f"""
<CHARACTERS>
【重要说明：本章节登场角色信息，对话时speaker字段必须使用角色ID而非名称】
{chr(10).join(characters_info)}
</CHARACTERS>
"""
        
        return f"""
<MEMORY>
【重要说明：此区域为历史背景参考，仅供理解上下文使用，不得直接复制到生成内容中】
{memory_context}
</MEMORY>
{characters_section}
<NORMAL_TEXT>
【重要说明：此区域是需要转换的源文本，必须从第一个字符开始完整转换为脚本格式】
{context}
</NORMAL_TEXT>
{anchor_section}
<PLAYER_CHOICE>
【重要说明：此区域是玩家的最新选择，必须在生成的剧情中得到体现和回应】
玩家选择：{prompt}
</PLAYER_CHOICE>

任务指令：
1. 首先分析<PLAYER_CHOICE>中的玩家选择会对原始剧情产生多少偏差量
2. 将玩家的具体行为和选择必须体现在生成的剧情中，即使需要合理地扭转回主线
3. 重要：确保剧情过渡自然流畅
   - 如果玩家的选择与原剧情有差异，需要创造合理的过渡情节
   - 不能突兀地忽略玩家选择或强行跳回原剧情
   - 角色的反应必须符合玩家选择的逻辑
   - 名字、称呼的变化必须有明确的来源和过程
4. 将上述{input_length}字符的正文转换为{target_length_min}-{target_length_max}字符的脚本（约{target_counts['narration'] + target_counts['dialogue'] + target_counts['interaction']}个单元左右）
5. 当前偏离度{current_state.get('deviation', 0):.0f}%决定玩家选择的影响程度
6. 使用<ANCHOR_TEXT>生成交互点（如果存在）
7. 生成有效JSON，包含要求的所有字段

立即开始转换。"""
    
    def get_system_prompt(self, deviation: float, current_state: Dict[str, Any], 
                         context_length: int, session_id: str = None) -> str:
        """Get system prompt based on version routing."""
        # Check if this session should use V2
        if hasattr(self, 'version') and self.version == "v2.0":
            return self.build_system_prompt_v2(deviation, current_state, context_length)
        else:
            return self.build_system_prompt(deviation, current_state, context_length)
    
    def get_user_message(self, context: str, memory_context: str, prompt: str,
                        anchor_info: Optional[Dict[str, Any]], current_state: Dict[str, Any],
                        target_counts: Dict[str, int], config: GenerationConfig,
                        session_id: str = None) -> str:
        """Get user message based on version routing."""
        # Check if this session should use V2
        if hasattr(self, 'version') and self.version == "v2.0":
            return self.build_user_message_v2(context, memory_context, prompt, anchor_info, 
                                             current_state, target_counts, config)
        else:
            return self.build_user_message(context, memory_context, prompt, anchor_info,
                                          current_state, target_counts, config)
    
    def _write_debug_log(self, prompt: str, context: str, memory_context: str, current_state: Dict[str, Any]):
        """Write debug information to log file for easier debugging."""
        try:
            # Create logs directory if it doesn't exist
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "player_choice": prompt,
                "anchor_text": context,
                "anchor_text_length": len(context),
                "memory_context_length": len(memory_context),
                "deviation": current_state.get('deviation', 0),
                "affinity": current_state.get('affinity', {}),
                "flags": current_state.get('flags', {}),
                "variables": current_state.get('variables', {}),
                "choice_relevance": "RELEVANT" if any(word in context.lower() for word in prompt.lower().split() if len(word) > 1) else "OFF-TOPIC"
            }
            
            # Write to debug log file
            debug_log_file = log_dir / "llm_debug.jsonl"
            with open(debug_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            print(f"📝 Debug info written to: {debug_log_file}")
            
        except Exception as e:
            print(f" Failed to write debug log: {e}")
    
    def log_generated_script(self, script_units: List[Any], session_id: str, player_choice: str):
        """Log the generated script for debugging purposes."""
        try:
            # Create logs directory if it doesn't exist
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Extract script content
            script_content = []
            for unit in script_units:
                unit_info = {
                    "type": getattr(unit, 'type', 'unknown'),
                    "content": getattr(unit, 'content', ''),
                    "speaker": getattr(unit, 'speaker', None),
                    "choice_id": getattr(unit, 'choice_id', None),
                    "default_reply": getattr(unit, 'default_reply', None)
                }
                script_content.append(unit_info)
            
            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "player_choice": player_choice,
                "generated_script": script_content,
                "script_units_count": len(script_units)
            }
            
            # Write to script log file
            script_log_file = log_dir / "generated_scripts.jsonl"
            with open(script_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            print(f"📜 Generated script logged to: {script_log_file}")
            
        except Exception as e:
            print(f" Failed to log generated script: {e}")


# Global settings instance with version management (V2 default)
llm_settings_manager = LLMSettingsManager()
llm_settings = llm_settings_manager.get_settings()

# Print initialization status
print(f"LLM Settings Initialized: Version {llm_settings.version}")
print(f" V2 Prompts Enabled: {llm_settings_manager.use_v2}")
print(f"Assignment Ratio: {llm_settings_manager.assignment_ratio * 100:.0f}%")

# Helper function for easy access
def get_llm_settings(session_id: str = None) -> LLMSettings:
    """Get appropriate LLM settings based on session and feature flags."""
    return llm_settings_manager.get_settings()


# === Emergency Controls and Circuit Breaker ===

class CircuitBreaker:
    """Circuit breaker for V2 prompt system."""
    
    def __init__(self, threshold: float = 0.1, window_size: int = 100):
        self.error_threshold = threshold
        self.window_size = window_size
        self.error_count = 0
        self.request_count = 0
        self.is_open = False
        self.reset_time = None
        
    def call(self, func, *args, kwargs):
        """Execute function with circuit breaker protection."""
        if self.is_open:
            # Circuit is open, use fallback (V1)
            return self.fallback_call(*args, kwargs)
        
        try:
            result = func(*args, kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        """Record successful operation."""
        self.request_count += 1
        if self.request_count >= self.window_size:
            self._reset_window()
    
    def on_failure(self):
        """Record failed operation."""
        self.error_count += 1
        self.request_count += 1
        
        if self.request_count >= self.window_size:
            error_rate = self.error_count / self.request_count
            if error_rate > self.error_threshold:
                self.is_open = True
                print(f" CIRCUIT BREAKER OPENED! Error rate: {error_rate:.2%}")
                # Trigger emergency rollback
                llm_settings_manager.emergency_rollback_to_v1()
            self._reset_window()
    
    def _reset_window(self):
        """Reset the measurement window."""
        self.error_count = 0
        self.request_count = 0
    
    def fallback_call(self, *args, kwargs):
        """Fallback to V1 system."""
        print(" Using V1 fallback due to circuit breaker")
        return llm_settings_manager.v1_settings


# Global circuit breaker instance
circuit_breaker = CircuitBreaker()


# === Emergency Command Functions ===
def emergency_rollback():
    """Emergency rollback function for immediate V1 switch."""
    global llm_settings_manager, llm_settings
    llm_settings_manager.emergency_rollback_to_v1()
    llm_settings = llm_settings_manager.get_settings()
    print(" EMERGENCY ROLLBACK EXECUTED: All traffic switched to V1")


def enable_v2_prompts():
    """Enable V2 prompts for all traffic."""
    global llm_settings_manager, llm_settings
    llm_settings_manager.enable_v2()
    llm_settings = llm_settings_manager.get_settings()
    print(" V2 PROMPTS ENABLED: All traffic switched to V2")


def get_version_status():
    """Get current version status and metrics."""
    return {
        "current_version": llm_settings.version if hasattr(llm_settings, 'version') else 'v1.0',
        "use_v2": llm_settings_manager.use_v2,
        "emergency_rollback": llm_settings_manager.emergency_rollback,
        "assignment_ratio": llm_settings_manager.assignment_ratio,
        "circuit_breaker_open": circuit_breaker.is_open,
        "circuit_breaker_errors": circuit_breaker.error_count,
        "circuit_breaker_requests": circuit_breaker.request_count
    }