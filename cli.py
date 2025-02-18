import logging
import re
from pathlib import Path

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
    test_text = """Eric Lampron


​
Patrick Guedj;
​
Marc Belliveau
​
Salut vous deux,

 

je sais que vous vivez un moment chaotique en ce moment et loin de moi le désire d'en ajouter.

Par contre, j'ai la conviction que 2025 sera l'année des Agents AI et j'ai vraiment l'intention de capitaliser ma relativement grande expertise. Je dis relativement car je conviens que ca fais juste 3 ans que je fais de la recherche et joue avec, mais comparativement au marché, je suis expert.

Ma compréhension des processus d'affaire, jumelé à mon expertise technique, font un mélange parfait pour conceptualiser , réaliser et déployer des solutions d'automatisation propulser par le AI. Ma maitrise du AI en ce moment me libère de la dépendance d'équipe de dev, et me permet une énorme créativité.

En 2025, il y aura beaucoup de services vendu qui touche le AI. Et moi je veux une part du gateau. Pas nécessairement pour le potentiel de revenu, mais surtout parce que ca me passionne. 

Par contre, j'ai aussi de grandes obligations financières et a 51 ans, je ne peux plus me permettre de laisse trop d'argent sur la table. Je dois penser a une retraite un jour et je dois me rebâtir.  Je vous considère comme des amis, et même de la famille et je vais toujours favoriser travailler avec vous. Mais ca ne doit plus être au détriment de mon futur. 

C'est pour ca que je vais vous mettre un peu de pression. Je sais que vos objectifs et budget ne sont pas encore bien définis et que ce n'est pas le meilleur timing, mais j'aimerais avoir une réponse à ce qui suit assez rapidement. Je dois savoir si je dois poke le marché. 

 

Voici la vison très personnelle d'Eric Lampron:

 

Agir en tant qu'architecte de solution AI chez Thinkmax (mon désir n'est pas de travailler avec l'équipe de BI et Tec de Talan, mais bien avec vous et vos clients) dont voici les responsabilités principales:

      Aider à définir l'offre de service et la vision

      Participer aux activités de ventes lorsque reliés au AI

      Participer aux réseautage relié au AI

      Définir, designer et implementer des solutions d'automatisation robustes pour vos clients existants, et nouveaux.

      Je peux manager de petites équipes au besoins. Mais ma préférence reste le travail relié au AI et non l'administration ou le leadership. C'est une préférence flexible si ca peut aider la justifications des couts

      Je n'ai pas besoin de vous convaincre que ma présence dans les équipes est la plupart du temps très appréciée, et que je suis un parfait mélange de bibitte technique, leader et communicateur. 

 

En gros, je veux faire bénéficier Thinkmax du meilleur des mes skills, tout en trippant avec vous.

Je vous offre le tout a mon nouveau taux famille de 135$. Je me suis commis a Tarek pour du temps plein afin de stabiliser les TI pour une période de 6 semaines. Je commencerais donc à avoir de la disponibilité à partir de la fin février. 

J'aimerais savoir assez rapidement, votre intérêt afin que j'ai assez de temps pour me trouver autre chose dans le cas ou il y en aurait pas.

Ceci est ce que je suis prêt à offrir a Thinkmax/Talan, en attendant qu'on puisse repartir autre chose ensemble �

 

Lampron

 

 

 """

    test_instructions = "Focus on personal and professional relationships, and family connections."
    
    click.echo("Running test with sample biographical text...")
    process_input.callback(test_text, test_instructions)

    # Test document processing
    test_file = "C:/Users/lampr/OneDrive/Pictures/67673571642__3A378B89-2C90-4849-9EA2-3734DB41017C.jpg"
    if Path(test_file).exists():
        click.echo("\nTesting document processing...")
        process_document.callback(test_file)


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