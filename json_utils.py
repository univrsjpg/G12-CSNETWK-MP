"""
json_utils.py - Helpers to ensure data structures are JSON serializable.
"""
from typing import Any


def sanitize_for_json(value: Any) -> Any:
    """
    Convert common pandas/numpy objects into plain Python types so json.dumps
    can handle them.
    """
    # numpy scalar or pandas Series value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    if isinstance(value, dict):
        return {key: sanitize_for_json(val) for key, val in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_json(item) for item in value]

    if isinstance(value, (int, float, str, bool)) or value is None:
        return value

    # Fallback to string representation for anything unexpected
    return str(value)

