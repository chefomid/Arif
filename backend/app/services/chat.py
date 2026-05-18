import logging
import re

from app.services.llm_client import llm_client
from app.services.scene_memory import scene_memory

logger = logging.getLogger(__name__)

_TIME_QUERY_PATTERNS = [
    re.compile(r"\b(\d+)\s*(?:min(?:ute)?s?|mins?)\s*ago\b", re.I),
    re.compile(r"\bwhat (?:did you |was )?see\b", re.I),
    re.compile(r"\b(?:earlier|before|past|history)\b", re.I),
    re.compile(r"\bwhat(?:'s| is| was) (?:on|in|around)\b", re.I),
]


class ChatService:
    def __init__(self) -> None:
        self._history: list[dict[str, str]] = []

    def _needs_memory_query(self, text: str) -> bool:
        return any(p.search(text) for p in _TIME_QUERY_PATTERNS)

    def _build_scene_context(self, user_text: str) -> str:
        parts: list[str] = []

        rolling = scene_memory.get_rolling_summary()
        if rolling:
            parts.append(rolling)

        if self._needs_memory_query(user_text):
            minutes_match = re.search(r"\b(\d+)\s*(?:min(?:ute)?s?|mins?)\s*ago\b", user_text, re.I)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                query_result = scene_memory.query_recent(minutes=minutes)
            else:
                query_result = scene_memory.query_recent(minutes=5)

            if query_result:
                parts.append("## Retrieved scene events\n" + query_result)

        return "\n\n".join(parts)

    async def send(self, user_text: str) -> str:
        user_text = user_text.strip()
        if not user_text:
            return ""

        scene_context = self._build_scene_context(user_text)
        self._history.append({"role": "user", "content": user_text})

        reply = await llm_client.chat(self._history, scene_context=scene_context)
        self._history.append({"role": "assistant", "content": reply})
        return reply

    async def send_stream(self, user_text: str):
        user_text = user_text.strip()
        if not user_text:
            return

        scene_context = self._build_scene_context(user_text)
        self._history.append({"role": "user", "content": user_text})

        full_reply: list[str] = []
        async for token in llm_client.chat_stream(self._history, scene_context=scene_context):
            full_reply.append(token)
            yield token

        self._history.append({"role": "assistant", "content": "".join(full_reply)})

    def clear_history(self) -> None:
        self._history.clear()


chat_service = ChatService()
