from __future__ import annotations

import hashlib
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Literal, TypeVar
from uuid import uuid4

from noesis.db.connection import with_tx
from noesis.db.models import ToolCacheEntryRow, ToolInvocationRow
from noesis.tools.contracts import (
    ToolCallRequest,
    ToolDescriptor,
    ToolRegistry,
    ToolUsage,
)

ResultT = TypeVar("ResultT")


class ToolExecutionError(RuntimeError):
    def __init__(self, message: str, *, original: Exception | None = None) -> None:
        super().__init__(message)
        self.original = original


class ToolExecutor:
    def __init__(
        self,
        *,
        conn: sqlite3.Connection,
        registry: ToolRegistry,
        now: Callable[[], str],
    ) -> None:
        self.conn = conn
        self.registry = registry
        self.now = now

    def execute(
        self,
        tool_name: str,
        request: ToolCallRequest,
        action: Callable[[], ResultT],
        *,
        serialize_result: Callable[[ResultT], str] | None = None,
        deserialize_result: Callable[[str], ResultT] | None = None,
        summarize_result: Callable[[ResultT], str] | None = None,
        usage_result: Callable[[ResultT], ToolUsage] | None = None,
    ) -> ResultT:
        descriptor = self.registry.get(tool_name)
        cached = self._read_cache(descriptor, request, deserialize_result)
        if cached is not None:
            self._record_invocation(
                descriptor,
                request,
                status="success",
                output_summary="cache hit",
                cache_hit=True,
                retry_count=0,
                latency_ms=0,
                error_message=None,
            )
            return cached

        started = time.monotonic()
        attempts = descriptor.retry_policy.max_attempts
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                result = action()
                payload_json = _serialize(serialize_result, result)
                self._write_cache(descriptor, request, payload_json)
                self._record_invocation(
                    descriptor,
                    request,
                    status="success",
                    output_summary=_summary(summarize_result, result),
                    cache_hit=False,
                    retry_count=attempt,
                    latency_ms=_elapsed_ms(started),
                    error_message=None,
                    usage=_usage(usage_result, result),
                )
                return result
            except Exception as exc:
                last_error = exc
                if attempt < attempts - 1 and descriptor.retry_policy.backoff_seconds > 0:
                    time.sleep(descriptor.retry_policy.backoff_seconds)

        self._record_invocation(
            descriptor,
            request,
            status="failed",
            output_summary=None,
            cache_hit=False,
            retry_count=max(0, attempts - 1),
            latency_ms=_elapsed_ms(started),
            error_message=str(last_error) if last_error is not None else "tool failed",
        )
        raise ToolExecutionError("tool execution failed", original=last_error)

    def _read_cache(
        self,
        descriptor: ToolDescriptor,
        request: ToolCallRequest,
        deserialize_result: Callable[[str], ResultT] | None,
    ) -> ResultT | None:
        if (
            descriptor.cache_policy.mode == "none"
            or request.cache_key is None
            or deserialize_result is None
        ):
            return None
        row = self.conn.execute(
            """
            SELECT * FROM tool_cache_entries
            WHERE cache_key = ?
            LIMIT 1
            """,
            (request.cache_key,),
        ).fetchone()
        if row is None:
            return None
        entry = ToolCacheEntryRow.model_validate(dict(row))
        if entry.payload_json is None or _is_expired(entry, self.now()):
            return None
        result = deserialize_result(entry.payload_json)
        with with_tx(self.conn):
            self.conn.execute(
                """
                UPDATE tool_cache_entries
                SET hit_count = hit_count + 1,
                    last_hit_at = ?,
                    updated_at = ?
                WHERE cache_key = ?
                """,
                (self.now(), self.now(), request.cache_key),
            )
        return result

    def _write_cache(
        self,
        descriptor: ToolDescriptor,
        request: ToolCallRequest,
        payload_json: str | None,
    ) -> None:
        if (
            descriptor.cache_policy.mode == "none"
            or request.cache_key is None
            or payload_json is None
        ):
            return
        row = _cache_row(descriptor, request, payload_json, self.now())
        with with_tx(self.conn):
            self.conn.execute(
                """
                INSERT INTO tool_cache_entries(
                  id, cache_key, tool_name, cache_policy, ttl_seconds, expires_at,
                  hit_count, last_hit_at, payload_hash, payload_json, created_at,
                  updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                  tool_name = excluded.tool_name,
                  cache_policy = excluded.cache_policy,
                  ttl_seconds = excluded.ttl_seconds,
                  expires_at = excluded.expires_at,
                  hit_count = excluded.hit_count,
                  last_hit_at = excluded.last_hit_at,
                  payload_hash = excluded.payload_hash,
                  payload_json = excluded.payload_json,
                  updated_at = excluded.updated_at
                """,
                (
                    row.id,
                    row.cache_key,
                    row.tool_name,
                    row.cache_policy,
                    row.ttl_seconds,
                    row.expires_at,
                    row.hit_count,
                    row.last_hit_at,
                    row.payload_hash,
                    row.payload_json,
                    row.created_at,
                    row.updated_at,
                ),
            )

    def _record_invocation(
        self,
        descriptor: ToolDescriptor,
        request: ToolCallRequest,
        *,
        status: Literal["success", "failed"],
        output_summary: str | None,
        cache_hit: bool,
        retry_count: int,
        latency_ms: int,
        error_message: str | None,
        usage: ToolUsage | None = None,
    ) -> None:
        row = _invocation_row(
            descriptor,
            request,
            status=status,
            output_summary=output_summary,
            cache_hit=cache_hit,
            retry_count=retry_count,
            latency_ms=latency_ms,
            error_message=error_message,
            usage=usage or ToolUsage(),
            now=self.now(),
        )
        with with_tx(self.conn):
            self.conn.execute(
                """
                INSERT INTO tool_invocations(
                  id, run_id, trace_id, tool_name, status, permission_level,
                  input_summary, output_summary, error_message, cache_key,
                  cache_hit, retry_count, latency_ms, token_input, token_output,
                  estimated_cost_usd, started_at, ended_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.id,
                    row.run_id,
                    row.trace_id,
                    row.tool_name,
                    row.status,
                    row.permission_level,
                    row.input_summary,
                    row.output_summary,
                    row.error_message,
                    row.cache_key,
                    int(row.cache_hit),
                    row.retry_count,
                    row.latency_ms,
                    row.token_input,
                    row.token_output,
                    row.estimated_cost_usd,
                    row.started_at,
                    row.ended_at,
                    row.created_at,
                ),
            )


def _cache_row(
    descriptor: ToolDescriptor,
    request: ToolCallRequest,
    payload_json: str,
    now: str,
) -> ToolCacheEntryRow:
    return ToolCacheEntryRow(
        id=f"cache-{uuid4().hex}",
        cache_key=request.cache_key or "",
        tool_name=descriptor.name,
        cache_policy=descriptor.cache_policy.mode,
        ttl_seconds=descriptor.cache_policy.ttl_seconds,
        expires_at=_expires_at(now, descriptor.cache_policy.ttl_seconds),
        hit_count=0,
        last_hit_at=None,
        payload_hash=_hash_payload(payload_json),
        payload_json=payload_json,
        created_at=now,
        updated_at=now,
    )


def _invocation_row(
    descriptor: ToolDescriptor,
    request: ToolCallRequest,
    *,
    status: Literal["success", "failed"],
    output_summary: str | None,
    cache_hit: bool,
    retry_count: int,
    latency_ms: int,
    error_message: str | None,
    usage: ToolUsage,
    now: str,
) -> ToolInvocationRow:
    return ToolInvocationRow(
        id=f"tool-call-{uuid4().hex}",
        run_id=request.run_id,
        trace_id=request.trace_id,
        tool_name=descriptor.name,
        status=status,
        permission_level=descriptor.permission_level,
        input_summary=request.input_summary,
        output_summary=output_summary,
        error_message=error_message,
        cache_key=request.cache_key,
        cache_hit=cache_hit,
        retry_count=retry_count,
        latency_ms=latency_ms,
        token_input=request.token_input + usage.token_input,
        token_output=request.token_output + usage.token_output,
        estimated_cost_usd=request.estimated_cost_usd + usage.estimated_cost_usd,
        started_at=now,
        ended_at=now,
        created_at=now,
    )


def _serialize(
    serialize_result: Callable[[ResultT], str] | None,
    result: ResultT,
) -> str | None:
    return serialize_result(result) if serialize_result is not None else None


def _summary(
    summarize_result: Callable[[ResultT], str] | None,
    result: ResultT,
) -> str | None:
    return summarize_result(result) if summarize_result is not None else None


def _usage(
    usage_result: Callable[[ResultT], ToolUsage] | None,
    result: ResultT,
) -> ToolUsage:
    return usage_result(result) if usage_result is not None else ToolUsage()


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


def _hash_payload(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _expires_at(now: str, ttl_seconds: int | None) -> str | None:
    if ttl_seconds is None:
        return None
    expires = _parse_iso(now).astimezone(UTC) + timedelta(seconds=ttl_seconds)
    return expires.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_expired(entry: ToolCacheEntryRow, now: str) -> bool:
    if entry.expires_at is None:
        return False
    return _parse_iso(entry.expires_at) <= _parse_iso(now)


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
