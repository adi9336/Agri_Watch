# Implementation Plan: Agri_watch Voice Engine

## Milestone M1 — Official Gnani LiveKit Plugin Setup & Voice Pipeline
- **Deliverable:** Install and configure the official `livekit-plugins-gnani` package with LiveKit Agents:
  - Authentication: `GNANI_API_KEY` loaded from `.env`
  - STT: `livekit.plugins.gnani.STT(language="hi-IN")` via streaming WebSockets
  - TTS: `livekit.plugins.gnani.TTS(model="timbre-v2.5", voice="Pranav")` with streaming audio
- **Demo Command:**
  ```bash
  python -c "import livekit.plugins.gnani; print('Gnani LiveKit Plugin Loaded Successfully')"
  ```

---

## Milestone M2 — Dual-Loop Steering Router & Multi-Agent Pricing
- **Deliverable:** `agents/steering_router.py` implementing:
  - Inner reactive loop: Entity resolution (Fuzzy crop mapping `Dhan` -> `Paddy`, `Jhansi` -> `Jhansi APMC`)
  - Outer deliberative loop: Multi-mandi price arbitrage + MSP benchmark comparison + Closed-mandi fallback
- **Demo Command:**
  ```bash
  python -m agents.steering_router --state "Uttar Pradesh" --district "Jhansi" --crop "Wheat"
  ```

---

## Milestone M3 — LiveKit WebRTC Voice Worker & Barge-in Pipeline
- **Deliverable:** `voice_engine/livekit_worker.py` integrating:
  - Audio resampler (48kHz WebRTC Opus <-> 16kHz linear PCM)
  - Silero VAD speech boundary detection
  - Sub-100ms barge-in / speech interruption cancellation
- **Demo Command:**
  ```bash
  python -m voice_engine.livekit_worker dev
  ```

