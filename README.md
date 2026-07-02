# Noesis

Noesis is a local-first investment intelligence agent. It starts from the
companies you own or watch, runs evidence-backed research, builds a lazy
industry graph, and helps you review a research thesis before exporting a
report.

Noesis is a research tool, not a trading product. It does not provide buy or
sell recommendations, target prices, price predictions, allocation advice, or
trade execution.

## What it does

- Add owned or watched companies, including private companies without tickers.
- Run an AI research workflow over company context, web evidence, and recent
  intelligence.
- Keep every user-visible claim tied to evidence IDs.
- Explore a supply-chain and industry graph with lazy one-hop expansion.
- Distinguish source-backed relationships from inferred relationships.
- Review thesis summaries and assumptions before confirmation.
- Inspect evidence in a dedicated drawer.
- Generate portfolio briefs and stock research reports as Markdown.
- Track run health, degraded paths, failed runs, and completed runs without a
  thesis.
- Run offline-friendly evaluation and release smoke checks.

## Product principles

Noesis is intentionally small and local-first:

- SQLite is the system of record.
- Chroma is used for local vector retrieval.
- SQLite FTS is used for local keyword search.
- LangGraph orchestrates the research workflow.
- FastAPI exposes the local API.
- React and React Flow power the web UI.
- The graph is a structure overview, not a place to cram every detail.
- Full relationship details live in a relationship list and evidence drawer.

## Architecture

```text
noesis/api/             FastAPI routes and response DTOs
noesis/db/              SQLite schema, migrations, thin repositories
noesis/eval/            Eval cases, metrics, reports, quality checks
noesis/graph/           LangGraph state, nodes, orchestration, tracing
noesis/tools/           LLM, search, retrieval, cache, and execution wrappers
prompts/                Prompt templates for graph nodes
scripts/                Smoke, quality, release, and eval scripts
tests/                  Pytest backend coverage
web/                    React + TypeScript frontend
```

Runtime data is local and ignored by Git:

- `noesis.db`
- `noesis.db.checkpoints`
- `.chroma/`
- `.env`
- `output/`

## Requirements

- Python 3.11+
- Node.js 18+
- npm

The backend dependencies are declared in `pyproject.toml`. The frontend
dependencies are declared in `web/package.json`.

## Quick start

Create a Python environment and install backend dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Install frontend dependencies:

```bash
npm --prefix web install
```

Create a local environment file:

```bash
cp .env.example .env
```

Fill in any providers you want to use. Empty keys are allowed for local
development, but real research needs search and model credentials.

Start the API:

```bash
uvicorn noesis.api.app:app --reload --host 127.0.0.1 --port 8000
```

Start the web app:

```bash
npm --prefix web run dev
```

Open:

- Web: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/docs

The API initializes and migrates the local SQLite database on demand.

## Configuration

Noesis reads configuration from `.env`.

| Variable | Purpose |
| --- | --- |
| `DEEPSEEK_API_KEY` | Strong synthesis model key |
| `DEEPSEEK_ENDPOINT` | Strong synthesis model endpoint |
| `DEEPSEEK_MODEL` | Strong synthesis model ID |
| `LIGHT_LLM_API_KEY` | Lightweight extraction model key |
| `LIGHT_ENDPOINT` | Lightweight extraction model endpoint |
| `LIGHT_MODEL` | Lightweight extraction model ID |
| `RISK_LLM_API_KEY` | Risk review model key |
| `RISK_ENDPOINT` | Risk review model endpoint |
| `RISK_MODEL` | Risk review model ID |
| `TAVILY_API_KEY` | Web search key |
| `NOESIS_DB_PATH` | SQLite database path |
| `CHROMA_DIR` | Local Chroma directory |

Never commit `.env`, database files, Chroma data, or smoke-test output.

## Running tests

Backend:

```bash
python -m pytest -q
```

Frontend:

```bash
npm --prefix web test
npm --prefix web run build
```

Useful smoke and quality scripts:

```bash
python scripts/eval.py --help
python scripts/quality_report.py --help
python scripts/smoke_web.py --help
python scripts/smoke_release.py --help
```

Some smoke scripts expect the local API and web app to be running.

## Core workflow

1. Add a holding or watched company.
2. Start a research run.
3. The API immediately returns a run ID and continues the LangGraph workflow in
   the background.
4. The UI polls run status and keeps old terminal results visible while a new
   run is refreshing.
5. Open the graph once the run is awaiting confirmation or completed.
6. Expand nodes lazily instead of pre-researching the entire graph.
7. Read full relationship details in the relationship list.
8. Open evidence from relationship rows, intelligence items, and thesis
   assumptions.
9. Confirm or revise the thesis.
10. Export Markdown reports or portfolio briefs.

## Grounding model

Noesis treats grounding as a product contract:

- User-visible claims must have evidence IDs.
- Source-backed graph edges must have evidence.
- Inferred graph edges must expose confidence and stay visibly labeled.
- Evidence snippets are stored separately from generated summaries.
- Risk review blocks investment advice language and unsupported thesis claims.

## API overview

Main resource areas:

- `/positions` - create and list owned or watched companies
- `/runs` - start and inspect research runs
- `/entities` - expand and inspect graph entities
- `/evidences` - read evidence records
- `/portfolio` - portfolio brief, run health, overlap, supply-chain views
- `/segments` - segment representatives
- `/theses` - confirm or update thesis records
- `/eval` - evaluation endpoints
- `/metrics` - agent operation metrics

See `http://127.0.0.1:8000/docs` after starting the API.

## Repository layout

```text
noesis/
  api/        FastAPI app and route handlers
  db/         SQLite schema, migrations, repository layer
  eval/       Evaluation cases, metrics, reports, quality checks
  graph/      LangGraph nodes, state, runner, grounding, tracing
  tools/      LLM, search, retrieval, cache, execution wrappers
prompts/      Prompt templates
scripts/      CLI utilities, smoke checks, release evidence package
tests/        Backend and integration tests
web/          React frontend
```

## Development notes

- Keep the project local-first and lightweight.
- Do not add Kafka, Flink, ClickHouse, Elasticsearch, Kubernetes, a graph
  database, or GraphRAG.
- Keep repository classes thin: SQL and row mapping only.
- Keep graph node behavior observable through traces and degraded states.
- Avoid real network calls in tests; use fakes or fixtures.
- Keep generated outputs out of Git.

## Roadmap

Potential next areas:

- Shared supplier exposure views.
- Correlation matrix and portfolio-level hidden risk.
- SEC and filing-oriented source adapters.
- PDF export.
- Change diff between research runs.
- Better local model routing.
- Stronger visual regression coverage.

## License

MIT. See `LICENSE`.
