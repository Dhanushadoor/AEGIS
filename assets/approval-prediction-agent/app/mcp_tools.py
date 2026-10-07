"""MCP tools indirection layer.

This module is the single entry point for loading MCP tools in application code.
It delegates to mcp_providers.agw.get_mcp_tools so that tests can patch this
module's get_mcp_tools name rather than the deeper implementation, keeping
test setup simple and application code stable.
"""

from mcp_providers.agw import get_mcp_tools

__all__ = ["get_mcp_tools"]
