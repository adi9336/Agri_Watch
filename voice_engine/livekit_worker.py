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
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

sys.stdout.reconfigure(encoding='utf-8')

# Ensure parent directory is in Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PARENT_DIR, ".env"))

from livekit.agents import JobContext, JobProcess, cli, AgentServer, llm
from livekit.agents.voice import AgentSession, Agent, UserStateChangedEvent, CloseEvent
from livekit.agents.voice.turn import TurnHandlingOptions, InterruptionOptions
from livekit.plugins import silero
import livekit.plugins.gnani as gnani

from agents.graph import get_agriwatch_graph
from agents.state import AgentState
from agents.observability import traceable
from agents.llm_adapter import AgriWatchLangGraphLLM
from agents.i18n import normalize_language, stt_language, t

logger = logging.getLogger("agriwatch-worker")
logging.basicConfig(level=logging.INFO)

# LiveKit Agent Server instance for lk CLI and production runner
server = AgentServer()


def prewarm(proc: JobProcess):
    """
    Pre-allocates tuned Silero VAD into memory at worker process startup.
    Tuned parameters per production barge-in standards:
    - activation_threshold=0.7: High confidence threshold to filter ambient farm/mandi noise
    - min_speech_duration=0.15: 150ms speech duration window to reject transient clicks/breaths
    - prefix_padding_duration=0.2: 200ms padding for clean onset capture
    - min_silence_duration=0.5: 500ms trailing silence to detect turn completion
    """
    try:
        proc.userdata["vad"] = silero.VAD.load(
            activation_threshold=0.7,
            min_speech_duration=0.15,
            prefix_padding_duration=0.2,
            min_silence_duration=0.5,
        )
        logger.info("[+] Prewarmed tuned Silero VAD (thresh=0.7, min_dur=150ms) into worker process memory.")
    except Exception as e:
        logger.warning(f"[!] Prewarming VAD warning: {e}")


server.setup_fnc = prewarm


# Common Indic passive backchannels that should NOT abort or interrupt the agent
INDIC_BACKCHANNELS = {
    "हाँ", "हा", "हाँ जी", "हां", "हूँ", "हुं", "अच्छा", "जी", "ठीक", "ठीक है",
    "सही है", "ok", "okay", "hmm", "mhm"
}


class AgriWatchVoiceAgent(Agent):
    """
    Enhanced Voice Agent with sub-150ms Indic backchanneling and acoustic pre-responses.
    Configured with use_tts_aligned_transcript=True for strict LLM context alignment on interruption.
    """
    def __init__(self, instructions: str, llm: Any, language: str = "hi-IN"):
        super().__init__(instructions=instructions, llm=llm, use_tts_aligned_transcript=True)
        self.language = language

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage):
        """Fires immediately when STT finishes, before the cognitive LLM reasoning finishes."""
        text = ""
        if hasattr(new_message, "text_content") and new_message.text_content:
            text = new_message.text_content.strip()
        elif hasattr(new_message, "content"):
            if isinstance(new_message.content, str):
                text = new_message.content.strip()
            elif isinstance(new_message.content, list):
                text = " ".join(str(c) for c in new_message.content).strip()

        # If the user spoke a standalone backchannel filler while agent is speaking or listening, skip heavy reasoning
        cleaned_lower = text.lower().strip()
        if cleaned_lower in INDIC_BACKCHANNELS:
            logger.info(f"[*] Detected Indic passive backchannel '{text}'; skipping heavy query trigger.")
            return

        # For heavy temporal, holding ROI, or multi-mandi comparisons, speak an instant acoustic filler
        if any(w in text for w in ("रोक कर", "रोककर", "वेयरहाउस", "गोदाम", "पूरा हिसाब", "स्टोर")):
            filler = t(self.language, "filler_specialist")
            logger.info(f"[*] Emitting specialist pre-response filler: '{filler}'")
            try:
                self.session.say(filler, add_to_chat_ctx=False)
            except Exception as e:
                logger.warning(f"[!] Filler emit notice: {e}")
        elif any(w in text for w in ("आसपास", "दूसरी मंडी", "कहाँ बेचूँ", "मुनाफा", "महीने", "महीना", "हफ्ते", "हफ्ता", "रुझान", "दिन के हिसाब")):
            filler = t(self.language, "filler_lookup")
            logger.info(f"[*] Emitting acoustic pre-response filler: '{filler}'")
            try:
                self.session.say(filler, add_to_chat_ctx=False)
            except Exception as e:
                logger.warning(f"[!] Filler emit notice: {e}")


class AgriWatchVoiceAssistant:
    def __init__(self, language: str = "hi-IN", default_district: str = "Jhansi", vad: Optional[Any] = None):
        self.language = language
        self.default_district = default_district
        self.graph = get_agriwatch_graph()
        self.session_context: Dict[str, Any] = {}
        self.turn_counter: int = 0
        self.vad = vad or silero.VAD.load(
            activation_threshold=0.7,
            min_speech_duration=0.15,
            prefix_padding_duration=0.2,
            min_silence_duration=0.5,
        )

        # Load Gnani Speech Plugins (use_streaming=False uses local Silero VAD to eliminate 60s idle socket drops)
        gnani_key = os.getenv("GNANI_API_KEY")
        if gnani_key:
            self.stt = gnani.STT(language=stt_language(self.language), sample_rate=16000, api_key=gnani_key, use_streaming=False)
            self.tts = gnani.TTS(model="timbre-v2.5", voice="Pranav", language=self.language, sample_rate=16000, api_key=gnani_key)
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
    """LiveKit agent worker room entrypoint with advanced voice interaction primitives."""
    logger.info(f"Connecting to LiveKit room: {ctx.room.name}")
    await ctx.connect()

    # Language picked by the farmer in the web app (token attribute); defaults to Hindi
    participant = await ctx.wait_for_participant()
    language = normalize_language(participant.attributes.get("language"))
    logger.info(f"[*] Farmer language: {language}")

    cached_vad = ctx.proc.userdata.get("vad") if hasattr(ctx, "proc") and ctx.proc else None
    assistant_engine = AgriWatchVoiceAssistant(language=language, vad=cached_vad)
    agri_llm = AgriWatchLangGraphLLM(graph=assistant_engine.graph, language=language)

    agent = AgriWatchVoiceAgent(
        instructions=(
            "आप एग्री-वॉच हैं - भारतीय किसानों और ग्रामीण व्यापारियों के लिए आधिकारिक "
            "मंडी मूल्य और आर्बिट्रेज सलाहकार। सदैव सरल, सम्मानजनक और सटीक हिंदी में बोलें।"
        ),
        llm=agri_llm,
        language=language
    )

    # Modern voice turn handling: adaptive barge-in, false-interruption resumption, and background noise filtering
    # Modern voice turn handling: adaptive barge-in, false-interruption resumption, and background noise filtering
    turn_handling = TurnHandlingOptions(
        interruption=InterruptionOptions(
            enabled=True,
            mode="adaptive",
            resume_false_interruption=True,
            false_interruption_timeout=1.2,
            min_duration=0.15,
            min_words=2,
        )
    )

    session = AgentSession(
        vad=assistant_engine.vad,
        stt=assistant_engine.stt,
        tts=assistant_engine.tts,
        llm=agri_llm,
        turn_handling=turn_handling,
        user_away_timeout=12.0
    )

    # Proactive Inactive Farmer Re-engagement Task
    inactivity_task: Optional[asyncio.Task] = None

    async def user_presence_task():
        """Prompts inactive callers before closing the session to preserve quota."""
        try:
            for attempt in range(2):
                await asyncio.sleep(12)
                ping_msg = t(language, "inactivity_ping")
                logger.info(f"[*] Inactivity check {attempt + 1}: Prompting user.")
                await session.say(ping_msg)
            
            # Second timeout without response -> graceful farewell
            await asyncio.sleep(10)
            farewell = t(language, "farewell")
            logger.info("[*] Inactivity limit reached: Initiating graceful disconnect.")
            await session.say(farewell, allow_interruptions=False)
            await asyncio.sleep(3)
            session.shutdown()
        except asyncio.CancelledError:
            pass

    @session.on("user_state_changed")
    def _user_state_changed(ev: UserStateChangedEvent):
        nonlocal inactivity_task
        if ev.new_state == "away":
            if inactivity_task is None or inactivity_task.done():
                inactivity_task = asyncio.create_task(user_presence_task())
        else:
            if inactivity_task is not None and not inactivity_task.done():
                inactivity_task.cancel()
                inactivity_task = None

    @session.on("agent_false_interruption")
    def _on_false_interruption(ev: Any):
        logger.info("[*] False interruption detected (backchannel or transient noise); resuming playback.")

    @session.on("close")
    def _on_session_close(ev: CloseEvent):
        logger.info(f"[+] Agri_watch session closed gracefully (Reason: {ev.reason})")

    # Start voice session inside the room
    await session.start(agent, room=ctx.room)

    # Initial Indic greeting
    greeting = t(language, "greeting")
    logger.info(f"Sending Greeting: {greeting}")
    await session.say(greeting)


# =====================================================================
# Automated Mandi Data Sync Scheduler (8:00 PM IST Daily Cron)
# =====================================================================
_sync_scheduler_started = False
IST = timezone(timedelta(hours=5, minutes=30))


def start_daily_sync_scheduler(run_immediate_check: bool = False):
    """
    Spawns a lightweight background daemon thread that monitors clock time.
    At 20:00 (8:00 PM IST) daily, it triggers sync_mandi_data(days=1)
    to ingest all finalized APMC market rates across India into the local snapshot.
    """
    global _sync_scheduler_started
    if _sync_scheduler_started:
        return
    _sync_scheduler_started = True

    def _scheduler_loop():
        try:
            from scripts.daily_mandi_sync import sync_mandi_data
        except ImportError:
            logger.warning("[!] Could not import sync_mandi_data; daily sync scheduler disabled.")
            return

        logger.info("[+] Mandi Daily Sync Cron Scheduler active (Scheduled for 20:00 IST daily).")
        last_synced_day = None

        if run_immediate_check:
            try:
                logger.info("[*] Mandi Sync Scheduler: Running startup check...")
                sync_mandi_data(days=1)
            except Exception as e:
                logger.error(f"[!] Startup mandi sync notice: {e}")

        while True:
            try:
                now_ist = datetime.now(timezone.utc).astimezone(IST)
                today_str = now_ist.strftime("%Y-%m-%d")

                # Trigger at or after 20:00 (8:00 PM IST) once per calendar day
                if now_ist.hour >= 20 and last_synced_day != today_str:
                    logger.info(f"[*] 8:00 PM IST Mandi Sync Triggered for {today_str}...")
                    res = sync_mandi_data(days=1)
                    last_synced_day = today_str
                    logger.info(f"[+] 8:00 PM IST Mandi Sync Completed: {res.get('status')} (Added: {res.get('new_records_added', 0)} records)")
            except Exception as e:
                logger.error(f"[!] Error in Mandi Daily Sync Scheduler loop: {e}")

            time.sleep(60)

    t = threading.Thread(target=_scheduler_loop, daemon=True, name="AgriWatch-DailySyncScheduler")
    t.start()


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

    # Start background daily mandi price synchronization scheduler (8:00 PM IST)
    start_daily_sync_scheduler()

    # Standard LiveKit CLI entrypoint (supports: dev, start, download-files, lk console)
    cli.run_app(server)
