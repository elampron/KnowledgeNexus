import os
import uuid
import logging
from db.db_manager import Neo4jManager
from nexus.pipeline import KnowledgeNexusPipeline
from db.vector_utils import get_embedding
from db import knowledge_search

def process_text_input_core(text, instructions=""):
    if not text.strip():
        return "No text provided."
    logger = logging.getLogger(__name__)
    logger.info("Processing text input of length %d", len(text))
    db_manager = Neo4jManager()
    db_manager.connect()
    try:
        temp_dir = os.path.join(os.getcwd(), "knowledge_nexus_files")
        os.makedirs(temp_dir, exist_ok=True)
        file_id = str(uuid.uuid4())
        temp_filename = f"{file_id}_text_input.txt"
        file_path = os.path.join(temp_dir, temp_filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            if instructions:
                f.write(f"Instructions: {instructions}\n\n")
            f.write(text)
        logger.info(f"Saved text input to temporary file: {file_path}")
        pipeline = KnowledgeNexusPipeline(db_manager)
        document = pipeline.process_document(file_path)
        result = f"Processed text as document: {document.file_name}\n"
        result += f"Document ID: {document.id}\n"
        result += f"Content Type: {document.content_type}\n"
        result += f"Status: {document.conversion_status}\n"
        result += f"Description: {document.description}\n\n"
        result += f"Summary: {document.summary}\n\n"
        result += f"Entities extracted ({len(document.entities)}):\n"
        for entity in document.entities:
            result += f"- {entity}\n"
        if document.error_message:
            result += f"\nWarnings/Errors: {document.error_message}\n"
        logger.info("Successfully processed text input as document")
        return result
    except Exception as e:
        logger.error("Error processing text input: %s", str(e))
        return f"Error: {str(e)}"
    finally:
        db_manager.close()

def process_document_file_core(file_path):
    if not file_path:
        return "No file provided."
    logger = logging.getLogger(__name__)
    logger.info("Processing document file: %s", file_path)
    db_manager = Neo4jManager()
    db_manager.connect()
    try:
        pipeline = KnowledgeNexusPipeline(db_manager)
        document = pipeline.process_document(file_path)
        result = f"Processed document: {document.file_name}\n"
        result += f"Document ID: {document.id}\n"
        result += f"Content Type: {document.content_type}\n"
        result += f"Status: {document.conversion_status}\n"
        result += f"Description: {document.description}\n\n"
        result += f"Summary: {document.summary}\n\n"
        result += f"Entities extracted ({len(document.entities)}):\n"
        for entity in document.entities:
            result += f"- {entity}\n"
        if document.error_message:
            result += f"\nWarnings/Errors: {document.error_message}\n"
        logger.info("Successfully processed document file")
        return result
    except Exception as e:
        logger.error("Error processing document file: %s", str(e))
        return f"Error: {str(e)}"
    finally:
        db_manager.close()

def search_knowledge_core(query_text: str, node_type: str = "ALL", k: int = 10, min_score: float = 0.5):
    if not query_text.strip():
        return "No search query provided."
    logger = logging.getLogger(__name__)
    db_manager = Neo4jManager()
    db_manager.connect()
    try:
        query_embedding = get_embedding(query_text)
        with db_manager.get_session() as session:
            results = knowledge_search.search_knowledge(
                session=session,
                query_embedding=query_embedding,
                node_type=node_type if node_type != "ALL" else None,
                k=k,
                min_score=min_score
            )
        if not results:
            return f"No matching {node_type.lower() if node_type else 'knowledge'} found with similarity >= {min_score}."
        output = f"Search Results for {node_type} (showing top {k} results with similarity >= {min_score}):\n\n"
        for node in results:
            node_types = node.get("types", [node_type]) if "types" in node else [node_type]
            node_type_str = ", ".join(node_types)
            similarity = node.get("similarity", "N/A")
            if "Memory" in node_types:
                content = node.get("content", "No content")
                confidence = node.get("confidence", "N/A")
                sentiment = node.get("sentiment", "N/A")
                tags = node.get("tags", [])
                output += (
                    f"Type: {node_type_str}\n"
                    f"Content: {content}\n"
                    f"Confidence: {confidence}\n"
                    f"Similarity: {similarity:.4f}\n"
                    f"Sentiment: {sentiment}\n"
                    f"Tags: {tags}\n"
                )
            elif "Document" in node_types:
                title = node.get("file_name", "Untitled")
                description = node.get("description", "No description")
                output += (
                    f"Type: {node_type_str}\n"
                    f"Title: {title}\n"
                    f"Description: {description}\n"
                    f"Similarity: {similarity:.4f}\n"
                )
            else:
                output += f"Type: {node_type_str}\n"
                for key, value in node.items():
                    if key not in ["embedding", "types", "similarity"] and not key.startswith("_"):
                        output += f"{key}: {value}\n"
                output += f"Similarity: {similarity:.4f}\n"
            output += "---\n"
        return output
    except Exception as e:
        logger.error("Error during knowledge search: %s", str(e))
        return f"Error during search: {str(e)}"
    finally:
        db_manager.close() 