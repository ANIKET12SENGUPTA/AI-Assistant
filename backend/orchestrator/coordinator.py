"""Multi-tool orchestrator for coordinating tool execution."""

import asyncio
import time
from typing import Dict, List, Optional

from core.config import Config
from core.constants import ExecutionStrategy, ToolStatus, FALLBACK_CHAINS
from core.logger import setup_logger
from core.types import (
    AggregatedContext,
    OrchestratedResults,
    RoutingDecision,
    ToolResult,
)

logger = setup_logger(__name__)


class ToolOrchestrator:
    """
    Orchestrates execution of multiple tools.
    Supports parallel, sequential, and conditional execution strategies.
    """

    def __init__(self):
        """Initialize tool orchestrator."""
        logger.info("Tool orchestrator initialized")

    async def execute(
        self,
        routing_decision: RoutingDecision,
        tool_manager,
    ) -> OrchestratedResults:
        """
        Execute tools according to routing decision.

        Args:
            routing_decision: Routing decision with tools to execute
            tool_manager: ToolManager instance

        Returns:
            OrchestratedResults with execution results
        """

        start_time = time.time()

        logger.info(
            f"Orchestrating execution ({routing_decision.execution_strategy.value}): "
            f"{[t.name for t in routing_decision.tools]}"
        )

        # If no tools specified, use LLM only
        if not routing_decision.tools:
            logger.debug("No tools specified, using LLM only")
            return OrchestratedResults(
                results=[],
                combined_context="",
                execution_time_ms=(time.time() - start_time) * 1000,
                fallback_used=False,
                strategy_used=routing_decision.execution_strategy,
            )

        # Execute tools based on strategy
        strategy = routing_decision.execution_strategy

        if strategy == ExecutionStrategy.PARALLEL:
            results = await self._execute_parallel(routing_decision, tool_manager)
        elif strategy == ExecutionStrategy.SEQUENTIAL:
            results = await self._execute_sequential(routing_decision, tool_manager)
        else:  # CONDITIONAL
            results = await self._execute_conditional(routing_decision, tool_manager)

        # Aggregate results
        combined = await self._aggregate_results(results, routing_decision)

        # Apply fallbacks if needed
        fallback_used = False
        if any(not r.success for r in results):
            logger.debug("Some tools failed, attempting fallbacks")
            combined = await self._apply_fallbacks(results, routing_decision, tool_manager)
            fallback_used = True

        execution_time = (time.time() - start_time) * 1000

        return OrchestratedResults(
            results=results,
            combined_context=combined.context,
            execution_time_ms=execution_time,
            fallback_used=fallback_used,
            strategy_used=strategy,
        )

    async def _execute_parallel(self, routing_decision: RoutingDecision, tool_manager) -> List[ToolResult]:
        """
        Execute multiple tools in parallel with timeout.

        Args:
            routing_decision: Routing decision
            tool_manager: ToolManager instance

        Returns:
            List of tool results
        """

        logger.debug("Executing tools in parallel")

        tasks = []
        tool_specs = []

        for tool_spec in routing_decision.tools:
            tool = tool_manager.registry.get_tool(tool_spec.name)

            if tool is None:
                logger.warning(f"Tool not found: {tool_spec.name}")
                continue

            # Check availability
            if not await tool_manager._is_tool_healthy(tool):
                logger.warning(f"Tool unavailable: {tool_spec.name}")
                continue

            timeout = tool.get_metadata().timeout_seconds

            # Create task
            task = asyncio.wait_for(
                tool.execute(query=tool_spec.query, **tool_spec.parameters),
                timeout=timeout,
            )

            tasks.append(task)
            tool_specs.append(tool_spec.name)

        # Execute all tasks in parallel, capture failures
        results = []

        if not tasks:
            logger.warning("No healthy tools available for parallel execution")
            return results

        for i, task in enumerate(asyncio.as_completed(tasks)):
            try:
                result = await task
                results.append(result)
                logger.debug(f"Tool {tool_specs[i]} completed successfully")
            except asyncio.TimeoutError:
                logger.error(f"Tool {tool_specs[i]} timed out")
                results.append(
                    ToolResult(
                        tool_name=tool_specs[i],
                        query="",
                        success=False,
                        error_message="Tool execution timed out",
                    )
                )
            except Exception as e:
                logger.error(f"Tool {tool_specs[i]} failed: {e}")
                results.append(
                    ToolResult(
                        tool_name=tool_specs[i],
                        query="",
                        success=False,
                        error_message=str(e),
                    )
                )

        return results

    async def _execute_sequential(self, routing_decision: RoutingDecision, tool_manager) -> List[ToolResult]:
        """
        Execute tools one after another.

        Args:
            routing_decision: Routing decision
            tool_manager: ToolManager instance

        Returns:
            List of tool results
        """

        logger.debug("Executing tools sequentially")

        results = []

        for tool_spec in routing_decision.tools:
            tool = tool_manager.registry.get_tool(tool_spec.name)

            if tool is None:
                logger.warning(f"Tool not found: {tool_spec.name}")
                continue

            if not await tool_manager._is_tool_healthy(tool):
                logger.warning(f"Tool unavailable: {tool_spec.name}")
                continue

            try:
                # Pass context from previous tool if available
                parameters = dict(tool_spec.parameters)

                if results and results[-1].success:
                    parameters["context"] = results[-1].data
                    logger.debug(f"Passing context from {results[-1].tool_name} to {tool_spec.name}")

                timeout = tool.get_metadata().timeout_seconds

                result = await asyncio.wait_for(
                    tool.execute(tool_spec.query, **parameters),
                    timeout=timeout,
                )

                results.append(result)
                logger.debug(f"Tool {tool_spec.name} completed")

                # Early exit if result is sufficient
                if result.success and result.confidence > 0.9:
                    logger.debug(f"High-confidence result from {tool_spec.name}, stopping")
                    break

            except asyncio.TimeoutError:
                logger.error(f"Tool {tool_spec.name} timed out")
                results.append(
                    ToolResult(
                        tool_name=tool_spec.name,
                        query=tool_spec.query,
                        success=False,
                        error_message="Tool execution timed out",
                    )
                )

            except Exception as e:
                logger.error(f"Tool {tool_spec.name} failed: {e}")
                results.append(
                    ToolResult(
                        tool_name=tool_spec.name,
                        query=tool_spec.query,
                        success=False,
                        error_message=str(e),
                    )
                )

        return results

    async def _execute_conditional(self, routing_decision: RoutingDecision, tool_manager) -> List[ToolResult]:
        """
        Execute tools based on previous results (conditional).

        Args:
            routing_decision: Routing decision
            tool_manager: ToolManager instance

        Returns:
            List of tool results
        """

        logger.debug("Executing tools conditionally")

        # For now, treat as sequential with early exit
        # This can be enhanced with more complex conditional logic
        return await self._execute_sequential(routing_decision, tool_manager)

    async def _aggregate_results(
        self,
        results: List[ToolResult],
        routing_decision: RoutingDecision,
    ) -> AggregatedContext:
        """
        Combine results from multiple tools into unified context.

        Args:
            results: List of tool results
            routing_decision: Original routing decision

        Returns:
            Aggregated context
        """

        logger.debug(f"Aggregating {len(results)} results")

        successful_results = [r for r in results if r.success]

        if not successful_results:
            logger.debug("No successful tool results")
            return AggregatedContext(
                context="Could not retrieve information from any tool",
                confidence=0.0,
                sources=[],
                tool_results=results,
            )

        # Aggregate based on tool type
        aggregated_text = ""
        sources = []
        confidence_scores = []

        for result in successful_results:
            # Add tool result to context
            aggregated_text += f"\n\n**{result.tool_name.upper()}:**\n"
            aggregated_text += str(result.data)

            confidence_scores.append(result.confidence)

            # Track sources
            if result.source_urls:
                sources.extend(result.source_urls)
            if result.document_ids:
                sources.extend(result.document_ids)

        # Calculate aggregate confidence
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.5
        )

        logger.debug(f"Aggregated {len(successful_results)} results with confidence {avg_confidence:.2f}")

        return AggregatedContext(
            context=aggregated_text.strip(),
            confidence=avg_confidence,
            sources=list(set(sources)),  # Deduplicate
            tool_results=results,
        )

    async def _apply_fallbacks(
        self,
        results: List[ToolResult],
        routing_decision: RoutingDecision,
        tool_manager,
    ) -> AggregatedContext:
        """
        Apply fallback strategy when tools fail.

        Args:
            results: Previous results
            routing_decision: Original routing decision
            tool_manager: ToolManager instance

        Returns:
            Aggregated context with fallback results
        """

        logger.info("Attempting fallback strategy")

        failed_tools = [r.tool_name for r in results if not r.success]

        # Try fallback chain
        for failed_tool in failed_tools:
            fallback_tools = FALLBACK_CHAINS.get(failed_tool, [])

            for fallback_tool_name in fallback_tools:
                logger.debug(f"Trying fallback: {failed_tool} -> {fallback_tool_name}")

                tool = tool_manager.registry.get_tool(fallback_tool_name)

                if tool is None or not await tool_manager._is_tool_healthy(tool):
                    continue

                try:
                    result = await asyncio.wait_for(
                        tool.execute(routing_decision.original_query),
                        timeout=tool.get_metadata().timeout_seconds,
                    )

                    if result.success:
                        logger.info(f"Fallback successful: {fallback_tool_name}")

                        return AggregatedContext(
                            context=result.data,
                            confidence=min(0.7, result.confidence),  # Lower confidence for fallback
                            sources=[fallback_tool_name],
                            tool_results=results + [result],
                        )

                except Exception as e:
                    logger.debug(f"Fallback {fallback_tool_name} failed: {e}")
                    continue

        logger.warning("All fallbacks failed")

        return AggregatedContext(
            context="Unable to retrieve information after trying all tools and fallbacks",
            confidence=0.0,
            sources=[],
            tool_results=results,
        )
