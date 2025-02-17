# KnowledgeNexus – CLI-Based Entity Extraction Pipeline

## 1. Overview

We’ll build a simple CLI command that accepts two arguments:
1. **Content Input** (required) – could be:
   - A file path (e.g., `./some_file.txt`)
   - A URL (e.g., `https://example.com/something`)
   - Or plain text (e.g., `"John met Mary in Paris last Monday..."`)
2. **Instructions** (optional) – additional guidance for how to handle the extraction (e.g., `"focus on people's full names"`).

The pipeline will:
1. Detect the **input type** (file path, URL, or raw text).
2. If it’s a file or a URL, eventually we could parse those—but **for now, we’ll handle only raw text**.
3. Send the text (plus optional instructions) to an **OpenAI model** (GPT-4o or GPT-o3-mini) with a prompt instructing it to extract entities as **structured JSON**.
4. **Automatically parse** the returned JSON with **Pydantic’s built-in OpenAI integration**.
5. (Optionally) **Store** or update those extracted entities in **Neo4j** by calling our database layer.
6. Return or log the extracted entities as proof of concept.

---

## 2. Neo4j Module Setup

### Directory Structure:
```
knowledge-nexus/
└── db/
    ├── db_manager.py
    ├── entity_queries.py  # (optional) specific entity Cypher queries
```

### Cypher Queries for Entities:
All Cypher logic will be in `db/` to keep the database logic centralized.

```cypher
MERGE (e:Entity { name: $entity_name })
  ON CREATE SET e.created_at = timestamp()
  ON MATCH SET e.last_seen_at = timestamp()
```

---

## 3. Pydantic Schemas

### Centralized Schema Location
- **Use a dedicated `models/` folder** (e.g., `models/entities.py`).
- Ensures schemas are reusable across different modules.

### Entity Schema with OpenAI Compatibility
```python
from pydantic import BaseModel
from openai import OpenAI

class EntitySchema(BaseModel):
    name: str
    entity_type: str

class ExtractedEntities(BaseModel):
    entities: list[EntitySchema]

# Example of direct OpenAI structured output
response = OpenAI().chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "Extract entities from text."},
        {"role": "user", "content": "John met Mary in Paris."}
    ],
    response_model=ExtractedEntities  # Automatically parses response into Pydantic
)
```
This eliminates manual JSON validation and parsing!

---

## 4. OpenAI Integration & Structured Output

### Prompting Strategy
- **GPT-4o for analysis and structured output**
- **GPT-o3-mini for deep reasoning**
- Use OpenAI’s **Pydantic `response_model` feature**

### Example OpenAI Call
```python
from openai import OpenAI
from models.entities import ExtractedEntities

def extract_entities_from_text(text: str, instructions: str = "") -> ExtractedEntities:
    """
    Sends text (and optional instructions) to OpenAI for entity extraction.
    Uses structured output directly.
    """
    client = OpenAI()
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Extract entities from text."},
            {"role": "user", "content": text + "\n\n" + instructions if instructions else text}
        ],
        response_model=ExtractedEntities  # OpenAI handles Pydantic validation
    )
```

---

## 5. CLI Command

```python
import click
from cognitive.entity_extraction import extract_entities_from_text

def process_input(content: str) -> str:
    """Detects if input is a file path, URL, or raw text."""
    from pathlib import Path
    import re

    possible_path = Path(content)
    if possible_path.is_file():
        return possible_path.read_text(encoding='utf-8')
    elif re.match(r'^(http|https)://', content.strip()):
        click.echo("URL input not yet implemented.")
        return ""
    return content  # Assume raw text

@click.group()
def cli():
    pass

@cli.command()
@click.argument('content', type=str)
@click.option('--instructions', '-i', default='', help='Optional instructions.')
def extract_entities(content: str, instructions: str):
    """CLI command for entity extraction."""
    text = process_input(content)
    if not text:
        click.echo("Invalid input.")
        return
    
    entities = extract_entities_from_text(text, instructions)
    click.echo(f"Extracted Entities: {entities}")
```

This **fully automates entity extraction**, ensuring a robust, scalable approach for KnowledgeNexus!

