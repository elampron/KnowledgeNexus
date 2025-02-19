import logging
from db.db_manager import Neo4jManager
from typing import List, Optional
from models.relationship import RelationshipSchema

logger = logging.getLogger(__name__)

MERGE_ENTITY_QUERY = """
MERGE (e:Entity { name: $name })
ON CREATE SET 
    e.created_at = timestamp(),
    e.aliases = $aliases,
    e.entity_type = $entity_type
ON MATCH SET 
    e.last_seen_at = timestamp(),
    e.aliases = $aliases
RETURN e
"""

SEARCH_SIMILAR_ENTITIES_QUERY = """
MATCH (e:Entity)
WHERE e.name =~ $name_pattern
RETURN e.name as name, e.aliases as aliases
"""

MERGE_RELATIONSHIP_QUERY = """
MATCH (s:Entity {name: $subject})
MATCH (o:Entity {name: $object})
MERGE (s)-[r:RELATED {predicate: $predicate}]->(o)
ON CREATE SET 
    r.confidence = $confidence,
    r.created_at = timestamp()
ON MATCH SET 
    r.last_seen_at = timestamp(),
    r.confidence = $confidence
RETURN r
"""

def update_entity(manager: Neo4jManager, name: str, aliases: List[str], entity_type: str):
    """Creates or updates an entity in the database using a MERGE query."""
    session = manager.get_session()
    try:
        result = session.run(
            MERGE_ENTITY_QUERY,
            name=name,
            aliases=aliases,
            entity_type=entity_type
        )
        record = result.single()
        logger.info("Entity updated: %s", record)
        return record
    finally:
        session.close()

def search_similar_entities(manager: Neo4jManager, name: str) -> List[dict]:
    """Searches for entities with similar names using case-insensitive pattern matching."""
    session = manager.get_session()
    try:
        name_pattern = f"(?i).*{name}.*"  # Case-insensitive partial match
        result = session.run(SEARCH_SIMILAR_ENTITIES_QUERY, name_pattern=name_pattern)
        records = [
            {"name": record["name"], "aliases": record.get("aliases", [])}
            for record in result
        ]
        logger.info("Found %d similar entities for '%s'", len(records), name)
        return records
    finally:
        session.close()

def store_relationship(manager: Neo4jManager, relationship: RelationshipSchema) -> None:
    """Creates or updates a relationship between two entities in the database."""
    session = manager.get_session()
    try:
        result = session.run(
            MERGE_RELATIONSHIP_QUERY,
            subject=relationship.subject,
            object=relationship.object,
            predicate=relationship.predicate,
            confidence=relationship.confidence
        )
        record = result.single()
        logger.info("Relationship stored: %s -[%s]-> %s", 
                   relationship.subject, relationship.predicate, relationship.object)
        return record
    finally:
        session.close()

def store_relationships(manager: Neo4jManager, relationships: List[RelationshipSchema]) -> None:
    """Store inferred relationships between entities in the graph database.
    For each relationship, match the two entities by name and create a relationship edge with the given predicate and confidence.
    """
    query = (
        "UNWIND $relationships AS rel "
        "MATCH (a:Entity {name: rel.subject}), (b:Entity {name: rel.object}) "
        "MERGE (a)-[r:RELATIONSHIP {predicate: rel.predicate}]->(b) "
        "SET r.confidence = rel.confidence"
    )
    with manager.get_session() as session:
        session.run(query, relationships=[rel.dict() for rel in relationships])

def store_relationships(manager: Neo4jManager, relationships: List[RelationshipSchema]) -> None:
    """Stores multiple relationships in the database."""
    for relationship in relationships:
        store_relationship(manager, relationship) 