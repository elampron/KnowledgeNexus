"""
Entity processing pipeline for KnowledgeNexus.
"""
import logging
from typing import List
from openai import OpenAI
from db.db_manager import Neo4jManager
from models.entities import ExtractedEntities, EntitySchema
from models.relationship import Relationships, RelationshipSchema
from nexus.entity_resolution import Entity, EntityResolutionPipeline
from db import entities as db_entities

logger = logging.getLogger(__name__)
client = OpenAI()

class EntityProcessingPipeline:
    def __init__(self, db_manager: Neo4jManager, resolution_pipeline: EntityResolutionPipeline):
        self.db_manager = db_manager
        self.resolution_pipeline = resolution_pipeline

    def extract_entities_from_text(self,text: str, instructions: str = "") -> ExtractedEntities:
        """Extract entities, topics, and memories from the provided text using an LLM call.
        The LLM should return JSON with keys: 'entities', 'topics', and optionally 'memories'.
        Each entity should have at least 'name' and 'entity_type', and optionally 'aliases'.
        Each topic should have at least 'name', and optionally 'aliases' and 'notes'.
        """
        system_prompt = (
            "You are an expert text analysis assistant. Extract all relevant entities, topics, and memories from the text. "
            "For entities, identify their 'name', 'entity_type', and optionally 'aliases'. "
            "For topics, identify the main subjects discussed, and provide a 'name', and optionally 'aliases' and 'notes'. "
            "For memories, extract key snippets of knowledge as 'content' with a 'confidence' score. "
            
        )
        user_prompt = f"Text: {text}\nInstructions: {instructions}"
        try:
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format=ExtractedEntities,
            )
            data = response.choices[0].message.parsed
            
            return data
        except Exception as e:
            logger.error("Failed to extract entities, topics, and memories: %s", e)
            return ExtractedEntities(entities=[], topics=[], memories=[]) 

    def process_extracted_entities(self, extracted_entities: ExtractedEntities) -> List[Entity]:
        """
        Process extracted entities through resolution pipeline and update the database.
        Returns the list of final entities (either new or merged).
        """
        logger.info("Processing %d extracted entities", len(extracted_entities.entities))
        final_entities = []
        
        for entity_schema in extracted_entities.entities:
            # Convert EntitySchema to Entity
            new_entity = Entity(
                name=entity_schema.name,
                aliases=[]  # Start with empty aliases, could be enhanced later
            )
            
            # Search for existing entities with similar names
            existing_entities_data = db_entities.search_similar_entities(self.db_manager, new_entity.name)
            existing_entities = [
                Entity(name=data["name"], aliases=data.get("aliases", []))
                for data in existing_entities_data
            ]
            
            # Run through resolution pipeline
            resolved_entity = self.resolution_pipeline.resolve_entities(new_entity, existing_entities)
            
            # Update or create in database
            db_entities.update_entity(
                self.db_manager,
                name=resolved_entity.name,
                aliases=resolved_entity.aliases,
                entity_type=entity_schema.entity_type
            )
            
            final_entities.append(resolved_entity)
            logger.info("Processed entity: %s", resolved_entity.name)
        
        return final_entities

    # Removed duplicate relationship inference methods (infer_relationships and infer_and_store_relationships) to consolidate relationship inference in DocumentConverter 