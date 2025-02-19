# models/relationship.py
from pydantic import BaseModel, Field
from typing import List

class RelationshipSchema(BaseModel):
    subject: str = Field(..., description="The subject entity in the relationship.")
    predicate: str = Field(..., description="The predicate describing the type of relationship.")
    object: str = Field(..., description="The object entity in the relationship.")
    confidence: float = Field(..., description="Confidence score for the relationship extraction (0.0 to 1.0).")

class Relationships(BaseModel):
    relationships: List[RelationshipSchema] = Field(..., description="List of relationships extracted.") 