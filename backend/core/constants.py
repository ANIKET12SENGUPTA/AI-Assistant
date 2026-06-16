"""Constants and enums for the AI Assistant."""

from enum import Enum
from typing import List


class IntentType(str, Enum):
    """User intent classification."""

    GENERAL_KNOWLEDGE = "general_knowledge"  # LLM can answer directly
    REAL_TIME_INFO = "real_time_info"  # Needs web search
    DOCUMENT_SEARCH = "document_search"  # Query user's documents (RAG)
    ACADEMIC_RESEARCH = "academic_research"  # Query arXiv
    MULTI_SOURCE = "multi_source"  # Combine multiple tools
    CLARIFICATION = "clarification"  # Ask for more info
    UNSUPPORTED = "unsupported"  # Cannot process


class ToolStatus(str, Enum):
    """Tool availability status."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    ERROR = "error"


class ExecutionStrategy(str, Enum):
    """Multi-tool execution strategy."""

    PARALLEL = "parallel"  # Execute all tools simultaneously
    SEQUENTIAL = "sequential"  # Execute one after another
    CONDITIONAL = "conditional"  # Execute based on previous results


class QueryType(str, Enum):
    """Types of queries tools can handle."""

    GENERAL = "general"
    WEB_SEARCH = "web_search"
    DOCUMENT = "document"
    RESEARCH = "research"
    WEATHER = "weather"
    NEWS = "news"
    CODE = "code"


# Intent Router
DEFAULT_INTENT_CONFIDENCE_THRESHOLD = 0.7
MAX_INTENT_ANALYSIS_RETRIES = 3

# Tools
TOOL_EXECUTION_TIMEOUT = 30
DEFAULT_WEB_SEARCH_RESULTS = 5
DEFAULT_ARXIV_RESULTS = 3
DEFAULT_WIKIPEDIA_SENTENCES = 3
DEFAULT_RAG_TOP_K = 3

# Memory
MAX_CONVERSATION_HISTORY = 50
DEFAULT_CONTEXT_WINDOW_TOKENS = 4000

# Tool health checks
TOOL_HEALTH_CHECK_TTL_SECONDS = 30
TOOL_HEALTH_CHECK_TIMEOUT = 5

# Error messages
ERROR_TOOL_OFFLINE = "Tool is currently offline or unavailable."
ERROR_NO_TOOLS_AVAILABLE = "No tools available to process this query."
ERROR_INTENT_ANALYSIS_FAILED = "Could not determine intent. Please rephrase your question."
ERROR_LLM_FAILED = "LLM service temporarily unavailable."
ERROR_ALL_TOOLS_FAILED = "All tools failed. Please try again later."

# System prompts
SYSTEM_PROMPT_BASE = """You are an intelligent AI assistant that helps answer questions using multiple sources of information.

You have access to:
- Your own knowledge
- Web search results for current information
- User's uploaded documents
- Academic papers from arXiv

When answering:
1. Use the most relevant information source
2. Cite your sources when using external tools
3. Be clear about what you found and what you didn't find
4. Ask for clarification if the question is ambiguous"""

INTENT_ANALYSIS_PROMPT = """Analyze the user's query and determine the best way to answer it.

Possible intent types:
- general_knowledge: The LLM can answer from its training data
- real_time_info: Needs current information (web search)
- document_search: Query refers to user's uploaded documents
- academic_research: Asking for research papers or academic info
- multi_source: Combine information from multiple sources
- clarification: Need more information from user

User query: "{query}"
Recent context: {context}

Respond ONLY with a valid JSON object (no markdown, no explanation):
{{
    "intent_type": "general_knowledge|real_time_info|document_search|academic_research|multi_source|clarification|unsupported",
    "confidence": 0.0-1.0,
    "primary_tool": "llm|web_search|document_rag|arxiv_search|none",
    "secondary_tools": ["..."],
    "execution_strategy": "parallel|sequential|conditional",
    "tool_parameters": {{"web_search": {{"query": "...", "num_results": 5}}}},
    "reasoning": "Brief explanation of why this intent and tools were selected"
}}"""

INTENT_VALIDATION_PROMPT = """Validate the following intent analysis. Is it correct and reasonable?

Analysis:
{analysis}

Respond with a JSON object:
{{
    "is_valid": true|false,
    "confidence_adjustment": -0.2 to 0.2,
    "feedback": "Explanation if invalid or suggestions"
}}"""

# Fallback chains
FALLBACK_CHAINS = {
    "web_search": ["document_rag", "llm"],
    "arxiv_search": ["document_rag", "web_search"],
    "document_rag": ["web_search"],
}

# Tool configurations
TOOL_CONFIGS = {
    "web_search": {
        "name": "web_search",
        "display_name": "Web Search",
        "description": "Search the web for current information",
        "required_online": True,
        "timeout_seconds": 10,
        "priority": 1,
        "supported_query_types": [
            QueryType.WEB_SEARCH,
            QueryType.NEWS,
            QueryType.GENERAL,
        ],
        "cost_score": 1.0,
        "latency_score": 1.5,
        "aliases": ["search", "ddg", "web"],
    },
    "wikipedia": {
        "name": "wikipedia",
        "display_name": "Wikipedia",
        "description": "Search Wikipedia for encyclopedia information",
        "required_online": True,
        "timeout_seconds": 8,
        "priority": 2,
        "supported_query_types": [QueryType.GENERAL, QueryType.RESEARCH],
        "cost_score": 0.5,
        "latency_score": 0.8,
        "aliases": ["wiki", "encyclopedia"],
    },
    "arxiv": {
        "name": "arxiv",
        "display_name": "arXiv",
        "description": "Search arXiv for research papers",
        "required_online": True,
        "timeout_seconds": 10,
        "priority": 1,
        "supported_query_types": [QueryType.RESEARCH, QueryType.ACADEMIC_RESEARCH],
        "cost_score": 1.0,
        "latency_score": 1.2,
        "aliases": ["arxiv_search", "papers", "research"],
    },
    "document_rag": {
        "name": "document_rag",
        "display_name": "Document Search",
        "description": "Search user's uploaded documents",
        "required_online": False,
        "timeout_seconds": 5,
        "priority": 1,
        "supported_query_types": [QueryType.DOCUMENT, QueryType.GENERAL],
        "cost_score": 0.3,
        "latency_score": 0.2,
        "aliases": ["documents", "rag", "my_docs", "my_documents"],
    },
}
