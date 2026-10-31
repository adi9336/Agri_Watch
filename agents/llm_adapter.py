"""
Agri_watch - Sovereign LLM Adapter for LiveKit Agents
Bridges LiveKit's standard LLM interface (llm.LLM, llm.LLMStream)
with the Dual-Loop Steering Router, Agmarknet tool calling, and Indic NLU.
"""

import time
import logging
from typing import Any, Optional, List
from livekit.agents import llm
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
from agents.steering_router import SteeringRouter

logger = logging.getLogger("agriwatch.llm")


class AgriWatchLLMStream(llm.LLMStream):
    def __init__(self, llm_instance: "AgriWatchLLM", **kwargs):
        super().__init__(llm_instance, **kwargs)
        self._router = llm_instance.router

    async def _run(self) -> None:
        msgs = self._chat_ctx.messages()
        user_query = ""
        for m in reversed(msgs):
            if m.role == "user" and m.raw_text_content:
                user_query = m.raw_text_content.strip()
                break

        if not user_query:
            return

        logger.info(f"[*] AgriWatchLLM processing query: '{user_query}'")
        res = self._router.process_request(query=user_query)
        spoken_response = res.get("spoken_hindi_response", "")

        chunk = llm.ChatChunk(
            id=f"agri_{int(time.time() * 1000)}",
            delta=llm.ChoiceDelta(role="assistant", content=spoken_response)
        )
        await self._event_ch.send(chunk)


class AgriWatchLLM(llm.LLM):
    """
    Sovereign Indian Agricultural Market Intelligence LLM
    Conforms to LiveKit Agents v1.8+ llm.LLM protocol.
    """
    def __init__(self, router: Optional[SteeringRouter] = None):
        super().__init__()
        self.router = router or SteeringRouter()

    @property
    def model(self) -> str:
        return "agri-watch-sovereign-v1"

    @property
    def provider(self) -> str:
        return "AgriWatch"

    def chat(self, *, chat_ctx: llm.ChatContext, **kwargs) -> llm.LLMStream:
        tools = kwargs.get("tools") or []
        conn_opts = kwargs.get("conn_options") or DEFAULT_API_CONNECT_OPTIONS
        return AgriWatchLLMStream(self, chat_ctx=chat_ctx, tools=tools, conn_options=conn_opts)

