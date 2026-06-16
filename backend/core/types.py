"""Type definitions and Pydantic models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .constants import IntentType, ExecutionStrategy


# Pydantic Models for API


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., min_length=1, max_length=5000)
    stream: bool = Field(default=False)


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str
    session_id: str
    tools_used: List[str] = Field(default_factory=list)
    intent: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


class ToolResultModel(BaseModel):
    """Tool result model for API."""

    tool_name: str
    query: str
    success: bool
    data: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0
    confidence: float = 1.0


class RoutingDecisionModel(BaseModel):
    """Routing decision model."""

    intent_type: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    primary_tool: Optional[str] = None
    secondary_tools: List[str] = Field(default_factory=list)
    execution_strategy: ExecutionStrategy = ExecutionStrategy.PARALLEL
    tool_parameters: Dict[str, Dict] = Field(default_factory=dict)
    reasoning: str = ""


# Dataclasses for Internal Use


@dataclass
class Message:
    """Conversation message."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Context for routing decisions."""

    messages: List[Message] = field(default_factory=list)
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    def to_summary(self) -> str:
        """Convert conversation to summary string."""
        if not self.messages:
            return "No previous context"

        summary_lines = []
        for msg in self.messages[-10:]:  # Last 10 messages
            summary_lines.append(f"{msg.role}: {msg.content[:100]}...")

        return "\n".join(summary_lines)


@dataclass
class ToolMetadata:
    """Metadata about a tool."""

    name: str
    description: str
    required_online: bool
    timeout_seconds: int
    priority: int
    supported_query_types: List[str]
    cost_score: float = 1.0
    latency_score: float = 1.0
    example_queries: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "required_online": self.required_online,
            "timeout_seconds": self.timeout_seconds,
            "priority": self.priority,
            "supported_query_types": self.supported_query_types,
            "cost_score": self.cost_score,
            "latency_score": self.latency_score,
        }


@dataclass
class ToolResult:
    """Standard result format from any tool."""

    tool_name: str
    query: str
    success: bool
    data: Any = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    source_urls: Optional[List[str]] = None
    document_ids: Optional[List[str]] = None
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "tool_name": self.tool_name,
            "query": self.query,
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "confidence": self.confidence,
        }


@dataclass
class ToolSelection:
    """Selection of a tool to execute."""

    name: str
    query: str
    parameters: Dict = field(default_factory=dict)
    priority: int = 1
    fallback: bool = False


@dataclass
class ExecutionPlan:
    """Plan for executing multiple tools."""

    tools: List[ToolSelection] = field(default_factory=list)
    strategy: ExecutionStrategy = ExecutionStrategy.PARALLEL
    timeout_seconds: int = 60


@dataclass
class AggregatedContext:
    """Aggregated context from multiple tools."""

    context: str
    confidence: float = 0.5
    sources: List[str] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)


@dataclass
class OrchestratedResults:
    """Results from orchestrated tool execution."""

    results: List[ToolResult] = field(default_factory=list)
    combined_context: str = ""
    execution_time_ms: float = 0.0
    fallback_used: bool = False
    strategy_used: ExecutionStrategy = ExecutionStrategy.PARALLEL


@dataclass
class RoutingDecision:
    """Routing decision for a query."""

    intent_type: IntentType
    confidence: float
    tools: List[ToolSelection] = field(default_factory=list)
    execution_strategy: ExecutionStrategy = ExecutionStrategy.PARALLEL
    reasoning: str = ""
    ask_user: bool = False
    clarification_prompt: Optional[str] = None
    original_query: str = ""
