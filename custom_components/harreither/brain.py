"""Brain client import wrapper.

Prefer the bundled client during development; fall back to global install otherwise.
"""

try:
    # Use local copy first to ease development
    from .harreither_brain_client.connection import Connection
    from .harreither_brain_client.entries import Entry, Entries
    from .harreither_brain_client.receive import ReceiveData
except ImportError:  # pragma: no cover - fallback for packaged installs
    from harreither_brain_client.connection import Connection
    from harreither_brain_client.entries import Entry, Entries
    from harreither_brain_client.receive import ReceiveData

__all__ = ["Connection", "Entry", "Entries", "ReceiveData"]
