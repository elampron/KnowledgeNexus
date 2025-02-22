from db.db_manager import Neo4jManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_apoc():
    """Check if APOC is available in the Neo4j instance."""
    db_manager = Neo4jManager()
    try:
        db_manager.connect()
        with db_manager.get_session() as session:
            # Try to list all APOC procedures
            result = session.run("CALL dbms.procedures() YIELD name WITH name WHERE name STARTS WITH 'apoc' RETURN name")
            procedures = [record["name"] for record in result]
            
            if procedures:
                logger.info("APOC is installed! Found %d APOC procedures:", len(procedures))
                for proc in procedures[:5]:  # Show first 5 procedures
                    logger.info("- %s", proc)
                if len(procedures) > 5:
                    logger.info("... and %d more", len(procedures) - 5)
            else:
                logger.warning("No APOC procedures found. APOC might not be installed.")
                
            # Specifically check for apoc.coll.union
            result = session.run("CALL dbms.procedures() YIELD name WITH name WHERE name = 'apoc.coll.union' RETURN name")
            if list(result):
                logger.info("apoc.coll.union is available!")
            else:
                logger.warning("apoc.coll.union is NOT available!")
                
    except Exception as e:
        logger.error("Error checking APOC: %s", str(e))
    finally:
        db_manager.close()

if __name__ == "__main__":
    check_apoc() 