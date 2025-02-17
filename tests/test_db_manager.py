"""
Tests for the database manager module.
"""
import os
import pytest
from db.db_manager import Neo4jManager

def test_neo4j_manager_init(monkeypatch):
    """Test Neo4j manager initialization with default values."""
    # Clear any existing environment variables
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_USER", raising=False)
    
    manager = Neo4jManager()
    assert manager.uri == "bolt://localhost:7687"
    assert manager.user == "neo4j"
    assert manager.password is None

def test_neo4j_manager_custom_init():
    """Test Neo4j manager initialization with custom values."""
    manager = Neo4jManager(
        uri="bolt://custom:7687",
        user="custom_user",
        password="custom_pass"
    )
    assert manager.uri == "bolt://custom:7687"
    assert manager.user == "custom_user"
    assert manager.password == "custom_pass"

def test_neo4j_manager_connect_no_password(monkeypatch):
    """Test connection attempt without password."""
    # Clear any existing environment variables
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    
    manager = Neo4jManager()
    with pytest.raises(ValueError, match="NEO4J_PASSWORD environment variable is required"):
        manager.connect()

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