import logging
from db.db_manager import Neo4jManager
from typing import List, Optional
from models.relationship import RelationshipSchema
from db.vector_utils import get_embedding
from db.memories import cosine_similarity

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
MATCH (s:Entity) WHERE toLower(s.name) = toLower($subject)
MATCH (o:Entity) WHERE toLower(o.name) = toLower($object)
MERGE (s)-[r:RELATED {predicate: $predicate}]->(o)
ON CREATE SET 
    r.confidence = $confidence,
    r.created_at = timestamp()
ON MATCH SET 
    r.last_seen_at = timestamp(),
    r.confidence = $confidence
RETURN r
"""

def setup_entity_infrastructure(session):
    """Creates necessary indexes and verifies APOC installation."""
    try:
        # Attempt to create vector index for entity embeddings.
        try:
            session.run("""
            CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
            FOR (e:Entity)
            ON (e.embedding)
            OPTIONS {
                indexConfig: {
                    `vector.dimensions`: 3072,
                    `vector.similarity_function`: 'cosine'
                }
            }
            """)
            logger.info("Entity embedding vector index created or already exists")
        except Exception as vec_err:
            logger.warning("Vector index creation not supported: %s", str(vec_err))
        
        # Test if APOC is available
        result = session.run("CALL apoc.help('coll')")
        if list(result):
            logger.info("APOC functions are available")
            return True
        else:
            logger.warning("APOC functions are not available")
            return False
    except Exception as e:
        logger.warning("Could not setup entity infrastructure: %s", str(e))
        return False

def update_entity(manager: Neo4jManager, name: str, aliases: List[str], entity_type: str):
    """
    Update or create an Entity node in the database.
    Uses a case-insensitive match on the entity name (stored in lowercase) and sets the embedding
    based on the normalized (lowercase) name.
    """
    normalized_name = name.lower()
    embedding = get_embedding(normalized_name)
    
    # First try to setup infrastructure
    with manager.get_session() as session:
        has_apoc = setup_entity_infrastructure(session)
    
    # Use appropriate query based on APOC availability
    if has_apoc:
        query = """
        MERGE (e:Entity {name: $normalized_name})
        ON CREATE SET 
            e.aliases = $aliases, 
            e.entity_type = $entity_type, 
            e.embedding = $embedding,
            e.created_at = timestamp()
        ON MATCH SET 
            e.entity_type = $entity_type, 
            e.embedding = $embedding,
            e.last_seen_at = timestamp(),
            e.aliases = apoc.coll.union(e.aliases, $aliases)
        RETURN e
        """
    else:
        query = """
        MERGE (e:Entity {name: $normalized_name})
        ON CREATE SET 
            e.aliases = $aliases, 
            e.entity_type = $entity_type, 
            e.embedding = $embedding,
            e.created_at = timestamp()
        ON MATCH SET 
            e.entity_type = $entity_type, 
            e.embedding = $embedding,
            e.last_seen_at = timestamp(),
            e.aliases = CASE 
                WHEN e.aliases IS NULL THEN $aliases 
                ELSE [x IN e.aliases + $aliases WHERE x IS NOT NULL] 
            END
        RETURN e
        """
    
    with manager.get_session() as session:
        session.run(query, 
                   normalized_name=normalized_name, 
                   aliases=aliases, 
                   entity_type=entity_type, 
                   embedding=embedding)

def search_similar_entities(manager: Neo4jManager, entity_name: str, threshold: float = 0.95, k: int = 5):
    """
    Search for similar entities using embedding similarity based on the entity name.
    Retrieves all Entity nodes that have an embedding and returns those with cosine similarity
    above the threshold.
    """
    query_embedding = get_embedding(entity_name.lower())
    query = "MATCH (e:Entity) WHERE e.embedding IS NOT NULL RETURN e"
    with manager.get_session() as session:
        result = session.run(query)
        nodes = [record["e"] for record in result]

    similar_entities = []
    for node in nodes:
        # Convert node to dictionary for mutation
        ent = dict(node)
        emb = ent.get("embedding")
        if emb:
            sim = cosine_similarity(query_embedding, emb)
            if sim >= threshold:
                ent["similarity"] = sim
                similar_entities.append(ent)

    similar_entities.sort(key=lambda x: x["similarity"], reverse=True)
    return similar_entities[:k]

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