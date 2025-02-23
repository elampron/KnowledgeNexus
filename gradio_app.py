import opentelemetry_setup
import gradio as gr
import os
import datetime
import logging
import tempfile
import uuid

# Import required components from our codebase
from db.db_manager import Neo4jManager
from nexus.entity_resolution import EntityResolutionPipeline
from nexus.entity_pipeline import EntityPipeline
from nexus.pipeline import KnowledgeNexusPipeline
from db.vector_utils import get_embedding  # newly imported for embedding
from db import knowledge_search

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_text_input(text, instructions=""):
    """
    Process text input by saving it as a temporary file and processing it through
    the document pipeline, ensuring consistent handling of all inputs.
    """
    if not text.strip():
        return "No text provided."
        
    logger.info("Processing text input of length %d", len(text))
    db_manager = Neo4jManager()
    db_manager.connect()
    
    try:
        # Create a temporary file with the text content
        temp_dir = os.path.join(os.getcwd(), "knowledge_nexus_files")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate a unique filename
        file_id = str(uuid.uuid4())
        temp_filename = f"{file_id}_text_input.txt"
        file_path = os.path.join(temp_dir, temp_filename)
        
        # Write the text content to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            if instructions:
                f.write(f"Instructions: {instructions}\n\n")
            f.write(text)
            
        logger.info(f"Saved text input to temporary file: {file_path}")
        
        # Process the file using the document pipeline
        pipeline = KnowledgeNexusPipeline(db_manager)
        document = pipeline.process_document(file_path)
        
        # Construct a detailed output summary
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

def process_document_file(file):
    """
    Process an uploaded document file.
    The file can be an image (jpg, png, etc.) or a text/PDF/etc. file.
    """
    if file is None:
        return "No file uploaded."
        
    logger.info("Processing document file: %s", file.name)
    db_manager = Neo4jManager()
    db_manager.connect()
    
    try:
        pipeline = KnowledgeNexusPipeline(db_manager)
        # Process the uploaded file
        document = pipeline.process_document(file.name)
        
        # Construct a detailed output summary
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

# New function: Search Memories using vector similarity

def search_memories_fn(query_text):
    """
    Search Memory nodes using vector similarity search using the query text.
    Returns details about matching memory nodes and their similarity scores.
    """
    if not query_text.strip():
        return "No search query provided."
    
    from db.db_manager import Neo4jManager
    from db import memories as db_memories
    
    db_manager = Neo4jManager()
    db_manager.connect()
    try:
        # Try to create the vector index if it doesn't exist
        with db_manager.get_session() as session:
            try:
                db_memories.create_vector_index(session)
            except Exception as e:
                logger.warning(f"Could not create vector index: {e}")

        # Generate query embedding and search
        query_embedding = get_embedding(query_text)
        with db_manager.get_session() as session:
            results = db_memories.search_memories(session, query_embedding)
        if not results:
            return "No matching memories found."
        output = "Memory Search Results:\n\n"
        for mem in results:
            content = mem.get('content', 'No content')
            confidence = mem.get('confidence', 'N/A')
            similarity = mem.get('similarity', 'N/A')
            sentiment = mem.get('sentiment', 'N/A')
            tags = mem.get('tags', [])
            output += f"Content: {content}\nConfidence: {confidence}\nSimilarity: {similarity:.4f}\nSentiment: {sentiment}\nTags: {tags}\n---\n"
        return output
    except Exception as e:
        return f"Error during memory search: {str(e)}"
    finally:
        db_manager.close()

def search_knowledge_fn(query_text: str, node_type: str = "ALL", k: int = 10, min_score: float = 0.5):
    """
    Search for knowledge nodes using vector similarity search.
    Supports filtering by node type and returns details about matching nodes with their similarity scores.
    
    Args:
        query_text: The search query
        node_type: Type of node to search for ("ALL" or specific type)
        k: Number of results to return
        min_score: Minimum similarity score threshold (0.0 to 1.0)
    """
    if not query_text.strip():
        return "No search query provided."
    
    db_manager = Neo4jManager()
    db_manager.connect()
    try:
        # Get the query embedding
        query_embedding = get_embedding(query_text)
        
        # Search for nodes
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
            
        # Format results
        output = f"Search Results for {node_type} (showing top {k} results with similarity >= {min_score}):\n\n"
        for node in results:
            # Get node type(s)
            node_types = node.get("types", [node_type]) if "types" in node else [node_type]
            node_type_str = ", ".join(node_types)
            
            # Common fields
            similarity = node.get("similarity", "N/A")
            
            # Type-specific formatting
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
                # Generic node display
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

def get_node_types():
    """Get available node types for the dropdown."""
    db_manager = Neo4jManager()
    db_manager.connect()
    try:
        with db_manager.get_session() as session:
            types = knowledge_search.get_searchable_types(session)
        return ["ALL"] + types
    except Exception as e:
        logger.error("Error getting node types: %s", str(e))
        return ["ALL", "Memory", "Document", "Entity"]  # Fallback default types
    finally:
        db_manager.close()

# Build the Gradio interface
with gr.Blocks(title="Knowledge Nexus") as demo:
    gr.Markdown("""
    # Knowledge Nexus Web UI
    Process text or documents to extract entities and relationships, and search knowledge.
    """)
    
    with gr.Tabs():
        # Text Processing Tab
        with gr.TabItem("Process Text Input"):
            text_input = gr.Textbox(
                label="Enter text",
                lines=10,
                placeholder="Paste or type text here..."
            )
            instructions_input = gr.Textbox(
                label="Instructions (optional)",
                lines=2,
                placeholder="e.g., focus on personal or professional relationships..."
            )
            text_button = gr.Button("Process Text", variant="primary")
            text_output = gr.Textbox(label="Results", lines=15)
            text_button.click(
                fn=process_text_input,
                inputs=[text_input, instructions_input],
                outputs=text_output
            )
        
        # Document Processing Tab
        with gr.TabItem("Process Document File"):
            file_input = gr.File(
                label="Upload a document file",
                file_types=[
                    ".txt", ".pdf", ".docx", ".doc",
                    ".jpg", ".jpeg", ".png", ".gif",
                    ".md", ".rtf"
                ]
            )
            doc_button = gr.Button("Process Document", variant="primary")
            doc_output = gr.Textbox(label="Results", lines=15)
            doc_button.click(
                fn=process_document_file,
                inputs=file_input,
                outputs=doc_output
            )
        
        # Updated Knowledge Search Tab
        with gr.TabItem("Search Knowledge"):
            with gr.Row():
                search_query = gr.Textbox(
                    label="Enter search query",
                    placeholder="Enter your search text...",
                    scale=3
                )
                node_type = gr.Dropdown(
                    choices=get_node_types(),
                    value="ALL",
                    label="Filter by Type",
                    scale=1
                )
            with gr.Row():
                num_results = gr.Number(
                    value=10,
                    label="Number of results",
                    minimum=1,
                    maximum=100,
                    step=1,
                    scale=1
                )
                min_similarity = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.5,
                    step=0.05,
                    label="Minimum Similarity Score",
                    scale=2
                )
            search_button = gr.Button("Search Knowledge", variant="primary")
            search_output = gr.Textbox(label="Search Results", lines=15)
            
            # Update click event to include new parameters
            search_button.click(
                fn=search_knowledge_fn,
                inputs=[search_query, node_type, num_results, min_similarity],
                outputs=search_output,
                api_name="search_knowledge"
            )
    
    gr.Markdown("""
    ---
    Built with Gradio for Knowledge Nexus
    """)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",  # Make accessible from other machines
        show_api=False,  # Hide API docs
        share=False  # Don't create a public URL
    ) 