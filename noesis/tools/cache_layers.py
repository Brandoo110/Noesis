from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from noesis.tools.contracts import ToolCallRequest
from noesis.tools.execution import ToolExecutor


class ToolCacheLayers:
    def __init__(self, executor: ToolExecutor) -> None:
        self.executor = executor

    def webpage_content(
        self,
        run_id: str,
        url: str,
        fetch: Callable[[], str],
    ) -> str:
        return self.executor.execute(
            "webpage.fetch",
            ToolCallRequest(
                run_id=run_id,
                input_summary=f"url={url[:160]}",
                cache_key=f"webpage.fetch:{_hash(url)}",
            ),
            fetch,
            serialize_result=json.dumps,
            deserialize_result=_load_string,
            summarize_result=lambda result: f"text_chars={len(result)}",
        )

    def pdf_parse(
        self,
        run_id: str,
        source: str,
        parse: Callable[[], str],
    ) -> str:
        return self.executor.execute(
            "pdf.parse",
            ToolCallRequest(
                run_id=run_id,
                input_summary=f"source={source[:160]}",
                cache_key=f"pdf.parse:{_hash(source)}",
            ),
            parse,
            serialize_result=json.dumps,
            deserialize_result=_load_string,
            summarize_result=lambda result: f"text_chars={len(result)}",
        )

    def embedding_vector(
        self,
        run_id: str,
        text: str,
        embed: Callable[[], list[float]],
    ) -> list[float]:
        return self.executor.execute(
            "embedding.vector",
            ToolCallRequest(
                run_id=run_id,
                input_summary=f"text_hash={_hash(text)} chars={len(text)}",
                cache_key=f"embedding.vector:{_hash(text)}",
            ),
            embed,
            serialize_result=lambda result: json.dumps(result, sort_keys=True),
            deserialize_result=_load_float_list,
            summarize_result=lambda result: f"dims={len(result)}",
        )


def _load_string(raw: str) -> str:
    value = json.loads(raw)
    if not isinstance(value, str):
        raise ValueError("cached payload is not a string")
    return value


def _load_float_list(raw: str) -> list[float]:
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("cached payload is not a list")
    return [float(item) for item in value]


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
