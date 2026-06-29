# Noesis Web

Minimal local runbook for the M3 graph frontend.

## Prerequisites

Create or update the project root `.env` before running the backend. Real model
and search runs need these keys:

- `LIGHT_LLM_API_KEY`
- `DEEPSEEK_API_KEY`
- `RISK_LLM_API_KEY`
- `TAVILY_API_KEY`

Endpoint and model overrides are optional; the backend settings already provide
the current defaults for GLM, DeepSeek, and Gemini.

## Start Backend

From the repository root:

```bash
uvicorn noesis.api.app:app --reload --port 8000
```

The frontend dev proxy expects the API at `http://localhost:8000` by default.
For isolated smoke runs, override it with `NOESIS_API_PROXY_TARGET`.

## Start Frontend

From the repository root:

```bash
npm --prefix web run dev
```

Vite serves the app at `http://localhost:5173` and proxies these API prefixes to
the backend: `/positions`, `/runs`, `/entities`, `/evidences`, `/theses`, and
`/segments`.

## Verification

```bash
npm --prefix web test
npm --prefix web run build
```

The production build is emitted to `web/dist/`.

For a read-only live smoke after both local services are running:

```bash
python scripts/smoke_web.py --api http://127.0.0.1:8000 --web http://127.0.0.1:5173
```

If Vite starts on another port, pass that URL with `--web`.

For a visual smoke baseline after both local services are running:

```bash
python scripts/smoke_visual.py --web http://127.0.0.1:5173 --update-baseline
python scripts/smoke_visual.py --web http://127.0.0.1:5173
```

The first command refreshes `web/visual-baselines/`; the second compares the
current desktop and mobile screenshots against that baseline and checks the page
is nonblank with the key workspace text present.

For a real UI interaction flow smoke after both local services are running:

```bash
python scripts/smoke_ui_flow.py --web http://127.0.0.1:5173 --symbol AAPL
```

This opens the live app and exercises search, filters, launch status, graph
opening, stock detail, evidence drawer, report export, and portfolio Brief
export without creating new holdings or starting a new research run.

For an isolated mutating UI smoke, no existing services are required:

```bash
python scripts/smoke_ui_mutation.py
```

This starts a fixture FastAPI server and a Vite server against a temporary
SQLite database, then creates a holding, starts research, opens the graph and
stock detail, checks write API requests, and verifies the persisted run detail.

For a release evidence package after the backend and frontend are running:

```bash
python scripts/smoke_release.py --api http://127.0.0.1:8000 --web http://127.0.0.1:5173
```

This runs the read-only web/API smoke, local data quality report, visual smoke,
UI flow smoke, and isolated mutation smoke, then writes `summary.md`,
`manifest.json`, stdout/stderr, logs, and screenshots under
`output/release-smoke/<run-id>/`.

The release package records the quality report without failing the archive step.
Use `python scripts/quality_report.py --fail-on-blockers` for release gating,
or `--fail-on-warnings` for a stricter clean-room check.
