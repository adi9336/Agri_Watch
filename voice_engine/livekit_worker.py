"""
Agri_watch - LiveKit Supporting Voice Environment & WebRTC Worker
Role:
1. Supporting Environment for Real-Time Voice:
   - WebRTC bidirectional audio streaming
   - Silero VAD (Voice Activity Detection & sub-100ms Barge-in Interruption)
   - Gnani Indic STT (Prisma v3.0 / hi-IN)
   - Gnani Indic TTS (Timbre v2.5 / Pranav)
2. Decoupled Cognitive Brain:
   - Delegates all NLU, multi-mandi arbitrage, price discovery, and MSP floor checks
     to the compiled LangGraph Multi-Agent Harness (agents.graph).
3. LangSmith Observability Tracing.
"""

import os
import sys
import asyncio
import logging
from typing import Optional, Dict, Any

sys.stdout.reconfigure(encoding='utf-8')

# Ensure parent directory is in Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PARENT_DIR, ".env"))

from livekit.agents import JobContext, cli, AgentServer
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import silero
import livekit.plugins.gnani as gnani

from agents.graph import get_agriwatch_graph
from agents.state import AgentState
from agents.observability import traceable
from agents.llm_adapter import AgriWatchLangGraphLLM

logger = logging.getLogger("agriwatch-worker")
logging.basicConfig(level=logging.INFO)

# LiveKit Agent Server instance for lk CLI and production runner
server = AgentServer()


class AgriWatchVoiceAssistant:
    def __init__(self, language: str = "hi-IN", default_district: str = "Jhansi"):
        self.language = language
        self.default_district = default_district
        self.graph = get_agriwatch_graph()
        self.session_context: Dict[str, Any] = {}
        self.turn_counter: int = 0

        # Load Silero VAD (Inner Reactive Loop: speech start, end, sub-100ms barge-in)
        self.vad = silero.VAD.load()

        # Load Gnani Speech Plugins (use_streaming=False uses local Silero VAD to eliminate 60s idle socket drops)
        gnani_key = os.getenv("GNANI_API_KEY")
        if gnani_key:
            self.stt = gnani.STT(language=self.language, sample_rate=16000, use_streaming=False)
            self.tts = gnani.TTS(model="timbre-v2.5", voice="Pranav", sample_rate=16000)
        else:
            logger.warning("[!] GNANI_API_KEY not found in .env; running in simulated audio mode.")
            self.stt = None
            self.tts = None

    @traceable(name="VoiceWorker:handle_user_utterance", run_type="chain")
    def handle_user_utterance(self, transcript: str) -> str:
        """Processes user voice transcription through the LangGraph cognitive harness."""
        logger.info(f"[*] Ingested user transcript: \"{transcript}\"")
        self.turn_counter += 1
        state_input: AgentState = {
            "turn_id": self.turn_counter,
            "user_query": transcript,
            "session_context": self.session_context
        }
        output = self.graph.invoke(state_input)
        self.session_context = output.get("session_context") or {}
        spoken_response = output.get("spoken_hindi_response", "")
        logger.info(f"[+] LangGraph response generated (Intent: {output.get('intent')}): \"{spoken_response}\"")
        return spoken_response


@server.rtc_session(agent_name="agri_watch")
async def entrypoint(ctx: JobContext):
    """LiveKit agent worker room entrypoint (LiveKit = Supporting Voice Environment)."""
    logger.info(f"Connecting to LiveKit room: {ctx.room.name}")
    await ctx.connect()

    assistant_engine = AgriWatchVoiceAssistant(language="hi-IN")
    agri_llm = AgriWatchLangGraphLLM(graph=assistant_engine.graph)

    agent = Agent(
        instructions=(
            "आप एग्री-वॉच हैं - भारतीय किसानों और ग्रामीण व्यापारियों के लिए आधिकारिक "
            "मंडी मूल्य और आर्बिट्रेज सलाहकार। सदैव सरल, सम्मानजनक और सटीक हिंदी में बोलें।"
        ),
        llm=agri_llm
    )

    session = AgentSession(
        vad=assistant_engine.vad,
        stt=assistant_engine.stt,
        tts=assistant_engine.tts,
        llm=agri_llm,
        allow_interruptions=True
    )

    # Start voice session inside the room
    await session.start(agent, room=ctx.room)

    # Initial Indic greeting
    greeting = "नमस्ते किसान भाई! मैं एग्री-वॉच हूँ। आप किस फसल या मंडी का भाव जानना चाहते हैं?"
    logger.info(f"Sending Greeting: {greeting}")
    await session.say(greeting)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("[*] Running Agri_watch Voice Worker (LangGraph Powered) Pre-Flight Test...")
        engine = AgriWatchVoiceAssistant()
        print(f"[+] Silero VAD loaded: {engine.vad}")
        print(f"[+] LangGraph Cognitive Harness ready: {engine.graph}")

        # Test simulated end-to-end voice processing
        test_query = "भैया आज गेहूँ का क्या रेट है?"
        print(f"\n[*] Simulating incoming voice turn: '{test_query}'")
        reply = engine.handle_user_utterance(test_query)
        print(f"\n[+] Outbound Spoken Audio Response Generated:")
        print(f"    \"{reply}\"\n")
        print("[+] Voice Worker Pre-Flight PASSED.")
        sys.exit(0)

    # Standard LiveKit CLI entrypoint (supports: dev, start, download-files, lk console)
    cli.run_app(server)
