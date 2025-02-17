"""
Tests for the database manager module.
"""
import os
import pytest
from db.db_manager import Neo4jManager

def test_neo4j_manager_init():
    """Test Neo4j manager initialization."""
    manager = Neo4jManager()
    assert manager.uri == "bolt://localhost:7687"
    assert manager.user == "neo4j"
    assert manager.driver is None

def test_neo4j_manager_connect_without_password():
    """Test connection attempt without password."""
    manager = Neo4jManager()
    with pytest.raises(ValueError) as exc:
        manager.connect()
    assert "NEO4J_PASSWORD environment variable is required" in str(exc.value)

@pytest.mark.skipif(
    not os.getenv("NEO4J_PASSWORD"),
    reason="NEO4J_PASSWORD environment variable not set"
)
def test_neo4j_manager_connect():
    """Test database connection with valid credentials."""
    manager = Neo4jManager()
    try:
        manager.connect()
        assert manager.driver is not None
    finally:
        manager.close() 