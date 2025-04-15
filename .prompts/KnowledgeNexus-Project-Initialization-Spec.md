KnowledgeNexus: Project Initialization Spec
This document outlines the initial project setup for KnowledgeNexus. We’ll create a skeleton repo structure with placeholders for core modules, tests, Docker files, and minimal configuration. Follow the KnowledgeNexus Coding Guidelines throughout.

1. Repository Structure
markdown
Copy
Edit
knowledge-nexus/
├── .cursor/
│   └── rules/
│       └── knowledge_nexus_guidelines.mdc
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── README.md
├── requirements.txt
├── main.py
├── knowledge/
│   ├── __init__.py
│   └── (placeholder for ingestion, storage logic)
├── nexus/
│   ├── __init__.py
│   └── (placeholder for core logic and processing)
├── cognitive/
│   ├── __init__.py
│   └── (placeholder for AI integrations with GPT-4o, GPT-4o-mini, GPT-o3-mini)
├── api/
│   ├── __init__.py
│   └── (placeholder for REST, CLI, or other interface code)
├── pipeline/
│   ├── __init__.py
│   └── pipeline.py
├── db/
│   ├── __init__.py
│   └── db_manager.py
├── cli/
│   ├── __init__.py
│   └── cli.py
└── tests/
    ├── __init__.py
    └── test_placeholder.py
Explanation
.cursor/rules/knowledge_nexus_guidelines.mdc

Contains our project-specific rules for Cursor AI.
.gitignore

Basic template for Python, ignoring virtual env folders, caches, etc.
docker-compose.yml & Dockerfile

Use Docker Compose to orchestrate services (e.g., app container, Neo4j container if needed).
The Dockerfile sets up a Python environment with dependencies.
pyproject.toml / requirements.txt

Python dependency management.
pyproject.toml (modern approach) or requirements.txt (traditional). You can keep both if you want easy pip installs.
main.py

Entry point for launching the application or bringing modules together.
Could watch a drop folder, start the CLI, or run any main loop logic.
knowledge/

Holds ingestion and storage logic (e.g., watchers, knowledge graph, etc.).
nexus/

Core processing and orchestration logic.
cognitive/

AI “brain” layer integrating GPT-4o for analysis, GPT-4o-mini for extraction, GPT-o3-mini for deep reasoning.
Direct usage of the OpenAI Python client, always returning structured outputs.
api/

Placeholder for REST, gRPC, or GraphQL endpoints, if we create them.
Or any other interface code (e.g., webhooks, local server).
pipeline/

pipeline.py processes newly ingested files or inputs, applies NLP, etc.
db/
Responsible for database connections, migrations, and queries.
db_manager.py might hold code for connecting to Neo4j and handling graph operations.
cli/
Contains CLI utilities (e.g., using click or argparse to add text/URL ingestions).
tests/
All unit tests; we aim for 90%+ coverage.
test_placeholder.py is an example file to kick off the test suite.
2. Placeholder Files
For each main folder (knowledge, nexus, cognitive, api, pipeline, db, cli), create an __init__.py and at least one Python file with minimal placeholder code and docstrings. For example:

python
Copy
Edit
# knowledge/__init__.py
\"\"\"Initializes the knowledge ingestion and storage layer.\"\"\"
python
Copy
Edit
# knowledge/watcher.py
\"\"\"
Placeholder for folder watcher logic using watchdog or similar.
\"\"\"
def watch_drop_folder():
    \"\"\"Monitor drop folder and invoke pipeline on new files.\"\"\"
    pass
Tip: Keep these placeholders minimal; we’ll flesh them out as we implement features.

3. Docker & Containerization
Dockerfile

Base on python:3.9-slim or similar.
Install system dependencies (e.g., build-essential, libpq-dev) if needed.
Copy project files, install packages from requirements.txt or pyproject.toml.
dockerfile
Copy
Edit
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD [\"python\", \"main.py\"]
docker-compose.yml

At minimum, define the app service.
If you plan to use a graph DB like Neo4j, add it here, mapping ports, volumes, etc.
yaml
Copy
Edit
version: '3.8'
services:
  knowledge-nexus:
    build: .
    container_name: knowledge-nexus-app
    volumes:
      - .:/app
    command: python main.py
    ports:
      - \"8080:8080\"

  # Example of adding Neo4j
  neo4j:
    image: neo4j:4.4
    container_name: knowledge-nexus-db
    environment:
      - NEO4J_AUTH=neo4j/secretpassword
    ports:
      - \"7474:7474\"
      - \"7687:7687\"
yaml
Copy
Edit

---

## 4. Basic Tests & CI Integration

1. **test_placeholder.py**  
   ```python
   def test_placeholder():
       assert True
Minimal test to confirm setup.
Pre-commit hooks (optional first step):

Could run black + flake8 + pytest.
CI/CD

If using GitHub Actions, define a workflow that builds Docker image, installs dependencies, and runs tests.
Example: .github/workflows/ci.yml to automate these checks.
5. Next Steps
Implement ingestion logic (folder watcher, CLI commands).
Set up the database (Neo4j or other graph DB).
Build out the pipeline with NLP, entity matching, etc.
Integrate GPT calls in cognitive/ for extraction and analysis.
Refine testing with real test cases.
Extend Docker config for dev vs. prod, add environment variables, secrets, and volumes as needed.
Keep referencing the KnowledgeNexus Coding Guidelines to ensure every step aligns with PEP8, logging, Pydantic models, and the rest of our best practices.