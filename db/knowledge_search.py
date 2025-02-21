import logging
import numpy as np
from neo4j import Session
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2) if norm1 and norm2 else 0

def search_knowledge(
    session: Session,
    query_embedding: list,
    node_type: Optional[str] = None,
    k: int = 10,
    min_score: float = 0.5
) -> List[Dict]:
    """
    Search for nodes with embeddings, optionally filtered by type.
    
    Args:
        session: Neo4j session
        query_embedding: Vector to search against
        node_type: Optional node label to filter by (e.g., "Memory", "Document", "Entity")
        k: Number of results to return
        min_score: Minimum similarity score threshold
    
    Returns:
        List of dictionaries containing node data and similarity scores
    """
    # Construct query based on whether a specific node type is requested
    if node_type and node_type.lower() != "all":
        query = f"""
        MATCH (n:{node_type})
        WHERE n.embedding IS NOT NULL
        RETURN n
        """
    else:
        query = """
        MATCH (n)
        WHERE n.embedding IS NOT NULL
        RETURN n, labels(n) as types
        """
    
    result = session.run(query)
    nodes = [record for record in result]
    
    # Compute similarities and sort
    node_scores = []
    for record in nodes:
        node = record["n"]
        if not node.get("embedding"):
            continue
            
        score = cosine_similarity(query_embedding, node["embedding"])
        if score >= min_score:
            node_data = dict(node.items())
            node_data["similarity"] = score
            
            # Include node type(s) if available
            if "types" in record:
                node_data["types"] = record["types"]
            
            node_scores.append(node_data)
    
    # Sort by similarity score and return top k
    node_scores.sort(key=lambda x: x["similarity"], reverse=True)
    return node_scores[:k]

def get_searchable_types(session: Session) -> List[str]:
    """
    Get a list of node labels that have nodes with embeddings.
    """
    query = """
    MATCH (n)
    WHERE n.embedding IS NOT NULL
    RETURN distinct labels(n) as types
    """
    result = session.run(query)
    types = set()
    for record in result:
        types.update(record["types"])
    return sorted(list(types)) 