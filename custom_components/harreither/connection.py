"""Connection import wrapper.

Prefer the bundled client during development; fall back to global install otherwise.
"""

try:
    # Use local copy first to ease development
    from .harreither_brain_client.connection import Connection
except ImportError:  # pragma: no cover - fallback for packaged installs
    from harreither_brain_client.connection import Connection

__all__ = ["Connection"]
