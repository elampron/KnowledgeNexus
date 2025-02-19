import logging
import re
from pathlib import Path
import os

import click
import cognitive.entity_extraction as ce
from db.db_manager import Neo4jManager
from nexus.entity_resolution import EntityResolutionPipeline
from nexus.entity_pipeline import EntityPipeline
from nexus.pipeline import KnowledgeNexusPipeline
from nexus.entity_processing import EntityProcessingPipeline

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """CLI group for KnowledgeNexus entity extraction and document processing."""
    pass


@cli.command(name='process_input')
@click.argument('text')
@click.option('--instructions', '-i', default="", help="Optional instructions for entity extraction")
def process_input(text: str, instructions: str = ""):
    """Process the input text by extracting entities, resolving them, and inferring relationships."""
    try:
        # Initialize components
        db_manager = Neo4jManager()
        db_manager.connect()
        
        resolution_pipeline = EntityResolutionPipeline()
        pipeline = EntityPipeline(db_manager, resolution_pipeline)
        
        # Process the full input (extract entities, resolve them, infer and store relationships)
        entities, relationships = pipeline.process_input(text, instructions)
        logger.info("Pipeline processed %d entities and inferred %d relationships.", 
                   len(entities), len(relationships))
        
        # Output results
        click.echo(f"\nProcessed {len(entities)} entities:")
        for entity in entities:
            click.echo(f"- {entity.name}")
        
        click.echo(f"\nInferred {len(relationships)} relationships:")
        for rel in relationships:
            click.echo(f"- {rel.subject} {rel.predicate} {rel.object} (confidence: {rel.confidence:.2f})")
        
    except Exception as e:
        logger.error("Error processing input: %s", str(e))
        click.echo(f"Error: {str(e)}", err=True)
    finally:
        if 'db_manager' in locals():
            db_manager.close()


@cli.command(name='process_document')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--storage-base', '-s', default=None, 
              help="Base directory for file storage (optional)")
def process_document(file_path: str, storage_base: str = None):
    """Process a document through the KnowledgeNexus pipeline.
    
    This command will:
    1. Convert the document to markdown
    2. Extract entities
    3. Store the document and its relationships in the knowledge graph
    """
    try:
        # Initialize components
        db_manager = Neo4jManager()
        db_manager.connect()
        
        # Initialize the main pipeline
        pipeline = KnowledgeNexusPipeline(
            db_manager=db_manager,
            file_storage_base=storage_base
        )
        
        # Process the document
        document = pipeline.process_document(file_path)
        
        # Output results
        click.echo(f"\nProcessed document: {document.file_name}")
        click.echo(f"Document ID: {document.id}")
        click.echo(f"Status: {document.conversion_status}")
        
        if document.error_message:
            click.echo(f"Errors: {document.error_message}")
            
        click.echo(f"\nExtracted {len(document.entities)} entities:")
        for entity in document.entities:
            click.echo(f"- {entity}")
            
    except Exception as e:
        logger.error("Error processing document: %s", str(e))
        click.echo(f"Error: {str(e)}", err=True)
    finally:
        if 'db_manager' in locals():
            db_manager.close()


@cli.command(name='process_directory')
@click.argument('directory_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--storage-base', '-s', default=None, 
              help="Base directory for file storage (optional)")
def process_directory(directory_path: str, storage_base: str = None):
    """Process all documents in a directory through the KnowledgeNexus pipeline.
    
    This command will process each document in the directory (and subdirectories) by:
    1. Converting them to markdown
    2. Extracting entities
    3. Storing the documents and their relationships in the knowledge graph
    """
    try:
        # Initialize components
        db_manager = Neo4jManager()
        db_manager.connect()
        
        # Initialize the main pipeline
        pipeline = KnowledgeNexusPipeline(
            db_manager=db_manager,
            file_storage_base=storage_base
        )
        
        # Process the directory
        documents = pipeline.process_directory(directory_path)
        
        # Output results
        click.echo(f"\nProcessed {len(documents)} documents:")
        for doc in documents:
            click.echo(f"\nDocument: {doc.file_name}")
            click.echo(f"Status: {doc.conversion_status}")
            click.echo(f"Entities: {len(doc.entities)}")
            
            if doc.error_message:
                click.echo(f"Errors: {doc.error_message}")
            
    except Exception as e:
        logger.error("Error processing directory: %s", str(e))
        click.echo(f"Error: {str(e)}", err=True)
    finally:
        if 'db_manager' in locals():
            db_manager.close()


@cli.command(name='get_document_info')
@click.argument('document_id')
def get_document_info(document_id: str):
    """Retrieve and display information about a processed document."""
    try:
        # Initialize components
        db_manager = Neo4jManager()
        db_manager.connect()
        
        # Initialize the main pipeline
        pipeline = KnowledgeNexusPipeline(db_manager=db_manager)
        
        # Get document metadata
        document = pipeline.get_document_metadata(document_id)
        if not document:
            click.echo(f"No document found with ID: {document_id}")
            return
        
        # Get document entities
        entities = pipeline.get_document_entities(document_id)
        
        # Output results
        click.echo(f"\nDocument Information:")
        click.echo(f"ID: {document.id}")
        click.echo(f"Name: {document.file_name}")
        click.echo(f"Type: {document.file_type}")
        click.echo(f"Size: {document.file_size} bytes")
        click.echo(f"Upload Date: {document.upload_date}")
        click.echo(f"Status: {document.conversion_status}")
        
        if document.error_message:
            click.echo(f"Errors: {document.error_message}")
        
        click.echo(f"\nEntities ({len(entities)}):")
        for entity in entities:
            click.echo(f"- {entity}")
            
    except Exception as e:
        logger.error("Error retrieving document info: %s", str(e))
        click.echo(f"Error: {str(e)}", err=True)
    finally:
        if 'db_manager' in locals():
            db_manager.close()


def run_test():
    """Run a test with hardcoded input."""
    # Set up detailed logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        test_text = """# Eric's Life details

## Summary
Name : Eric Lampron
Date of Birth : December 21, 1973
Place of Birth : Senneterre, Province of Quebec, Canada
Gender : Male
Current Job: CO-Owmner of Me.cie with Marie-Eve Girard, Presently Subcontracting my to time to Thinkmax as their Director of IT.
Current Relationship Status: In a healthy and loving open relationship with Marie-Eve Girard.
Current Children: 2 Boys from a previous relationship with Roxanne Chabot, William Lampron (Feb. 19 2001) and Edouard Lampron ( March 28, 2006), and 1 boy with my current relationship, Arthur Lampron ( Dec. 17, 2021)
Parents: Mother: Danielle Bertrand ( March 18, 1950) and Father: Jacques Lampron ( Dec. 4 1949)
Siblings: Sister: Claudine Lampron ( Dec. 27, 1976)
Current Living Situation : Renting an nice Canadian Style house in Beloeil, Qc, Canada

## Personal information
Cell: 514-501-0124
Main personal email: elampron@gmail.com
Thinkmax email: elampron@thinkmax.com
M.E Cie. email: elampron@mecie.ca
Fondation Leski email: elampron@fondationleski.com

Marie-eve cell: 514-433-9555
Marie-eve gmail: girard.marie.ev@gmail.com
Marie-eve M.E Cie. email: megirard@mecie.ca
Marie-eve Fondation Leksi: megirard@fondationleski.com


## Childhood
Born on December 21, 1973, in a small canadian village called Senneterre, situated in a region named Abitibi, about 500 km north of Montreal in the Quebec province, Eric Lampron spent a modest but happy childhood. Like many boys at this stage in life, Eric wanted to become an Astronaut, or a Marine Biologist later. He loved reading sci-fi, fleuve noir series. He LOVED star Wars. He was so curious about everything, including science, space, technology, animals. For 10 years, he lived in the rural part of the small village of Senneterre. """

        test_instructions = "Focus on personal and professional relationships, and family connections."
        
        click.echo("Running test with sample biographical text...")
        
        # Initialize components with explicit error handling
        try:
            db_manager = Neo4jManager()
            db_manager.connect()
            logger.info("Successfully connected to Neo4j database")
        except Exception as e:
            logger.error("Failed to connect to Neo4j: %s", str(e))
            click.echo("Error: Failed to connect to database", err=True)
            return

        try:
            process_input.callback(test_text, test_instructions)
            logger.info("Successfully processed test input")
        except Exception as e:
            logger.error("Error processing test input: %s", str(e))
            click.echo(f"Error processing test input: {str(e)}", err=True)
        finally:
            db_manager.close()
            logger.info("Closed database connection")

        # Test document processing with explicit error handling
        # test_file = "C:/Users/lampr/OneDrive/Pictures/67673571642__3A378B89-2C90-4849-9EA2-3734DB41017C.jpg"
        # if os.path.exists(test_file):
        #     click.echo("\nTesting document processing...")
        #     try:
        #         process_document.callback(test_file)
        #         logger.info("Successfully processed test document")
        #     except Exception as e:
        #         logger.error("Error processing test document: %s", str(e))
        #         click.echo(f"Error processing test document: {str(e)}", err=True)
    except Exception as e:
        logger.error("Test run failed: %s", str(e))
        click.echo(f"Test run failed: {str(e)}", err=True)


if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # If no arguments are provided, run the test
    import sys
    if len(sys.argv) == 1:
        run_test()
    else:
        cli() 