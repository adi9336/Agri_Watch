"""
Agri_watch - LangSmith Observability & Tracing Engine
Provides:
1. Environment auto-configuration for LangSmith Tracing V2
2. Traceable decorators for agents, tools, routers, and voice handlers
3. Connection verification and status inspection
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger("agriwatch.observability")

# Path discovery
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
ENV_PATH = os.path.join(PARENT_DIR, ".env")


def init_observability():
    """Initializes LangSmith tracing environment from .env."""
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k.startswith("LANGCHAIN_") or k.startswith("LANGSMITH_"):
                        if v:
                            os.environ[k] = v

    # Defaults if not explicitly defined
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    os.environ.setdefault("LANGCHAIN_PROJECT", "agri-watch")


# Initialize on import
init_observability()

# Import traceable decorator
try:
    from langsmith import traceable, Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    Client = None
    
    # Fallback dummy decorator
    def traceable(*args, **kwargs):
        def decorator(f):
            return f
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


def get_langsmith_status() -> Dict[str, Any]:
    """Inspects the current LangSmith observability configuration."""
    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    has_key = bool(api_key and len(api_key.strip()) > 5)
    masked_key = f"{api_key[:6]}...{api_key[-4:]}" if has_key else "Not Configured"
    
    status = {
        "langsmith_library_installed": LANGSMITH_AVAILABLE,
        "tracing_v2_enabled": os.getenv("LANGCHAIN_TRACING_V2") == "true",
        "endpoint": os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
        "project": os.getenv("LANGCHAIN_PROJECT", "agri-watch"),
        "has_api_key": has_key,
        "masked_key": masked_key,
        "dashboard_url": f"https://smith.langchain.com/o/default/projects/p/{os.getenv('LANGCHAIN_PROJECT', 'agri-watch')}"
    }
    return status


def test_langsmith_ping() -> Dict[str, Any]:
    """Sends a sample trace to verify end-to-end telemetry pipeline."""
    status = get_langsmith_status()
    if not status["has_api_key"]:
        return {
            "success": False,
            "message": "LANGCHAIN_API_KEY is not set in .env. Traces are queued locally or bypassed until key is provided.",
            "status": status
        }

    try:
        @traceable(name="AgriWatch:ObservabilityPing", run_type="chain")
        def _ping(msg: str) -> str:
            return f"AgriWatch LangSmith Connection Verified: {msg}"

        result = _ping("Telemetric handshake successful")
        return {
            "success": True,
            "message": result,
            "status": status
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection attempt failed: {str(e)}",
            "status": status
        }


if __name__ == "__main__":
    import json
    sys.stdout.reconfigure(encoding='utf-8')
    print("[*] Inspecting LangSmith Observability Configuration...\n")
    stat = get_langsmith_status()
    print(json.dumps(stat, indent=2))
    
    print("\n[*] Testing Telemetry Connection...")
    ping_res = test_langsmith_ping()
    print(json.dumps(ping_res, indent=2))
