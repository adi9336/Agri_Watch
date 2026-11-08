"""
Agri_watch - Unified FastAPI Backend
Provides:
1. WebRTC Participant Token Generation for LiveKit audio streaming
2. Cognitive LangGraph Chat endpoint for text & voice transcripts
3. Direct Mandi Price, Multi-Mandi Arbitrage, and MSP Discovery APIs
4. Static file serving for the compiled React frontend SPA
"""

import os
import sys
import uuid
import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

# Add project root to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from voice_engine.generate_token import generate_participant_token
from agents.graph import get_agriwatch_graph
from agents.tools import (
    get_crop_price,
    compare_mandi_arbitrage,
    check_msp_floor,
    get_crop_price_trend,
    DISTRICT_NORM_MAP,
    CROP_NORM_MAP
)
from mandi_tracker import load_env
from agents.i18n import LANGUAGES, normalize_language

logger = logging.getLogger("agriwatch.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(
    title="Agri_watch API",
    description="Sovereign Indic Agricultural Voice Intelligence API & WebRTC Engine",
    version="2.0.0"
)

# Enable CORS for local development and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LangGraph
graph = get_agriwatch_graph()


# ---------------------------------------------------------------------------
# Request & Response Models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., description="User query in Hindi or Hinglish", example="झांसी में गेहूं का भाव क्या है?")
    session_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session state carryover")
    language: Optional[str] = Field("hi-IN", description="Reply language (BCP-47), e.g. hi-IN, ta-IN")


class ChatResponse(BaseModel):
    intent: str
    response: str
    status: str
    session_context: Dict[str, Any]


class TokenRequest(BaseModel):
    room: Optional[str] = Field("agri-room-1", description="LiveKit room name")
    identity: Optional[str] = Field(None, description="Unique participant identity")
    name: Optional[str] = Field("किसान भाई", description="Display name of user")
    language: Optional[str] = Field("hi-IN", description="Farmer language (BCP-47)")


class TokenResponse(BaseModel):
    serverUrl: str
    room: str
    identity: str
    token: str


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    """Health check endpoint monitoring system components."""
    env = load_env()
    has_livekit = bool(env.get("LIVEKIT_API_KEY") and env.get("LIVEKIT_API_SECRET"))
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    has_data_gov = bool(os.getenv("DATA_GOV_IN_KEY") or env.get("API_KEY"))
    has_gnani = bool(os.getenv("GNANI_API_KEY"))

    cache_file = ROOT_DIR / "data" / "mandi_prices_snapshot.csv"
    cache_ready = cache_file.exists() and cache_file.stat().st_size > 1024 * 1024

    return {
        "status": "online",
        "service": "Agri_watch Sovereign Indic Voice Engine",
        "providers": {
            "livekit_webrtc": has_livekit,
            "groq_llm": has_groq,
            "gnani_speech": has_gnani,
            "data_gov_in": has_data_gov,
            "local_mandi_cache": cache_ready
        }
    }


def _create_token(room: str, identity: Optional[str], name: str, language: str = "hi-IN") -> TokenResponse:
    env = load_env()
    server_url = env.get("LIVEKIT_URL", "")
    if not server_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LIVEKIT_URL is not configured in .env"
        )
    user_id = identity or f"farmer-{uuid.uuid4().hex[:6]}"
    try:
        jwt_token = generate_participant_token(room_name=room, identity=user_id, name=name, language=normalize_language(language))
        return TokenResponse(
            serverUrl=server_url,
            room=room,
            identity=user_id,
            token=jwt_token
        )
    except Exception as e:
        logger.error(f"[!] Error generating LiveKit token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/token", response_model=TokenResponse)
def get_livekit_token(
    room: str = Query("agri-room-1", description="LiveKit room name"),
    identity: Optional[str] = Query(None, description="Unique participant identity"),
    name: str = Query("किसान भाई", description="Display name of user"),
    language: str = Query("hi-IN", description="Farmer language (BCP-47)")
):
    """Generates a WebRTC participant JWT access token via GET query params."""
    return _create_token(room=room, identity=identity, name=name, language=language)


@app.post("/api/token", response_model=TokenResponse)
def post_livekit_token(payload: TokenRequest):
    """Generates a WebRTC participant JWT access token via JSON POST."""
    return _create_token(
        room=payload.room or "agri-room-1",
        identity=payload.identity,
        name=payload.name or "किसान भाई",
        language=payload.language or "hi-IN"
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    """
    Text / Transcribed voice chat endpoint delegating directly to the 
    compiled LangGraph 3-Node Cognitive Multi-Agent Harness.
    """
    query = payload.message.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query message cannot be empty")

    try:
        state_input = {
            "user_query": query,
            "language": normalize_language(payload.language),
            "session_context": payload.session_context or {}
        }
        output = graph.invoke(state_input)
        
        spoken = output.get("spoken_hindi_response") or "किसान भाई, मैं आपका प्रश्न समझ नहीं पाया। कृपया दोबारा पूछें।"
        return ChatResponse(
            intent=output.get("intent", "UNKNOWN"),
            response=spoken,
            status=output.get("status", "success"),
            session_context=output.get("session_context") or {}
        )
    except Exception as e:
        logger.error(f"[!] Chat execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Inference error: {e}")


@app.get("/api/price")
def get_price_endpoint(
    crop: str = Query(..., description="Crop name (e.g. Wheat, Gram, Mustard)"),
    district: str = Query(..., description="District or Mandi name (e.g. Jhansi, Rath, Kalyan)"),
    state: Optional[str] = Query(None, description="State (e.g. Uttar Pradesh, Maharashtra)"),
    date: Optional[str] = Query("today", description="Target date (e.g. today, yesterday, DD/MM/YYYY)")
):
    """Direct API for factual wholesale APMC mandi price discovery."""
    raw_res = get_crop_price(crop=crop, district=district, state=state, date=date)
    return json.loads(raw_res)


@app.get("/api/arbitrage")
def get_arbitrage_endpoint(
    crop: str = Query(..., description="Crop name"),
    district: str = Query(..., description="Base district or Mandi name"),
    state: Optional[str] = Query(None, description="State")
):
    """Direct API for the 5 nearest mandis reporting a crop, sorted by rate."""
    raw_res = compare_mandi_arbitrage(crop=crop, district=district, state=state)
    return json.loads(raw_res)


@app.get("/api/msp")
def get_msp_endpoint(crop: str = Query(..., description="Crop name")):
    """Direct API for Government Minimum Support Price (MSP) lookup."""
    raw_res = check_msp_floor(crop=crop)
    return json.loads(raw_res)


@app.get("/api/metadata")
def get_metadata():
    """Returns curated crops, districts, and popular queries for farmer UI chips."""
    popular_crops = [
        {"en": "Wheat", "hi": "गेहूँ", "icon": "🌾"},
        {"en": "Gram", "hi": "चना", "icon": "🌱"},
        {"en": "Mustard", "hi": "सरसों", "icon": "🌼"},
        {"en": "Paddy", "hi": "धान", "icon": "🍚"},
        {"en": "Peas(Dry)", "hi": "मटर", "icon": "🫛"},
        {"en": "Potato", "hi": "आलू", "icon": "🥔"},
        {"en": "Onion", "hi": "प्याज", "icon": "🧅"}
    ]
    popular_mandis = [
        {"en": "Jhansi", "hi": "झाँसी मंडी", "state": "Uttar Pradesh"},
        {"en": "Rath", "hi": "राठ मंडी", "state": "Uttar Pradesh"},
        {"en": "Mauranipur", "hi": "मऊरानीपुर मंडी", "state": "Uttar Pradesh"},
        {"en": "Atarra", "hi": "अतर्रा मंडी", "state": "Uttar Pradesh"},
        {"en": "Mahoba", "hi": "महोबा मंडी", "state": "Uttar Pradesh"},
        {"en": "Damoh", "hi": "दमोह मंडी", "state": "Madhya Pradesh"},
        {"en": "Satna", "hi": "सतना मंडी", "state": "Madhya Pradesh"},
        {"en": "Katni", "hi": "कटनी मंडी", "state": "Madhya Pradesh"},
        {"en": "Kalyan", "hi": "कल्याण मंडी (ठाणे)", "state": "Maharashtra"}
    ]
    suggested_questions = [
        "राठ मंडी में चने का भाव बताओ",
        "राठ के आसपास की मंडियों के दाम बताओ",
        "झाँसी में गेहूँ का आज का भाव क्या है?",
        "कल्याण मंडी में चने का क्या भाव चल रहा है?",
        "गेहूँ का सरकारी समर्थन मूल्य (MSP) कितना है?"
    ]
    languages = [{"code": code, "name": v["name"], "native": v["native"]} for code, v in LANGUAGES.items()]
    return {
        "languages": languages,
        "crops": popular_crops,
        "mandis": popular_mandis,
        "suggestions": suggested_questions
    }


# ---------------------------------------------------------------------------
# Static SPA Hosting (When frontend/dist is built)
# ---------------------------------------------------------------------------
DIST_DIR = ROOT_DIR / "frontend" / "dist"

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
else:
    @app.get("/")
    def root():
        return {
            "message": "Agri_watch API Backend is running.",
            "docs": "/docs",
            "frontend_status": "React frontend not built yet. Build frontend/ to enable SPA hosting."
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
