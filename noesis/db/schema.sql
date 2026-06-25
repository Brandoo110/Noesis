CREATE TABLE IF NOT EXISTS positions(
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, symbol TEXT NOT NULL,
  market TEXT NOT NULL, name TEXT, kind TEXT NOT NULL,
  qty REAL, cost_basis REAL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_positions_user ON positions(user_id);

CREATE TABLE IF NOT EXISTS entities(
  id TEXT PRIMARY KEY, node_type TEXT NOT NULL, name TEXT NOT NULL,
  aliases_json TEXT NOT NULL DEFAULT '[]', identifiers_json TEXT NOT NULL DEFAULT '{}',
  market TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_entities_symbol ON entities(market, name);

CREATE TABLE IF NOT EXISTS run_registry(
  id TEXT PRIMARY KEY, position_id TEXT, entity_id TEXT, node_kind TEXT NOT NULL,
  status TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_runs_position ON run_registry(position_id);

CREATE TABLE IF NOT EXISTS node_traces(
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL, node_name TEXT NOT NULL, entity_id TEXT,
  inputs_ref TEXT, outputs_ref TEXT, status TEXT NOT NULL, reason TEXT,
  fallback_used TEXT, model_id TEXT, evidence_ids_json TEXT,
  started_at TEXT NOT NULL, ended_at TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_traces_run ON node_traces(run_id);

CREATE TABLE IF NOT EXISTS evidences(
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL, entity_id TEXT, source TEXT NOT NULL,
  source_tier INTEGER NOT NULL, url TEXT, title TEXT, snippet TEXT NOT NULL,
  captured_at TEXT NOT NULL, published_at TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_evidences_run ON evidences(run_id);

CREATE TABLE IF NOT EXISTS intel_items(
  id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, run_id TEXT NOT NULL, source TEXT NOT NULL,
  source_tier INTEGER NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, url TEXT,
  published_at TEXT, sentiment_json TEXT NOT NULL, event_type TEXT NOT NULL,
  evidence_ids_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_intel_entity ON intel_items(entity_id);

CREATE TABLE IF NOT EXISTS theses(
  id TEXT PRIMARY KEY, position_id TEXT NOT NULL, run_id TEXT NOT NULL,
  summary TEXT NOT NULL, status TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_theses_position ON theses(position_id);

CREATE TABLE IF NOT EXISTS thesis_assumptions(
  id TEXT PRIMARY KEY, thesis_id TEXT NOT NULL, text TEXT NOT NULL, kind TEXT NOT NULL,
  evidence_ids_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_assumptions_thesis ON thesis_assumptions(thesis_id);

CREATE TABLE IF NOT EXISTS approvals(
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL, object_type TEXT NOT NULL, object_id TEXT NOT NULL,
  status TEXT NOT NULL, payload_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_approvals_run ON approvals(run_id);

CREATE VIRTUAL TABLE IF NOT EXISTS evidences_fts USING fts5(
  evidence_id UNINDEXED, snippet, title, content='');
