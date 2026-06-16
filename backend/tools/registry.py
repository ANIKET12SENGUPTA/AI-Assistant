"""Tool registry for discovering and managing available tools."""

from typing import Dict, List, Optional

from core.constants import QueryType
from core.logger import setup_logger
from core.types import ToolMetadata

from .base import BaseTool

logger = setup_logger(__name__)


class ToolRegistry:
    """
    Central registry of all available tools.
    Supports dynamic tool registration for extensibility.
    """

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._tool_aliases: Dict[str, str] = {}  # Aliases map to tool names
        logger.info("Tool registry initialized")

    def register(
        self, tool: BaseTool, name: str, aliases: Optional[List[str]] = None
    ) -> None:
        """
        Register a tool with optional aliases.

        Args:
            tool: Tool instance to register
            name: Primary name for the tool
            aliases: Optional list of aliases for the tool
        """
        if name in self._tools:
            logger.warning(f"Overwriting tool: {name}")

        self._tools[name] = tool

        if aliases:
            for alias in aliases:
                self._tool_aliases[alias] = name
                logger.debug(f"Registered alias '{alias}' -> '{name}'")

        logger.info(f"Registered tool: {name}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Name of tool to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if name not in self._tools:
            return False

        del self._tools[name]

        # Remove aliases
        aliases_to_remove = [
            alias for alias, tool_name in self._tool_aliases.items() if tool_name == name
        ]
        for alias in aliases_to_remove:
            del self._tool_aliases[alias]

        logger.info(f"Unregistered tool: {name}")
        return True

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get tool by name or alias.

        Args:
            name: Tool name or alias

        Returns:
            Tool instance or None if not found
        """
        # Check if it's an alias
        resolved_name = self._tool_aliases.get(name, name)

        tool = self._tools.get(resolved_name)
        if tool is None and name != resolved_name:
            logger.debug(f"Tool not found: {name} (resolved to {resolved_name})")
        return tool

    def list_tools(self) -> List[ToolMetadata]:
        """
        List all registered tools.

        Returns:
            List of tool metadata
        """
        return [tool.get_metadata() for tool in self._tools.values()]

    def list_tool_names(self) -> List[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_tools_by_query_type(self, query_type: str) -> List[BaseTool]:
        """
        Get all tools supporting a query type.

        Args:
            query_type: Type of query to support

        Returns:
            List of tools supporting the query type
        """
        return [
            tool
            for tool in self._tools.values()
            if tool.supports_query_type(query_type)
        ]

    def get_tools_by_capability(self, capability: str) -> List[BaseTool]:
        """
        Get all tools by capability (query type).

        Args:
            capability: Capability/query type name

        Returns:
            List of tools with this capability
        """
        # Try to match as IntentType or QueryType
        supported_tools = []

        for tool in self._tools.values():
            metadata = tool.get_metadata()
            for query_type in metadata.supported_query_types:
                if capability.lower() in query_type.lower():
                    supported_tools.append(tool)
                    break

        return supported_tools

    def get_online_tools(self) -> List[BaseTool]:
        """
        Get all tools that require internet connectivity.

        Returns:
            List of online tools
        """
        return [
            tool for tool in self._tools.values() if tool.get_metadata().required_online
        ]

    def get_offline_tools(self) -> List[BaseTool]:
        """
        Get all tools that work offline.

        Returns:
            List of offline tools
        """
        return [
            tool
            for tool in self._tools.values()
            if not tool.get_metadata().required_online
        ]

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __repr__(self) -> str:
        """String representation."""
        tool_names = ", ".join(self._tools.keys())
        return f"ToolRegistry({len(self._tools)} tools: {tool_names})"
