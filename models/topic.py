from pydantic import BaseModel, Field
from typing import List, Optional


class TopicSchema(BaseModel):
    name: str = Field(..., description="Name of the topic.")
    aliases: List[str] = Field(default_factory=list, description="Aliases for the topic.")