"""
Database operations for document management.
"""
import logging
from typing import Optional, List, Dict
from db.db_manager import Neo4jManager
from models.document import Document
from datetime import datetime

logger = logging.getLogger(__name__)

def create_document(db_manager: Neo4jManager, document: Document) -> None:
    """
    Create a Document node in Neo4j with the provided document metadata, including the embedding vector.
    Args:
        db_manager: Neo4jManager instance
        document: Document model instance containing metadata and embedding property.
    """
    query = (
        "CREATE (d:Document {"
        "id: $id, "
        "fileName: $file_name, "
        "fileType: $file_type, "
        "fileSize: $file_size, "
        "uploadDate: $upload_date, "
        "originalPath: $original_path, "
        "markdownPath: $markdown_path, "
        "conversionStatus: $conversion_status, "
        "errorMessage: $error_message, "
        "topics: $topics, "
        "entities: $entities, "
        "embedding: $embedding, "
        "description: $description, "
        "contentType: $content_type, "
        "summary: $summary"
        "}) RETURN d"
    )
    
    upload_date = document.upload_date.isoformat() if isinstance(document.upload_date, datetime) else document.upload_date
    
    params = {
        "id": document.id,
        "file_name": document.file_name,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "upload_date": upload_date,
        "original_path": document.original_path,
        "markdown_path": document.markdown_path,
        "conversion_status": document.conversion_status,
        "error_message": document.error_message,
        "topics": document.topics,
        "entities": document.entities,
        "embedding": document.embedding,
        "description": document.description,
        "content_type": document.content_type,
        "summary": document.summary
    }
    
    try:
        with db_manager.get_session() as session:
            logger.debug("Executing query: %s", query)
            logger.debug("With parameters: %s", params)
            
            result = session.run(query, params)
            summary = result.consume()
            
            if summary.counters.nodes_created == 1:
                logger.info("Document node created successfully: %s", document.file_name)
            else:
                logger.error("Failed to create document node: no node was created")
                raise RuntimeError("Document node creation failed")
                
    except Exception as e:
        logger.error("Failed to create document: %s", str(e))
        raise RuntimeError(f"Failed to create document node: {str(e)}")

def create_document_entity_relationship(db_manager: Neo4jManager, document_id: str, entity_name: str) -> None:
    """
    Create a relationship between the Document and an Entity node.
    Args:
        db_manager: Neo4jManager instance
        document_id (str): The ID of the Document node
        entity_name (str): The name of the Entity node
    """
    query = (
        "MATCH (d:Document {id: $document_id}), (e:Entity {name: $entity_name}) "
        "MERGE (d)-[:MENTIONS]->(e)"
    )
    try:
        with db_manager.get_session() as session:
            session.run(query, document_id=document_id, entity_name=entity_name)
            logger.info("Created relationship between document %s and entity %s", document_id, entity_name)
    except Exception as e:
        logger.error("Failed to create document-entity relationship: %s", e)
        raise

def get_document_metadata(db_manager: Neo4jManager, document_id: str) -> Optional[Dict]:
    """Retrieve metadata for a document."""
    with db_manager.get_session() as session:
        result = session.run("""
            MATCH (d:Document {id: $doc_id})
            RETURN d {.*} as metadata
        """, {'doc_id': document_id})
        record = result.single()
        return record["metadata"] if record else None

def get_document_entities(db_manager: Neo4jManager, document_id: str) -> List[str]:
    """Retrieve all entities mentioned in a document."""
    with db_manager.get_session() as session:
        result = session.run("""
            MATCH (d:Document {id: $doc_id})-[:MENTIONS]->(e:Entity)
            RETURN e.name as entity_name
        """, {'doc_id': document_id})
        return [record["entity_name"] for record in result]

def update_document_status(db_manager: Neo4jManager, document_id: str, status: str, error_message: str) -> None:
    """
    Update the status and error message of a Document node in Neo4j.
    Args:
        db_manager: Neo4jManager instance
        document_id (str): The ID of the Document node
        status (str): New status
        error_message (str): Error message to store
    """
    query = (
        "MATCH (d:Document {id: $document_id}) "
        "SET d.conversion_status = $status, d.error_message = $error_message"
    )
    try:
        with db_manager.get_session() as session:
            session.run(query, document_id=document_id, status=status, error_message=error_message)
            logger.info("Updated document %s status to %s", document_id, status)
    except Exception as e:
        logger.error("Failed to update document status: %s", e)
        raise 