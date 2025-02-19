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
from db.vector_utils import get_embedding

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
            # Initialize OpenAI client for image processing if needed
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            if file_type in image_extensions:
                from openai import OpenAI
                client = OpenAI()
                md = MarkItDown(llm_client=client, llm_model="gpt-4o")
            else:
                md = MarkItDown()
                
            result = md.convert(dest_original)
            markdown_text = result.text_content
            logger.info("File converted successfully: %s", base_name)
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

        # New LLM step to generate document metadata (content type, description, summary) using the extracted markdown text
        try:
            from openai import OpenAI
            # Import the Pydantic model for LLM metadata
            from models.llm_document_metadata import DocumentLLMMetadata
            
            client = OpenAI()
            
            # Construct system prompt that includes the schema information
            system_prompt = """
            You are an assistant that analyzes document text and generates metadata.
            Classify the content into one of the following categories: Email, Note, Documentation, Post, Image, or Other.
            Then, generate a short description (maximum 150 characters) and a brief summary (maximum 300 characters) of the document.
            """
            
            # First 1000 characters of the document as user content
            user_content = f"Document text: {markdown_text[:1000]}..."
            
            completion = client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format=DocumentLLMMetadata,
                temperature=0.3
            )
            
            # Get the parsed response directly as our Pydantic model
            llm_metadata = completion.choices[0].message.parsed
            computed_content_type = llm_metadata.content_type
            computed_description = llm_metadata.description
            computed_summary = llm_metadata.summary
            logger.info("LLM generated metadata: content_type=%s, description=%s, summary=%s", 
                       computed_content_type, computed_description, computed_summary)
        except Exception as e:
            logger.error("LLM metadata generation failed: %s", e)
            computed_content_type = file_type
            computed_description = markdown_text.strip()[:150] if markdown_text.strip() else ""
            computed_summary = markdown_text.strip()[:300] if markdown_text.strip() else ""

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

        # Process extracted topics similarly to entities
        try:
            from db import topics as db_topics
            final_topics = []
            for topic in extracted_entities.topics:
                similar = db_topics.search_similar_topics(self.db_manager, topic.name)
                if similar:
                    existing_topic = similar[0]
                    merged_aliases = list(set((existing_topic.get('aliases') or []) + topic.aliases))
                    db_topics.update_topic(self.db_manager, existing_topic['name'], merged_aliases, topic.notes or "")
                    final_topics.append(existing_topic['name'])
                else:
                    final_topics.append(topic.name)
                    db_topics.update_topic(self.db_manager, topic.name, topic.aliases, topic.notes or "")
        except Exception as e:
            logger.error("Topic processing failed: %s", e)
            raise RuntimeError(f"Topic processing failed: {str(e)}")

        # Generate embedding for the combined text content including extra fields
        vectorization_input = "\n".join([markdown_text, computed_description, computed_content_type, computed_summary])
        embedding = None
        if markdown_text.strip():
            try:
                embedding = get_embedding(vectorization_input)
                logger.info("Generated embedding for document: %s", base_name)
            except Exception as e:
                logger.error("Embedding generation failed: %s", e)
                # Don't raise here, we can still proceed with document creation

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
            entities=[entity.name for entity in final_entities],
            topics=final_topics,
            embedding=embedding,
            description=computed_description,
            content_type=computed_content_type,
            summary=computed_summary
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
            # Create relationships to topics
            from db import topics as db_topics
            for topic_name in document.topics:
                db_topics.create_document_topic_relationship(self.db_manager, document.id, topic_name)
        except Exception as e:
            logger.error("Database operation failed: %s", e)
            documents.update_document_status(
                self.db_manager, document.id, 
                "Database Error", str(e)
            )
            raise RuntimeError(f"Database operation failed: {str(e)}")

        # Infer relationships between entities based on document context
        from db import entities as db_entities
        relationships = self.entity_pipeline.infer_relationships(markdown_text, final_entities)
        logger.info("Inferred %d relationships.", len(relationships))
        db_entities.store_relationships(self.db_manager, relationships)

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