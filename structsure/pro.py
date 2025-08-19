import os
from typing import Optional, Dict, Any

# NOTE: Licenzy is optional. If installed, we'll use it for license checks.
# Fallback remains the STRUCTSURE_LICENSE env var for CE/testing.

def _licenzy_available() -> bool:
    try:
        __import__("licenzy")
        return True
    except Exception:
        return False


def get_license_info() -> Optional[Dict[str, Any]]:
    """Return detailed license info when available.
    Uses licenzy if installed; otherwise returns None or a minimal stub when
    STRUCTSURE_LICENSE is set.
    """
    if _licenzy_available():
        try:
            from licenzy import get_license_manager  # type: ignore

            mgr = get_license_manager()
            return mgr.get_license_info()
        except Exception:
            return None
    # Fallback: treat presence of STRUCTSURE_LICENSE as a Pro license
    if os.environ.get("STRUCTSURE_LICENSE"):
        return {"plan": "pro", "source": "env"}
    return None


def license_plan() -> str:
    """Return the current license plan string (e.g., 'free', 'pro', 'business')."""
    info = get_license_info()
    if info and isinstance(info, dict):
        plan = str(info.get("plan") or "").strip().lower()
        if plan:
            return plan
    return "free"


def pro_enabled() -> bool:
    """Return True if Pro features should be enabled.
    Prefers licenzy.check_license() and plan in allowed set; falls back to env.
    """
    if _licenzy_available():
        try:
            from licenzy import check_license  # type: ignore

            if check_license():
                plan = license_plan()
                return plan in {"pro", "business", "enterprise"}
            return False
        except Exception:
            # If licenzy exists but errors, be conservative
            return False
    # Fallback: env toggle
    return bool(os.environ.get("STRUCTSURE_LICENSE"))
