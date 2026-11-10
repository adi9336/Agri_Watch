"""
Agri_watch - Vercel entrypoint
Serves the FastAPI backend as a serverless function. The React build is served by
Vercel's CDN, and the LiveKit voice worker runs separately (it needs a long-lived process).
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app  # noqa: E402,F401
