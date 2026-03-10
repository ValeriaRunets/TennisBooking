"""Persistence layer — reads/writes app state to a JSON file."""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import date, time
from pathlib import Path

from config.settings import STATE_FILE_PATH
from src.models.types import AppState, Watch

logger = logging.getLogger(__name__)


def _watch_to_dict(w: Watch) -> dict:
    return {
        "id": w.id,
        "location_slug": w.location_slug,
        "dates": [d.isoformat() for d in w.dates],
        "time_start": w.time_start.strftime("%H:%M") if w.time_start else None,
        "time_end": w.time_end.strftime("%H:%M") if w.time_end else None,
        "active": w.active,
        "created_at": w.created_at,
    }


def _watch_from_dict(d: dict) -> Watch:
    return Watch(
        id=d["id"],
        location_slug=d["location_slug"],
        dates=[date.fromisoformat(s) for s in d["dates"]],
        time_start=time.fromisoformat(d["time_start"]) if d.get("time_start") else None,
        time_end=time.fromisoformat(d["time_end"]) if d.get("time_end") else None,
        active=d.get("active", True),
        created_at=d.get("created_at", ""),
    )


class StateManager:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or STATE_FILE_PATH

    def load(self) -> AppState:
        if not self._path.exists():
            return AppState()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return AppState(
                watches=[_watch_from_dict(w) for w in raw.get("watches", [])],
                last_seen=raw.get("last_seen", {}),
                monitoring_enabled=raw.get("monitoring_enabled", True),
            )
        except Exception:
            logger.exception("Failed to load state from %s", self._path)
            return AppState()

    def save(self, state: AppState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "watches": [_watch_to_dict(w) for w in state.watches],
            "last_seen": state.last_seen,
            "monitoring_enabled": state.monitoring_enabled,
        }
        # Atomic write
        tmp = tempfile.NamedTemporaryFile(
            mode="w", dir=self._path.parent, suffix=".tmp", delete=False
        )
        try:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp.close()
            Path(tmp.name).replace(self._path)
        except Exception:
            Path(tmp.name).unlink(missing_ok=True)
            raise
        logger.debug("State saved to %s", self._path)

    def add_watch(self, watch: Watch) -> None:
        state = self.load()
        state.watches.append(watch)
        self.save(state)

    def remove_watch(self, watch_id: str) -> bool:
        state = self.load()
        before = len(state.watches)
        state.watches = [w for w in state.watches if w.id != watch_id]
        if len(state.watches) < before:
            self.save(state)
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove watches whose dates have all passed."""
        state = self.load()
        today = date.today()
        before = len(state.watches)
        state.watches = [w for w in state.watches if any(d >= today for d in w.dates)]
        removed = before - len(state.watches)
        if removed:
            self.save(state)
            logger.info("Cleaned up %d expired watches", removed)
        return removed
