# models/entities.py
import logging
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EntitySchema(BaseModel):
    name: str = Field(..., description="Name of the entity.")
    entity_type: str = Field(..., description="Category or type of the entity.")
    aliases: Optional[list[str]] = Field(None, description="Aliases for the entity.")
    notes: Optional[str] = Field(None, description="Notes about the entity.")


class ExtractedEntities(BaseModel):
    entities: list[EntitySchema] = Field(..., description="List of extracted entity objects.")
   