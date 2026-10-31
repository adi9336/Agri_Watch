"""
Agri_watch - WebRTC Participant Token Generator
Generates participant JWT access tokens to connect a microphone to the LiveKit room.
"""

import os
import sys
import argparse
from livekit import api

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from mandi_tracker import load_env


def generate_participant_token(room_name: str = "agri-room-1", identity: str = "farmer-1", name: str = "Farmer User") -> str:
    env = load_env()
    api_key = env.get("LIVEKIT_API_KEY")
    api_secret = env.get("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        raise ValueError("LIVEKIT_API_KEY or LIVEKIT_API_SECRET missing in .env")

    token = (
        api.AccessToken(api_key=api_key, api_secret=api_secret)
        .with_identity(identity)
        .with_name(name)
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )
    return token


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate LiveKit room token")
    parser.add_argument("--room", default="agri-room-1", help="Room name (default: agri-room-1)")
    parser.add_argument("--identity", default="farmer-1", help="Participant identity")
    args = parser.parse_args()

    env = load_env()
    url = env.get("LIVEKIT_URL", "")
    token = generate_participant_token(room_name=args.room, identity=args.identity)

    print("\n" + "=" * 60)
    print("🌾 Agri_watch WebRTC Room Token Generated")
    print("=" * 60)
    print(f"Server URL : {url}")
    print(f"Room Name  : {args.room}")
    print(f"Identity   : {args.identity}")
    print("\n[JWT Access Token]:")
    print(token)
    print("\n[How to Test from Browser]:")
    print(f"1. Open LiveKit Agents Playground: https://agents-playground.livekit.io/")
    print(f"2. Enter your LiveKit Server URL and Token above.")
    print(f"3. Click Connect and speak into your mic in Hindi (e.g., 'भैया झाँसी में गेहूँ का भाव बताओ').")
    print("=" * 60 + "\n")
