from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The operational chat context stream"]
    user_id: str
    active_route: str
    extracted_payload: dict
