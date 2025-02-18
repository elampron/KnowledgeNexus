"""
Database operations for document management.
"""
import logging
from typing import Optional, List, Dict
from db.db_manager import Neo4jManager
from models.document import Document

logger = logging.getLogger(__name__)

def create_document(db_manager: Neo4jManager, document: Document) -> None:
    """Create a new document node in the database."""
    with db_manager.get_session() as session:
        session.run("""
            CREATE (d:Document {
                id: $id,
                fileName: $file_name,
                fileType: $file_type,
                fileSize: $file_size,
                uploadDate: $upload_date,
                originalPath: $original_path,
                markdownPath: $markdown_path,
                conversionStatus: $conversion_status,
                errorMessage: $error_message
            })
        """, document.model_dump())
        logger.info("Created document node: %s", document.file_name)

def create_document_entity_relationship(db_manager: Neo4jManager, document_id: str, entity_name: str) -> None:
    """Create a MENTIONS relationship between a document and an entity."""
    with db_manager.get_session() as session:
        session.run("""
            MATCH (d:Document {id: $doc_id})
            MATCH (e:Entity {name: $entity_name})
            MERGE (d)-[:MENTIONS]->(e)
        """, {'doc_id': document_id, 'entity_name': entity_name})
        logger.debug("Created MENTIONS relationship: %s -> %s", document_id, entity_name)

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

def update_document_status(db_manager: Neo4jManager, document_id: str, 
                         status: str, error_message: Optional[str] = None) -> None:
    """Update the conversion status and error message of a document."""
    with db_manager.get_session() as session:
        session.run("""
            MATCH (d:Document {id: $doc_id})
            SET d.conversionStatus = $status,
                d.errorMessage = $error_message
        """, {
            'doc_id': document_id,
            'status': status,
            'error_message': error_message
        })
        logger.info("Updated document status: %s -> %s", document_id, status) 