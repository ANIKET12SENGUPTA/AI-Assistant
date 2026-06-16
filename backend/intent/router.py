"""Intent-based router for intelligent tool selection."""

import json
import re
from typing import Dict, List, Optional

from core.config import Config
from core.constants import (
    ExecutionStrategy,
    IntentType,
    INTENT_ANALYSIS_PROMPT,
    INTENT_VALIDATION_PROMPT,
    QueryType,
)
from core.logger import setup_logger
from core.types import (
    ConversationContext,
    RoutingDecision,
    ToolSelection,
)

logger = setup_logger(__name__)


class IntentRouter:
    """
    LLM-based intent router for intelligent tool selection.
    Analyzes user queries to determine intent and select appropriate tools.
    """

    def __init__(self, llm_client):
        """
        Initialize intent router.

        Args:
            llm_client: LLM client for intent analysis
        """
        self.llm_client = llm_client
        logger.info("Intent router initialized")

    async def route(
        self, user_query: str, context: ConversationContext, tool_manager=None
    ) -> RoutingDecision:
        """
        Analyze user query and determine routing.

        Args:
            user_query: User's query string
            context: Conversation context
            tool_manager: Optional tool manager for availability checks

        Returns:
            RoutingDecision with routing information
        """

        logger.info(f"Routing query: {user_query[:100]}...")

        # 1. Quick heuristic check
        heuristic_intent = self._heuristic_classify(user_query)
        logger.debug(f"Heuristic classification: {heuristic_intent}")

        # 2. LLM-based intent analysis
        llm_intent = await self._llm_analyze_intent(user_query, context)

        # 3. Validation pass (if enabled)
        if Config.INTENT_VALIDATION_ENABLED:
            llm_intent = await self._validate_intent(llm_intent)

        # 4. Calculate confidence
        confidence = self._calculate_confidence(heuristic_intent, llm_intent)

        logger.debug(
            f"Final intent: {llm_intent.get('intent_type', 'unknown')} (confidence: {confidence:.2f})"
        )

        # 5. Build tool selections
        tool_selections = self._build_tool_selections(llm_intent, tool_manager)

        # 6. Determine execution strategy
        strategy = self._determine_execution_strategy(
            llm_intent.get("execution_strategy", "parallel")
        )

        # 7. Create routing decision
        routing_decision = RoutingDecision(
            intent_type=IntentType(llm_intent.get("intent_type", "general_knowledge")),
            confidence=confidence,
            tools=tool_selections,
            execution_strategy=strategy,
            reasoning=llm_intent.get("reasoning", ""),
            original_query=user_query,
        )

        logger.info(
            f"Routing decision: {routing_decision.intent_type} "
            f"({len(tool_selections)} tools, strategy: {strategy.value})"
        )

        return routing_decision

    def _heuristic_classify(self, query: str) -> Optional[IntentType]:
        """
        Quick heuristic classification based on keywords.

        Args:
            query: User query

        Returns:
            IntentType or None if heuristic doesn't match
        """
        query_lower = query.lower()

        # Check for personal document references
        personal_keywords = [
            "my document",
            "my file",
            "uploaded",
            "my notes",
            "my resume",
            "my research",
        ]
        if any(kw in query_lower for kw in personal_keywords):
            logger.debug("Heuristic: document_search (personal keywords)")
            return IntentType.DOCUMENT_SEARCH

        # Check for time sensitivity
        time_keywords = [
            "today",
            "yesterday",
            "latest",
            "recent",
            "current",
            "news",
            "breaking",
            "latest news",
            "what happened",
        ]
        if any(kw in query_lower for kw in time_keywords):
            logger.debug("Heuristic: real_time_info (time keywords)")
            return IntentType.REAL_TIME_INFO

        # Check for academic research
        academic_keywords = [
            "research",
            "paper",
            "study",
            "arxiv",
            "published",
            "academic",
            "peer-reviewed",
        ]
        if any(kw in query_lower for kw in academic_keywords):
            logger.debug("Heuristic: academic_research (academic keywords)")
            return IntentType.ACADEMIC_RESEARCH

        return None

    async def _llm_analyze_intent(
        self, query: str, context: ConversationContext
    ) -> Dict:
        """
        Use LLM to analyze intent and recommend tools.

        Args:
            query: User query
            context: Conversation context

        Returns:
            Dictionary with intent analysis
        """

        context_summary = context.to_summary() if context else "No previous context"

        prompt = INTENT_ANALYSIS_PROMPT.format(query=query, context=context_summary)

        try:
            response = await self.llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=Config.INTENT_ANALYSIS_TEMPERATURE,
                max_tokens=500,
            )

            # Extract JSON from response
            intent_analysis = self._extract_json(response)

            if not intent_analysis:
                logger.warning("Could not parse LLM intent analysis response")
                # Fallback to general knowledge
                return {
                    "intent_type": "general_knowledge",
                    "confidence": 0.5,
                    "primary_tool": "llm",
                    "reasoning": "Could not analyze intent",
                }

            return intent_analysis

        except Exception as e:
            logger.error(f"LLM intent analysis error: {e}")
            return {
                "intent_type": "general_knowledge",
                "confidence": 0.3,
                "primary_tool": "llm",
                "reasoning": f"Analysis failed: {str(e)}",
            }

    async def _validate_intent(self, intent_analysis: Dict) -> Dict:
        """
        Validate intent analysis with a second LLM call.

        Args:
            intent_analysis: Initial intent analysis

        Returns:
            Updated intent analysis
        """

        prompt = INTENT_VALIDATION_PROMPT.format(
            analysis=json.dumps(intent_analysis, indent=2)
        )

        try:
            response = await self.llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200,
            )

            validation = self._extract_json(response)

            if validation and not validation.get("is_valid", True):
                logger.debug(
                    f"Intent validation feedback: {validation.get('feedback', '')}"
                )

                # Adjust confidence based on validation
                confidence_adjustment = validation.get("confidence_adjustment", 0)
                original_confidence = intent_analysis.get("confidence", 0.7)
                new_confidence = max(0.0, min(1.0, original_confidence + confidence_adjustment))

                intent_analysis["confidence"] = new_confidence
                intent_analysis["validation_feedback"] = validation.get("feedback", "")

            return intent_analysis

        except Exception as e:
            logger.warning(f"Intent validation error: {e}")
            return intent_analysis

    def _build_tool_selections(
        self, intent_analysis: Dict, tool_manager=None
    ) -> List[ToolSelection]:
        """
        Build tool selections from intent analysis.

        Args:
            intent_analysis: Intent analysis result
            tool_manager: Optional tool manager for availability checks

        Returns:
            List of tool selections
        """

        tool_selections = []

        # Primary tool
        primary_tool = intent_analysis.get("primary_tool", "llm")
        if primary_tool and primary_tool != "llm":
            tool_selections.append(
                ToolSelection(
                    name=primary_tool,
                    query=intent_analysis.get("tool_parameters", {})
                    .get(primary_tool, {})
                    .get("query", ""),
                    parameters=intent_analysis.get("tool_parameters", {}).get(
                        primary_tool, {}
                    ),
                    priority=1,
                )
            )

        # Secondary tools
        for i, secondary_tool in enumerate(intent_analysis.get("secondary_tools", [])):
            if secondary_tool != "llm":
                tool_selections.append(
                    ToolSelection(
                        name=secondary_tool,
                        query=intent_analysis.get("tool_parameters", {})
                        .get(secondary_tool, {})
                        .get("query", ""),
                        parameters=intent_analysis.get("tool_parameters", {}).get(
                            secondary_tool, {}
                        ),
                        priority=2 + i,
                    )
                )

        return tool_selections

    def _extract_json(self, text: str) -> Optional[Dict]:
        """
        Extract JSON from LLM response.

        Args:
            text: LLM response text

        Returns:
            Parsed JSON or None
        """

        try:
            # Try direct JSON parsing first
            return json.loads(text)
        except:
            pass

        # Try to find JSON in response
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass

        return None

    def _calculate_confidence(
        self, heuristic_intent: Optional[IntentType], llm_intent: Dict
    ) -> float:
        """
        Calculate confidence score for routing decision.

        Args:
            heuristic_intent: Heuristic classification result
            llm_intent: LLM analysis result

        Returns:
            Confidence score (0-1)
        """

        base_confidence = llm_intent.get("confidence", 0.5)

        # Boost confidence if heuristic and LLM agree
        if heuristic_intent:
            llm_intent_type = llm_intent.get("intent_type", "")
            if heuristic_intent.value == llm_intent_type:
                base_confidence = min(1.0, base_confidence + 0.15)
                logger.debug("Confidence boosted due to heuristic agreement")

        return min(1.0, max(0.0, base_confidence))

    def _determine_execution_strategy(self, strategy_str: str) -> ExecutionStrategy:
        """
        Determine execution strategy from string.

        Args:
            strategy_str: Strategy string from LLM

        Returns:
            ExecutionStrategy enum
        """

        strategy_map = {
            "parallel": ExecutionStrategy.PARALLEL,
            "sequential": ExecutionStrategy.SEQUENTIAL,
            "conditional": ExecutionStrategy.CONDITIONAL,
        }

        return strategy_map.get(strategy_str, ExecutionStrategy.PARALLEL)
