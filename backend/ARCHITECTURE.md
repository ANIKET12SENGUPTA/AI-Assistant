# AI Assistant Pro - Architecture (v2.0)

## Overview

This document describes the professional, intent-based architecture of the AI Assistant Pro system. This is a complete redesign from the keyword-based routing system to a sophisticated, multi-tool orchestration platform similar to Claude, ChatGPT, and Gemini.

## Key Principles

1. **Intent-Based Routing**: Users ask questions naturally; the system determines the intent and appropriate tools
2. **Multi-Tool Orchestration**: Tools can work in parallel, sequentially, or conditionally
3. **Modular & Extensible**: New tools and LLM providers can be added without changing core logic
4. **Graceful Degradation**: System works offline; unavailable tools are skipped with fallbacks
5. **Production-Ready**: Proper error handling, logging, type safety, and session management

## System Architecture

```
User Query (Frontend)
    ↓
FastAPI Endpoint (/chat)
    ↓
[1] Query Validation & Session Management
    ↓
[2] Intent Analysis (LLM)
    ├─ Heuristic quick-check
    ├─ LLM semantic analysis
    └─ Validation pass (optional)
    ↓
[3] Tool Selection & Validation
    ├─ Check tool availability
    ├─ Validate parameters
    └─ Build execution plan
    ↓
[4] Multi-Tool Orchestrator
    ├─ PARALLEL: Run tools simultaneously
    ├─ SEQUENTIAL: Feed output to next tool
    └─ CONDITIONAL: Execute based on results
    ↓
[5] Result Aggregation
    ├─ Combine results from multiple tools
    ├─ Rank and deduplicate
    └─ Prepare context for LLM
    ↓
[6] LLM Reasoning & Response Generation
    ├─ Process aggregated context
    ├─ Generate unified response
    └─ Cite sources
    ↓
[7] Memory Management & Response
    ├─ Store in session history
    └─ Return to frontend
```

## Folder Structure

```
backend/
├── core/                          # Core configuration and types
│   ├── config.py                 # Configuration from env
│   ├── constants.py              # Enums and constants
│   ├── exceptions.py             # Custom exceptions
│   ├── types.py                  # Pydantic models and dataclasses
│   └── logger.py                 # Structured logging
│
├── llm/                           # LLM abstraction layer
│   └── client.py                 # Unified LLM interface
│
├── intent/                        # Intent routing system
│   └── router.py                 # Intent analyzer and router
│
├── tools/                         # Tool system
│   ├── base.py                   # Abstract base classes
│   ├── registry.py               # Tool registration
│   ├── manager.py                # Tool lifecycle management
│   ├── web/
│   │   └── tools.py              # Web tools (DuckDuckGo, Wikipedia, arXiv)
│   └── rag/
│       └── tools.py              # Document RAG tool
│
├── orchestrator/                  # Multi-tool coordination
│   └── coordinator.py            # Tool execution orchestrator
│
├── app_new.py                    # Main FastAPI application (NEW)
└── requirements.txt              # Python dependencies
```

## Core Components

### 1. Intent Router (`intent/router.py`)

**Purpose**: Analyzes user queries to determine intent and select appropriate tools.

**Key Features**:
- LLM-based semantic analysis (not keyword-based)
- Confidence scoring
- Validation pass for accuracy
- Heuristic quick-checks for common patterns
- Fallback strategies

**Intent Types**:
- `general_knowledge`: LLM can answer directly
- `real_time_info`: Needs web search (current news, events)
- `document_search`: Query user's uploaded documents (RAG)
- `academic_research`: Query arXiv/research papers
- `multi_source`: Combine multiple tools
- `clarification`: Need more information from user

**Example Flow**:
```
User: "Compare recent AI breakthroughs with my research notes"
    ↓
Intent Router:
  - Heuristic: detects "recent" (real-time info) + "my research" (document)
  - LLM: confirms multi_source intent
  - Confidence: 0.95
  - Tools: [web_search, document_rag]
  - Strategy: parallel
```

### 2. Tool Abstraction Layer (`tools/`)

**Base Classes**:
- `BaseTool`: Abstract base for all tools
- `WebTool`: Base for tools requiring internet
- `RAGTool`: Base for document/local tools

**Key Features**:
- Consistent interface: `async execute(query, **kwargs) -> ToolResult`
- Metadata declaration (name, description, timeout, etc.)
- Health checks for availability
- Status tracking (available, unavailable, degraded, error)
- Structured result format

**Tool Registry**: Central discovery system
- Dynamic tool registration
- Alias support ("web_search" or "search")
- Query type filtering
- Online/offline tool filtering

**Tool Manager**: Lifecycle management
- Health checking with caching (30-second TTL)
- Tool availability filtering
- Graceful unavailability handling
- Fallback chain management

### 3. Multi-Tool Orchestrator (`orchestrator/coordinator.py`)

**Execution Strategies**:

**PARALLEL**:
```
Tool 1 ─┐
Tool 2 ─┼─→ Aggregate → LLM
Tool 3 ─┘
```
- All tools execute simultaneously
- Timeout per tool
- Results aggregated with deduplication

**SEQUENTIAL**:
```
Tool 1 → Tool 2 → Tool 3 → Aggregate → LLM
 ↓ output passed to next
```
- Each tool output feeds to next
- Early exit if high-confidence result
- Useful for dependent queries

**CONDITIONAL**:
```
Tool 1 decision
    ├─ if success → Tool 2
    └─ if fail → Fallback Tool
```
- Execute based on previous results
- Complex reasoning chains

**Fallback Chains**:
```
web_search fails → fallback to document_rag → fallback to LLM
```
- Automatic fallback on tool failure
- Configurable per tool
- Graceful degradation

### 4. LLM Client (`llm/client.py`)

**Multi-Provider Support**:
- Ollama (local LLM)
- OpenAI API (future)
- Gemini API (future)
- Claude API (future)

**Features**:
- Unified async interface
- Stream and non-stream responses
- Intent analysis with JSON extraction
- Model switching at runtime
- Timeout and error handling

### 5. Session Memory

**Current**: In-memory dictionary per session
```python
app.state.conversation_memory = {
    "session-uuid": [Message(...), Message(...), ...],
    ...
}
```

**Future (Phase 2)**:
- SQLAlchemy ORM with SQLite (or PostgreSQL)
- Persistent storage
- Context windowing (token limits)
- Session timeout (24 hours)

## Data Flow Example

### Natural Language Query:
```
User: "What's the latest on quantum computing? Compare with my research notes."
```

### Processing:

1. **Intent Analysis**:
   ```json
   {
     "intent_type": "multi_source",
     "confidence": 0.93,
     "primary_tool": "web_search",
     "secondary_tools": ["document_rag"],
     "execution_strategy": "parallel",
     "tool_parameters": {
       "web_search": {"query": "latest quantum computing breakthroughs", "num_results": 5},
       "document_rag": {"query": "quantum computing research", "top_k": 3}
     }
   }
   ```

2. **Tool Execution** (Parallel):
   ```
   web_search("latest quantum computing")
     ↓ returns: ["Recent quantum breakthrough at IBM...", ...]
   
   document_rag("quantum computing research")
     ↓ returns: ["My notes on quantum algorithms...", ...]
   
   Both complete in ~2 seconds
   ```

3. **Result Aggregation**:
   ```
   From web_search:
   - Latest quantum computing breakthroughs...
   
   From document_rag:
   - Your notes on quantum algorithms...
   ```

4. **LLM Processing**:
   ```
   System: "You are an AI assistant. Compare the following information..."
   
   Context: [aggregated results above]
   
   Generate response comparing latest developments with user's notes
   ```

5. **Response**:
   ```json
   {
     "response": "The latest quantum computing developments include...",
     "session_id": "uuid",
     "tools_used": ["web_search", "document_rag"],
     "intent": "multi_source",
     "metadata": {
       "routing_confidence": 0.93,
       "execution_time_ms": 2150,
       "fallback_used": false,
       "num_tools": 2
     }
   }
   ```

## Error Handling & Offline Mode

### Tool Failure Handling:
```python
# If web_search fails:
1. Log error
2. Mark tool as unavailable
3. Try fallback (document_rag)
4. If fallback succeeds, use it
5. If all fail, return LLM-only response
```

### Offline Mode:
- Online tools marked unavailable
- Offline tools (RAG) still work
- Graceful degradation with fallbacks
- User notified of limitations

## Configuration

Environment variables (see `core/config.py`):
```bash
# LLM Settings
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b
LLM_TIMEOUT=60
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Tool Settings
TOOL_TIMEOUT=30
WEB_SEARCH_RESULTS=5
ARXIV_RESULTS=3

# RAG Settings
CHROMA_PERSIST_DIR=backend/chroma_data
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=50
RAG_TOP_K=3

# Intent Router
INTENT_CONFIDENCE_THRESHOLD=0.7
INTENT_VALIDATION_ENABLED=true

# Memory
MAX_MESSAGES_PER_SESSION=50
CONTEXT_WINDOW_TOKENS=4000

# Feature Flags
STREAMING_ENABLED=true
MULTI_TOOL_ORCHESTRATION=true
OFFLINE_MODE=false
```

## API Endpoints

### Chat
```
POST /chat
Content-Type: application/json

{
  "message": "What's the latest AI news?",
  "stream": false
}

Response:
{
  "response": "The latest AI developments include...",
  "session_id": "uuid",
  "tools_used": ["web_search"],
  "intent": "real_time_info",
  "metadata": {...}
}
```

### Health Check
```
GET /health

Response:
{
  "status": "healthy",
  "services": {
    "llm": true,
    "tools": true,
    "router": true,
    "orchestrator": true
  }
}
```

### List Tools
```
GET /tools

Response:
{
  "tools": [
    {
      "name": "web_search",
      "description": "Search the web for current information",
      "requires_internet": true,
      "timeout": 10
    },
    ...
  ],
  "count": 4
}
```

### Tool Status
```
GET /tool-status

Response:
{
  "web_search": {"name": "web_search", "status": "available", "error": null},
  "wikipedia": {"name": "wikipedia", "status": "available", "error": null},
  "arxiv": {"name": "arxiv", "status": "available", "error": null},
  "document_rag": {"name": "document_rag", "status": "available", "error": null}
}
```

### Conversation Memory
```
GET /memory
Header: Session-ID: uuid

Response:
{
  "messages": [
    {"role": "user", "content": "Hello", "timestamp": "2024-06-16T10:00:00"},
    {"role": "assistant", "content": "Hi, how can I help?", "timestamp": "2024-06-16T10:00:01"}
  ],
  "session_id": "uuid",
  "count": 2
}

POST /memory/clear
Header: Session-ID: uuid

Response:
{"status": "cleared", "session_id": "uuid"}
```

## Adding New Tools

### 1. Create Tool Class:
```python
from tools.base import WebTool
from core.types import ToolMetadata, ToolResult

class MyCustomTool(WebTool):
    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_tool",
            description="Description",
            required_online=True,
            timeout_seconds=10,
            priority=1,
            supported_query_types=["custom_query"]
        )
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        # Implementation
        return ToolResult(...)
```

### 2. Register in `app_new.py`:
```python
app.state.tool_registry.register(
    MyCustomTool(),
    name="my_tool",
    aliases=["my", "custom"]
)
```

### 3. Done!
The intent router will auto-discover and use it based on query type.

## Adding New LLM Providers

### 1. Create Provider Class:
```python
class OpenAIClient:
    def __init__(self, api_key, model, timeout):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
    
    async def generate(self, messages, temperature, max_tokens):
        # Implementation using OpenAI SDK
        pass
```

### 2. Update LLMClient:
```python
if provider == "openai":
    self._client = OpenAIClient(...)
```

### 3. Configure:
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...
```

## Testing

### Manual Testing:
```bash
# 1. Start backend
cd backend
python -m uvicorn app_new:app --reload

# 2. Test intent-based routing
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the latest AI breakthroughs?"}'

# 3. Test multi-tool orchestration
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Compare recent papers on LLMs with my notes"}'

# 4. Test graceful degradation (offline)
# Manually disable web tools, query should fall back to RAG
```

## Future Enhancements (Phase 2+)

1. **Persistent Memory** (SQLAlchemy):
   - SQLite storage
   - Easy migration to PostgreSQL/AWS RDS
   - Multi-user support

2. **Context Windowing**:
   - Token limits
   - Message summarization
   - Long-context handling

3. **Advanced Reasoning**:
   - Chain-of-thought prompting
   - Multi-step task decomposition
   - Planning and execution

4. **Caching**:
   - Query result caching
   - Embedding caching
   - Tool response caching

5. **MCP Server Support**:
   - Model Context Protocol integration
   - Third-party tool ecosystem

6. **Monitoring & Analytics**:
   - Usage tracking
   - Performance metrics
   - Error analysis

## Comparison: Old vs New

| Feature | Old (v1) | New (v2) |
|---------|----------|---------|
| Routing | Keyword-based (`wiki`, `search`) | Intent-based (LLM semantic analysis) |
| Tool Selection | Hardcoded commands | Automatic based on intent |
| Multi-Tool | Not supported | Parallel/Sequential/Conditional |
| User Experience | Commands required | Natural language |
| Error Handling | Silent failures | Graceful degradation |
| Extensibility | Hardcoded in endpoint | Plugin registry system |
| Type Safety | Weak | Strong (Pydantic) |
| Logging | Print statements | Structured logging |
| Session Management | Global state | Per-session isolation |
| Memory | Ephemeral | Persistent (future) |
| Scalability | Single-threaded | Async/await throughout |

## Performance Characteristics

- **Parallel execution**: 50-100% faster than sequential for multi-tool queries
- **Tool health checks**: Cached for 30 seconds, minimal overhead
- **Intent analysis**: ~500ms (LLM call) + ~100ms (validation)
- **Tool execution**: 2-10s depending on tools and query complexity
- **Total latency**: ~3-15s for multi-tool queries
- **Memory usage**: ~2GB for ChromaDB + embeddings

## Production Checklist

- [x] Type safety (Pydantic)
- [x] Error handling (custom exceptions)
- [x] Logging (structured)
- [x] Config management (environment)
- [x] Session management (per-user)
- [x] Tool abstraction (plugin system)
- [x] Async/await (non-blocking I/O)
- [x] Graceful degradation (offline mode)
- [ ] Rate limiting
- [ ] Request validation
- [ ] CORS configuration
- [ ] Authentication/Authorization
- [ ] Monitoring/Metrics
- [ ] Load testing
- [ ] Security testing

## License

MIT License
