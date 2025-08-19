import os

def pro_enabled() -> bool:
    """Return True if Pro features should be enabled.
    Current heuristic: presence of STRUCTSURE_LICENSE env var or import of structsure_pro.
    This is a placeholder until proper license verification is implemented.
    """
    if os.environ.get("STRUCTSURE_LICENSE"):
        return True
    try:
        __import__("structsure_pro")
        return True
    except Exception:
        return False
