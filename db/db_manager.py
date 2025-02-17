"""
Database manager module for Neo4j operations.
"""
import logging
import os
from typing import Optional
from neo4j import GraphDatabase, Driver, Session

logger = logging.getLogger(__name__)

class Neo4jManager:
    """Manages Neo4j database connections and operations."""
    
    def __init__(self):
        """Initialize the Neo4j connection manager."""
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver: Optional[Driver] = None
        
    def connect(self) -> None:
        """Establish connection to Neo4j database."""
        if not self.password:
            raise ValueError("NEO4J_PASSWORD environment variable is required")
            
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            logger.info(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
            
    def close(self) -> None:
        """Close the database connection."""
        if self.driver:
            self.driver.close()
            logger.info("Closed Neo4j connection")
            
    def get_session(self) -> Session:
        """Get a new database session."""
        if not self.driver:
            raise RuntimeError("Database connection not initialized")
        return self.driver.session() 