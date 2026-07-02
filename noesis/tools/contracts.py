from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Literal

from pydantic import BaseModel, Field

PermissionLevel = Literal["local", "network", "model", "storage"]
CacheMode = Literal["none", "ttl"]


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=1, ge=1)
    backoff_seconds: float = Field(default=0, ge=0)


class CachePolicy(BaseModel):
    mode: CacheMode = "none"
    ttl_seconds: int | None = Field(default=None, ge=1)


class ToolDescriptor(BaseModel):
    name: str
    description: str
    input_schema: Mapping[str, object]
    output_schema: Mapping[str, object]
    permission_level: PermissionLevel
    timeout_seconds: float = Field(gt=0)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    cache_policy: CachePolicy = Field(default_factory=CachePolicy)


class ToolCallRequest(BaseModel):
    run_id: str
    trace_id: str | None = None
    input_summary: str | None = None
    cache_key: str | None = None
    token_input: int = Field(default=0, ge=0)
    token_output: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0, ge=0)


class ToolUsage(BaseModel):
    token_input: int = Field(default=0, ge=0)
    token_output: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0, ge=0)


class ToolRegistry:
    def __init__(self, descriptors: Iterable[ToolDescriptor] | None = None) -> None:
        self._descriptors = {item.name: item for item in descriptors or []}

    def register(self, descriptor: ToolDescriptor) -> None:
        self._descriptors[descriptor.name] = descriptor

    def get(self, name: str) -> ToolDescriptor:
        descriptor = self._descriptors.get(name)
        if descriptor is None:
            raise KeyError(f"unknown tool: {name}")
        return descriptor

    def list(self) -> list[ToolDescriptor]:
        return list(self._descriptors.values())


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ToolDescriptor(
                name="search.tavily",
                description="Tavily web/news search for stock research evidence",
                input_schema={"type": "object", "required": ["query"]},
                output_schema={"type": "array", "items": {"type": "object"}},
                permission_level="network",
                timeout_seconds=20,
                retry_policy=RetryPolicy(max_attempts=2),
                cache_policy=CachePolicy(mode="ttl", ttl_seconds=86_400),
            ),
            ToolDescriptor(
                name="llm.light",
                description="Lightweight structured LLM call",
                input_schema={"type": "object", "required": ["prompt"]},
                output_schema={"type": "object"},
                permission_level="model",
                timeout_seconds=30,
                retry_policy=RetryPolicy(max_attempts=1),
                cache_policy=CachePolicy(mode="none"),
            ),
            ToolDescriptor(
                name="llm.synth",
                description="Synthesis LLM call",
                input_schema={"type": "object", "required": ["prompt"]},
                output_schema={"type": "object"},
                permission_level="model",
                timeout_seconds=60,
                retry_policy=RetryPolicy(max_attempts=1),
                cache_policy=CachePolicy(mode="none"),
            ),
            ToolDescriptor(
                name="llm.risk",
                description="Risk review LLM call",
                input_schema={"type": "object", "required": ["prompt"]},
                output_schema={"type": "object"},
                permission_level="model",
                timeout_seconds=60,
                retry_policy=RetryPolicy(max_attempts=1),
                cache_policy=CachePolicy(mode="none"),
            ),
            ToolDescriptor(
                name="retrieval.evidence",
                description="Local FTS/Chroma evidence retrieval",
                input_schema={"type": "object", "required": ["query", "run_id"]},
                output_schema={"type": "array", "items": {"type": "object"}},
                permission_level="local",
                timeout_seconds=5,
                retry_policy=RetryPolicy(max_attempts=1),
                cache_policy=CachePolicy(mode="ttl", ttl_seconds=3_600),
            ),
            ToolDescriptor(
                name="webpage.fetch",
                description="Fetch and cache raw webpage content",
                input_schema={"type": "object", "required": ["url"]},
                output_schema={"type": "string"},
                permission_level="network",
                timeout_seconds=20,
                retry_policy=RetryPolicy(max_attempts=2),
                cache_policy=CachePolicy(mode="ttl", ttl_seconds=86_400),
            ),
            ToolDescriptor(
                name="pdf.parse",
                description="Parse and cache PDF text content",
                input_schema={"type": "object", "required": ["source"]},
                output_schema={"type": "string"},
                permission_level="local",
                timeout_seconds=20,
                retry_policy=RetryPolicy(max_attempts=1),
                cache_policy=CachePolicy(mode="ttl", ttl_seconds=604_800),
            ),
            ToolDescriptor(
                name="embedding.vector",
                description="Generate and cache embedding vectors",
                input_schema={"type": "object", "required": ["text"]},
                output_schema={"type": "array", "items": {"type": "number"}},
                permission_level="local",
                timeout_seconds=10,
                retry_policy=RetryPolicy(max_attempts=1),
                cache_policy=CachePolicy(mode="ttl", ttl_seconds=604_800),
            ),
        ]
    )
