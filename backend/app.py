"""
AI Assistant Pro - Main Application
Intent-based multi-tool orchestration system

This is the main entry point. Everything is self-contained and ready for production.
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ============================================================================
# CONFIGURATION (from environment variables)
# ============================================================================

class Config:
    """Application configuration from environment variables."""

    # LLM Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:8b")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))

    # Tool Settings
    TOOL_TIMEOUT = int(os.getenv("TOOL_TIMEOUT", "30"))
    WEB_SEARCH_RESULTS = int(os.getenv("WEB_SEARCH_RESULTS", "5"))

    # RAG Settings
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "backend/chroma_data")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
    RAG_MIN_SIMILARITY = float(os.getenv("RAG_MIN_SIMILARITY", "0.3"))

    # Memory Settings
    MAX_MESSAGES_PER_SESSION = int(os.getenv("MAX_MESSAGES_PER_SESSION", "50"))

    # Intent Router
    INTENT_CONFIDENCE_THRESHOLD = float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.7"))
    INTENT_VALIDATION_ENABLED = os.getenv("INTENT_VALIDATION_ENABLED", "true").lower() == "true"

    # API Settings
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", "8000"))


# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS & TYPES
# ============================================================================

class ChatRequest(BaseModel):
    """Chat request."""
    message: str = Field(..., min_length=1, max_length=5000)
    stream: bool = False


class ChatResponse(BaseModel):
    """Chat response."""
    response: str
    session_id: str
    tools_used: List[str] = Field(default_factory=list)
    intent: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


class Message:
    """Conversation message."""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }


# ============================================================================
# LLM CLIENT
# ============================================================================

class LLMClient:
    """LLM client for Ollama."""

    def __init__(self, model: str, timeout: int = 60):
        self.model = model
        self.timeout = timeout
        import ollama
        self.ollama = ollama
        logger.info(f"LLM initialized: {model}")

    async def generate(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Generate response using Ollama."""
        try:
            response = await asyncio.to_thread(
                self._generate_sync, messages, temperature, max_tokens
            )
            return response
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise

    def _generate_sync(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """Synchronous generation (for thread pool)."""
        response = self.ollama.chat(
            model=self.model,
            messages=messages,
            stream=False,
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        return response["message"]["content"]

    async def analyze_intent(self, prompt: str) -> Dict:
        """Analyze intent with structured JSON output."""
        messages = [{"role": "user", "content": prompt}]
        response = await self.generate(messages, temperature=0.3, max_tokens=500)

        # Extract JSON
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {"intent_type": "general_knowledge", "confidence": 0.5}


# ============================================================================
# TOOL SYSTEM
# ============================================================================

class ToolResult:
    """Standard result from a tool."""
    def __init__(self, tool_name: str, query: str, success: bool, data: str = "",
                 error: str = "", confidence: float = 1.0):
        self.tool_name = tool_name
        self.query = query
        self.success = success
        self.data = data
        self.error = error
        self.confidence = confidence


class WebSearchTool:
    """DuckDuckGo web search."""
    def __init__(self):
        from ddgs import DDGS
        self.ddgs_class = DDGS

    async def execute(self, query: str, num_results: int = 5) -> ToolResult:
        try:
            results = await asyncio.to_thread(self._search, query, num_results)
            text = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
            return ToolResult("web_search", query, True, text, confidence=0.8)
        except Exception as e:
            logger.warning(f"Web search error: {e}")
            return ToolResult("web_search", query, False, error=str(e))

    def _search(self, query: str, num_results: int):
        with self.ddgs_class() as ddgs:
            return list(ddgs.text(query, max_results=num_results)) or []


class WikipediaTool:
    """Wikipedia search."""
    async def execute(self, query: str) -> ToolResult:
        try:
            import wikipedia
            summary = await asyncio.to_thread(
                lambda: wikipedia.summary(query, sentences=3)
            )
            return ToolResult("wikipedia", query, True, summary, confidence=0.9)
        except Exception as e:
            logger.warning(f"Wikipedia error: {e}")
            return ToolResult("wikipedia", query, False, error=str(e))


class ArxivTool:
    """arXiv paper search."""
    async def execute(self, query: str, num_results: int = 3) -> ToolResult:
        try:
            import arxiv
            search = arxiv.Search(query=query, max_results=num_results)
            papers = []
            for result in search.results():
                papers.append(f"**{result.title}**\n{result.summary[:300]}")
            text = "\n\n".join(papers)
            return ToolResult("arxiv", query, True, text, confidence=0.85)
        except Exception as e:
            logger.warning(f"arXiv error: {e}")
            return ToolResult("arxiv", query, False, error=str(e))


class RAGTool:
    """ChromaDB document search."""
    def __init__(self, db_path: str = "backend/chroma_data"):
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            self.client = chromadb.PersistentClient(path=db_path)
            self.collection = self.client.get_or_create_collection(name="documents")
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"RAG initialization failed: {e}")
            self.collection = None
            self.embedder = None

    async def execute(self, query: str, top_k: int = 3) -> ToolResult:
        if not self.collection or not self.embedder:
            return ToolResult("document_rag", query, False, error="RAG not initialized")

        try:
            results = await asyncio.to_thread(self._search, query, top_k)
            if not results:
                return ToolResult("document_rag", query, True, "No matching documents found", confidence=0.0)

            text = "\n".join([f"**From {r['source']}**: {r['content'][:200]}..." for r in results])
            return ToolResult("document_rag", query, True, text, confidence=0.8)
        except Exception as e:
            logger.warning(f"RAG error: {e}")
            return ToolResult("document_rag", query, False, error=str(e))

    def _search(self, query: str, top_k: int):
        try:
            from numpy import dot
            from numpy.linalg import norm

            query_embedding = self.embedder.encode(query).tolist()
            results = self.collection.query(query_embeddings=[query_embedding], n_results=top_k)

            documents = []
            if results["documents"] and results["documents"][0]:
                for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                    documents.append({
                        "content": doc,
                        "source": metadata.get("source", "unknown")
                    })
            return documents
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return []


# ============================================================================
# INTENT ROUTER
# ============================================================================

INTENT_ANALYSIS_PROMPT = """Analyze this query and determine the best tools to use.

Intent types:
- general_knowledge: Answer from LLM knowledge
- real_time_info: Needs web search (current news, events)
- document_search: Query user's documents
- academic_research: Query academic papers
- multi_source: Combine multiple tools

Query: "{query}"

Respond ONLY with JSON:
{{"intent_type": "...", "confidence": 0.0-1.0, "primary_tool": "...", "secondary_tools": [...], "reasoning": "..."}}"""


class IntentRouter:
    """LLM-based intent router."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def route(self, query: str) -> Dict:
        """Analyze query and determine routing."""
        logger.info(f"Routing query: {query[:100]}...")

        # Heuristic check
        if any(kw in query.lower() for kw in ["today", "latest", "current", "news", "breaking"]):
            return {
                "intent_type": "real_time_info",
                "confidence": 0.8,
                "primary_tool": "web_search",
                "secondary_tools": [],
            }

        if any(kw in query.lower() for kw in ["my document", "my notes", "my research", "uploaded"]):
            return {
                "intent_type": "document_search",
                "confidence": 0.8,
                "primary_tool": "document_rag",
                "secondary_tools": [],
            }

        if any(kw in query.lower() for kw in ["research", "paper", "arxiv", "published"]):
            return {
                "intent_type": "academic_research",
                "confidence": 0.8,
                "primary_tool": "arxiv",
                "secondary_tools": [],
            }

        if any(kw in query.lower() for kw in ["compare", "with my", "both"]):
            return {
                "intent_type": "multi_source",
                "confidence": 0.8,
                "primary_tool": "web_search",
                "secondary_tools": ["document_rag"],
            }

        # LLM analysis
        try:
            prompt = INTENT_ANALYSIS_PROMPT.format(query=query)
            result = await self.llm_client.analyze_intent(prompt)
            logger.info(f"Intent: {result.get('intent_type')} (confidence: {result.get('confidence', 0):.2f})")
            return result
        except Exception as e:
            logger.error(f"Intent analysis error: {e}")
            return {
                "intent_type": "general_knowledge",
                "confidence": 0.5,
                "primary_tool": "llm",
                "secondary_tools": [],
            }


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class ToolOrchestrator:
    """Execute multiple tools."""

    async def execute(self, routing_decision: Dict, tools: Dict) -> List[ToolResult]:
        """Execute tools according to routing."""
        results = []

        # Primary tool
        primary = routing_decision.get("primary_tool")
        if primary and primary in tools:
            result = await tools[primary].execute(routing_decision.get("query", ""))
            results.append(result)

        # Secondary tools (parallel)
        secondary = routing_decision.get("secondary_tools", [])
        if secondary:
            tasks = [tools[t].execute(routing_decision.get("query", "")) for t in secondary if t in tools]
            if tasks:
                results.extend(await asyncio.gather(*tasks, return_exceptions=False))

        return [r for r in results if isinstance(r, ToolResult)]


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="AI Assistant Pro",
    description="Intent-based multi-tool AI assistant",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("Starting AI Assistant Pro...")

    app.state.llm_client = LLMClient(Config.LLM_MODEL)
    app.state.orchestrator = ToolOrchestrator()
    app.state.intent_router = IntentRouter(app.state.llm_client)
    app.state.tools = {
        "web_search": WebSearchTool(),
        "wikipedia": WikipediaTool(),
        "arxiv": ArxivTool(),
        "document_rag": RAGTool(Config.CHROMA_PERSIST_DIR),
    }
    app.state.conversation_memory = {}
    logger.info("Startup complete!")


@app.post("/chat")
async def chat(request: ChatRequest, session_id: Optional[str] = Header(None)) -> ChatResponse:
    """Chat endpoint with intent-based routing."""
    session_id = session_id or str(uuid.uuid4())
    logger.info(f"Chat [{session_id}]: {request.message[:100]}...")

    try:
        # Get conversation context
        if session_id not in app.state.conversation_memory:
            app.state.conversation_memory[session_id] = []

        messages = app.state.conversation_memory[session_id]

        # Analyze intent
        routing = await app.state.intent_router.route(request.message)
        routing["query"] = request.message

        # Execute tools
        tool_results = await app.state.orchestrator.execute(routing, app.state.tools)

        # Build context
        tool_context = "\n".join([r.data for r in tool_results if r.success])

        # Generate response
        system_prompt = """You are an intelligent AI assistant. Use the provided context when relevant.
Cite your sources."""
        if tool_context:
            system_prompt += f"\n\nContext from tools:\n{tool_context}"

        llm_messages = [
            {"role": "system", "content": system_prompt},
            *[{"role": m.role, "content": m.content} for m in messages[-10:]],
            {"role": "user", "content": request.message},
        ]

        response_text = await app.state.llm_client.generate(
            llm_messages, Config.LLM_TEMPERATURE, Config.LLM_MAX_TOKENS
        )

        # Store in memory
        app.state.conversation_memory[session_id].append(Message("user", request.message))
        app.state.conversation_memory[session_id].append(Message("assistant", response_text))

        # Limit history
        if len(app.state.conversation_memory[session_id]) > Config.MAX_MESSAGES_PER_SESSION:
            app.state.conversation_memory[session_id] = app.state.conversation_memory[session_id][
                -Config.MAX_MESSAGES_PER_SESSION :
            ]

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            tools_used=[r.tool_name for r in tool_results if r.success],
            intent=routing.get("intent_type"),
            metadata={
                "confidence": routing.get("confidence", 0),
                "num_tools": len(tool_results),
            },
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return ChatResponse(
            response="An error occurred. Please try again.",
            session_id=session_id,
            error=str(e),
        )


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


@app.get("/tools")
async def list_tools():
    """List available tools."""
    return {
        "tools": [
            {"name": "web_search", "description": "Web search via DuckDuckGo"},
            {"name": "wikipedia", "description": "Wikipedia search"},
            {"name": "arxiv", "description": "arXiv paper search"},
            {"name": "document_rag", "description": "Document/RAG search"},
        ]
    }


@app.post("/memory/clear")
async def clear_memory(session_id: Optional[str] = Header(None)):
    """Clear conversation memory."""
    if session_id and session_id in app.state.conversation_memory:
        del app.state.conversation_memory[session_id]
        return {"status": "cleared"}
    return {"status": "not_found"}


@app.get("/memory")
async def get_memory(session_id: Optional[str] = Header(None)):
    """Get conversation memory."""
    if not session_id or session_id not in app.state.conversation_memory:
        return {"messages": []}

    messages = app.state.conversation_memory[session_id]
    return {
        "messages": [m.to_dict() for m in messages],
        "count": len(messages),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=Config.API_HOST, port=Config.API_PORT, reload=True)
