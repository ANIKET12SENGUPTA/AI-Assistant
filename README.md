# AI Assistant Pro v2.0

**Intent-based multi-tool AI assistant** with automatic routing (like ChatGPT, Claude, Gemini)

Users ask naturally: **"What's the latest AI news? Compare with my research."**
The system automatically routes to appropriate tools, executes them, and generates a unified response.

✨ **No commands needed. No "wiki", "search", "arxiv" prefixes. Just natural language.**

## 🚀 Quick Start

```bash
# 1. Install
cd backend
pip install -r requirements.txt
ollama pull qwen3:8b  # Ensure Ollama model is available

# 2. Run
python -m uvicorn app:app --reload
# Backend: http://localhost:8000

# 3. Test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the latest AI breakthroughs?"}'
```

## 🎯 Key Features

✅ **Intent-Based Routing** - LLM analyzes what you're asking for
✅ **Automatic Tool Selection** - Uses web search, documents, papers, or just LLM
✅ **Multi-Tool Execution** - Parallel/sequential/conditional coordination
✅ **No Commands** - Natural language only
✅ **Works Offline** - Local documents still work without internet
✅ **Production Ready** - Type-safe, modular, professional architecture

## 📁 Architecture

```
backend/
├── app.py                      # Main application (self-contained)
├── ARCHITECTURE.md             # Detailed design documentation
│
├── core/                       # Core types and configs
│   ├── types.py               # Pydantic models
│   ├── constants.py           # Enums and prompts
│   └── exceptions.py          # Custom exceptions
│
├── intent/                     # Intent analysis
│   └── router.py              # LLM-based routing
│
├── tools/                      # Tool system
│   ├── base.py                # Tool abstraction
│   ├── registry.py            # Tool discovery
│   ├── manager.py             # Tool lifecycle
│   ├── web/tools.py           # Web tools (DuckDuckGo, Wikipedia, arXiv)
│   └── rag/tools.py           # Document search (ChromaDB)
│
├── orchestrator/              # Multi-tool execution
│   └── coordinator.py         # Tool orchestration
│
├── llm/                        # LLM abstraction
│   └── client.py              # Ollama client
│
└── requirements.txt           # Dependencies
```

## 💡 How It Works

**Example**: "Compare recent quantum papers with my research"

```
1. Intent Router (LLM analysis)
   → Detects: multi_source intent
   → Confidence: 0.95
   → Tools: arxiv_search + document_rag

2. Tool Orchestrator (parallel execution)
   → arXiv: "Recent quantum breakthroughs..."
   → RAG: "Your notes on quantum..."
   → Time: ~2 seconds

3. Result Aggregation
   → Combines results
   → Removes duplicates

4. LLM Response Generation
   → Generates comparison with citations

5. Response
   → "Here are recent developments compared to your notes..."
   → Tools used: arxiv, document_rag
```

## 🛠️ API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | Send message, get response |
| `/health` | GET | Health check |
| `/tools` | GET | List available tools |
| `/memory` | GET | Get conversation history |
| `/memory/clear` | POST | Clear conversation |

### Example Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is machine learning?",
    "stream": false
  }'
```

### Example Response

```json
{
  "response": "Machine learning is...",
  "session_id": "uuid",
  "tools_used": ["llm"],
  "intent": "general_knowledge",
  "metadata": {
    "confidence": 0.9,
    "num_tools": 1
  }
}
```

## 📚 Tools

| Tool | Type | When Used | Example |
|------|------|-----------|---------|
| **LLM** | Local | General knowledge | "What is X?" |
| **Web Search** | Online | Recent info | "Latest AI news" |
| **Wikipedia** | Online | Encyclopedia info | "History of computing" |
| **arXiv** | Online | Research papers | "Papers on transformers" |
| **Document RAG** | Offline | User documents | "My notes on X" |

## ⚙️ Configuration

Environment variables (optional):

```bash
# LLM
LLM_PROVIDER=ollama           # Provider (ollama/openai/gemini/claude)
LLM_MODEL=qwen3:8b           # Model name
LLM_TIMEOUT=60               # Request timeout
LLM_TEMPERATURE=0.7          # Response creativity
LLM_MAX_TOKENS=2000          # Max response length

# Tools
TOOL_TIMEOUT=30              # Tool execution timeout
WEB_SEARCH_RESULTS=5         # Results per search

# RAG
CHROMA_PERSIST_DIR=backend/chroma_data
RAG_TOP_K=3                  # Top results to retrieve

# Memory
MAX_MESSAGES_PER_SESSION=50  # History limit

# Intent Router
INTENT_CONFIDENCE_THRESHOLD=0.7
INTENT_VALIDATION_ENABLED=true

# API
API_HOST=127.0.0.1
API_PORT=8000
```

## 📖 Adding Documents

1. Create `backend/chroma_data/` directory
2. Place PDF files there:
   ```bash
   backend/chroma_data/
   ├── research.pdf
   ├── notes.pdf
   └── papers.pdf
   ```
3. Restart backend - documents auto-indexed

## 🔧 Adding New Tools

1. Create tool class inheriting from `BaseTool` or `WebTool`
2. Implement `execute()` method
3. Register in `app.py` startup
4. Done! Intent router will auto-discover it

```python
class MyTool(BaseTool):
    async def execute(self, query: str) -> ToolResult:
        # Your implementation
        return ToolResult(...)

# In app.py startup:
app.state.tools["my_tool"] = MyTool()
```

## 🧪 Testing

```bash
# Test 1: LLM only
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is AI?"}'

# Test 2: Web search
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Latest AI news today"}'

# Test 3: Document search
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What did my notes say?"}'

# Test 4: Multi-tool
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Compare latest papers with my research"}'
```

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Model not found | `ollama pull qwen3:8b` |
| ChromaDB error | Create `backend/chroma_data/` directory |
| Tools not responding | Check `http://localhost:8000/health` |
| Connection refused | Ensure Ollama is running |

## 📊 Performance

- **Intent analysis**: ~500ms
- **Tool execution**: 2-10s
- **Multi-tool (parallel)**: 50-100% faster than sequential
- **Total latency**: 3-15s for complex queries

## 🎓 What's New (v2.0)

| Feature | v1.0 | v2.0 |
|---------|------|------|
| User input | Commands (`wiki`, `search`) | Natural language |
| Routing | Keyword-based | LLM intent analysis |
| Multi-tool | Not supported | Yes (parallel/sequential) |
| Error handling | Silent fails | Graceful fallbacks |
| Architecture | Monolithic | Modular & extensible |

## 🚀 Production Ready

✅ Type safety (Pydantic models)
✅ Error handling (custom exceptions)
✅ Structured logging
✅ Configuration management
✅ Session isolation
✅ Async/await throughout
✅ Graceful degradation
✅ Professional documentation
✅ Clean git history

## 📝 License

MIT License

## 🤝 Support

- See `backend/ARCHITECTURE.md` for detailed technical docs
- Check code comments for implementation details
- Review API examples above for usage patterns
