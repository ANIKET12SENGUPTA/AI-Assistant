"""Tool manager for managing tool lifecycle and availability."""

import time
from typing import Dict, List, Optional, Tuple

from core.constants import IntentType, ToolStatus
from core.logger import setup_logger

from .base import BaseTool
from .registry import ToolRegistry

logger = setup_logger(__name__)


class ToolManager:
    """
    Manages tool lifecycle, availability, and health.
    """

    def __init__(self, registry: ToolRegistry, health_check_ttl: int = 30):
        """
        Initialize tool manager.

        Args:
            registry: ToolRegistry instance
            health_check_ttl: Time-to-live for health check cache (seconds)
        """
        self.registry = registry
        self._health_cache: Dict[str, Tuple[ToolStatus, float]] = {}
        self._cache_ttl = health_check_ttl
        logger.info(f"Tool manager initialized with {len(registry)} tools")

    async def get_available_tools(
        self, intent_type: Optional[IntentType] = None
    ) -> List[BaseTool]:
        """
        Get tools available for given intent type.
        Filters out unavailable tools (offline, errors, etc.).

        Args:
            intent_type: Optional intent type to filter by

        Returns:
            List of available tools
        """
        if intent_type:
            all_tools = self.registry.get_tools_by_capability(intent_type.value)
        else:
            all_tools = self.registry.list_tools()

        available = []
        for tool in all_tools:
            if await self._is_tool_healthy(tool):
                available.append(tool)

        logger.debug(f"Found {len(available)}/{len(all_tools)} available tools for {intent_type}")
        return available

    async def _is_tool_healthy(self, tool: BaseTool) -> bool:
        """
        Check if tool is healthy (with caching).
        Uses cache to avoid hammering tools with health checks.

        Args:
            tool: Tool to check

        Returns:
            True if tool is healthy, False otherwise
        """
        tool_name = tool.get_metadata().name

        # Check cache
        if tool_name in self._health_cache:
            status, timestamp = self._health_cache[tool_name]
            cache_age = time.time() - timestamp

            if cache_age < self._cache_ttl:
                is_healthy = status == ToolStatus.AVAILABLE
                logger.debug(f"Tool {tool_name} health (cached): {status.value}")
                return is_healthy

        # Perform actual health check
        try:
            status = await tool.health_check()
            self._health_cache[tool_name] = (status, time.time())

            is_healthy = status == ToolStatus.AVAILABLE
            logger.debug(f"Tool {tool_name} health check: {status.value}")
            return is_healthy
        except Exception as e:
            logger.error(f"Health check failed for {tool_name}: {e}")
            self._health_cache[tool_name] = (ToolStatus.ERROR, time.time())
            return False

    async def get_online_tools_available(self) -> List[BaseTool]:
        """
        Get all available online tools.

        Returns:
            List of available online tools
        """
        online_tools = self.registry.get_online_tools()
        available = []

        for tool in online_tools:
            if await self._is_tool_healthy(tool):
                available.append(tool)

        return available

    async def get_offline_tools(self) -> List[BaseTool]:
        """
        Get all offline tools (don't require internet).

        Returns:
            List of offline tools
        """
        return self.registry.get_offline_tools()

    def get_tool_status(self, tool_name: str) -> Optional[dict]:
        """
        Get status of a specific tool.

        Args:
            tool_name: Name of tool

        Returns:
            Tool status dict or None if not found
        """
        tool = self.registry.get_tool(tool_name)
        if tool:
            return tool.get_status()
        return None

    def get_all_tool_statuses(self) -> Dict[str, dict]:
        """
        Get status of all tools.

        Returns:
            Dictionary mapping tool names to status
        """
        statuses = {}
        for tool in self.registry.list_tools():
            tool_obj = self.registry.get_tool(tool.name)
            if tool_obj:
                statuses[tool.name] = tool_obj.get_status()
        return statuses

    def clear_health_cache(self) -> None:
        """Clear health check cache."""
        self._health_cache.clear()
        logger.info("Health check cache cleared")

    async def invalidate_tool_health(self, tool_name: str) -> None:
        """
        Invalidate health cache for a specific tool.

        Args:
            tool_name: Name of tool to invalidate
        """
        if tool_name in self._health_cache:
            del self._health_cache[tool_name]
            logger.info(f"Invalidated health cache for {tool_name}")

    async def mark_tool_unavailable(self, tool_name: str, reason: str = None) -> None:
        """
        Mark a tool as unavailable.

        Args:
            tool_name: Name of tool
            reason: Reason for unavailability
        """
        tool = self.registry.get_tool(tool_name)
        if tool:
            tool.set_status(ToolStatus.UNAVAILABLE, reason)
            self._health_cache[tool_name] = (ToolStatus.UNAVAILABLE, time.time())
            logger.warning(f"Marked {tool_name} as unavailable: {reason}")

    async def mark_tool_available(self, tool_name: str) -> None:
        """
        Mark a tool as available.

        Args:
            tool_name: Name of tool
        """
        tool = self.registry.get_tool(tool_name)
        if tool:
            tool.set_status(ToolStatus.AVAILABLE)
            # Invalidate cache to force health check
            await self.invalidate_tool_health(tool_name)
            logger.info(f"Marked {tool_name} as available")

    def __repr__(self) -> str:
        """String representation."""
        return f"ToolManager(registry={self.registry})"
