from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class EventInfo(CamelModel):

    id: str
    decision_text: str
    goal: str
    importance: str                                 
    type: str                               


class GameStateResponse(CamelModel):

    phase: str | None
    event: EventInfo | None
    turn: int
    player_name: str | None
    awaiting_next_event: bool
    game_ended: bool = False


class NarrativeResponse(CamelModel):

    text: str
    phase: str | None
    event_id: str | None
    turn: int


class SaveInfo(CamelModel):

    slot: int
    save_time: str
    player_name: str
    current_event_id: str | None
    current_phase: str | None
    total_turns: int
    description: str
    worldpkg_title: str


class SaveListResponse(CamelModel):

    saves: list[SaveInfo]


class MessageResponse(CamelModel):

    message: str
