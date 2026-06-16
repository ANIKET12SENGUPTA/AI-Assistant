"""Web tools implementations."""

import asyncio
from typing import Dict, List, Optional

import wikipedia
from ddgs import DDGS

from core.constants import QueryType, ToolStatus
from core.logger import setup_logger
from core.types import ToolMetadata, ToolResult

from ..base import WebTool

logger = setup_logger(__name__)


class DuckDuckGoTool(WebTool):
    """DuckDuckGo web search tool."""

    def _define_metadata(self) -> ToolMetadata:
        """Define tool metadata."""
        return ToolMetadata(
            name="web_search",
            description="Search the web for current information using DuckDuckGo",
            required_online=True,
            timeout_seconds=10,
            priority=1,
            supported_query_types=[QueryType.WEB_SEARCH, QueryType.NEWS, QueryType.GENERAL],
            cost_score=1.0,
            latency_score=1.5,
            example_queries=[
                "latest AI breakthroughs",
                "what happened today",
                "current stock market news",
            ],
        )

    async def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
        """
        Execute web search using DuckDuckGo.

        Args:
            query: Search query
            num_results: Number of results to return
            **kwargs: Additional parameters

        Returns:
            ToolResult with search results
        """
        start_time = asyncio.get_event_loop().time()

        try:
            results = await asyncio.to_thread(self._search, query, num_results)

            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

            # Format results
            formatted_results = "\n".join([f"- {r['title']}: {r['body']}" for r in results])

            source_urls = [r.get("href", "") for r in results if r.get("href")]

            return ToolResult(
                tool_name=self.metadata.name,
                query=query,
                success=True,
                data=formatted_results,
                execution_time_ms=execution_time,
                source_urls=source_urls,
                confidence=0.8,
                metadata={"num_results": len(results)},
            )

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return ToolResult(
                tool_name=self.metadata.name,
                query=query,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                confidence=0.0,
            )

    def _search(self, query: str, num_results: int) -> List[Dict]:
        """Perform the actual search (blocking operation)."""
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=num_results)
            return list(results) if results else []

    async def health_check(self) -> ToolStatus:
        """Check if DuckDuckGo is accessible."""
        try:
            # Try a simple search
            result = await asyncio.to_thread(self._search, "test", 1)
            if result:
                self.set_status(ToolStatus.AVAILABLE)
                return ToolStatus.AVAILABLE
            else:
                self.set_status(ToolStatus.DEGRADED, "No results returned")
                return ToolStatus.DEGRADED
        except Exception as e:
            logger.warning(f"DuckDuckGo health check failed: {e}")
            self.set_status(ToolStatus.UNAVAILABLE, str(e))
            return ToolStatus.UNAVAILABLE


class WikipediaTool(WebTool):
    """Wikipedia search tool."""

    def _define_metadata(self) -> ToolMetadata:
        """Define tool metadata."""
        return ToolMetadata(
            name="wikipedia",
            description="Search Wikipedia for encyclopedia information",
            required_online=True,
            timeout_seconds=8,
            priority=2,
            supported_query_types=[QueryType.GENERAL, QueryType.RESEARCH],
            cost_score=0.5,
            latency_score=0.8,
            example_queries=[
                "What is machine learning?",
                "History of computers",
                "Albert Einstein biography",
            ],
        )

    async def execute(self, query: str, sentences: int = 3, **kwargs) -> ToolResult:
        """
        Execute Wikipedia search.

        Args:
            query: Search query
            sentences: Number of sentences in summary
            **kwargs: Additional parameters

        Returns:
            ToolResult with Wikipedia summary
        """
        start_time = asyncio.get_event_loop().time()

        try:
            summary = await asyncio.to_thread(self._get_summary, query, sentences)

            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return ToolResult(
                tool_name=self.metadata.name,
                query=query,
                success=True,
                data=summary,
                execution_time_ms=execution_time,
                confidence=0.9,
                metadata={"source": "wikipedia"},
            )

        except Exception as e:
            logger.debug(f"Wikipedia search error for '{query}': {e}")
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return ToolResult(
                tool_name=self.metadata.name,
                query=query,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                confidence=0.0,
            )

    def _get_summary(self, query: str, sentences: int) -> str:
        """Get Wikipedia summary (blocking operation)."""
        try:
            summary = wikipedia.summary(query, sentences=sentences)
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            # Return first option on disambiguation
            if e.options:
                return wikipedia.summary(e.options[0], sentences=sentences)
            raise
        except wikipedia.exceptions.PageError:
            raise ValueError(f"No Wikipedia page found for '{query}'")

    async def health_check(self) -> ToolStatus:
        """Check if Wikipedia is accessible."""
        try:
            _ = await asyncio.to_thread(self._get_summary, "test", 1)
            self.set_status(ToolStatus.AVAILABLE)
            return ToolStatus.AVAILABLE
        except Exception as e:
            logger.warning(f"Wikipedia health check failed: {e}")
            self.set_status(ToolStatus.UNAVAILABLE, str(e))
            return ToolStatus.UNAVAILABLE


class ArxivTool(WebTool):
    """arXiv paper search tool."""

    def _define_metadata(self) -> ToolMetadata:
        """Define tool metadata."""
        return ToolMetadata(
            name="arxiv",
            description="Search arXiv for research papers and academic publications",
            required_online=True,
            timeout_seconds=10,
            priority=1,
            supported_query_types=[QueryType.RESEARCH, "academic_research"],
            cost_score=1.0,
            latency_score=1.2,
            example_queries=[
                "large language models transformers",
                "attention mechanism neural networks",
                "reinforcement learning",
            ],
        )

    async def execute(self, query: str, num_results: int = 3, **kwargs) -> ToolResult:
        """
        Execute arXiv search.

        Args:
            query: Search query
            num_results: Number of papers to return
            **kwargs: Additional parameters

        Returns:
            ToolResult with paper summaries
        """
        start_time = asyncio.get_event_loop().time()

        try:
            papers = await asyncio.to_thread(self._search_papers, query, num_results)

            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

            formatted_papers = "\n\n".join(
                [f"**{p['title']}** ({p['date']})\n{p['summary']}" for p in papers]
            )

            source_urls = [p.get("arxiv_url", "") for p in papers]

            return ToolResult(
                tool_name=self.metadata.name,
                query=query,
                success=True,
                data=formatted_papers,
                execution_time_ms=execution_time,
                source_urls=source_urls,
                confidence=0.85,
                metadata={"num_papers": len(papers)},
            )

        except Exception as e:
            logger.error(f"arXiv search error: {e}")
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return ToolResult(
                tool_name=self.metadata.name,
                query=query,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                confidence=0.0,
            )

    def _search_papers(self, query: str, num_results: int) -> List[Dict]:
        """Search arXiv papers (blocking operation)."""
        import arxiv

        search = arxiv.Search(query=query, max_results=num_results)

        papers = []
        for result in search.results():
            papers.append(
                {
                    "title": result.title,
                    "summary": result.summary[:500],  # Truncate to 500 chars
                    "date": result.published.strftime("%Y-%m-%d"),
                    "arxiv_url": result.entry_id,
                }
            )

        return papers

    async def health_check(self) -> ToolStatus:
        """Check if arXiv is accessible."""
        try:
            _ = await asyncio.to_thread(self._search_papers, "machine learning", 1)
            self.set_status(ToolStatus.AVAILABLE)
            return ToolStatus.AVAILABLE
        except Exception as e:
            logger.warning(f"arXiv health check failed: {e}")
            self.set_status(ToolStatus.UNAVAILABLE, str(e))
            return ToolStatus.UNAVAILABLE
