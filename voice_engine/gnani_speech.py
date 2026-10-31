"""
Agri_watch - Gnani.ai Voice Integration Module
Supports:
1. LiveKit Plugin Mode (livekit.plugins.gnani STT/TTS for real-time WebRTC voice sessions)
2. Standalone REST/SSE API Mode (https://api.vachana.ai with X-API-Key-ID for direct scripting/fallback)
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from typing import Optional, Dict

sys.stdout.reconfigure(encoding='utf-8')

VACHANA_BASE_URL = "https://api.vachana.ai"
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")


from dotenv import load_dotenv
load_dotenv(ENV_PATH)


def get_gnani_api_key() -> Optional[str]:
    """Retrieve GNANI_API_KEY from environment or .env file."""
    key = os.getenv("GNANI_API_KEY")
    if key:
        return key
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() in ("GNANI_API_KEY", "GNANI_KEY", "VACHANA_API_KEY"):
                        return v.strip().strip('"').strip("'")
    return None


class GnaniVoiceClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_gnani_api_key()

    def get_livekit_stt(self, language: str = "hi-IN", sample_rate: int = 16000, use_streaming: bool = False):
        """Creates a LiveKit Gnani STT instance."""
        import livekit.plugins.gnani as gnani
        return gnani.STT(language=language, sample_rate=sample_rate, api_key=self.api_key, use_streaming=use_streaming)

    def get_livekit_tts(self, model: str = "timbre-v2.5", voice: str = "Pranav", sample_rate: int = 16000):
        """Creates a LiveKit Gnani TTS streaming instance."""
        import livekit.plugins.gnani as gnani
        return gnani.TTS(model=model, voice=voice, sample_rate=sample_rate, api_key=self.api_key)

    def synthesize_speech_rest(
        self,
        text: str,
        language: str = "hi-IN",
        output_format: str = "wav"
    ) -> bytes:
        """
        Direct REST fallback for Text-to-Speech via https://api.vachana.ai
        """
        if not self.api_key:
            raise ValueError("GNANI_API_KEY is not configured in .env or environment.")

        endpoint = f"{VACHANA_BASE_URL}/api/v1/tts/inference"
        payload = json.dumps({
            "text": text,
            "language": language,
            "format": output_format
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "X-API-Key-ID": self.api_key,
            "User-Agent": "AgriWatch/1.0"
        }

        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agri_watch Gnani Speech Engine")
    parser.add_argument("--test-tts", type=str, help="Text to synthesize using Gnani TTS")
    parser.add_argument("--lang", type=str, default="hi-IN", help="Language code (e.g. hi-IN, mr-IN)")
    parser.add_argument("--check-plugin", action="store_true", help="Verify livekit-plugins-gnani availability")

    args = parser.parse_args()

    print("[*] Agri_watch Voice Engine Initialized")

    # Verify LiveKit plugin loading
    try:
        import livekit.plugins.gnani as gnani
        print("[+] livekit.plugins.gnani is successfully imported and available.")
        print(f"    Available exports: {', '.join([x for x in dir(gnani) if not x.startswith('_')][:6])}")
    except Exception as e:
        print(f"[-] livekit.plugins.gnani import error: {e}")

    api_key = get_gnani_api_key()
    if api_key:
        print(f"[+] GNANI_API_KEY detected: {api_key[:6]}...{api_key[-4:]}")
    else:
        print("[-] Notice: GNANI_API_KEY not yet configured in .env (add GNANI_API_KEY=your_key to enable cloud speech)")

    if args.test_tts:
        print(f"\n[*] Synthesizing spoken Hindi test prompt:")
        print(f"    Text: \"{args.test_tts}\"")
        if not api_key:
            print("[!] Cannot call Gnani API without GNANI_API_KEY in .env. Showing simulated output:")
            print("    [Simulated TTS] Audio frame generation ready (16kHz PCM / WAV format).")
        else:
            try:
                client = GnaniVoiceClient(api_key=api_key)
                audio_bytes = client.synthesize_speech_rest(args.test_tts, language=args.lang)
                out_file = "test_output.wav"
                with open(out_file, "wb") as f:
                    f.write(audio_bytes)
                print(f"[+] Audio successfully synthesized and saved to {out_file} ({len(audio_bytes)} bytes)")
            except Exception as e:
                print(f"[!] REST TTS API call note: {e}")

