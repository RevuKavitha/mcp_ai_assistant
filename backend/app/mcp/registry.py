from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


ToolFn = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: ToolFn


class ToolRegistry:
    """MCP-style tool registry where tools are registered as callable units."""

    def __init__(self) -> None:
        self._tools: Dict[str, MCPTool] = {}

    def register(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> MCPTool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered")
        return self._tools[name]

    def list_for_prompt(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for name, tool in self._tools.items()
        }
