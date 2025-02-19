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

    def infer_relationships(self, text: str, entities: List[Entity]) -> List[RelationshipSchema]:
        """
        Infer relationships between entities using the full text as context.
        Uses logical reasoning through LLM to identify meaningful relationships between entities,
        such as family relationships (e.g. 'son_of', 'is_father'), professional relationships, etc.
        Returns a list of RelationshipSchema objects.
        """
        # Get entity names and build a comma-separated list
        entity_names = [entity.name for entity in entities]
        entities_str = ", ".join(entity_names)
        
        # Define a system prompt that asks the LLM to use logical reasoning
        system_prompt = (
            "You are an expert relationship inference system. Your task is to analyze the following text along "
            "with a list of entities extracted from it. Based on logical and contextual clues in the text, "
            "determine if there are significant relationships between these entities.\n\n"
            "Consider relationships such as: family relationships (e.g., 'son_of', 'is_father'), "
            "professional relationships, personal relationships, and organizational relationships.\n\n"
            "For each relationship found, use the exact entity names as subject and object, choose a clear predicate, "
            "and assign a confidence score between 0 and 1. Return the result as JSON with a key 'relationships', which is a list of objects. "
            "Each object should have 'subject', 'predicate', 'object', and 'confidence'."
        )
        
        # The user prompt includes the full text context and the list of entities
        user_prompt = (
            f"Text:\n{text}\n\nAvailable Entities: {entities_str}\n\n"
            "Analyze the text and identify logical relationships between these entities. "
            "Only include relationships that are explicitly supported by the text."
        )
        
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=Relationships,
                temperature=0.0
            )
            # Add debug logging for the raw LLM output
            raw_output = completion.choices[0].message.content
            logger.debug("LLM relationship inference raw output: %s", raw_output)
            
            return completion.choices[0].message.parsed.relationships
        except Exception as e:
            logger.error("Error extracting relationships: %s", str(e))
            return []

    def infer_and_store_relationships(self, text: str, entities: List[Entity]):
        """
        Infer relationships between entities from the text and store them in the database.
        This is a placeholder for future relationship inference implementation.
        """
        # TODO: Implement relationship inference using the resolution pipeline's
        # infer_relationships method and store the relationships in Neo4j
        pass 