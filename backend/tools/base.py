"""Base tool abstraction layer for all tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.types import ToolMetadata, ToolResult
from core.constants import ToolStatus


class BaseTool(ABC):
    """Abstract base class for all tools."""

    def __init__(self):
        """Initialize the tool."""
        self.metadata = self._define_metadata()
        self._status = ToolStatus.AVAILABLE
        self._error_message: Optional[str] = None

    @abstractmethod
    def _define_metadata(self) -> ToolMetadata:
        """Define tool metadata. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def execute(self, query: str, **kwargs) -> ToolResult:
        """
        Execute tool with given query.

        Args:
            query: Search/query string
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with structured output

        Must handle exceptions gracefully - never raise uncaught exceptions
        """
        pass

    async def health_check(self) -> ToolStatus:
        """
        Perform health check on tool.

        For web tools: Try simple query to check connectivity
        For RAG tools: Check ChromaDB connection
        For API tools: Check API key validity

        Returns:
            ToolStatus indicating current health
        """
        return self._status

    async def is_available(self) -> bool:
        """Check if tool is currently available."""
        return self._status == ToolStatus.AVAILABLE

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return self.metadata

    def supports_query_type(self, query_type: str) -> bool:
        """Check if tool supports given query type."""
        return query_type in self.metadata.supported_query_types

    def set_status(self, status: ToolStatus, error_message: str = None):
        """Update tool status."""
        self._status = status
        self._error_message = error_message

    def get_status(self) -> Dict[str, Any]:
        """Get current tool status."""
        return {
            "name": self.metadata.name,
            "status": self._status.value,
            "error": self._error_message,
            "available": self._status == ToolStatus.AVAILABLE,
        }


class WebTool(BaseTool):
    """Base class for web-based tools."""

    def __init__(self):
        """Initialize web tool."""
        super().__init__()
        self.requires_internet = True

    async def health_check(self) -> ToolStatus:
        """Check if web tool has internet connectivity."""
        # Default implementation - subclasses can override
        # This is a simple check that doesn't actually test connectivity
        if self._status == ToolStatus.UNAVAILABLE:
            return ToolStatus.UNAVAILABLE
        return ToolStatus.AVAILABLE


class RAGTool(BaseTool):
    """Base class for RAG/document-based tools."""

    def __init__(self):
        """Initialize RAG tool."""
        super().__init__()
        self.requires_internet = False

    async def health_check(self) -> ToolStatus:
        """Check if RAG tool is working."""
        # Default implementation - subclasses can override
        if self._status == ToolStatus.UNAVAILABLE:
            return ToolStatus.UNAVAILABLE
        return ToolStatus.AVAILABLE
