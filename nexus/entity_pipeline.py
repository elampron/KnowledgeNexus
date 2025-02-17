import logging
from typing import List, Tuple
from db.db_manager import Neo4jManager
import cognitive.entity_extraction as ce
from nexus.entity_resolution import Entity, EntityResolutionPipeline
from nexus.pipeline import EntityProcessingPipeline
from models.relationship import Relationships, RelationshipSchema
from db import entities as db_entities
from openai import OpenAI
import json

logger = logging.getLogger(__name__)
client = OpenAI()

class EntityPipeline:
    def __init__(self, db_manager: Neo4jManager, resolution_pipeline: EntityResolutionPipeline):
        self.db_manager = db_manager
        self.resolution_pipeline = resolution_pipeline
        # Reuse our existing pipeline for processing entities
        self.entity_processing_pipeline = EntityProcessingPipeline(db_manager, resolution_pipeline)
    
    def process_input(self, text: str, instructions: str = "") -> Tuple[List[Entity], List[RelationshipSchema]]:
        """
        Process the full input text:
         1. Extract entities from text.
         2. Run resolution (deduplication/merging) and update the database.
         3. Infer relationships between the resolved entities using the full text as context.
        Returns a tuple (final entities, extracted relationships).
        """
        logger.info("Starting full entity pipeline processing.")
        
        # Step 1: Extract entities
        extracted_entities = ce.extract_entities_from_text(text, instructions)
        logger.info("Extracted %d entities.", len(extracted_entities.entities))
        
        # Step 2: Process and resolve entities, updating the database
        final_entities = self.entity_processing_pipeline.process_extracted_entities(extracted_entities)
        logger.info("After resolution, %d final entities.", len(final_entities))
        
        # Step 3: Infer relationships using the full input and the final entities
        relationships = self.infer_relationships(text, final_entities)
        logger.info("Inferred %d relationships.", len(relationships))
        
        # Step 4: Store relationships in the database
        db_entities.store_relationships(self.db_manager, relationships)
        
        return final_entities, relationships

    def infer_relationships(self, text: str, entities: List[Entity]) -> List[RelationshipSchema]:
        """
        Infer relationships between entities using the full text as context.
        Uses logical reasoning through LLM to identify meaningful relationships between entities,
        such as family relationships, professional relationships, ownership, etc.
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
            "Consider relationships such as:\n"
            "- Family relationships (parent of, sibling of, spouse of)\n"
            "- Professional relationships (works with, reports to, manages)\n"
            "- Personal relationships (friend of, partner of)\n"
            "- Organizational relationships (member of, owner of, employed by)\n"
            "- Temporal relationships (preceded by, succeeded by)\n"
            "- Spatial relationships (located in, part of)\n\n"
            "For each relationship found:\n"
            "1. Use the exact entity names as subject and object\n"
            "2. Choose a clear, specific predicate that best describes the relationship\n"
            "3. Assign a confidence score (0-1) based on how explicitly the relationship is stated in the text\n"
            "Return your findings as a JSON object."
        )
        
        # The user prompt includes the full text context and the list of entities
        user_prompt = (
            f"Text:\n{text}\n\n"
            f"Available Entities: {entities_str}\n\n"
            "Analyze the text and identify logical relationships between these entities. "
            "Only include relationships that are supported by the text content."
        )
        
        try:
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "relationships",
                        "description": "A list of relationships between entities",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "relationships": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "subject": {"type": "string"},
                                            "predicate": {"type": "string"},
                                            "object": {"type": "string"},
                                            "confidence": {"type": "number"}
                                        },
                                        "required": ["subject", "predicate", "object", "confidence"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["relationships"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                temperature=0.0
            )
            
            # Get the content from the response
            content = completion.choices[0].message.content
            
            # Parse the JSON response
            parsed_data = json.loads(content)
            
            # Convert to RelationshipSchema objects
            relationships = [
                RelationshipSchema(
                    subject=rel["subject"],
                    predicate=rel["predicate"],
                    object=rel["object"],
                    confidence=rel["confidence"]
                )
                for rel in parsed_data.get("relationships", [])
            ]
            
            # Log the inferred relationships for debugging
            for rel in relationships:
                logger.debug("Inferred relationship: %s -[%s]-> %s (confidence: %.2f)",
                           rel.subject, rel.predicate, rel.object, rel.confidence)
            
            return relationships
        
        except Exception as e:
            logger.error("Error extracting relationships: %s", str(e))
            return [] 