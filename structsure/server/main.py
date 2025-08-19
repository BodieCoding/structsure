import os
import sys

def main() -> int:
    try:
        import uvicorn  # type: ignore
    except Exception:
        print("uvicorn is not installed. Install server extras: pip install -e .[server]", file=sys.stderr)
        return 1

    # Lazy import to avoid requiring FastAPI unless running
    from .api import app

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "false").lower() in {"1", "true", "yes"}

    uvicorn.run(app, host=host, port=port, reload=reload)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
