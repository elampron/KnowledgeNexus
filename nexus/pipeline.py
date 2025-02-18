"""
Main pipeline for KnowledgeNexus.
"""
import logging
from typing import List, Optional
from db.db_manager import Neo4jManager
from nexus.entity_resolution import EntityResolutionPipeline
from nexus.entity_processing import EntityProcessingPipeline
from nexus.document_pipeline import DocumentProcessingPipeline

logger = logging.getLogger(__name__)

class KnowledgeNexusPipeline:
    """
    Main pipeline for KnowledgeNexus that coordinates document processing and entity extraction.
    """
    
    def __init__(self, db_manager: Neo4jManager, file_storage_base: Optional[str] = None):
        """
        Initialize the main KnowledgeNexus pipeline.
        
        Args:
            db_manager: Neo4j database manager instance
            file_storage_base: Base directory for file storage (optional)
        """
        self.db_manager = db_manager
        
        # Initialize pipeline components
        self.resolution_pipeline = EntityResolutionPipeline()
        self.entity_pipeline = EntityProcessingPipeline(
            db_manager=self.db_manager,
            resolution_pipeline=self.resolution_pipeline
        )
        
        # Initialize document processing pipeline
        self.document_pipeline = DocumentProcessingPipeline(
            db_manager=self.db_manager,
            file_storage_base=file_storage_base
        )
        
        logger.info("KnowledgeNexus pipeline initialized")
    
    def process_document(self, file_path: str) -> dict:
        """
        Process a single document through the pipeline.
        
        Args:
            file_path: Path to the document to process
            
        Returns:
            dict: Document record with metadata and extracted information
        """
        return self.document_pipeline.process_document(file_path)
    
    def process_directory(self, directory_path: str) -> List[dict]:
        """
        Process all supported documents in a directory.
        
        Args:
            directory_path: Path to directory containing documents
            
        Returns:
            List[dict]: List of document records for successfully processed files
        """
        return self.document_pipeline.process_directory(directory_path)
    
    def get_document_entities(self, document_id: str) -> List[str]:
        """
        Retrieve all entities mentioned in a document.
        
        Args:
            document_id: ID of the document to query
            
        Returns:
            List[str]: Names of entities mentioned in the document
        """
        return self.document_pipeline.get_document_entities(document_id)
    
    def get_document_metadata(self, document_id: str) -> Optional[dict]:
        """
        Retrieve metadata for a document.
        
        Args:
            document_id: ID of the document to query
            
        Returns:
            Optional[dict]: Document metadata if found, None if not found
        """
        return self.document_pipeline.get_document_metadata(document_id) 