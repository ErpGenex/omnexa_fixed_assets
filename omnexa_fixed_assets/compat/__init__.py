"""Universal compatibility layer for this Frappe application.

The layer is additive and conservative: callers can opt into wrappers without
changing existing business logic or database state.
"""

from .version_manager import VersionManager

__all__ = ["VersionManager"]
