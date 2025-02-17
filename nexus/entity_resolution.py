import logging
import difflib
from openai import OpenAI
from typing import List, Optional
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)

client = OpenAI()


class Entity(BaseModel):
    id: Optional[int] = None
    name: str
    aliases: List[str] = []


class AIResolutionResult(BaseModel):
    match: str  # Expected values: "yes" or "no"
    confidence: float
    reason: str


class EntityResolutionPipeline:
    def __init__(self, lower_threshold: float = 0.5, upper_threshold: float = 0.9):
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold

    def compute_similarity(self, entity_a: Entity, entity_b: Entity) -> float:
        """
        Compute overall similarity between two entities based on name and aliases.
        Weighted sum: 70% for name similarity, 30% for alias similarity.
        """
        name_similarity = difflib.SequenceMatcher(
            None,
            entity_a.name.lower(),
            entity_b.name.lower()
        ).ratio()

        alias_similarity = 0.0
        for alias_a in entity_a.aliases:
            for alias_b in entity_b.aliases:
                sim = difflib.SequenceMatcher(
                    None,
                    alias_a.lower(),
                    alias_b.lower()
                ).ratio()
                alias_similarity = max(alias_similarity, sim)

        overall_similarity = 0.7 * name_similarity + 0.3 * alias_similarity
        logger.debug("Computed similarity between '%s' and '%s': %.2f",
                     entity_a.name, entity_b.name, overall_similarity)
        return overall_similarity

    def ai_assisted_resolution(self, entity_a: Entity, entity_b: Entity) -> AIResolutionResult:
        """
        Use GPT to determine if two entities refer to the same real-world object.
        Returns a structured result with match decision, confidence, and reasoning.
        """
        system_prompt = """
        You are an entity resolution assistant. Determine if two entities refer to the same real-world object.
        You must provide:
        - match: "yes" or "no" indicating if they are the same entity
        - confidence: a float between 0 and 1 indicating your confidence
        - reason: a string explaining your decision
        """
        
        user_prompt = f"""
        Entity A:
        - Name: {entity_a.name}
        - Aliases: {', '.join(entity_a.aliases) if entity_a.aliases else 'None'}

        Entity B:
        - Name: {entity_b.name}
        - Aliases: {', '.join(entity_b.aliases) if entity_b.aliases else 'None'}

        Are these the same entity?
        """

        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=AIResolutionResult,
                temperature=0.0
            )
            
            # The response is already parsed into our Pydantic model
            result = completion.choices[0].message.parsed
            
            logger.info("AI resolution result for '%s' and '%s': %s",
                        entity_a.name, entity_b.name, result.dict())
            return result
            
        except Exception as e:
            logger.error("OpenAI API error: %s", str(e))
            # Fallback to similarity-based resolution
            sim = self.compute_similarity(entity_a, entity_b)
            return AIResolutionResult(
                match="no",
                confidence=sim,
                reason="OpenAI API error, falling back to similarity"
            )

    def merge_entities(self, entity_a: Entity, entity_b: Entity) -> Entity:
        """
        Merge two entities by choosing the longer name and uniting aliases.
        """
        name = entity_a.name if len(entity_a.name) >= len(entity_b.name) else entity_b.name
        aliases = list(set(entity_a.aliases + entity_b.aliases))
        merged_entity = Entity(name=name, aliases=aliases)
        logger.info("Merged entity: %s", merged_entity.dict())
        return merged_entity

    def resolve_entities(self, new_entity: Entity, existing_entities: List[Entity]) -> Entity:
        """
        Compare a new entity with existing entities and resolve duplicates.
        If a match is found with similarity above thresholds, perform merge.
        """
        best_similarity = 0.0
        best_match = None

        for existing in existing_entities:
            sim = self.compute_similarity(new_entity, existing)
            logger.info("Similarity between '%s' and '%s': %.2f",
                        new_entity.name, existing.name, sim)
            if sim > best_similarity:
                best_similarity = sim
                best_match = existing

        if best_similarity < self.lower_threshold:
            logger.info("No sufficient match found for '%s'. Adding as new entity.",
                        new_entity.name)
            existing_entities.append(new_entity)
            return new_entity
        elif best_similarity >= self.upper_threshold:
            logger.info("High similarity (%.2f) found. Auto-merging '%s' with '%s'.",
                        best_similarity, new_entity.name, best_match.name)
            merged = self.merge_entities(new_entity, best_match)
            existing_entities.remove(best_match)
            existing_entities.append(merged)
            return merged
        else:
            logger.info("Ambiguous similarity (%.2f) for '%s'. Invoking AI-assisted resolution.",
                        best_similarity, new_entity.name)
            ai_result = self.ai_assisted_resolution(new_entity, best_match)
            if ai_result.match.lower() == "yes" and ai_result.confidence >= self.upper_threshold:
                merged = self.merge_entities(new_entity, best_match)
                existing_entities.remove(best_match)
                existing_entities.append(merged)
                return merged
            else:
                logger.info("AI resolution did not approve merge for '%s'. Adding as separate entity.",
                            new_entity.name)
                existing_entities.append(new_entity)
                return new_entity

    def infer_relationships(self, text: str):
        """
        Placeholder for relationship inference from text.
        This simulates extraction of relationships.
        """
        # In a real implementation, NLP methods would be used here.
        relationship = {
            "subject": "Entity A",
            "predicate": "related_to",
            "object": "Entity B",
            "confidence": 0.8
        }
        logger.info("Inferred relationship: %s", relationship)
        return relationship 