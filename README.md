# 🌾 AgriWatch: Solution Pitch

**🌐 Live app:** **[agri-watch-eight.vercel.app](https://agri-watch-eight.vercel.app)**

**🎬 Demo video (2 min):** **[Watch on Google Drive](https://drive.google.com/file/d/1WOFM06ZWQADyjP9vZlHh9ov3pcFgDlvs/view?usp=sharing)**. Live Hindi and Marathi voice calls, powered by Gnani Prisma and Timbre.

Built for the Gnani.ai Great Indian AI Internship Challenge

### The problem
Most Indian farmers sell their harvest without knowing the day's fair price. The government publishes daily mandi prices and the official MSP (Minimum Support Price), but in English, in tables and online. For a farmer at the mandi gate, that information is out of reach, so the trader's first offer often decides the price.

### The solution
**AgriWatch is a voice assistant farmers can simply talk to, in their own language.** A farmer asks, *"गाज़ियाबाद में चावल का आज का भाव क्या है?"*, and hears the answer within seconds: *"आज गाज़ियाबाद (हापूर मंडी) में चावल का भाव ₹4504 प्रति क्विंटल है।"*

- **10 Indian languages:** Hindi, Marathi, Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Punjabi and English. Both the voice and the whole screen switch.
- **Live mandi prices** from official government data (data.gov.in / Agmarknet).
- **Below-MSP warning**, using the official 2026-27 MSP list for all 22 notified crops.
- **The 5 nearest mandis**, ranked by best rate.
- **Hold-or-sell advice:** weighs storage cost against the price trend.
- **Honest by design:** if today's price isn't uploaded yet, it says so and offers nearby mandis or the MSP instead. Every number comes from a government source, never from the AI.

### Gnani AI models: what we use, and how
| Gnani model | What it does in AgriWatch | How it is applied and implemented |
|---|---|---|
| **Gnani Prisma**, speech-to-text (`vachana-stt-v3`) | Turns the farmer's spoken question into text in their language | Runs inside the LiveKit voice agent (`voice_engine/livekit_worker.py`) through the official `livekit-plugins-gnani` plugin. The language the farmer picks in the app is passed into the call and mapped to one Prisma locale (`hi-IN`, `mr-IN`, … in `agents/i18n.py`). Audio is 16 kHz, and Silero VAD detects when the farmer stops speaking before each utterance is sent for recognition. |
| **Gnani Timbre v2.5**, text-to-speech | Speaks every reply back in a natural Indian voice | Configured as the agent's voice (`model="timbre-v2.5"`, voice **Pranav**, `language` = the farmer's language). It voices the greeting, "checking the records" fillers while data loads, the answer itself and the inactivity check, in all 10 languages. The demo video also uses Timbre for the narrator (**Kaveri**) and the farmer (**Deepak**). |

### How a question flows
**Farmer speaks** → LiveKit (real-time call) → Silero VAD → **Gnani Prisma** (speech → text) → LangGraph agent (guardrail → Groq LLM choosing a price, MSP, nearby-mandi or hold-or-sell tool → backup path if the LLM is down) → official data → **Gnani Timbre v2.5** (text → speech) → **farmer hears the answer**.

### Where it runs
- **Website and API** on **Vercel**, Mumbai region: [agri-watch-eight.vercel.app](https://agri-watch-eight.vercel.app). This covers the dashboard, the MSP list and text chat in 10 languages.
- **The voice agent** is a long-running LiveKit worker (`run_local.sh`), because Vercel functions are short-lived. Voice calls on the website connect when the worker is running.

### Why it matters
It lets a farmer check the rate, spot a below-MSP offer and find a better mandi **before** selling, using only their voice and their own language. No reading, no typing and no English needed.

---

# 🌾 Agri_watch - Sovereign Indic Agricultural Voice Intelligence Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Cloud-f55036.svg)](https://groq.com/)
[![LiveKit](https://img.shields.io/badge/Voice-LiveKit%20WebRTC-00BFFF.svg)](https://livekit.io/)
[![Gnani.ai](https://img.shields.io/badge/Indic%20Speech-Gnani.ai-green.svg)](https://gnani.ai/)

**Agri_watch** is a production-grade, voice-first AI agent designed for Indian farmers and rural traders. It enables effortless, natural Hindi voice interaction over WebRTC to discover **live APMC Mandi wholesale prices**, calculate **multi-mandi transport arbitrage**, analyze **7-day price trends**, and verify **Government MSP (Minimum Support Price) floor protections**.

---

## 🏗️ System Architecture

Agri_watch decouples real-time audio streaming from cognitive deliberative reasoning using an event-driven architecture:

```mermaid
flowchart TD
    Farmer([👨‍🌾 Indian Farmer / Web User]) <-->|Spoken Voice / WebRTC| LK[LiveKit Cloud WebRTC Server]
    Farmer <-->|Modern Web Browser| WebUI[⚛️ React 19 SPA Frontend\nTailwind CSS, Glassmorphism, Dual Voice/Chat]

    subgraph BackendApp["⚡ Unified FastAPI Application (:8000)"]
        WebUI <-->|REST API / Static SPA| FAPI[FastAPI Server]
        FAPI --> TokenGen[WebRTC JWT Token Dispatcher]
        FAPI --> DirectAPI[APMC Price, Arbitrage, MSP APIs]
        FAPI --> LangGraphChat[Cognitive Chat Endpoint]
    end

    subgraph AudioEngine["🎙️ Real-Time Voice Environment (LiveKit Worker)"]
        LK <--> VAD[Silero VAD\n<100ms Barge-In Interruption]
        VAD <--> STT[Gnani Prisma STT\nhi-IN Speech-to-Text]
        TTS[Gnani Timbre TTS\nPranav Natural Hindi Voice] <--> LK
    end

    STT -->|Transcribed Utterance| LLMAdapter[LangGraph LLM Adapter]
    LLMAdapter -->|Spoken Response| TTS
    LangGraphChat --> LangGraph

    subgraph LangGraph["🧠 3-Node Cognitive Multi-Agent Harness"]
        direction TB
        G[1. Fast Guardrail & Scope Node\nSub-ms exits for greetings, affirmations, and off-topic]
        R[2. Groq Deliberative LLM Reasoner\nopenai/gpt-oss-120b with Tool Calling]
        F[3. Sovereign Offline Fallback Node\nZero-crash resilient local price retrieval]

        G -->|In-Scope Market Query| R
        G -->|Off-Topic / Affirmation| End1([Fast Voice Exit])
        R -->|Tool Execution| Tools[APMC Market Intelligence Suite]
        R -->|Cloud API Interruption| F
        Tools -->|Synthesized Spoken Answer| End2([Spoken Voice Output])
        F --> End2
    end
```

### 🛠️ Market Intelligence Suite (Agent Tools)
1. **`get_crop_price_tool`**: Fetches date-specific APMC modal wholesale rates. If today's rates have not yet been posted by the mandi, it chronologically scans and retrieves the nearest available date.
2. **`compare_mandi_arbitrage_tool`**: Compares commodity rates across multiple APMC markets within a district, adjusting for estimated diesel/freight costs ($\approx ₹35/\text{km}$) to recommend where the farmer will net the highest profit.
3. **`check_msp_floor_tool`**: Looks up official CACP (Commission for Agricultural Costs and Prices) Minimum Support Price floor benchmarks.
4. **`get_crop_price_trend_tool`**: Analyzes 7-day price movement and momentum (Rising, Falling, Stable) to guide whether to sell now or wait.

---

## 📋 Prerequisites

Before setting up Agri_watch, ensure you have:
- **Python**: Version `3.10`, `3.11`, or `3.12` installed.
- **Git**: Installed on your system.
- **API Keys**:
  - [Groq Cloud](https://console.groq.com) (Free account)
  - [LiveKit Cloud](https://cloud.livekit.io) (Free sandbox project)
  - [Gnani.ai](https://gnani.ai) (Indic STT/TTS API key)
  - [data.gov.in](https://data.gov.in) (Open Government Data API key, optional for live auctions)

---

## ⚡ Quickstart Setup ("Setup Skill")

Follow these steps to set up and run Agri_watch on your local machine:

### 1. Clone the Repository
```bash
git clone https://github.com/adi9336/Agri_Watch.git
cd Agri_Watch
```

### 2. Create and Activate a Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Required Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the `.env.example` template to `.env`:
```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your keys:
```ini
# Agmarknet / Government Open Data API
API_KEY=your_data_gov_in_api_key_here
DATA_GOV_IN_KEY=your_data_gov_in_api_key_here

# Groq Cloud (Ultra-fast Hindi reasoning)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

# Gnani.ai Indic Speech Engine (hi-IN STT & TTS)
GNANI_API_KEY=your_gnani_api_key_here

# LiveKit Cloud (WebRTC voice environment)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key_here
LIVEKIT_API_SECRET=your_livekit_api_secret_here

# LangSmith Observability (Optional)
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2_pt_your_langsmith_key_here
LANGSMITH_PROJECT=agriwatch
```

---

## 🚀 Running Agri_watch

### Mode 0: Unified Web UI & FastAPI Server (Recommended for Web Users)
Agri_watch comes with a modern React 19 single-page application and FastAPI backend.

**One-Click Launch:**
- **On Windows:**
  ```powershell
  .\run_local.bat
  ```
- **On Linux / macOS:**
  ```bash
  chmod +x run_local.sh
  ./run_local.sh
  ```

Or manually:
```bash
# 1. Build the React frontend SPA
cd frontend
npm install
npm run build
cd ..

# 2. Launch FastAPI (serves both REST APIs and frontend assets)
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at **[http://localhost:8000](http://localhost:8000)** to access:
- 🎙️ **Live WebRTC Voice Orb**: Connect directly via browser microphone with Silero VAD barge-in.
- 💬 **Factual Chat Interface**: Hindi conversational chat with instant Agmarknet price cards and suggestion chips.
- 📖 **Interactive Swagger API Docs**: At `http://localhost:8000/docs`.

---

### Mode 1: Docker & Cloud Deployment
Launch both the FastAPI web server and the LiveKit voice worker in isolated containers:
```bash
docker compose up --build
```
This automatically builds the frontend in a multi-stage Docker build, installs all Python dependencies, and starts both services with automatic restarts and healthchecks.

---

### Mode 2: Live WebRTC Voice Worker (Standalone CLI)
Connects directly to your LiveKit Cloud room and listens for real-time voice:
```bash
python voice_engine/livekit_worker.py dev
```

1. Open your browser and go to your **[LiveKit Cloud Console](https://cloud.livekit.io)**.
2. Navigate to **Agents** $\rightarrow$ **Playground**.
3. Select your agent (`agri_watch`), click **Connect**, and start speaking in Hindi!

### Mode 3: Interactive Terminal Console (No Microphone Required)
Test multi-turn text conversations and tool executions without starting LiveKit:
```bash
python voice_engine/interactive_console.py
```

### Mode 4: Direct Mandi Price Discovery CLI
Quickly test Agmarknet data retrieval for any crop and mandi:
```bash
python mandi_tracker.py --crop "चना" --district "कटनी" --date "पिछले हफ्ते"
```

---

## 🧪 Running Automated Tests

Run both the LangGraph multi-agent tests and the FastAPI/SPA integration suite:
```bash
# 1. Multi-Agent Cognitive Tests
python -m unittest tests/test_langgraph_pipeline.py

# 2. FastAPI & Web SPA Integration Tests
python -m unittest tests/test_backend_api.py
```

All 6 integration tests will verify:
- ✅ Fast-path greeting and affirmation handling
- ✅ Off-topic guardrail routing
- ✅ Single-entity disambiguation (asking for missing crop/district)
- ✅ Date-aware price discovery with nearest-date resolution
- ✅ Transport-adjusted multi-mandi arbitrage
- ✅ MSP floor protection queries

---

## 💡 Key Design & Conversational Intelligence

- **Spoken-First Conciseness**: LLM output is strictly limited to **1 to 2 short sentences**, formatted without markdown characters (`**`, `#`, bullets) or emojis so TTS engines pronounce numbers and currency cleanly.
- **Pan-India District Resolution**: Transparently recognizes mandis across state borders (e.g., *Katni*, *Jabalpur*, *Indore*, *Jhansi*, *Agra*, *Kota*).
- **In-Session Entity Continuity**: Maintains session memory across turns. If you ask about *"चना in लखनऊ"* and follow up with *"और गेहूं का भाव क्या था?"*, it seamlessly retains Lucknow without asking for your district again.
- **Autonomous Fallback**: If cloud connectivity is lost, the sovereign fallback node answers with locally cached market data to prevent dropping calls with farmers.

---

## 📂 Project Directory Structure

```text
Agri_watch/
├── backend/                    # Unified FastAPI Application
│   ├── __init__.py
│   └── app.py                  # WebRTC token, chat, prices, & SPA serving
├── frontend/                   # Modern React 19 + Tailwind CSS Frontend
│   ├── src/
│   │   ├── App.jsx             # Dual-mode Voice Orb & Factual Chat interface
│   │   ├── useLiveKitVoice.js  # LiveKit WebRTC hook with track subscription
│   │   ├── index.css           # Glassmorphism & pulsing waveform animations
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── agents/                     # LangGraph Multi-Agent Cognitive Harness
│   ├── fallback.py             # Sovereign offline fallback node
│   ├── graph.py                # StateGraph orchestration & conditional edges
│   ├── guardrail.py            # Scope, greeting, and affirmation guardrail
│   ├── llm_adapter.py          # LiveKit Agents v1.8+ LLM adapter
│   ├── llm_reasoner.py         # Groq LLM tool calling and synthesis node
│   ├── observability.py        # LangSmith tracing wrappers
│   ├── state.py                # AgentState TypedDict schema
│   └── tools.py                # LangChain market intelligence tool suite
├── data/
│   ├── mandi_prices_snapshot.csv # APMC Agmarknet snapshot
│   ├── market_directory.json   # 2,500+ APMC Mandi lookup directory
│   └── msp_benchmarks.json     # Official CACP MSP floor price benchmarks
├── tests/
│   ├── test_langgraph_pipeline.py # Comprehensive multi-agent unit tests
│   └── test_backend_api.py     # FastAPI endpoints & SPA delivery tests
├── voice_engine/               # LiveKit Supporting Audio Environment
│   ├── interactive_console.py  # Text-based interactive testing harness
│   ├── livekit_worker.py       # LiveKit WebRTC worker with Silero VAD & Gnani
│   ├── gnani_speech.py         # Gnani STT and TTS client definitions
│   └── generate_token.py       # LiveKit room access token generator
├── Dockerfile                  # Multi-stage production container build
├── docker-compose.yml          # Unified Web + Worker container orchestration
├── run_local.bat               # Windows one-click launcher
├── run_local.sh                # Linux/macOS launcher
├── mandi_tracker.py            # APMC Agmarknet data retrieval & date resolver
├── requirements.txt            # Python dependencies
├── .env.example                # Configuration template
└── README.md                   # Project documentation
```

---

## 🤝 Contributing & License
Contributions, feedback, and pull requests are welcome. Distributed under the MIT License.


---

# How AgriWatch works, in plain language

## 1. Big picture: every route a farmer's question can take

```mermaid
flowchart TD
    START(["Farmer opens the AgriWatch website"]) --> LANG["Farmer picks a language<br/>(or the last one used is kept)"]
    LANG --> HOW{"Does the farmer<br/>talk or type?"}

    HOW -- "Talks" --> V1["Ask the server for a pass<br/>to join a voice call"]
    V1 -- "Voice server not set up" --> VE1["Show: 'Voice server<br/>is not configured'"]
    V1 --> V2["Join the call and<br/>switch on the microphone"]
    V2 -- "No microphone, permission<br/>refused, or mic busy" --> VE2["Show a clear microphone<br/>message in the farmer's language"]
    V2 --> V3["The voice assistant joins<br/>and greets the farmer"]
    V3 --> V4["Listen until the farmer<br/>stops speaking"]
    V4 -- "Farmer stays silent" --> V5["Gently ask 'Anything else?'<br/>up to two times"]
    V5 -- "Farmer speaks again" --> V4
    V5 -- "Still silent" --> V6(["Say goodbye and end the call"])
    V4 -- "Speech can't be turned<br/>into text, again and again" --> VE3(["The call ends with an error"])
    V4 --> V7["Turn the farmer's speech into text"]

    HOW -- "Types" --> T0{"Is the message empty?"}
    T0 -- Yes --> TE(["The send button stays disabled"])
    T0 -- No --> T1["Send the question together<br/>with the conversation so far"]
    T1 -- "Server error" --> TE2["Show: 'Temporary problem,<br/>please ask again'"]

    V7 --> R{"Receptionist:<br/>is it a quick case?"}
    T1 --> R
    R -- "Off-topic: weather,<br/>pests, cricket…" --> RQ1["Reply: 'I only help with<br/>mandi prices, nearby mandis and MSP'"]
    R -- "Only 'yes' or 'ok'" --> RQ2["Reply: 'Another crop or mandi?'"]
    R -- "Only a greeting" --> RQ3["Greet back and ask<br/>which crop or mandi"]
    R -- "A real question" --> AI{"Is the AI service<br/>set up?"}

    AI -- No --> FB["Backup clerk:<br/>simple rules, no AI"]
    AI -- Yes --> AID["The AI reads the question,<br/>the recent conversation,<br/>and the crop and place in use"]
    AID -- "AI busy or unreachable,<br/>even after 2 automatic retries" --> FB
    AID --> AIC{"What does the AI decide?"}
    AIC -- "Something is missing" --> AQ["Ask back: 'Which crop?'<br/>or 'Which district or mandi?'"]
    AIC -- "It needs data" --> TOOLS["Use the right helper:<br/>price, nearest mandis, MSP,<br/>price trend, or hold-or-sell"]
    AIC -- "It can answer directly" --> AW
    TOOLS --> AW["The AI writes a 1–2 sentence answer<br/>in the farmer's language"]
    AW -- "The AI fails at this point" --> FB
    AW -- "The AI gives an empty answer" --> AE["Say: 'Please say your<br/>question again'"]

    FB --> FBC{"Is a crop mentioned<br/>or remembered?"}
    FBC -- No --> FBQ["Ask: 'Which crop?'"]
    FBC -- "Yes, asking about MSP" --> FBM["Read out the MSP"]
    FBC -- "Yes, asking a price" --> FBP["Read out the mandi price,<br/>or ask for the place,<br/>or say it isn't in the record"]

    RQ1 --> OUT{"Did the farmer<br/>talk or type?"}
    RQ2 --> OUT
    RQ3 --> OUT
    AQ --> OUT
    AW --> OUT
    AE --> OUT
    FBQ --> OUT
    FBM --> OUT
    FBP --> OUT
    OUT -- "Talked" --> OV["Speak the answer and show<br/>both sides as a live transcript"]
    OV --> V4
    OUT -- "Typed" --> OT["Show the answer in the chat,<br/>plus a price card when a crop<br/>and place are known"]
    OT --> END(["Farmer asks the next question"])
```

## 2. Each step in detail

### Step 1: Starting a voice call

```mermaid
flowchart TD
    A["Farmer taps 'Talk to the live assistant'<br/>or the glowing orb"] --> B["The screen switches to the voice view"]
    B --> C["Ask the server for a call pass<br/>that carries the farmer's language<br/>and asks for the AgriWatch assistant by name"]
    C -- "Voice server address missing" --> E1["Show: 'Voice server is not configured'"]
    C --> D["Join the call room"]
    D --> F["Switch on the microphone<br/>with echo and noise reduction"]
    F -- "No microphone found" --> E2["Show: 'Microphone not found'"]
    F -- "Permission refused" --> E3["Show: 'Please allow the microphone'"]
    F -- "Used by another app" --> E4["Show: 'Microphone is busy'"]
    F -- "Not supported" --> E5["Show: 'This microphone is not supported'"]
    E2 --> X["Leave the call;<br/>the farmer can try again"]
    E3 --> X
    E4 --> X
    E5 --> X
    F --> G["The assistant joins the same room"]
    G --> H["It reads the farmer's language<br/>from the call pass"]
    H --> I{"Is it one of the<br/>10 supported languages?"}
    I -- No --> J["Use Hindi"]
    I -- Yes --> K["Use that language for listening,<br/>thinking and speaking"]
    J --> L["Greet the farmer:<br/>'Hello! Which crop or mandi price<br/>would you like to know?'"]
    K --> L
    L --> M["Start listening"]
```

### Step 2: Listening and taking turns

```mermaid
flowchart TD
    A["Hear sound from the<br/>farmer's microphone"] --> B{"Is it clearly speech?<br/>Loud enough and longer<br/>than a click or a breath"}
    B -- "No: background noise" --> A
    B -- Yes --> C{"Is the assistant<br/>speaking right now?"}
    C -- Yes --> D{"Is it a real interruption,<br/>at least two words?"}
    D -- "No: a cough or 'hmm'" --> D1["Keep talking, picking up<br/>again after a short pause"] --> A
    D -- Yes --> D2["Stop talking and listen"]
    C -- No --> E
    D2 --> E["Wait for half a second of silence<br/>to know the farmer has finished"]
    E --> F["Send the recording to<br/>Gnani speech-to-text"]
    F -- "Request fails" --> F1["Restart listening<br/>and try again"] --> A
    F -- "Fails again and again" --> F2["End the call with an error"]
    F --> G{"Is the text only<br/>'yes', 'ok' or 'hmm'?"}
    G -- Yes --> G1["Meant to be ignored,<br/>but the receptionist still replies<br/>'Anything else?'"]
    G -- No --> H{"Is it a slow question?<br/>Nearby mandis, storage, past month<br/>(spotted from Hindi words only)"}
    H -- Yes --> H1["Say a short filler first:<br/>'One moment, I am checking the records…'"] --> I
    H -- No --> I["Pass the text to the brain"]

    A -. "Farmer silent for 12 seconds" .-> S1["Ask: 'Would you like another mandi price?'"]
    S1 -. "Silent for 12 more seconds" .-> S2["Ask once more"]
    S2 -. "Silent for 10 more seconds" .-> S3["Say goodbye and end the call"]
    S1 -. "Farmer speaks" .-> A
```

### Step 3: The receptionist (instant replies, no AI)

```mermaid
flowchart TD
    A["Take the farmer's sentence"] --> B{"Does it contain an off-topic word<br/>(weather, rain, pest, fertiliser,<br/>cricket, election…) and no market word<br/>like price, rate or mandi?"}
    B -- Yes --> B1["Reply: 'I only help with mandi prices,<br/>nearby mandis and MSP'"]
    B -- No --> C{"Is every word in the message<br/>just 'yes', 'ok', 'right'<br/>or 'thanks'?"}
    C -- Yes --> C1["Reply: 'Sure! Another crop or mandi?'"]
    C -- No --> D{"Three words or fewer,<br/>and a greeting such as<br/>namaste, vanakkam, sat sri akal?"}
    D -- Yes --> D1["Greet back and ask<br/>which crop or mandi"]
    D -- No --> E["Hand it to the AI expert"]
    B1 --> F["Reply uses a ready-made sentence<br/>in the farmer's language"]
    C1 --> F
    D1 --> F
```

### Step 4: The AI expert

```mermaid
flowchart TD
    A["A real question arrives"] --> B{"Is an AI key set up?"}
    B -- No --> FB["Hand over to the backup clerk"]
    B -- Yes --> C["Prepare what the AI sees:<br/>the house rules, the farmer's language,<br/>the crop and place in use,<br/>the last 4 messages, and the question"]
    C --> D["Ask the AI what to do"]
    D -- "Busy or network error" --> D1["Retry automatically,<br/>up to 2 times"]
    D1 -- "Still failing" --> FB
    D1 -- "Works" --> E
    D --> E{"What did the AI choose?"}
    E -- "Ask the farmer something" --> Q["Use its question as the answer,<br/>for example 'Which crop?'"]
    E -- "Answer directly" --> Q2["Use its words as the answer"]
    E -- "Use one or more helpers" --> T["Remember the crop and place it picked"]
    T --> T1["Run each helper"]
    T1 -- "A helper crashes" --> T2["Pass the error to the AI<br/>instead of a result"]
    T1 --> W["Ask the AI to turn the results<br/>into 1–2 short sentences"]
    T2 --> W
    W -- "This second request fails" --> FB
    W --> X{"Is the answer empty?"}
    Q --> X
    Q2 --> X
    X -- Yes --> X1["Say: 'Please say your question again'"]
    X -- No --> M["Save the question and the answer<br/>(the last 6 messages are kept)"]
    X1 --> M
    M --> OUT["The answer is ready"]
```

**The house rules the AI is given:**

| Rule | What it means for the farmer |
|---|---|
| Pick the helper by the kind of question | Price, nearby mandis, MSP, trend and storage each have their own helper |
| Answer only what was asked | No MSP or other mandis unless the farmer asks (except the below-MSP warning) |
| Always name the date when a price is not today's | The farmer is never told an old price is today's |
| Never invent a price or a date | If nothing is found, it says so |
| Warn when a price is below MSP | One extra sentence pointing to a government procurement centre |
| Never estimate transport cost or profit | Distances are given, money for the trip is not |
| Pass place and crop names in English | 'இந்தூரில்' is understood as Indore |
| Reply in the farmer's language, 1–2 sentences, no symbols | Short and clear when spoken aloud |

### Step 5: Looking up a price

```mermaid
flowchart TD
    A["Crop, place and date from the AI"] --> B["Understand the crop:<br/>gehu or गेहूँ means wheat,<br/>chana means gram, and so on"]
    B --> C{"Is the place a known mandi<br/>or town? (2,811 in the list)"}
    C -- Yes --> P["Use its district and state"]
    C -- No --> C2{"Is it a known district name<br/>in Hindi or English?"}
    C2 -- Yes --> P
    C2 -- No --> C3{"Does it start like<br/>a known mandi name?"}
    C3 -- Yes --> P
    C3 -- No --> C4["Use the name as given<br/>(Jhansi if no place at all)"]
    C4 --> D
    P --> D["Understand the date:<br/>today, yesterday, last week,<br/>or a written date"]
    D --> E{"Asking for today, and is<br/>a government data key set up?"}
    E -- Yes --> F["Ask the government website<br/>for today's rates<br/>(waits up to about 30 seconds)"]
    F -- "Found this crop there" --> R
    F -- "Nothing found or an error" --> G
    E -- No --> G["Look in the saved price file"]
    G -- "File not on this computer yet" --> G0["Download it once (about 50 MB)"] --> G
    G --> H{"Is there a rate for that exact date?<br/>(the named mandi's own rate first)"}
    H -- Yes --> R
    H -- No --> I{"Is there any other date<br/>for this crop and place?"}
    I -- Yes --> I1["Use the nearest earlier date<br/>(a later date only if nothing earlier)"] --> R
    I -- No --> NF["Report: 'Not in the official record'"]
    R["Price found: mandi, price and date"] --> S{"Does this crop have an MSP?"}
    S -- Yes --> S1["Note whether the price is below MSP,<br/>and by how much"]
    S -- No --> OUT
    S1 --> OUT["Give the AI the result,<br/>including whether it is today's rate"]
```

### Step 6: Finding the nearest mandis

```mermaid
flowchart TD
    A["Crop and place from the AI"] --> B["Find the place on the map<br/>(the centre of its district)"]
    B -- "Place has no map location" --> B1["Use a hand-made list<br/>of neighbouring districts"]
    B --> C["Pick every district within<br/>about 150 km by road"]
    B1 --> D
    C --> D["Collect each mandi's latest rate<br/>for this crop in those districts,<br/>from today's government rates<br/>and the saved price file"]
    D --> E{"Was any mandi found?"}
    E -- No --> E1["Report: 'No recent arrivals<br/>in this area'"]
    E -- Yes --> F{"Did at least 5 mandis report<br/>in the last 60 days?"}
    F -- Yes --> G["Keep only those recent rates"]
    F -- No --> G2["Also use older rates;<br/>each keeps its own date"]
    G --> H["Take the 5 nearest mandis"]
    G2 --> H
    H --> I["Sort those 5 by rate,<br/>highest first"]
    I --> J["Check the best rate against MSP"]
    J --> K["Give the AI the names, distance in km,<br/>rates and dates<br/>(no transport cost is estimated)"]
```

### Step 7: Answering an MSP question

```mermaid
flowchart TD
    A["Crop from the AI"] --> B["Understand the crop name"]
    B --> C{"Is it in the government's<br/>2026-27 MSP list? (all 22 crops)"}
    C -- Yes --> D["Give the MSP and the season"]
    C -- No --> E["Report: 'No MSP is announced<br/>for this crop'"]
```

### Step 8: Describing the price trend

```mermaid
flowchart TD
    A["Crop, place and time span<br/>(last week or last month)"] --> B["Collect up to 100 saved rates,<br/>plus today's government rates"]
    B -- "No rates at all" --> N["Report: 'No past data for this place'"]
    B --> C["Remove repeats and sort by date"]
    C --> D["Find the lowest, highest and latest rate"]
    D --> E["Compare the latest rate with<br/>the average of the few before it"]
    E --> F{"How big is the difference?"}
    F -- "Up by more than ₹30" --> F1["Rising"]
    F -- "Down by more than ₹30" --> F2["Falling"]
    F -- "Within ₹30" --> F3["Stable"]
    F1 --> G["Describe the price range<br/>and the overall change"]
    F2 --> G
    F3 --> G
```

### Step 9: Hold the crop or sell now?

```mermaid
flowchart TD
    A["Crop, place and days to store<br/>(30 if not said; kept between 7 and 180)"] --> B["Build a day-by-day price history<br/>for the last 60 days"]
    B --> B1{"Does the named mandi have<br/>at least 6 days of rates?"}
    B1 -- Yes --> B2["Use that mandi's history"]
    B1 -- No --> B3["Use the whole district's history"]
    B2 --> C{"Is there any history at all?"}
    B3 --> C
    C -- No --> C1["Say: 'No record, so I can't<br/>advise on storing'"]
    C -- Yes --> D["Work out the cost of storing:<br/>warehouse rent, loading and unloading,<br/>crop loss, and interest on the money"]
    D --> E{"Does the crop spoil quickly?<br/>onion, potato, tomato…"}
    E -- Yes --> E1["Say: 'Don't keep it in a normal warehouse;<br/>check cold-storage rates first'"]
    E -- No --> F{"At least 6 days of rates<br/>spread over 2 weeks?"}
    F -- No --> F1["Say: 'Too little data to predict.<br/>Storing costs about ₹X, so the price<br/>must rise at least that much'"]
    F -- Yes --> G["Find the typical daily price change,<br/>and a cautious version of it"]
    G --> H["Project the change over the storage days,<br/>never further ahead than the history covers"]
    H --> I["Rate the confidence: high, medium or low,<br/>from how much data there is,<br/>how consistent it is, and how old it is"]
    I --> J{"Does even the cautious projection<br/>beat the cost by ₹25,<br/>with confidence not low?"}
    J -- Yes --> J1["Hold: 'You may get about ₹X more<br/>after costs, but it is not guaranteed'"]
    J -- No --> K{"Is the normal projection<br/>below the cost?"}
    K -- Yes --> K1["Sell now: 'Prices are falling'<br/>or 'storing costs more than the likely gain'"]
    K -- No --> K2["Unclear: 'Sell now if you need the money'"]
    J1 --> L{"Is today's price below MSP?"}
    K1 --> L
    K2 --> L
    L -- Yes --> L1["Add: 'A government procurement centre<br/>is also an option'"]
    L -- No --> OUT["Give the AI the advice"]
    L1 --> OUT
```

### Step 10: The backup clerk (when the AI is unavailable)

```mermaid
flowchart TD
    A["The AI could not answer"] --> B{"Is a crop word in the sentence,<br/>or a crop remembered<br/>from earlier?"}
    B -- No --> B1["Ask: 'Which crop?'"]
    B -- Yes --> C["Look for a known district name<br/>in the sentence, or use the one<br/>remembered from earlier"]
    C --> D{"Does the sentence mention<br/>MSP or the government price?"}
    D -- Yes --> D1["Look up the MSP"]
    D1 -- "Found" --> D3["Read out the MSP"]
    D1 -- "Crop has no MSP" --> D2["Say: 'No MSP is announced<br/>for this crop'"]
    D -- No --> P{"Is a place known?"}
    P -- No --> P1["Ask: 'Which district or mandi?'"]
    P -- Yes --> E["Look up the price"]
    E -- "Found" --> E2["Read out the mandi price"]
    E -- "Nothing found" --> E1["Say: 'The price is not<br/>in the official record'"]
```

### Step 11: Giving the answer back

```mermaid
flowchart TD
    A["The answer text is ready"] --> B{"Voice call or text chat?"}
    B -- "Voice call" --> C["Gnani text-to-speech reads it aloud<br/>in the farmer's language"]
    C --> D["The answer bubble fills in<br/>word by word as it is spoken"]
    B -- "Voice call" --> U["The farmer's own words appear<br/>once speech-to-text finishes,<br/>first as a draft, then final"]
    D --> W["The transcript scrolls<br/>and stays after the call ends"]
    U --> W
    B -- "Text chat" --> T1["Show the answer bubble in the chat"]
    T1 --> T2{"Are a crop and place<br/>now remembered?"}
    T2 -- Yes --> T3["Look up that price and<br/>show a price card"]
    T3 -- "Lookup fails" --> T4["No card is shown"]
    T2 -- No --> T5["Only the chat bubble"]
```

### Step 12: Changing the language

```mermaid
flowchart TD
    A["Farmer picks a language<br/>from the dropdown"] --> B["Remember it in this browser"]
    B --> C["Switch every label, button,<br/>date and tab title on the page,<br/>loading the right script font"]
    C --> D{"Is a voice call running?"}
    D -- Yes --> D1["End it: a call uses one language"]
    D -- No --> E
    D1 --> E["The next call listens and speaks<br/>in that language<br/>(Hindi also copes with Hinglish)"]
    E --> F["Every AI answer is written<br/>in that language"]
    F --> G["Quick replies and backup answers<br/>use ready-made sentences<br/>in that language"]
```

### Step 13: The nightly price update (behind the scenes)

```mermaid
flowchart TD
    A["Every minute, check the clock<br/>(Indian time), while the voice<br/>assistant is running"] --> B{"Is it after 8 PM and<br/>not yet updated today?"}
    B -- No --> A
    B -- Yes --> C{"Is a government data key set up?"}
    C -- No --> C1["Skip and note an error in the log;<br/>try again tomorrow"] --> A
    C -- Yes --> D["Download today's rates for all of India,<br/>1,000 at a time, up to 25,000,<br/>with a short pause between pages"]
    D -- "A page fails" --> D1["Stop downloading for today<br/>and keep what was received"]
    D --> E["Skip rates that are already saved"]
    D1 --> E
    E --> F["Add the new rates to the saved price file"]
    F --> G["Mark today as done"] --> A
    B -. "Something crashes" .-> H["Note it in the log and<br/>check again in a minute"] -.-> A
```

## 3. Why each step is built this way

| Step | What happens | Why | File (optional) |
|---|---|---|---|
| Call pass asks for the assistant by name | The pass names the AgriWatch assistant and carries the language | A named assistant only joins rooms that ask for it, so this is what makes it join | `voice_engine/generate_token.py` |
| Language travels with the call | The assistant reads it when it joins | One setting controls listening, thinking and speaking | `voice_engine/livekit_worker.py` |
| Strict noise filter | Only clear speech counts; half a second of silence ends a turn | Farms and mandis are noisy; stray sounds shouldn't trigger answers | `voice_engine/livekit_worker.py` |
| Interruptions need two words | A cough or 'hmm' doesn't stop the assistant | Natural calls are full of small sounds | `voice_engine/livekit_worker.py` |
| Filler sentence for slow questions | "One moment, checking the records…" | Silence on a call feels like the line dropped | `voice_engine/livekit_worker.py` |
| Silence reminders, then goodbye | Two reminders, then the call ends | Saves credits and doesn't leave calls hanging | `voice_engine/livekit_worker.py` |
| One language code per call for speech-to-text | Never a mix like "English + Hindi" | Gnani rejects mixed codes; the Hindi model already handles Hinglish | `agents/i18n.py` |
| Receptionist before the AI | Greetings, 'ok' and off-topic get instant ready-made replies | Free, instant, and no AI tokens used | `agents/guardrail.py` |
| Short English instructions for the AI | About 630 tokens instead of 2,300 | Hindi text costs about 3x more tokens; this keeps under the 8,000 per minute limit | `agents/llm_reasoner.py` |
| Last 4 messages plus the crop and place in use | The AI remembers "and gram?" means the same place | Follow-up questions feel natural | `agents/llm_reasoner.py` |
| The AI only picks helpers and writes the answer | Numbers come from code, not the AI | AI is good at language, bad at arithmetic and facts | `agents/llm_reasoner.py` |
| Two automatic retries, then the backup clerk | The farmer still gets an answer when the AI is down | A voice call should never just go silent | `agents/graph.py` |
| Backup clerk never guesses | It asks for the place, or says "not in the record", instead of using defaults | A made-up price or the wrong district could cost the farmer money | `agents/fallback.py` |
| Market words override off-topic words | "Will prices rise after the rain?" reaches the AI | Rain and weather often affect prices; blocking them loses real questions | `agents/guardrail.py` |
| 2,811-mandi list and spelling fixes | 'Rath', 'रॉड' and Hindi names are understood | Farmers name their mandi, not the official district | `agents/tools.py` |
| Today's rate from the government website first | Then the saved file, then the nearest earlier date | Freshest data first, but always some honest answer | `agents/tools.py` |
| Always say the date | "Today's rate isn't posted yet; on 24 Sep it was…" | An old price passed off as today's could cost the farmer money | `agents/llm_reasoner.py` |
| Below-MSP check in code | Every price result says whether it is below MSP | The farmer learns they may be underpaid, without asking | `agents/tools.py` |
| Official 2026-27 MSP list | All 22 MSP crops with their government rates | Old MSP figures would give wrong warnings | `data/msp_benchmarks.json` |
| District map locations, worked out once | 560 district centres saved in a file | Lets "nearest mandis" work anywhere in India, not just a few districts | `scripts/build_district_coords.py` |
| 5 nearest, then sorted by rate | No transport cost is shown | Too many unknowns (vehicle, load, tolls) to give a trustworthy cost | `agents/tools.py` |
| Hold-or-sell uses a robust trend and a cautious estimate | One odd report can't flip the advice | Wrong "hold" advice costs the farmer real money | `agents/specialists/economic_advisor.py` |
| Full storage cost, including interest | Rent, handling, crop loss and money tied up | Leaving out interest makes storing look better than it is | `agents/specialists/economic_advisor.py` |
| Spoiling crops and thin data never get "hold" | Onion, potato, tomato; fewer than 6 days of data | No advice is better than confident wrong advice | `agents/specialists/economic_advisor.py` |
| Ready-made sentences in 10 languages | Greetings, reminders and backup answers | These replies don't use the AI, so they need their own translations | `agents/i18n.py` |
| Whole page translated, with script fonts | Labels, dates and tab title switch language | A Tamil farmer shouldn't face a Hindi screen | `frontend/src/i18n.js` |
| Live transcript of both sides | Farmer's words and the answer appear as bubbles | Builds trust: the farmer sees what was heard | `frontend/src/useLiveKitVoice.js` |
| Nightly update at 8 PM | Adds the day's rates for all of India | Mandis post rates during the day; the saved file stays current | `scripts/daily_mandi_sync.py` |

## 4. Every situation

| Situation | What the farmer sees |
|---|---|
| "राम राम" (a greeting) | An instant greeting back, asking which crop or mandi |
| "हाँ ठीक है" ("yes, okay") | "Sure! Another crop or mandi?" |
| "आज मौसम कैसा है?" (weather) | "I only help with mandi prices, nearby mandis and MSP" |
| "झाँसी का भाव बताओ" (place, no crop) | "Which crop would you like the price of?" |
| "चने का भाव?" (crop, no place) | "Please tell me your district or mandi" |
| "झाँसी में गेहूँ का भाव?" when today's rate is posted | Today's rate at that mandi |
| The same question before today's rate is posted | "Today's rate isn't recorded yet; on 24/09 it was ₹2,355" |
| A price below MSP | The price, plus "This is ₹230 below MSP; consider a government procurement centre" |
| A place with no records at all | "The price is not in the official record" |
| "राठ मंडी में चने का भाव" (a small mandi) | The Rath price, without being asked for the district |
| "और गेहूँ का?" ("and wheat?") after asking about Rath gram | Wheat price in Rath: the place is remembered |
| "आसपास की मंडियों के दाम" ("nearby mandi prices") | 5 nearest mandis with km and rates, highest first |
| A place with no map location | Nearby mandis from a hand-made neighbour list, or "no recent arrivals" |
| "गेहूँ का MSP?" (wheat MSP) | ₹2,585 per quintal (2026-27) |
| MSP for a crop without one, like onion | "No MSP is announced for this crop" |
| "भाव बढ़ रहा है या घट रहा है?" ("rising or falling?") | Rising, falling or stable, with the price range |
| "सोयाबीन रोक कर बेचूँ?" ("should I hold my soybean?") with a falling price | "Prices are falling; storing would cost about ₹71 a quintal, so sell now" |
| Storage question for onions | "It spoils quickly; check cold-storage rates first" |
| Storage question with very little data | "Too little data to predict; storing costs about ₹X" |
| "ट्रैक्टर का भाड़ा कितना?" ("how much is tractor freight?") | "I can't estimate transport cost" |
| Question in Tamil, Telugu, Marathi, etc. | The answer in that language, spoken and written |
| Farmer switches language mid-call | The call ends; the next call uses the new language |
| The AI is busy (too many requests) | A short wait while it retries, then an answer from the backup clerk |
| No AI key set | Every real question is answered by the backup clerk |
| Backup clerk, no crop mentioned | "Which crop?" |
| Backup clerk, nothing found | "The price is not in the official record" |
| Backup clerk, MSP for a crop without one | "No MSP is announced for this crop" |
| Backup clerk, place not named and none remembered | "Please tell me your district or mandi" |
| "हाँ, गेहूँ बताओ" ("yes, tell me wheat") | The wheat question is answered normally |
| "हाँ ठीक है" ("yes, okay") on its own | "Sure! Another crop or mandi?" |
| "बारिश के बाद भाव बढ़ेगा?" ("will prices rise after the rain?") | Treated as a market question and answered |
| A cough or "hmm" while the assistant talks | It keeps talking |
| Farmer interrupts with a real sentence | It stops and listens |
| Farmer goes silent | Two gentle reminders, then a goodbye |
| Speech-to-text keeps failing | The call ends with an error |
| Microphone missing, blocked or busy | A clear message in the farmer's language |
| Voice server not configured | "Voice server is not configured" |
| Typed chat fails | "Temporary problem, please ask again" |
| Typed question about a crop and place | The answer plus a price card |
| Government data key missing | Prices come only from the saved file, with their dates |

## 5. Lessons

1. **Let code handle facts and arithmetic, and the AI handle language.** The AI picks a helper and phrases the result; prices, distances, MSP checks and storage costs are all computed in code.
2. **Answer the cheap cases before calling the AI.** A rule-based receptionist handles greetings, "ok" and off-topic questions instantly and for free.
3. **Always have a fallback, and make it honest.** Retries, then a backup clerk, then "please repeat". But a fallback that invents numbers is worse than saying "I don't know".
4. **Say how old the data is.** Every answer names its date. Trust comes from transparency, not from sounding confident.
5. **Only advise when the cautious case still holds.** Hold-or-sell says "hold" only if even the pessimistic estimate pays off, and says nothing confident when data is thin.
