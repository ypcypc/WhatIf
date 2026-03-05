from typing import Literal

from pydantic import BaseModel, Field


class AgentResult(BaseModel):

    success: bool = True
    error: str | None = None


class L0Response(BaseModel):
    summary: str
    tags: list[str]


class L0Summary(BaseModel):
    event_id: str
    summary: str
    tags: list[str]
    char_count: int


class L1Response(BaseModel):
    summary: str
    tags: list[str]


class L1Summary(BaseModel):
    id: str
    covers: str
    summary: str
    tags: list[str]
    char_count: int
    l0_summaries: list[L0Summary]


class EntityRecognitionResult(BaseModel):
    entity_ids: list[str] = Field(default_factory=list)


class HistoryEntry(BaseModel):
    player_input: str | None = None
    response_summary: str | None = None


class DeviationControlOutput(BaseModel):
    scratch: str = Field(description="multi-step reasoning, max 120 chars")
    is_deviation: bool
    has_world_change: bool
    persistence_count: int = Field(ge=0, le=10)
    release: bool
    guidance_method: Literal[
        "none", "environmental_limit", "character_reaction",
        "ability_boundary", "timing_issue", "emotional_bond",
        "consequence_foreshadow", "positive_progression",
    ]
    guidance_tone: Literal[
        "warm", "urgent", "sorrowful", "fateful", "encouraging", "neutral",
    ]
    guidance_hint: str = Field(description="max 50 chars")
    delta_fact: str | None = None
    delta_intensity: int | None = Field(default=None, ge=1, le=5)


class L1SelectionOutput(BaseModel):
    selected_l1_ids: list[str] = Field(default_factory=list, description="max 5")
    selected_pending_ids: list[str] = Field(default_factory=list, description="max 5")


class L0SelectionOutput(BaseModel):
    selected_event_ids: list[str] = Field(
        default_factory=list,
        description="max 8, sorted by relevance",
    )


class RecallResult(BaseModel):
    restored_context: str = Field(default="")


class ToolCall(BaseModel):
    name: Literal[
        "recall_history", "query_entities", "check_deviation",
        "request_bridge", "request_adaptation",
    ]
    arguments: dict


class ToolCallsOutput(BaseModel):
    tool_calls: list[ToolCall] = Field(min_length=1)


class EventMeta(BaseModel):
    event_id: str
    importance: Literal["key", "normal", "optional"]
    goal: str | None = None
    event_type: Literal["interactive", "narrative"] = "interactive"
    soft_guide_hints: list[str] = Field(default_factory=list)
    preconditions: list[dict] = Field(default_factory=list)


class EventContext(BaseModel):
    setup_narrative: str | None = None
    confrontation_history: list[HistoryEntry] = Field(default_factory=list)
    deviation_history: list[HistoryEntry] = Field(default_factory=list)


class ToolResult(BaseModel):
    tool_name: str
    content: str


class DeviationAnalysis(BaseModel):
    scratch: str
    is_deviation: bool
    has_world_change: bool
    persistence_count: int
    release: bool
    guidance_method: str
    guidance_tone: str
    guidance_hint: str
    delta_fact: str | None = None
    delta_intensity: int | None = None


class DeltaEvolution(BaseModel):
    original_delta_id: str
    evolved_fact: str = Field(description="演化后的兼容型 Delta 事实")
    evolved_intensity: int
    evolution_rationale: str = Field(description="演化推理过程摘要")


class BridgeResult(AgentResult):
    delta_evolutions: list[DeltaEvolution] = Field(default_factory=list)
    bridge_narrative: str = ""


class AdaptationItem(BaseModel):
    strategies: list[Literal["addition", "rewrite"]] = Field(
        min_length=1,
        description="适配策略: addition（新增）和/或 rewrite（改写）",
    )
    target: str = Field(description="原文中的目标位置描述")
    delta_source: str = Field(default="", description="触发此适配的 Delta ID(s)")
    original: str | None = Field(
        default=None,
        description="需要改写的原文片段（纯 addition 时为 null）",
    )
    plan: str = Field(description="具体适配指令")
    nearest_state_reasoning: str = Field(
        description="为什么这是最近似原文的替代方案",
    )
    intensity_guidance: Literal["简要带过", "正常描写", "重点刻画"] = Field(
        description="Writer 着墨量指导",
    )


class AdaptationPlan(AgentResult):
    event_id: str
    delta_impact_summary: str = Field(
        description="Delta 对本事件的整体影响概述",
    )
    adaptations: list[AdaptationItem] = Field(default_factory=list)
