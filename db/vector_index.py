import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def create_vector_index(driver, label: str, property: str, dimensions: int, similarity: str = "COSINE") -> None:
    """
    Create a vector index on nodes with the given label and property using Neo4j's native vector indexing.

    Args:
        driver: Neo4j driver instance.
        label (str): The node label (e.g., 'Document' or 'Entity').
        property (str): The property name that stores the embedding vector.
        dimensions (int): The dimensionality of the embedding vector (e.g., 3072 for text-embedding-3-large).
        similarity (str): Similarity measure to use (default is "COSINE").
    """
    index_name = f"{label}_{property}_vector_index"
    query = (
        f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON (n.{property}) "
        f"OPTIONS {{ indexProvider: 'native-vector', vectorDimensions: {dimensions}, similarity: '{similarity}' }}"
    )
    try:
        with driver.session() as session:
            session.run(query)
            logger.info("Created vector index: %s", index_name)
    except Exception as e:
        logger.error("Error creating vector index: %s", str(e))
        raise


def find_nearest_nodes(driver, embedding: list, label: str, property: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Find the nearest nodes based on vector similarity using the provided embedding.

    Args:
        driver: Neo4j driver instance.
        embedding (list): The query embedding vector.
        label (str): The node label to search (e.g., 'Document' or 'Entity').
        property (str): The property name containing the embedding vector.
        limit (int): Maximum number of nodes to return.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing node and similarity score.
    """
    query = (
        f"MATCH (n:{label}) "
        f"RETURN n, gds.alpha.similarity.cosine(n.{property}, $embedding) AS similarity "
        f"ORDER BY similarity DESC "
        f"LIMIT $limit"
    )
    try:
        with driver.session() as session:
            result = session.run(query, embedding=embedding, limit=limit)
            nodes = []
            for record in result:
                nodes.append({"node": record["n"], "similarity": record["similarity"]})
            return nodes
    except Exception as e:
        logger.error("Error finding nearest nodes: %s", str(e))
        raise 