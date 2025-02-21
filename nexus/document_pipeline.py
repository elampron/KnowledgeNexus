"""
Document processing pipeline for KnowledgeNexus.
Handles document ingestion, conversion, and entity extraction.
"""
import logging
from typing import List, Optional
from pathlib import Path

from db.db_manager import Neo4jManager
from db import documents
from models.document import Document
from document_converter import DocumentConverter
from nexus.entity_resolution import EntityResolutionPipeline
from nexus.entity_processing import EntityProcessingPipeline

logger = logging.getLogger(__name__)

class DocumentProcessingPipeline:
    """
    Pipeline for processing documents through KnowledgeNexus.
    Handles document conversion, entity extraction, and knowledge graph updates.
    """
    
    def __init__(self, 
                 db_manager: Neo4jManager,
                 file_storage_base: Optional[str] = None):
        """
        Initialize the document processing pipeline.
        
        Args:
            db_manager: Neo4j database manager instance
            file_storage_base: Base directory for file storage (optional)
        """
        self.db_manager = db_manager
        
        # Set up storage directories
        self.file_storage_base = file_storage_base or "knowledge_nexus_files"
        # Use a single storage directory for all files as per updated design
        self.storage_dir = self.file_storage_base
        self.original_dir = str(Path(self.file_storage_base) / "originals")
        self.markdown_dir = str(Path(self.file_storage_base) / "markdown")
        
        # Initialize pipeline components
        self.resolution_pipeline = EntityResolutionPipeline()
        self.entity_pipeline = EntityProcessingPipeline(
            db_manager=self.db_manager,
            resolution_pipeline=self.resolution_pipeline
        )
        
        # Initialize document converter
        self.document_converter = DocumentConverter(
            db_manager=self.db_manager,
            entity_pipeline=self.entity_pipeline,
            storage_dir=self.storage_dir
        )
        
        # Create vector index for document embeddings
        try:
            from db.vector_index import create_vector_index
            create_vector_index(
                self.db_manager.driver,
                label="Document",
                property="embedding",
                dimensions=3072  # text-embedding-3-large dimensions
            )
            logger.info("Vector index created for Document embeddings")
        except Exception as e:
            logger.error("Failed to create vector index: %s", str(e))
            # Don't raise, we can still proceed with document processing
        
        logger.info("Document processing pipeline initialized")
    
    def process_document(self, file_path: str) -> Document:
        """
        Process a single document through the pipeline.
        
        Args:
            file_path: Path to the document to process
            
        Returns:
            Document: Processed document with metadata and extracted information
        """
        logger.info("Processing document: %s", file_path)
        
        try:
            # Process the document through the converter
            document = self.document_converter.store_file_and_convert(file_path)
            logger.info("Document processed successfully: %s", document.file_name)
            return document
            
        except Exception as e:
            logger.error("Failed to process document %s: %s", file_path, str(e))
            raise
    
    def process_directory(self, directory_path: str) -> List[Document]:
        """
        Process all supported documents in a directory.
        
        Args:
            directory_path: Path to directory containing documents
            
        Returns:
            List[Document]: List of processed documents
        """
        logger.info("Processing directory: %s", directory_path)
        
        processed_documents = []
        failed_files = []
        
        # Process each file in the directory
        for file_path in Path(directory_path).rglob('*'):
            if file_path.is_file():
                try:
                    document = self.process_document(str(file_path))
                    processed_documents.append(document)
                except Exception as e:
                    logger.error("Failed to process %s: %s", file_path, str(e))
                    failed_files.append((str(file_path), str(e)))
        
        # Log summary
        logger.info("Directory processing complete. Processed: %d, Failed: %d",
                   len(processed_documents), len(failed_files))
        
        if failed_files:
            logger.warning("Failed files: %s", 
                         "\n".join(f"{path}: {error}" for path, error in failed_files))
        
        return processed_documents
    
    def get_document_entities(self, document_id: str) -> List[str]:
        """
        Retrieve all entities mentioned in a document.
        
        Args:
            document_id: ID of the document to query
            
        Returns:
            List[str]: Names of entities mentioned in the document
        """
        return documents.get_document_entities(self.db_manager, document_id)
    
    def get_document_metadata(self, document_id: str) -> Optional[Document]:
        """
        Retrieve metadata for a document.
        
        Args:
            document_id: ID of the document to query
            
        Returns:
            Optional[Document]: Document if found, None if not found
        """
        metadata = documents.get_document_metadata(self.db_manager, document_id)
        if metadata:
            return Document(**metadata)
        return None 