# models/relationship.py
from pydantic import BaseModel
from typing import List

class RelationshipSchema(BaseModel):
    subject: str
    predicate: str
    object: str
    confidence: float

class Relationships(BaseModel):
    relationships: List[RelationshipSchema] 