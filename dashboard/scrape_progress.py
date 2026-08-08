"""In-memory scrape progress for the web UI."""

import threading
from collections import deque
from datetime import datetime, timezone

_lock = threading.Lock()
_state = {
    "running": False,
    "lines": deque(maxlen=200),
    "started_at": None,
    "finished_at": None,
    "error": None,
}


def clear_and_start():
    with _lock:
        _state["running"] = True
        _state["lines"].clear()
        _state["started_at"] = datetime.now(timezone.utc).isoformat()
        _state["finished_at"] = None
        _state["error"] = None
        _state["lines"].append("Scrape started...")


def append(message):
    text = str(message).rstrip()
    if not text:
        return
    with _lock:
        _state["lines"].append(text)


def finish(error=None):
    with _lock:
        _state["running"] = False
        _state["finished_at"] = datetime.now(timezone.utc).isoformat()
        _state["error"] = str(error) if error else None
        if error:
            _state["lines"].append(f"ERROR: {error}")
        else:
            _state["lines"].append("Scrape finished.")


def snapshot():
    with _lock:
        return {
            "running": _state["running"],
            "lines": list(_state["lines"]),
            "started_at": _state["started_at"],
            "finished_at": _state["finished_at"],
            "error": _state["error"],
        }
