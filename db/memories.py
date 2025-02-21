import logging
from neo4j import Session
import numpy as np

logger = logging.getLogger(__name__)

CREATE_MEMORY_QUERY = """
CREATE (m:Memory {
  id: apoc.create.uuid(),
  content: $content,
  confidence: $confidence,
  created_at: timestamp(),
  sentiment: $sentiment,
  source: $source,
  tags: $tags
})
RETURN m
"""

def create_memory(session: Session, content: str, confidence: float):
    """Creates a new Memory node in the database."""
    result = session.run(
        CREATE_MEMORY_QUERY,
        content=content,
        confidence=confidence
    )
    record = result.single()
    if not record:
        return None
    return record["m"]

# Optional: Create a Memory node with vector embedding
from db.vector_utils import get_embedding

CREATE_MEMORY_EMBEDDING_QUERY = """
CREATE (m:Memory {
  id: apoc.create.uuid(),
  content: $content,
  confidence: $confidence,
  embedding: $embedding,
  created_at: timestamp()
})
RETURN m
"""

def create_memory_with_embedding(session: Session, content: str, confidence: float):
    """Creates a new Memory node with an embedding in the database."""
    embedding = get_embedding(content)
    result = session.run(
        CREATE_MEMORY_EMBEDDING_QUERY,
        content=content,
        confidence=confidence,
        embedding=embedding
    )
    record = result.single()
    if not record:
        return None
    return record["m"]

# Add vector similarity search for Memory nodes

def create_vector_index(session: Session):
    """Creates a vector index on Memory nodes' embedding property."""
    try:
        query = """
        CREATE VECTOR INDEX memoryIndex IF NOT EXISTS
        FOR (m:Memory)
        ON (m.embedding)
        OPTIONS {
            indexConfig: {
                `vector.dimensions`: 3072,
                `vector.similarity_function`: 'cosine'
            }
        }
        """
        session.run(query)
        logger.info("Vector index created or already exists")
    except Exception as e:
        logger.error(f"Failed to create vector index: {str(e)}")
        raise

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2) if norm1 and norm2 else 0

def search_memories(session: Session, query_embedding: list, k: int = 10, min_score: float = 0.5):
    """Search Memory nodes using vector similarity.
    Fetches all Memory nodes with embeddings and computes similarity scores in Python.
    """
    # First, fetch all Memory nodes with embeddings
    query = """
    MATCH (m:Memory)
    WHERE exists(m.embedding)
    RETURN m
    """
    result = session.run(query)
    memories = [record["m"] for record in result]
    
    # Compute similarities and sort
    memory_scores = []
    for memory in memories:
        if not memory.get("embedding"):
            continue
        score = cosine_similarity(query_embedding, memory["embedding"])
        if score >= min_score:
            memory_data = dict(memory.items())
            memory_data["similarity"] = score
            memory_scores.append(memory_data)
    
    # Sort by similarity score and return top k
    memory_scores.sort(key=lambda x: x["similarity"], reverse=True)
    return memory_scores[:k]

def create_document_memory_relationship(db_manager, document_id: str, memory):
    """Creates a relationship between a Document and a Memory node. If the Memory node does not exist, it is created with an embedding."""
    from db.vector_utils import get_embedding
    # Compute embedding for the memory content
    embedding = get_embedding(memory.content)
    query = """
    MATCH (d:Document {id: $doc_id})
    MERGE (m:Memory {content: $content})
    ON CREATE SET m.confidence = $confidence, m.sentiment = $sentiment, m.tags = $tags, m.created_at = timestamp(), m.embedding = $embedding
    MERGE (d)-[:HAS_MEMORY]->(m)
    """
    with db_manager.get_session() as session:
        session.run(query, doc_id=document_id, content=memory.content, confidence=memory.confidence, sentiment=memory.sentiment, tags=memory.tags, embedding=embedding) 