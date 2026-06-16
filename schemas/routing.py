from pydantic import BaseModel, Field
from typing import Literal


class OrchestratorRoutingContract(BaseModel):
    action: Literal["ingest", "categorize", "analyze", "anomaly", "budget", "forecast", "advise", "notify", "clarify"] = Field(
        ..., description="The specific sub-agent to execute the request next"
    )
    reasoning: str = Field(..., description="Contextual deduction for why this path was selected")
    agent_payload: dict = Field(default_factory=dict, description="Normalized structural arguments")
