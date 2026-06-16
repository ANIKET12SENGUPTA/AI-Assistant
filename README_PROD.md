# AI Assistant Pro - v2.0

**Intent-based multi-tool AI assistant with automatic routing** (like ChatGPT, Claude, Gemini)

## 🎯 Key Features

✅ **No Commands Needed** - Ask naturally: "What's the latest AI news?" instead of `search latest AI news`
✅ **Automatic Tool Selection** - System determines which tools to use (web search, documents, papers, LLM)
✅ **Multi-Tool Orchestration** - Combines results from multiple sources intelligently
✅ **Works Offline** - Local documents (RAG) still work without internet
✅ **Graceful Degradation** - Automatic fallbacks when tools fail
✅ **Production Ready** - Type-safe, well-structured, professional logging

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ 
- Ollama with `qwen3:8b` model installed
  ```bash
  ollama pull qwen3:8b
  ```

### Installation

```bash
# Clone/navigate to project
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
# Start the backend
python -m uvicorn app:app --reload

# Backend runs on: http://localhost:8000
```

### Test

```bash
# Test 1: Simple question (LLM only)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is machine learning?"}'

# Test 2: Recent info (web search)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the latest AI breakthroughs?"}'

# Test 3: Multi-source (combine web + documents)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Compare recent AI papers with my research notes"}'

# Test 4: Document search
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What did my notes say about transformers?"}'
```

## 📁 Project Structure

```
backend/
├── app.py                    # Main application (self-contained)
│
├── core/
│   ├── types.py             # Pydantic models and dataclasses
│   ├── constants.py         # Enums, prompts, constants
│   └── exceptions.py        # Custom exceptions
│
├── intent/
│   └── router.py            # Intent analysis (LLM-based)
│
├── tools/
│   ├── base.py              # Tool abstraction
│   ├── registry.py          # Tool discovery system
│   ├── manager.py           # Tool lifecycle management
│   ├── web/
│   │   └── tools.py         # DuckDuckGo, Wikipedia, arXiv
│   └── rag/
│       └── tools.py         # ChromaDB document search
│
├── orchestrator/
│   └── coordinator.py       # Multi-tool execution
│
├── llm/
│   └── client.py            # LLM abstraction (Ollama)
│
├── ARCHITECTURE.md          # Detailed architecture docs
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🔄 How It Works

```
User: "Compare recent quantum papers with my notes"
    ↓
[1] Intent Router (LLM analyzes intent)
    → Detects: multi_source (web + documents)
    → Confidence: 0.95
    ↓
[2] Tool Selection & Validation
    → Primary: web_search
    → Secondary: document_rag
    ↓
[3] Multi-Tool Execution (parallel)
    → web_search: "Recent quantum breakthroughs..." ✓
    → document_rag: "My notes on quantum..." ✓
    ↓
[4] Result Aggregation
    → Combines both results
    ↓
[5] LLM Reasoning
    → Generates comparison with citations
    ↓
Response: "Here are the recent developments compared to your notes..."
```

## 🛠️ API Endpoints

### POST /chat
Chat with automatic routing
```json
{
  "message": "What's the latest AI news?",
  "stream": false
}
```

### GET /health
Health check

### GET /tools
List available tools

### GET /memory
Get conversation history (add header `Session-ID: <uuid>`)

### POST /memory/clear
Clear conversation (add header `Session-ID: <uuid>`)

## ⚙️ Configuration

Environment variables (create `.env`):
```bash
# LLM
LLM_PROVIDER=ollama          # ollama, openai, gemini, claude (future)
LLM_MODEL=qwen3:8b
LLM_TIMEOUT=60
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Tools
TOOL_TIMEOUT=30
WEB_SEARCH_RESULTS=5

# RAG
CHROMA_PERSIST_DIR=backend/chroma_data
RAG_TOP_K=3

# Memory
MAX_MESSAGES_PER_SESSION=50

# Intent Router
INTENT_CONFIDENCE_THRESHOLD=0.7
INTENT_VALIDATION_ENABLED=true

# API
API_HOST=127.0.0.1
API_PORT=8000
```

## 📚 Adding Documents

Place PDF files in `backend/chroma_data/` directory:
```bash
backend/
├── chroma_data/
│   ├── my_research.pdf
│   ├── notes.pdf
│   └── resume.pdf
└── ...
```

They'll be automatically indexed at startup.

## 🔧 Adding New Tools

1. **Create tool in `tools/web/tools.py` or `tools/rag/tools.py`**:
```python
class MyTool:
    async def execute(self, query: str) -> ToolResult:
        # Implementation
        return ToolResult(...)
```

2. **Register in `app.py` startup**:
```python
app.state.tools["my_tool"] = MyTool()
```

3. **Done!** Intent router will auto-discover it.

## 📊 Intent Types

| Type | Triggered By | Examples |
|------|--------------|----------|
| `general_knowledge` | General questions | "What is X?", "Explain Y" |
| `real_time_info` | Recent/current events | "Latest news", "Today's weather" |
| `document_search` | User's documents | "My notes", "My research" |
| `academic_research` | Research papers | "Papers on X", "arXiv papers" |
| `multi_source` | Combining sources | "Compare X with my notes" |

## 🧪 Testing

### Unit Testing
```bash
# Test individual tools
pytest backend/tests/test_tools.py

# Test intent router
pytest backend/tests/test_intent.py

# Test orchestrator
pytest backend/tests/test_orchestrator.py
```

### Integration Testing
```bash
# Test end-to-end flow
pytest backend/tests/test_e2e.py
```

## 🚨 Troubleshooting

**Error: Model not found**
```bash
# Ensure model is pulled
ollama pull qwen3:8b
```

**Error: ChromaDB not initialized**
```bash
# Create directory
mkdir -p backend/chroma_data
```

**Tools not responding**
```bash
# Check health
curl http://localhost:8000/health

# Check tool status
curl http://localhost:8000/tools
```

## 📈 Performance

- **Intent analysis**: ~500ms (LLM call)
- **Tool execution**: 2-10s (depending on tools)
- **Multi-tool (parallel)**: 50-100% faster than sequential
- **Total latency**: 3-15s for complex queries

## 🔐 Production Checklist

- [x] Type safety (Pydantic models)
- [x] Error handling (custom exceptions)
- [x] Structured logging
- [x] Configuration management
- [x] Session isolation
- [x] Graceful degradation
- [ ] Rate limiting
- [ ] Authentication
- [ ] Monitoring/metrics
- [ ] Load testing

## 🎓 What's Different from v1.0

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Routing | `wiki Python` | "Explain Python" |
| Commands | Required | Not needed |
| Multi-tool | No | Yes |
| Tool selection | Hardcoded | Automatic (LLM) |
| Error handling | Fails silently | Graceful fallbacks |
| Architecture | Monolithic | Modular/extensible |

## 📖 Documentation

- **ARCHITECTURE.md** - Detailed design documentation
- **API Endpoints** - See above
- **Code Comments** - Throughout codebase

## 🤝 Contributing

To add new features:
1. Create new tool or enhance existing
2. Update `app.py` to register
3. Test with curl or frontend
4. Document in ARCHITECTURE.md

## 📝 License

MIT License - See LICENSE file

## 🙋 Support

- **Documentation**: See ARCHITECTURE.md
- **Issues**: Check existing issues or create new
- **Questions**: Refer to code comments and docstrings

---

**Built with**: FastAPI, Ollama, ChromaDB, Pydantic, asyncio
