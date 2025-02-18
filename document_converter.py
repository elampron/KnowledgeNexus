import os
import uuid
import datetime
import shutil
import logging
from typing import Dict, Optional

# Try to import markitdown; if not available, instruct the user to install it
try:
    from markitdown import MarkItDown
except ImportError as e:
    raise ImportError("markitdown module not found. Please install it via pip install markitdown.")

from db.db_manager import Neo4jManager
from db import documents
from models.document import Document
from models.entities import ExtractedEntities
from cognitive.entity_extraction import extract_entities_from_text
from nexus.entity_processing import EntityProcessingPipeline

logger = logging.getLogger(__name__)

class DocumentConverter:
    def __init__(self, 
                 db_manager: Neo4jManager,
                 entity_pipeline: EntityProcessingPipeline,
                 original_dir: str = 'knowledge_nexus_files/originals',
                 markdown_dir: str = 'knowledge_nexus_files/markdown'):
        """
        Initialize DocumentConverter with Neo4j database manager and entity processing pipeline.
        
        Args:
            db_manager: Neo4j database manager instance
            entity_pipeline: Entity processing pipeline instance
            original_dir: Directory to store original files
            markdown_dir: Directory to store converted markdown files
        """
        self.db_manager = db_manager
        self.entity_pipeline = entity_pipeline
        self.original_dir = original_dir
        self.markdown_dir = markdown_dir

        # Ensure the directories exist
        os.makedirs(self.original_dir, exist_ok=True)
        os.makedirs(self.markdown_dir, exist_ok=True)

    def store_file_and_convert(self, src_file_path: str) -> Document:
        """
        Process the file by:
        1. Storing it in the original files directory
        2. Converting it to Markdown using MarkItDown
        3. Saving the markdown output
        4. Extracting entities from the markdown
        5. Processing entities through the pipeline
        6. Creating a document node in Neo4j with metadata and entity relationships
        
        Returns:
            Document: The processed document with metadata and extracted information
        """
        # Generate a unique ID and construct a unique file name
        file_id = str(uuid.uuid4())
        base_name = os.path.basename(src_file_path)
        unique_file_name = f"{file_id}_{base_name}"
        dest_original = os.path.join(self.original_dir, unique_file_name)

        # Copy the original file to the storage directory
        try:
            shutil.copy2(src_file_path, dest_original)
        except Exception as e:
            logger.error("Error copying file to original storage: %s", e)
            raise e

        # Get file metadata
        file_size = os.path.getsize(dest_original)
        file_type = os.path.splitext(dest_original)[1].lower()
        upload_date = datetime.datetime.now()

        # Convert the file to Markdown using MarkItDown
        markdown_text = ""
        conversion_status = "Success"
        error_message = None
        try:
            md = MarkItDown()
            result = md.convert(dest_original)
            markdown_text = result.text_content
        except Exception as e:
            conversion_status = "Conversion Failed"
            error_message = str(e)
            logger.error("Conversion failed: %s", e)
            raise RuntimeError(f"Document conversion failed: {str(e)}")

        # Determine the markdown file path (same base name, .md extension)
        markdown_file_name = os.path.splitext(unique_file_name)[0] + ".md"
        dest_markdown = os.path.join(self.markdown_dir, markdown_file_name)

        # Write the markdown output
        try:
            with open(dest_markdown, "w", encoding="utf-8") as md_file:
                md_file.write(markdown_text)
        except Exception as e:
            logger.error("Saving markdown file failed: %s", e)
            raise RuntimeError(f"Failed to save markdown file: {str(e)}")

        # Extract entities from the markdown text
        try:
            extracted_entities = extract_entities_from_text(markdown_text)
        except Exception as e:
            logger.error("Entity extraction failed: %s", e)
            raise RuntimeError(f"Entity extraction failed: {str(e)}")

        # Process extracted entities through the pipeline
        try:
            final_entities = self.entity_pipeline.process_extracted_entities(extracted_entities)
        except Exception as e:
            logger.error("Entity processing failed: %s", e)
            raise RuntimeError(f"Entity processing failed: {str(e)}")

        # Create document record
        document = Document(
            id=file_id,
            file_name=base_name,
            file_type=file_type,
            file_size=file_size,
            upload_date=upload_date,
            original_path=dest_original,
            markdown_path=dest_markdown,
            conversion_status=conversion_status,
            error_message=error_message,
            entities=[entity.name for entity in final_entities]
        )

        # Store document in database
        try:
            # Create document node
            documents.create_document(self.db_manager, document)
            
            # Create relationships to entities
            for entity_name in document.entities:
                documents.create_document_entity_relationship(
                    self.db_manager, document.id, entity_name
                )
        except Exception as e:
            logger.error("Database operation failed: %s", e)
            documents.update_document_status(
                self.db_manager, document.id, 
                "Database Error", str(e)
            )
            raise RuntimeError(f"Database operation failed: {str(e)}")

        # Infer relationships between entities based on document context
        self.entity_pipeline.infer_and_store_relationships(markdown_text, final_entities)

        logger.info("Document processed successfully: %s", document.file_name)
        return document


# If this module is run as a script, demonstrate a simple test
if __name__ == "__main__":
    import sys
    from db.db_manager import Neo4jManager
    from nexus.entity_resolution import EntityResolutionPipeline
    from nexus.pipeline import EntityProcessingPipeline

    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python document_converter.py <path_to_file>")
        sys.exit(1)

    # Initialize components
    db_manager = Neo4jManager()
    db_manager.connect()
    
    resolution_pipeline = EntityResolutionPipeline()
    entity_pipeline = EntityProcessingPipeline(db_manager, resolution_pipeline)
    
    # Process the file
    try:
        file_path = sys.argv[1]
        converter = DocumentConverter(db_manager, entity_pipeline)
        document = converter.store_file_and_convert(file_path)
        print("File processed. Document:", document.model_dump())
    finally:
        db_manager.close() 