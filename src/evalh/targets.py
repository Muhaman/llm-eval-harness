"""Targets: the system under test, called once per case."""

import asyncio
import importlib
import inspect
import json
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

import httpx

from evalh.config import ConfigError, Input, TargetSpec

Target = Callable[[Input], Awaitable[str]]


def _stringify(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, default=str)


def _load_python_function(ref: str, base_dir: Path | None) -> Callable[[Input], Any]:
    module_name, _, attr = ref.partition(":")
    if not module_name or not attr:
        raise ConfigError(f"python target ref must be 'module:function', got {ref!r}")
    if base_dir is not None and str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ConfigError(f"cannot import target module {module_name!r}: {exc}") from exc
    function = getattr(module, attr, None)
    if not callable(function):
        raise ConfigError(f"target {ref!r}: {attr!r} is not a callable in {module_name!r}")
    return cast(Callable[[Input], Any], function)


def _python_target(function: Callable[[Input], Any]) -> Target:
    async def call(value: Input) -> str:
        if inspect.iscoroutinefunction(function):
            return _stringify(await function(value))
        # Sync targets run in a worker thread so they cannot block the event loop.
        return _stringify(await asyncio.to_thread(function, value))

    return call


def _http_target(client: httpx.AsyncClient, url: str) -> Target:
    async def call(value: Input) -> str:
        response = await client.post(url, json={"input": value})
        response.raise_for_status()
        try:
            body = response.json()
        except ValueError:
            return response.text
        if isinstance(body, dict) and isinstance(body.get("output"), str):
            return str(body["output"])
        return response.text

    return call


@asynccontextmanager
async def open_target(spec: TargetSpec, base_dir: Path | None = None) -> AsyncIterator[Target]:
    if spec.type == "python":
        yield _python_target(_load_python_function(spec.ref, base_dir))
        return
    async with httpx.AsyncClient(timeout=None) as client:
        yield _http_target(client, spec.ref)
