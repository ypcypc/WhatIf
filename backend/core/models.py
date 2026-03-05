from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class EventImportance(str, Enum):
    KEY = "key"
    NORMAL = "normal"
    OPTIONAL = "optional"


class PhaseType(str, Enum):
    SETUP = "setup"
    CONFRONTATION = "confrontation"
    RESOLUTION = "resolution"


class CharacterImportance(str, Enum):
    PROTAGONIST = "protagonist"
    KEY = "key"
    SUPPORTING = "supporting"
    MINOR = "minor"


class LocationImportance(str, Enum):
    KEY = "key"
    NORMAL = "normal"
    BACKGROUND = "background"


class ItemImportance(str, Enum):
    KEY = "key"
    NORMAL = "normal"
    BACKGROUND = "background"


class LocationType(str, Enum):
    REGION = "region"
    SETTLEMENT = "settlement"
    BUILDING = "building"
    ROOM = "room"
    WILDERNESS = "wilderness"
    PATH = "path"


class ItemCategory(str, Enum):
    WEAPON = "weapon"
    TOOL = "tool"
    CONTAINER = "container"
    DOCUMENT = "document"
    KEY_ITEM = "key_item"
    CONSUMABLE = "consumable"
    OTHER = "other"


class RelationType(str, Enum):
    MASTER = "master"
    DISCIPLE = "disciple"
    ALLY = "ally"
    ENEMY = "enemy"
    RIVAL = "rival"
    FRIEND = "friend"
    FAMILY = "family"
    ACQUAINTANCE = "acquaintance"
    SUBORDINATE = "subordinate"
    SUPERIOR = "superior"


class Sentence(BaseModel):
    index: int = Field(description="句子编号，从 1 开始")
    text: str = Field(description="句子内容")
    start: int = Field(description="在原文中的起始字符位置")
    end: int = Field(description="在原文中的结束字符位置")


class SentenceData(BaseModel):
    total_sentences: int
    total_characters: int
    sentences: list[Sentence]


class EventPhaseDetail(BaseModel):
    sentence_range: Optional[list[int]] = Field(
        default=None,
        description="该阶段对应的句子范围 [start, end]，可为空",
    )
    description: str = Field(default="", description="阶段内容描述")
    decision_text: str = Field(default="", description="决策摘要（由 DecisionTextExtractor 后填）")


class Event(BaseModel):
    id: str = Field(description="唯一标识符，使用 snake_case")
    type: Literal["interactive", "narrative"] = Field(description="事件类型")
    goal: str = Field(description="这个事件要达成什么（对叙事推进的意义）")
    sentence_range: list[int] = Field(description="句子编号范围 [start, end]，闭区间")
    importance: EventImportance
    soft_guide_hints: list[str] = Field(
        default_factory=list,
        description="给 Writer 的软引导提示，用于玩家卡住/偏离时",
    )
                      
    phases: Optional[dict[str, EventPhaseDetail]] = Field(
        default=None,
        description='三幕结构 {"setup": ..., "confrontation": ..., "resolution": ...}',
    )
                    
    narrative: Optional[str] = Field(
        default=None,
        description="叙事型事件的内容概括",
    )
    decision_text: str = Field(default="", description="事件级决策摘要")


class EventData(BaseModel):
    events: list[Event]


class CharacterIdentity(BaseModel):
    role: str = Field(description="身份/职位")
    affiliation: Optional[str] = Field(default=None, description="所属势力/门派")


class CharacterPersonality(BaseModel):
    traits: list[str] = Field(description="性格特征列表")
    speaking_style: Optional[str] = Field(default=None, description="说话风格描述")
    motivations: Optional[list[str]] = Field(default=None, description="主要动机/目标")
    fears: Optional[list[str]] = Field(default=None, description="恐惧/弱点")


class CharacterAppearance(BaseModel):
    physical: Optional[str] = Field(default=None, description="外貌描述")
    distinctive_features: Optional[list[str]] = Field(default=None, description="标志性特征")
    typical_attire: Optional[str] = Field(default=None, description="典型穿着")


class CharacterRelationship(BaseModel):
    target_id: str = Field(description="另一角色ID")
    type: RelationType = Field(description="关系类型")
    description: str = Field(description="关系描述")
    initial_attitude: int = Field(description="初始态度值，-100到100")


class Character(BaseModel):
    id: str = Field(description="唯一标识符")
    name: str = Field(description="角色名字")
    aliases: list[str] = Field(default_factory=list, description="其他称呼/别名")
    importance: CharacterImportance
    identity: CharacterIdentity
    personality: Optional[CharacterPersonality] = Field(default=None)
    appearance: Optional[CharacterAppearance] = Field(default=None)
    relationships: list[CharacterRelationship] = Field(default_factory=list)
    dialogue_examples: list[str] = Field(default_factory=list, description="典型台词")


class CharacterData(BaseModel):
    characters: list[Character]


class LocationDescription(BaseModel):
    overview: str = Field(description="地点概述")
    atmosphere: Optional[str] = Field(default=None, description="氛围描述")
    visual_details: Optional[list[str]] = Field(default=None, description="视觉细节")
    sounds: Optional[list[str]] = Field(default=None, description="声音描述")
    smells: Optional[list[str]] = Field(default=None, description="气味描述")
    notable_features: Optional[list[str]] = Field(default=None, description="标志性特征")


class LocationConnection(BaseModel):
    location_id: str = Field(description="相连地点ID")
    direction: str = Field(description="方向")
    travel_description: Optional[str] = Field(default=None, description="移动描述")
    accessibility: Optional[str] = Field(default=None, description="通行条件")


class Location(BaseModel):
    id: str = Field(description="唯一标识符")
    name: str = Field(description="地点名称")
    aliases: list[str] = Field(default_factory=list, description="别名")
    importance: LocationImportance
    type: LocationType
    parent_location: Optional[str] = Field(default=None, description="父级地点ID")
    description: LocationDescription
    connected_to: list[LocationConnection] = Field(default_factory=list)


class LocationData(BaseModel):
    locations: list[Location]


class ItemDescription(BaseModel):
    appearance: str = Field(description="外观描述")
    material: Optional[str] = Field(default=None, description="材质")
    size: Optional[str] = Field(default=None, description="大小描述")


class ItemFunction(BaseModel):
    primary_use: str = Field(description="主要用途")
    special_abilities: Optional[list[str]] = Field(default=None, description="特殊能力")
    limitations: Optional[list[str]] = Field(default=None, description="使用限制")


class ItemSignificance(BaseModel):
    narrative_role: Optional[str] = Field(default=None, description="在故事中的作用")
    symbolic_meaning: Optional[str] = Field(default=None, description="象征意义")


class Item(BaseModel):
    id: str = Field(description="唯一标识符")
    name: str = Field(description="物品名称")
    aliases: list[str] = Field(default_factory=list, description="别名")
    importance: ItemImportance
    category: ItemCategory
    description: ItemDescription
    function: Optional[ItemFunction] = Field(default=None)
    significance: Optional[ItemSignificance] = Field(default=None)


class ItemData(BaseModel):
    items: list[Item]


class Knowledge(BaseModel):
    id: str = Field(description="唯一标识符")
    name: str = Field(description="信息简述")
    initial_holders: list[str] = Field(description="最初知晓此信息的角色 ID 列表")
    description: str = Field(description="信息的具体内容")


class KnowledgeData(BaseModel):
    knowledge: list[Knowledge]


class LorebookData(BaseModel):
    characters: list[Character]
    locations: list[Location]
    items: list[Item]
    knowledge: list[Knowledge]


class Precondition(BaseModel):
    name: str = Field(description="实体名")
    type: Literal["character", "item", "information", "location"]
    attribute: Literal["地点", "持有者", "知晓者"]
    from_value: Optional[str] = Field(default=None, description="事件开始前的归属（unnecessary 实体置 null）", alias="from")
    granularity: Literal["named", "functional"]

    model_config = {"populate_by_name": True}


class Effect(BaseModel):
    name: str = Field(description="实体名")
    type: Literal["character", "item", "information", "location"]
    attribute: Literal["地点", "持有者", "知晓者"]
    from_value: Optional[str] = Field(default=None, description="变化前的归属（unnecessary 实体置 null）", alias="from")
    to: Optional[str] = Field(default=None, description="变化后的归属（unnecessary 实体置 null）")
    granularity: Literal["named", "functional"]

    model_config = {"populate_by_name": True}


class EventTransition(BaseModel):
    event_id: str
    preconditions: list[Precondition] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)


class TransitionData(BaseModel):
    transitions: list[EventTransition]


class NecessityReasoning(BaseModel):
    entity: str
    type: Literal["character", "item", "information", "location"]
    step_a_counterfactual: str = Field(description="反事实推理")
    necessary: bool
    step_b_substitution: Optional[str] = Field(default=None, description="替代性推理")
    granularity: Optional[Literal["named", "functional"]] = None
    forward_references: list[str] = Field(default_factory=list)


class NecessaryEntity(BaseModel):
    name: str
    granularity: Literal["named", "functional"]


class NecessaryEntities(BaseModel):
    characters: list[NecessaryEntity] = Field(default_factory=list)
    items: list[NecessaryEntity] = Field(default_factory=list)
    information: list[NecessaryEntity] = Field(default_factory=list)
    locations: list[NecessaryEntity] = Field(default_factory=list)


class EventNecessity(BaseModel):
    event_id: str
    reasoning: list[NecessityReasoning]
    necessary_entities: NecessaryEntities


class NecessityData(BaseModel):
    events: list[EventNecessity]


class TransitionError(BaseModel):
    type: Literal[
        "ability_leak", "continuity_break", "precondition_missing",
        "precondition_redundant", "annotation_inconsistent",
        "granularity_misjudge", "unnecessary_entity_reference",
    ]
    entity: str
    current_granularity: Optional[str] = None
    suggested_granularity: Optional[str] = None
    evidence: str
    description: str
    suggestion: str


class EventValidationReport(BaseModel):
    event_id: str
    errors: list[TransitionError]


class ValidationReport(BaseModel):
    reports: list[EventValidationReport]


class Metadata(BaseModel):
    title: str = Field(description="作品标题")
    source_file: str = Field(description="源文件路径")
    total_characters: int = Field(description="总字符数")
    total_sentences: int = Field(description="总句子数")
    event_count: int = Field(description="事件数量")
    character_count: int = Field(description="角色数量")
    location_count: int = Field(description="地点数量")
    item_count: int = Field(description="物品数量")
    knowledge_count: int = Field(default=0, description="知识/信息数量")
    transition_count: int = Field(default=0, description="实体转移数量")
    created_at: str = Field(description="创建时间 ISO 格式")
