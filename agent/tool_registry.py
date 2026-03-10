"""Tool registry with decorator-based registration + OpenAI function calling schema."""

from __future__ import annotations

import inspect
import json
import logging
from typing import Any, Callable, Coroutine, get_type_hints

logger = logging.getLogger(__name__)

# Type mapping for JSON Schema
_PY_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Coroutine]] = {}
        self._schemas: dict[str, dict[str, Any]] = {}

    def tool(
        self, name: str | None = None, description: str = ""
    ) -> Callable:
        """Decorator to register an async function as a callable tool."""
        def decorator(fn: Callable[..., Coroutine]) -> Callable:
            tool_name = name or fn.__name__
            tool_desc = description or (fn.__doc__ or "").strip()
            self._tools[tool_name] = fn
            self._schemas[tool_name] = self._build_schema(tool_name, tool_desc, fn)
            logger.info("Registered tool: %s", tool_name)
            return fn
        return decorator

    def _build_schema(self, name: str, description: str, fn: Callable) -> dict[str, Any]:
        """Build OpenAI function calling JSON Schema from function signature."""
        sig = inspect.signature(fn)
        hints = get_type_hints(fn)
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            ptype = hints.get(param_name, str)
            json_type = _PY_TO_JSON.get(ptype, "string")
            prop: dict[str, Any] = {"type": json_type}

            # Extract param description from docstring
            if fn.__doc__:
                for line in fn.__doc__.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith(f"{param_name}:"):
                        prop["description"] = stripped.split(":", 1)[1].strip()
                        break

            properties[param_name] = prop
            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def get_openai_tools(self) -> list[dict[str, Any]]:
        return list(self._schemas.values())

    async def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool and return result as JSON string."""
        fn = self._tools.get(tool_name)
        if not fn:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        try:
            result = await fn(**arguments)
            return json.dumps(result, default=str, ensure_ascii=False)
        except Exception as e:
            logger.exception("Tool %s failed", tool_name)
            return json.dumps({"error": str(e)})

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


registry = ToolRegistry()
