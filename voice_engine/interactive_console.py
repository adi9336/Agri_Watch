"""
Agri_watch - Interactive Voice & Conversation Console
Enables interactive real-time conversation testing directly in the terminal
with full multi-turn session persistence, Groq reasoning, and Agmarknet live data.
"""

import os
import sys

# Ensure UTF-8 output on Windows console
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PARENT_DIR, ".env"))

from agents.graph import get_agriwatch_graph
from agents.state import AgentState


def start_console():
    print("=" * 65)
    print("🌾 Agri_watch - Real-Time Interactive Voice Intelligence Console")
    print("=" * 65)
    print("Model     : Groq (Auto-resolved Qwen / Llama)")
    print("Brain     : LangGraph Multi-Agent Cognitive Harness")
    print("Guardrail : Sub-millisecond Scope & Affirmation Protection")
    print("Type 'exit' or 'quit' to end session.")
    print("-" * 65)

    graph = get_agriwatch_graph()
    session_context = {}
    turn = 0

    # Initial Agent Greeting
    print("\n[Agri_watch]: नमस्ते किसान भाई! मैं एग्री-वॉच हूँ। आप किस फसल या मंडी का भाव जानना चाहते हैं?\n")

    while True:
        try:
            user_input = input("[किसान भाई]: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "बाहर"):
                print("\n[Agri_watch]: राम राम किसान भाई! फिर मिलेंगे।\n")
                break

            turn += 1
            state_input: AgentState = {
                "turn_id": turn,
                "user_query": user_input,
                "session_context": session_context
            }

            result = graph.invoke(state_input)
            session_context = result.get("session_context") or {}
            spoken_response = result.get("spoken_hindi_response", "")
            intent = result.get("intent", "UNKNOWN")
            status = result.get("status", "unknown")

            print(f"[Agri_watch ({intent} / {status})]: {spoken_response}\n")

        except KeyboardInterrupt:
            print("\n\n[Session closed]")
            break
        except Exception as e:
            print(f"\n[!] Error during processing: {e}\n")


if __name__ == "__main__":
    start_console()

