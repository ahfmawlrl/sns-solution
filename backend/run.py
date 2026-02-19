"""
Development server entry point.

Uvicorn on Windows hardcodes ProactorEventLoop in its asyncio loop factory,
which is incompatible with asyncpg. This script patches that before startup.

Usage:
    python run.py              # normal mode
    python run.py --reload     # with auto-reload
"""
import sys

if sys.platform == "win32":
    import asyncio

    # Uvicorn hardcodes ProactorEventLoop on Windows in loops/asyncio.py.
    # Patch it to return SelectorEventLoop, which asyncpg requires.
    import uvicorn.loops.asyncio as _uvicorn_loops

    def _selector_loop_factory(use_subprocess: bool = False):
        return asyncio.SelectorEventLoop

    _uvicorn_loops.asyncio_loop_factory = _selector_loop_factory

import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reload", action="store_true", default=False)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        loop="asyncio",  # ensure asyncio_loop_factory is used (not uvloop)
    )
