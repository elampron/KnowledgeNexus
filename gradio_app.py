import gradio as gr
import os
import logging
import tempfile
import uuid

# Import required components from our codebase
from db.db_manager import Neo4jManager
from nexus.pipeline import KnowledgeNexusPipeline
from db.vector_utils import get_embedding  # newly imported for embedding
from db import knowledge_search

# Import the new core functions
from nexus.core import process_text_input_core, process_document_file_core, search_knowledge_core

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_text_input(text, instructions=""):
    """
    Process text input by delegating to the core logic.
    """
    return process_text_input_core(text, instructions)

def process_document_file(file):
    """
    Process an uploaded document file by saving it to disk and delegating to the core logic.
    """
    if file is None:
        return "No file uploaded."
    # Gradio provides a file-like object; save it to a temp file
    temp_dir = os.path.join(os.getcwd(), "knowledge_nexus_files")
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = f"{uuid.uuid4()}_{file.name}"
    file_path = os.path.join(temp_dir, temp_filename)
    with open(file_path, "wb") as f:
        f.write(file.read())
    return process_document_file_core(file_path)

def search_knowledge_fn(query_text: str, node_type: str = "ALL", k: int = 10, min_score: float = 0.5):
    """
    Search for knowledge nodes using the core logic.
    """
    return search_knowledge_core(query_text, node_type, k, min_score)

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