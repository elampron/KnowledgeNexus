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
from nexus.entity_processing import EntityProcessingPipeline
from db.vector_utils import get_embedding

logger = logging.getLogger(__name__)

class DocumentConverter:
    def __init__(self, 
                 db_manager: Neo4jManager,
                 entity_pipeline: EntityProcessingPipeline,
                 storage_dir: str = 'knowledge_nexus_files'):
        """
        Initialize DocumentConverter with Neo4j database manager and entity processing pipeline.
        
        Args:
            db_manager: Neo4j database manager instance
            entity_pipeline: EntityProcessingPipeline instance
            storage_dir: Directory to store both original and converted markdown files.
        """
        self.db_manager = db_manager
        self.entity_pipeline = entity_pipeline
        self.storage_dir = storage_dir

        # Ensure the storage directory exists
        os.makedirs(self.storage_dir, exist_ok=True)

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
        file_name, file_ext = os.path.splitext(base_name)
        unique_file_name = f"{file_name}_{file_id}{file_ext}"
        dest_original = os.path.join(self.storage_dir, unique_file_name)

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
        if file_type == ".md":
            try:
                with open(dest_original, "r", encoding="utf-8") as f:
                    markdown_text = f.read()
                conversion_status = "Conversion Skipped"
                error_message = None
                logger.info("File is markdown. Skipping conversion and using original content.")
            except Exception as e:
                conversion_status = "Conversion Failed"
                error_message = str(e)
                logger.error("Reading markdown file failed: %s", e)
                raise RuntimeError(f"Failed to read markdown file: {str(e)}")
        else:
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
                conversion_status = "Success"
                error_message = None
            except Exception as e:
                conversion_status = "Conversion Failed"
                error_message = str(e)
                logger.error("Conversion failed: %s", e)
                raise RuntimeError(f"Document conversion failed: {str(e)}")

        # Determine the markdown file path (same base name, .md extension)
        markdown_file_name = os.path.splitext(unique_file_name)[0] + ".md"
        dest_markdown = os.path.join(self.storage_dir, markdown_file_name)

        # Write the markdown output
        try:
            with open(dest_markdown, "w", encoding="utf-8") as md_file:
                md_file.write(markdown_text)
        except Exception as e:
            logger.error("Saving markdown file failed: %s", e)
            raise RuntimeError(f"Failed to save markdown file: {str(e)}")

        # LLM Metadata Extraction: Generate content_type, description, and summary from the markdown text
        try:
            from openai import OpenAI
            from models.llm_document_metadata import DocumentLLMMetadata
            client = OpenAI()

            system_prompt = """
            You are an assistant that analyzes document text and generates metadata.
            Classify the content into one of the following categories: Email, Note, Documentation, Post, Image, or Other.
            Then, generate a short description (maximum 150 characters) and a brief summary (maximum 300 characters) of the document.
            """

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

            llm_metadata = completion.choices[0].message.parsed
            computed_content_type = llm_metadata.content_type
            computed_description = llm_metadata.description
            computed_summary = llm_metadata.summary
            logger.info("LLM generated metadata: content_type=%s, description=%s, summary=%s", computed_content_type, computed_description, computed_summary)
        except Exception as e:
            logger.error("LLM metadata generation failed: %s", e)
            computed_content_type = file_type
            computed_description = markdown_text.strip()[:150] if markdown_text.strip() else ""
            computed_summary = markdown_text.strip()[:300] if markdown_text.strip() else ""

        # Extraction of entities, topics, and memories using extract_entities_from_text
        try:
            
            extracted = self.entity_pipeline.extract_entities_from_text(markdown_text)
            # Process extracted entities through the entity pipeline
            final_entities = self.entity_pipeline.process_extracted_entities(extracted)
            extracted_entities = final_entities
            extracted_topics = extracted.topics
            extracted_memories = extracted.memories
            logger.info("Entity extraction and processing completed.")
        except Exception as e:
            logger.error("Entity extraction failed: %s", e)
            extracted_entities = []
            extracted_topics = []
            extracted_memories = []

        # Process extracted topics
        try:
            from db import topics as db_topics
            final_topics = []
            for topic in extracted_topics:
                similar = db_topics.search_similar_topics(self.db_manager, topic.name)
                if similar:
                    existing_topic = similar[0]
                    merged_aliases = list(set((existing_topic.get('aliases') or []) + topic.aliases))
                    db_topics.update_topic(self.db_manager, existing_topic['name'], merged_aliases)
                    final_topics.append(existing_topic['name'])
                else:
                    final_topics.append(topic.name)
                    db_topics.update_topic(self.db_manager, topic.name, topic.aliases)
        except Exception as e:
            logger.error("Topic processing failed: %s", e)
            raise RuntimeError(f"Topic processing failed: {str(e)}")

        # Process extracted memories (no additional processing assumed)
        final_memories = extracted_memories

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
            entities=[entity.name for entity in extracted_entities],
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
            
            # Create relationships to memories
            from db import memories as db_memories
            for memory in final_memories:
                db_memories.create_document_memory_relationship(self.db_manager, document.id, memory)
        except Exception as e:
            logger.error("Database operation failed: %s", e)
            documents.update_document_status(
                self.db_manager, document.id, 
                "Database Error", str(e)
            )
            raise RuntimeError(f"Database operation failed: {str(e)}")

        # Infer inter-node relationships between all extracted nodes using a unified LLM call
        try:
            from models.relationship import Relationships
            from openai import OpenAI
            client = OpenAI()
            
            # Consolidate all nodes
            all_nodes = {
                "entities": document.entities,
                "topics": final_topics,
                "memories": [mem.content for mem in final_memories if hasattr(mem, 'content')]
            }
            
            system_prompt = """
            You are an assistant that infers inter-node relationships in a knowledge graph.
            You are provided with a snippet of a document and a JSON object that groups nodes extracted from the document into categories: 'entities', 'topics', and 'memories'.
            Your task is to analyze the document text and identify explicit relationships between these nodes.
            For each relationship found, return an object with the following keys:
              - subject: the name of one node
              - predicate: a relationship label (e.g., 'son_of', 'father_of', 'related_to')
              - object: the name of the other node
              - confidence: a score between 0 and 1 indicating your confidence in this relationship
            If no explicit relationship is found, return an empty array.
            Return the output strictly as a JSON object with a key 'relationships' mapping to an array of relationship objects.
            """
            
            user_prompt = f"Document text: {markdown_text[:1000]}...\nNodes: {all_nodes}"
            
            completion = client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=Relationships,
                temperature=0.0
            )
            
            inferred_relationships = completion.choices[0].message.parsed.relationships
            logger.info("Inferred %d inter-node relationships.", len(inferred_relationships))
            from db import entities as db_entities
            db_entities.store_relationships(self.db_manager, inferred_relationships)
        except Exception as e:
            logger.error("Failed to infer inter-node relationships: %s", str(e))

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