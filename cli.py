import logging
import re
from pathlib import Path

import click
import cognitive.entity_extraction as ce
from db.db_manager import Neo4jManager
from nexus.entity_resolution import EntityResolutionPipeline
from nexus.entity_pipeline import EntityPipeline

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """CLI group for KnowledgeNexus entity extraction."""
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


def run_test():
    """Run a test with hardcoded input."""
    test_text = """# Eric's Life details
## Summary
Name : Eric Lampron
Date of Birth : December 21, 1973
Place of Birth : Senneterre, Province of Quebec, Canada
Gender : Male
Current Job: CO-Owner of Me.cie with Marie-Eve Girard, Presently Subcontracting my time to Thinkmax as their Director of IT.
Current Relationship Status: In a healthy and loving open relationship with Marie-Eve Girard.
Current Children: 2 Boys from a previous relationship with Roxanne Chabot, William Lampron (Feb. 19 2001) and Edouard Lampron ( March 28, 2006), and 1 boy with my current relationship, Arthur Lampron ( Dec. 17, 2021)
Parents: Mother: Danielle Bertrand ( March 18, 1950) and Father: Jacques Lampron ( Dec. 4 1949)
Siblings: Sister: Claudine Lampron ( Dec. 27, 1976)
Current Living Situation : Renting a nice Canadian Style house in Beloeil, Qc, Canada"""

    test_instructions = "Focus on personal and professional relationships, and family connections."
    
    click.echo("Running test with sample biographical text...")
    process_input.callback(test_text, test_instructions)


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