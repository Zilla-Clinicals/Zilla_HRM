# Vercel serverless entry point.
# Vercel's Python runtime (@vercel/python) detects the module-level ASGI `app`
# object and serves it — no uvicorn needed here. All routes are rewritten to
# this function by vercel.json.
#
# We prepend the backend/ directory (this file's grandparent) to sys.path so
# `from app.main import app` resolves the same way it does locally, regardless
# of Vercel's working directory.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402,F401
