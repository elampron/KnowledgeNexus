import logging
from typing import List, Dict
from db.db_manager import Neo4jManager
from models.topic import TopicSchema

logger = logging.getLogger(__name__)

def search_similar_topics(db_manager: Neo4jManager, topic_name: str) -> List[Dict]:
    """Search for topics similar to the given topic_name using a simple case-insensitive match."""
    query = "MATCH (t:Topic) WHERE toLower(t.name) CONTAINS toLower($topic_name) RETURN t.name as name, t.aliases as aliases, t.notes as notes"
    with db_manager.get_session() as session:
        result = session.run(query, topic_name=topic_name)
        return [dict(record) for record in result]


def update_topic(db_manager: Neo4jManager, name: str, aliases: List[str]) -> None:
    """Update or create a Topic node with the provided name, aliases, and notes."""
    query = "MERGE (t:Topic {name: $name}) SET t.aliases = $aliases"
    with db_manager.get_session() as session:
        session.run(query, name=name, aliases=aliases)
        logger.info("Updated topic: %s", name)


def create_document_topic_relationship(db_manager: Neo4jManager, document_id: str, topic_name: str) -> None:
    """Create a relationship between a Document node and a Topic node."""
    query = "MATCH (d:Document {id: $document_id}) MERGE (t:Topic {name: $topic_name}) MERGE (d)-[:HAS_TOPIC]->(t)"
    with db_manager.get_session() as session:
        session.run(query, document_id=document_id, topic_name=topic_name)
        logger.info("Created relationship between document %s and topic %s", document_id, topic_name) 