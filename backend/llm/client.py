"""LLM client abstraction layer supporting multiple providers."""

import json
import logging
import re
from typing import AsyncGenerator, Dict, List, Optional, Union

import ollama

from core.config import Config
from core.exceptions import LLMError, LLMTimeoutError
from core.logger import setup_logger

logger = setup_logger(__name__)


class LLMClient:
    """
    Unified LLM interface supporting multiple providers.
    Abstracts away provider-specific logic.
    """

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen3:8b",
        timeout: int = 60,
    ):
        """
        Initialize LLM client.

        Args:
            provider: LLM provider (ollama, openai, gemini, claude)
            model: Model name/ID
            timeout: Request timeout in seconds
        """
        self.provider = provider
        self.model = model
        self.timeout = timeout

        logger.info(f"Initializing LLM client: {provider}/{model}")

        if provider == "ollama":
            self._client = OllamaClient(model, timeout)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        logger.info(f"LLM client ready: {provider}/{model}")

    async def generate(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
    ) -> Union[str, AsyncGenerator]:
        """
        Generate response from LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            stream: Whether to stream response

        Returns:
            Generated text (or async generator if streaming)
        """
        try:
            if stream:
                return await self._client.stream_generate(messages, temperature, max_tokens)
            else:
                return await self._client.generate(messages, temperature, max_tokens)

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise LLMError(f"Generation failed: {e}", provider=self.provider)

    async def analyze_intent(self, prompt: str) -> Dict:
        """
        Analyze user intent with structured JSON output.

        Args:
            prompt: Analysis prompt

        Returns:
            Parsed JSON from LLM response
        """
        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self._client.generate(
                messages,
                temperature=0.3,  # Lower temp for deterministic output
                max_tokens=500,
            )

            # Parse JSON from response
            json_obj = self._extract_json(response)

            if json_obj:
                return json_obj

            logger.warning("Could not parse JSON from intent analysis response")
            return {
                "intent_type": "general_knowledge",
                "confidence": 0.5,
                "primary_tool": "llm",
                "reasoning": "Could not parse response as JSON",
            }

        except Exception as e:
            logger.error(f"Intent analysis error: {e}")
            raise LLMError(f"Intent analysis failed: {e}", provider=self.provider)

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from LLM response."""
        try:
            # Try direct parsing first
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

    async def set_model(self, model: str) -> None:
        """Change active model."""
        self.model = model
        await self._client.set_model(model)
        logger.info(f"Model changed to: {model}")


class OllamaClient:
    """Ollama provider implementation."""

    def __init__(self, model: str, timeout: int):
        """Initialize Ollama client."""
        self.model = model
        self.timeout = timeout

    async def generate(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate response using Ollama."""
        try:
            import asyncio

            # Run in thread pool to avoid blocking
            response = await asyncio.to_thread(
                self._generate_sync, messages, temperature, max_tokens
            )
            return response
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise LLMError(f"Ollama error: {e}", provider="ollama")

    def _generate_sync(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Synchronous Ollama generation (for thread pool)."""
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                stream=False,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    async def stream_generate(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        """Stream response using Ollama."""
        try:
            import asyncio

            async for chunk in asyncio.to_thread(
                self._stream_sync, messages, temperature, max_tokens
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise LLMError(f"Ollama stream error: {e}", provider="ollama")

    def _stream_sync(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
    ):
        """Synchronous Ollama streaming (for thread pool)."""
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )

            for chunk in response:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content

        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise

    async def set_model(self, model: str) -> None:
        """Change active model."""
        self.model = model
