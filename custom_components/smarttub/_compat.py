"""Compatibility helpers for different Home Assistant releases."""

try:  # Home Assistant 2026.x uses probatio (voluptuous successor)
    import probatio as vol
except ImportError:  # pragma: no cover - older Home Assistant releases
    import voluptuous as vol  # type: ignore[no-redef]

__all__ = ["vol"]
