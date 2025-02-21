# models/entities.py
import logging
from typing import Optional
from pydantic import BaseModel, Field
from models.topic import TopicSchema
from models.memory import LLMMemorySchema
logger = logging.getLogger(__name__)


class EntitySchema(BaseModel):
    name: str = Field(..., description="Name of the entity.")
    entity_type: str = Field(..., description="Category or type of the entity.")
    aliases: list[str]= Field(default_factory=list, description="Aliases for the entity.")
    notes: list[str] = Field(default_factory=list, description="Notes about the entity.")

class ExtractedEntities(BaseModel):
    entities: list[EntitySchema] = Field(..., description="List of extracted entity objects.")
    topics: list[TopicSchema] = Field(default_factory=list, description="List of extracted topics.")
    memories: list[LLMMemorySchema] = Field(default_factory=list, description="List of extracted memories.")
   