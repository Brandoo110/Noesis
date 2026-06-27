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

The frontend dev proxy expects the API at `http://localhost:8000`.

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
