# models/entities.py
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EntitySchema(BaseModel):
    name: str
    entity_type: str


class ExtractedEntities(BaseModel):
    entities: list[EntitySchema] 