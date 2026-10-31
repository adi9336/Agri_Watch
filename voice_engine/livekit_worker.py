"""
Agri_watch - LiveKit WebRTC Voice Worker
Integrates:
1. Silero VAD (Voice Activity Detection & sub-100ms Barge-in Interruption)
2. Gnani Indic STT & TTS (livekit.plugins.gnani)
3. Dual-Loop Steering Router (agents.steering_router) for Mandi Pricing & Arbitrage
4. WebRTC Bi-directional Audio Session Management with LiveKit Cloud
5. LangSmith Observability Tracing
"""

import os
import sys
import asyncio
import logging
from typing import Optional

sys.stdout.reconfigure(encoding='utf-8')

# Ensure parent directory is in Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PARENT_DIR, ".env"))

from livekit.agents import JobContext, WorkerOptions, cli, AgentServer
from livekit.agents.voice import AgentSession, Agent, UserInputTranscribedEvent, ConversationItemAddedEvent
from livekit.plugins import silero
import livekit.plugins.gnani as gnani

from agents.steering_router import SteeringRouter
from agents.tools import LIVEKIT_TOOLS
from agents.observability import traceable

logger = logging.getLogger("agriwatch-worker")
logging.basicConfig(level=logging.INFO)

# LiveKit Agent Server instance for lk CLI and production runner
server = AgentServer()


class AgriWatchVoiceAssistant:
    def __init__(self, language: str = "hi-IN", default_district: str = "Jhansi"):
        self.language = language
        self.default_district = default_district
        self.router = SteeringRouter()

        # Load Silero VAD (Inner Reactive Loop)
        self.vad = silero.VAD.load()

        # Load Gnani Speech Plugins
        gnani_key = os.getenv("GNANI_API_KEY")
        if gnani_key:
            self.stt = gnani.STT(language=self.language, sample_rate=16000)
            self.tts = gnani.TTS(model="timbre-v2.5", voice="Pranav", sample_rate=16000)
        else:
            logger.warning("[!] GNANI_API_KEY not found in .env; running in simulated audio mode.")
            self.stt = None
            self.tts = None

    @traceable(name="VoiceWorker:handle_user_utterance", run_type="chain")
    def handle_user_utterance(self, transcript: str) -> str:
        """Processes user voice transcription through outer-loop deliberative router."""
        logger.info(f"[*] Ingested user transcript: \"{transcript}\"")
        res = self.router.process_request(query=transcript)
        spoken_response = res.get("spoken_hindi_response", "")
        logger.info(f"[*] Synthesized agent response: \"{spoken_response}\"")
        return spoken_response


@server.rtc_session(agent_name="agri_watch")
async def entrypoint(ctx: JobContext):
    """LiveKit agent worker room entrypoint."""
    logger.info(f"Connecting to LiveKit room: {ctx.room.name}")
    await ctx.connect()

    assistant_engine = AgriWatchVoiceAssistant(language="hi-IN")

    session = AgentSession(
        vad=assistant_engine.vad,
        stt=assistant_engine.stt,
        tts=assistant_engine.tts,
        allow_interruptions=True
    )

    agent = Agent(
        instructions=(
            "आप एग्री-वॉच हैं - भारतीय किसानों और ग्रामीण व्यापारियों के लिए आधिकारिक "
            "मंडी मूल्य और आर्बिट्रेज सलाहकार। सदैव सरल, सम्मानजनक और सटीक हिंदी में बोलें।"
        ),
        tools=LIVEKIT_TOOLS
    )

    @session.on("user_input_transcribed")
    def on_user_input(event: UserInputTranscribedEvent):
        if event.is_final and event.transcript.strip():
            text = event.transcript.strip()
            logger.info(f"[Farmer Voice Query]: {text}")
            reply = assistant_engine.handle_user_utterance(text)
            asyncio.create_task(session.say(reply))

    @session.on("conversation_item_added")
    def on_conversation_item(event: ConversationItemAddedEvent):
        # Triggered when typing text in console mode or when text chat messages arrive
        if event.item.role == "user" and event.item.raw_text_content:
            text = event.item.raw_text_content.strip()
            if text:
                logger.info(f"[Farmer Text Query]: {text}")
                reply = assistant_engine.handle_user_utterance(text)
                asyncio.create_task(session.say(reply))

    # Start voice session inside the room
    await session.start(agent, room=ctx.room)

    # Initial Indic greeting
    greeting = "नमस्ते किसान भाई! मैं एग्री-वॉच हूँ। आप किस फसल या मंडी का भाव जानना चाहते हैं?"
    logger.info(f"Sending Greeting: {greeting}")
    await session.say(greeting)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("[*] Running Agri_watch Voice Worker Self-Test...")
        engine = AgriWatchVoiceAssistant()
        print(f"[+] Silero VAD loaded: {engine.vad}")
        print(f"[+] Dual-Loop Steering Router ready: {engine.router}")
        
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
