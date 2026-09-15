# literag

RAG (retrieval-only) system built with LangChain, VoyageAI embeddings, and Neo4j
vector store, exposed via FastAPI.

## Stack

- **FastAPI** — HTTP API
- **LangChain** — orchestration + relation-building agent
- **VoyageAI** — embeddings
- **LLM (OpenAI-compatible)** — entity extraction, chunk relations & QuestionToCypher (DeepSeek / OpenRouter)
- **Neo4j** — vector store + knowledge graph (5.11+)
- **Celery + Redis** — background relation building

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Docker](https://www.docker.com/) + Docker Compose (for Neo4j)
- A [VoyageAI](https://www.voyageai.com/) API key
- A [DeepSeek](https://platform.deepseek.com/) or [OpenRouter](https://openrouter.ai/) API key
- Redis (Celery broker/backend)
- Neo4j with the **APOC** plugin (required for the knowledge-graph import)

## Setup

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Configure environment:

   ```bash
   cp .env.example .env
   # then edit .env and fill in VOYAGE_API_KEY, LLM_API_KEY,
   # REDIS_URL, and Neo4j credentials
   ```

3. Start Neo4j (local Docker), or use Neo4j AuraDB (cloud).

   Local Docker:

   ```bash
   docker compose up -d
   ```

   Check it's running:

   ```bash
   docker compose ps
   docker compose logs -f neo4j
   ```

   AuraDB (skip the Docker step): set these in `.env` instead —

   ```bash
   NEO4J_URI=neo4j+s://<instance-id>.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=<your-password>
   NEO4J_DATABASE=<your-database-name>
   ```

   For AuraDB, `NEO4J_DATABASE` is usually your **instance name** (not `neo4j`).
   You can find it in the Aura Console → instance → **Query** → **Connection
   details**, or run `SHOW DATABASES;` in Neo4j Browser.

4. Run the API:

   ```bash
   uv run main.py
   ```

   or directly with uvicorn (dev mode, auto-reload):

   ```bash
   uv run uvicorn app.main:app --reload
   ```

   The API will be available at http://localhost:8000 and interactive docs at
   http://localhost:8000/docs.

5. Run the relation-building worker (requires Redis + APOC-enabled Neo4j):

   ```bash
   uv run celery -A app.core.celery_app worker --loglevel=info
   ```

   After uploading a document, a background task extracts entities and builds
   chunk-to-chunk relations. Progress is tracked via the document `status`
   field (`indexed` → `building` → `done` / `failed`).

## Useful commands

- Stop Neo4j:

  ```bash
  docker compose down
  ```

- Reset Neo4j data (wipe database):

  ```bash
  docker compose down -v
  ```

- Generate/refresh the OpenAPI spec file:

  ```bash
  uv run python -c "import json; from app.main import app; open('openapi.json','w').write(json.dumps(app.openapi(), indent=2))"
  ```

- View live OpenAPI spec while server is running: http://localhost:8000/openapi.json

## Endpoints

| Method | Path                                    | Purpose                                    |
| ------ | --------------------------------------- | ------------------------------------------ |
| POST   | `/documents/upload`                     | Upload a `.txt` file                       |
| POST   | `/query`                                | Retrieve relevant chunks (no LLM)          |
| GET    | `/documents`                            | List documents                             |
| GET    | `/documents/{document_id}`              | Document detail (incl. relation status)    |
| GET    | `/documents/{document_id}/chunks`       | All chunks of a document                   |
| GET    | `/documents/{document_id}/chunks/{id}`  | A single chunk of a document               |
| GET    | `/documents/{document_id}/relations`    | Chunk-to-chunk relations                   |
| POST   | `/documents/{document_id}/relations`    | Rebuild relations (Celery task)            |
| GET    | `/documents/{document_id}/entities`     | Extracted entities (knowledge graph)       |
| GET    | `/documents/{document_id}/entity-relations` | Entity-to-entity relations             |
| GET    | `/healthz`                              | Health check                               |

### Examples

Upload:

```bash
curl -F "file=@notes.txt" http://localhost:8000/documents/upload
```

Query:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "top_k": 4}'
```

List documents:

```bash
curl http://localhost:8000/documents
```

Get a document's chunks:

```bash
curl http://localhost:8000/documents/<document_id>/chunks
```
