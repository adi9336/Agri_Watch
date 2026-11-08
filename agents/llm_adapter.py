"""
Agri_watch - LangGraph LLM Adapter for LiveKit Agents
Bridges LiveKit's real-time WebRTC/VAD/STT voice environment with the
decoupled LangGraph Multi-Agent Cognitive Harness.
"""

import time
import logging
from typing import Any, Optional, Dict
from livekit.agents import llm
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

from agents.graph import get_agriwatch_graph
from agents.state import AgentState
from agents.i18n import normalize_language, t
from agents.observability import traceable

logger = logging.getLogger("agriwatch.llm")


class LangGraphLLMStream(llm.LLMStream):
    def __init__(self, llm_instance: "AgriWatchLangGraphLLM", **kwargs):
        super().__init__(llm_instance, **kwargs)
        self._graph = llm_instance.graph
        self._llm = llm_instance

    async def _run(self) -> None:
        msgs = self._chat_ctx.messages()
        user_query = ""
        for m in reversed(msgs):
            if m.role == "user" and m.raw_text_content:
                user_query = m.raw_text_content.strip()
                break

        if not user_query:
            return

        logger.info(f"[*] LangGraphLLMStream: Ingesting query '{user_query}'")
        self._llm.turn_counter += 1

        state_input: AgentState = {
            "turn_id": self._llm.turn_counter,
            "user_query": user_query,
            "language": self._llm.language,
            "session_context": self._llm.session_context
        }

        # Invoke the compiled LangGraph state machine
        result = self._graph.invoke(state_input)
        self._llm.session_context = result.get("session_context") or {}
        spoken_response = (result.get("spoken_hindi_response") or "").strip()
        if not spoken_response:
            spoken_response = t(self._llm.language, "retry")

        logger.info(f"[+] LangGraphLLMStream: Emitting response (Intent: {result.get('intent')}): '{spoken_response}'")

        chunk = llm.ChatChunk(
            id=f"agri_{int(time.time() * 1000)}",
            delta=llm.ChoiceDelta(role="assistant", content=spoken_response)
        )
        await self._event_ch.send(chunk)


class AgriWatchLangGraphLLM(llm.LLM):
    """
    Sovereign Indic Agricultural Intelligence LLM Adapter
    Conforms to LiveKit Agents v1.8+ llm.LLM protocol, delegating cognitive reasoning
    and multi-agent routing to the compiled LangGraph harness.
    """
    def __init__(self, graph=None, language: str = "hi-IN"):
        super().__init__()
        self.graph = graph or get_agriwatch_graph()
        self.language = normalize_language(language)
        self.session_context: Dict[str, Any] = {}
        self.turn_counter: int = 0

    @property
    def model(self) -> str:
        return "agri-watch-langgraph-v1"

    @property
    def provider(self) -> str:
        return "AgriWatch-LangGraph"

    def chat(self, *, chat_ctx: llm.ChatContext, **kwargs) -> llm.LLMStream:
        tools = kwargs.get("tools") or []
        conn_opts = kwargs.get("conn_options") or DEFAULT_API_CONNECT_OPTIONS
        return LangGraphLLMStream(self, chat_ctx=chat_ctx, tools=tools, conn_options=conn_opts)


# Alias for backward compatibility
AgriWatchLLM = AgriWatchLangGraphLLM
