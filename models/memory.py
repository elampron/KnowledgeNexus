from pydantic import BaseModel, Field
from typing import Optional


class MemorySchema(BaseModel):
    content: str = Field(..., description="Excerpt or snippet of key knowledge extracted from text.")
    confidence: float = Field(..., description="Confidence level for this memory.")
    timestamp: Optional[str] = None
    tags: list[str] = []
    source: Optional[str] = None 
    sentiment: Optional[str] = None

class LLMMemorySchema(BaseModel):
    content: str = Field(..., description="Excerpt or snippet of key knowledge extracted from text.")
    confidence: float = Field(..., description="Confidence level for this memory.")
    tags: list[str] = Field(...,description="Tags for the memory.")
    sentiment: Optional[str] = Field(..., description="Sentiment of the memory.")
