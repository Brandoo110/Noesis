"""Run a read-only Noesis web/API smoke against local services.

Start the backend and frontend first, then run:
python scripts/smoke_web.py --api http://127.0.0.1:8000 --web http://127.0.0.1:5173

If Vite picked another port, pass that URL with --web.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CheckStatus = Literal["passed", "failed", "skipped"]


@dataclass(frozen=True)
class WebSmokeArgs:
    api: str
    web: str
    timeout: float


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    status: CheckStatus
    detail: str


def parse_args(argv: Sequence[str] | None = None) -> WebSmokeArgs:
    parser = argparse.ArgumentParser(description="Run Noesis web/API smoke.")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--web", default="http://127.0.0.1:5173")
    parser.add_argument("--timeout", type=float, default=5.0)
    parsed = parser.parse_args(argv)
    return WebSmokeArgs(
        api=str(parsed.api).rstrip("/"),
        web=str(parsed.web).rstrip("/"),
        timeout=float(parsed.timeout),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    with httpx.Client(timeout=args.timeout, follow_redirects=True) as client:
        checks = run_smoke(client, args)
    print(format_checks(checks))
    return 0 if all(check.status != "failed" for check in checks) else 1


def run_smoke(client: httpx.Client, args: WebSmokeArgs) -> list[SmokeCheck]:
    checks: list[SmokeCheck] = []
    checks.append(_check_web_home(client, args.web))
    positions, position_check = _check_positions(client, args.api)
    checks.append(position_check)
    checks.append(_check_brief(client, args.api))
    checks.append(_check_overlaps(client, args.api))
    checks.extend(_check_latest_run_surfaces(client, args.api, positions))
    return checks


def format_checks(checks: Sequence[SmokeCheck]) -> str:
    return "\n".join(
        f"[{check.status.upper()}] {check.name}: {check.detail}"
        for check in checks
    )


def _check_web_home(client: httpx.Client, web_base: str) -> SmokeCheck:
    response = _safe_get(client, web_base)
    if isinstance(response, str):
        return SmokeCheck("web_home", "failed", response)
    if response.status_code != 200:
        return SmokeCheck("web_home", "failed", f"status={response.status_code}")
    if "Noesis" not in response.text:
        return SmokeCheck("web_home", "failed", "missing Noesis page marker")
    return SmokeCheck("web_home", "passed", "Noesis marker found")


def _check_positions(
    client: httpx.Client, api_base: str
) -> tuple[list[Mapping[str, Any]], SmokeCheck]:
    payload, error = _safe_json(client, api_base, "/positions")
    if error is not None:
        return [], SmokeCheck("positions", "failed", error)
    if not isinstance(payload, list):
        return [], SmokeCheck("positions", "failed", "payload is not a list")
    positions = [item for item in payload if isinstance(item, Mapping)]
    return positions, SmokeCheck("positions", "passed", f"count={len(positions)}")


def _check_brief(client: httpx.Client, api_base: str) -> SmokeCheck:
    payload, error = _safe_json(client, api_base, "/portfolio/brief")
    if error is not None:
        return SmokeCheck("portfolio_brief", "failed", error)
    if not isinstance(payload, Mapping):
        return SmokeCheck("portfolio_brief", "failed", "payload is not an object")
    positions = payload.get("positions")
    overlaps = payload.get("overlaps")
    run_health = payload.get("run_health")
    if not isinstance(positions, list) or not isinstance(overlaps, list):
        return SmokeCheck(
            "portfolio_brief",
            "failed",
            "missing positions/overlaps arrays",
        )
    if not isinstance(run_health, Mapping):
        return SmokeCheck(
            "portfolio_brief",
            "failed",
            "missing run_health object",
        )
    return SmokeCheck(
        "portfolio_brief",
        "passed",
        " ".join(
            [
                f"positions={len(positions)}",
                f"overlaps={len(overlaps)}",
                f"latest_runs={run_health.get('total_latest_runs')}",
            ]
        ),
    )


def _check_overlaps(client: httpx.Client, api_base: str) -> SmokeCheck:
    payload, error = _safe_json(client, api_base, "/portfolio/overlaps")
    if error is not None:
        return SmokeCheck("portfolio_overlaps", "failed", error)
    if not isinstance(payload, list):
        return SmokeCheck("portfolio_overlaps", "failed", "payload is not a list")
    return SmokeCheck("portfolio_overlaps", "passed", f"count={len(payload)}")


def _check_latest_run_surfaces(
    client: httpx.Client,
    api_base: str,
    positions: Sequence[Mapping[str, Any]],
) -> list[SmokeCheck]:
    position = next(
        (item for item in positions if isinstance(item.get("latest_run_id"), str)),
        None,
    )
    if position is None:
        return [
            SmokeCheck(
                "latest_run",
                "skipped",
                "no position with latest_run_id",
            )
        ]
    run_id = str(position["latest_run_id"])
    run_payload, run_error = _safe_json(client, api_base, f"/runs/{run_id}")
    if run_error is not None:
        return [SmokeCheck("latest_run", "failed", run_error)]
    if not isinstance(run_payload, Mapping):
        return [SmokeCheck("latest_run", "failed", "payload is not an object")]

    checks = [
        _run_detail_check(run_id, run_payload),
        _neighbors_check(client, api_base, position),
        _first_evidence_check(client, api_base, run_payload),
    ]
    return checks


def _run_detail_check(run_id: str, payload: Mapping[str, Any]) -> SmokeCheck:
    status = payload.get("status")
    if status not in {"running", "awaiting_confirmation", "completed", "failed"}:
        return SmokeCheck("latest_run", "failed", f"unexpected status={status}")
    evidence_count = len(payload.get("evidences", [])) if isinstance(payload.get("evidences"), list) else 0
    thesis_state = "present" if payload.get("thesis") is not None else "missing"
    return SmokeCheck(
        "latest_run",
        "passed",
        f"run_id={run_id} status={status} evidences={evidence_count} thesis={thesis_state}",
    )


def _neighbors_check(
    client: httpx.Client,
    api_base: str,
    position: Mapping[str, Any],
) -> SmokeCheck:
    entity = position.get("latest_run_entity")
    if not isinstance(entity, Mapping) or not isinstance(entity.get("id"), str):
        return SmokeCheck("neighbors", "skipped", "latest run entity missing")
    entity_id = str(entity["id"])
    payload, error = _safe_json(client, api_base, f"/entities/{entity_id}/neighbors")
    if error is not None:
        return SmokeCheck("neighbors", "failed", error)
    if not isinstance(payload, Mapping) or not isinstance(payload.get("edges"), list):
        return SmokeCheck("neighbors", "failed", "missing edges array")
    return SmokeCheck(
        "neighbors",
        "passed",
        f"entity_id={entity_id} edges={len(payload['edges'])}",
    )


def _first_evidence_check(
    client: httpx.Client,
    api_base: str,
    run_payload: Mapping[str, Any],
) -> SmokeCheck:
    evidences = run_payload.get("evidences")
    if not isinstance(evidences, list) or not evidences:
        return SmokeCheck("evidence_detail", "skipped", "run has no evidence")
    first = evidences[0]
    if not isinstance(first, Mapping) or not isinstance(first.get("id"), str):
        return SmokeCheck("evidence_detail", "failed", "first evidence id missing")
    evidence_id = str(first["id"])
    payload, error = _safe_json(client, api_base, f"/evidences/{evidence_id}")
    if error is not None:
        return SmokeCheck("evidence_detail", "failed", error)
    if not isinstance(payload, Mapping) or payload.get("id") != evidence_id:
        return SmokeCheck("evidence_detail", "failed", "evidence id mismatch")
    return SmokeCheck("evidence_detail", "passed", f"id={evidence_id}")


def _safe_json(
    client: httpx.Client, base_url: str, path: str
) -> tuple[Any | None, str | None]:
    response = _safe_get(client, _join_url(base_url, path))
    if isinstance(response, str):
        return None, response
    if response.status_code != 200:
        return None, f"status={response.status_code}"
    try:
        return response.json(), None
    except ValueError as exc:
        return None, f"invalid json: {exc}"


def _safe_get(client: httpx.Client, url: str) -> httpx.Response | str:
    try:
        return client.get(url)
    except httpx.HTTPError as exc:
        return str(exc)


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


if __name__ == "__main__":
    raise SystemExit(main())
