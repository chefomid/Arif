import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Arif, a helpful multimodal AI assistant running locally on a Jetson device.

You have access to vision detection logs from a camera with timestamps. When the user asks about the environment, past events, or what you have seen, use the scene context provided below.

Be concise and accurate. If you do not have relevant scene data, say so clearly."""


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
        self._model = settings.llm_model

    async def chat(
        self,
        messages: list[dict[str, str]],
        scene_context: str = "",
    ) -> str:
        system = SYSTEM_PROMPT
        if scene_context:
            system += f"\n\n## Recent scene detections\n{scene_context}"

        full_messages = [{"role": "system", "content": system}, *messages]
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                temperature=0.7,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.exception("LLM chat failed")
            raise RuntimeError(
                f"LLM unavailable at {get_settings().llm_base_url}. "
                "Ensure llama-server is running with Nemotron. "
                f"Details: {exc}"
            ) from exc

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        scene_context: str = "",
    ) -> AsyncIterator[str]:
        system = SYSTEM_PROMPT
        if scene_context:
            system += f"\n\n## Recent scene detections\n{scene_context}"

        full_messages = [{"role": "system", "content": system}, *messages]
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                temperature=0.7,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            logger.exception("LLM stream failed")
            raise RuntimeError(f"LLM stream failed: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            import asyncio

            await asyncio.wait_for(self._client.models.list(), timeout=3.0)
            return True
        except Exception:
            return False


llm_client = LLMClient()
