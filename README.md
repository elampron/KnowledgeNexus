# KnowledgeNexus

An intelligent knowledge management and processing system that leverages AI for deep understanding and analysis of information.

## Project Structure

```
knowledge-nexus/
├── knowledge/        # Data ingestion and storage
├── nexus/           # Core logic and processing
├── cognitive/       # AI integrations (GPT-4o, GPT-4o-mini, GPT-o3-mini)
├── api/            # Interface layer
├── pipeline/       # Processing pipeline
├── db/             # Database operations
├── cli/            # Command-line interface
└── tests/          # Test suite
```

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/knowledge-nexus.git
   cd knowledge-nexus
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   .\venv\Scripts\activate   # Windows
   ```

3. Install dependencies:
   ```bash
   pip install poetry
   poetry install
   ```

4. Set up environment variables:
   Create a `.env` file with:
   ```
   OPENAI_API_KEY=your_openai_key
   NEO4J_PASSWORD=your_neo4j_password
   ```

5. Start the services:
   ```bash
   docker-compose up -d
   ```

## Development

- Run tests: `pytest`
- Format code: `black .`
- Lint code: `flake8`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.