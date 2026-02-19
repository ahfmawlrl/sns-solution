"""LLM unified client — Claude/GPT provider abstraction."""
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client supporting Claude and OpenAI providers.

    Usage:
        client = LLMClient(provider="claude")
        result = await client.generate(system_prompt, user_prompt)
    """

    def __init__(self, provider: str | None = None):
        self.provider = provider or settings.AI_PROVIDER

        if self.provider == "claude":
            self.model = "claude-sonnet-4-20250514"
        elif self.provider == "openai":
            self.model = "gpt-4o"
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text completion.

        Returns the generated text string.
        Falls back to a mock response if API keys are not configured.
        """
        if self.provider == "claude" and settings.ANTHROPIC_API_KEY:
            return await self._generate_claude(system_prompt, user_prompt, max_tokens, temperature)
        elif self.provider == "openai" and settings.OPENAI_API_KEY:
            return await self._generate_openai(system_prompt, user_prompt, max_tokens, temperature)
        else:
            # Mock response when API keys are not configured
            logger.warning("No API key configured for %s, returning mock response", self.provider)
            return f"[Mock {self.provider} response] Based on your request: {user_prompt[:100]}..."

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """Stream text generation token by token.

        Yields text chunks as they're generated.
        Falls back to mock streaming if API keys are not configured.
        """
        if self.provider == "claude" and settings.ANTHROPIC_API_KEY:
            async for chunk in self._stream_claude(system_prompt, user_prompt, max_tokens):
                yield chunk
        elif self.provider == "openai" and settings.OPENAI_API_KEY:
            async for chunk in self._stream_openai(system_prompt, user_prompt, max_tokens):
                yield chunk
        else:
            # Mock streaming
            mock = f"[Mock streamed response] Regarding: {user_prompt[:80]}..."
            for word in mock.split():
                yield word + " "

    # ── Claude (Anthropic) ──

    async def _generate_claude(
        self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float
    ) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        try:
            message = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text
        finally:
            await client.close()

    async def _stream_claude(
        self, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> AsyncIterator[str]:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        try:
            async with client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        finally:
            await client.close()

    # ── OpenAI ──

    async def _generate_openai(
        self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float
    ) -> str:
        import openai

        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            response = await client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""
        finally:
            await client.close()

    async def _stream_openai(
        self, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> AsyncIterator[str]:
        import openai

        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            stream = await client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        finally:
            await client.close()
