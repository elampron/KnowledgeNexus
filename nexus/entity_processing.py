"""
Entity processing pipeline for KnowledgeNexus.
"""
import logging
from typing import List
from db.db_manager import Neo4jManager
from models.entities import ExtractedEntities, EntitySchema
from nexus.entity_resolution import Entity, EntityResolutionPipeline
from db import entities as db_entities

logger = logging.getLogger(__name__)

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

    def infer_and_store_relationships(self, text: str, entities: List[Entity]):
        """
        Infer relationships between entities from the text and store them in the database.
        This is a placeholder for future relationship inference implementation.
        """
        # TODO: Implement relationship inference using the resolution pipeline's
        # infer_relationships method and store the relationships in Neo4j
        pass 