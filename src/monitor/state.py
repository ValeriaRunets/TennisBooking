"""Persistence layer — reads/writes app state to a JSON file."""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import time
from pathlib import Path

from config.settings import STATE_FILE_PATH
from src.models.types import AppState, MonitoredLink

logger = logging.getLogger(__name__)


def _link_to_dict(link: MonitoredLink) -> dict:
    return {
        "id": link.id,
        "url": link.url,
        "time_start": link.time_start.strftime("%H:%M") if link.time_start else None,
        "time_end": link.time_end.strftime("%H:%M") if link.time_end else None,
        "label": link.label,
        "active": link.active,
        "created_at": link.created_at,
    }


def _link_from_dict(d: dict) -> MonitoredLink:
    return MonitoredLink(
        id=d["id"],
        url=d["url"],
        time_start=time.fromisoformat(d["time_start"]) if d.get("time_start") else None,
        time_end=time.fromisoformat(d["time_end"]) if d.get("time_end") else None,
        label=d.get("label", ""),
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
                links=[_link_from_dict(l) for l in raw.get("links", [])],
                notified=raw.get("notified", {}),
                monitoring_enabled=raw.get("monitoring_enabled", True),
            )
        except Exception:
            logger.exception("Failed to load state from %s", self._path)
            return AppState()

    def save(self, state: AppState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "links": [_link_to_dict(l) for l in state.links],
            "notified": state.notified,
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

    def add_link(self, link: MonitoredLink) -> None:
        state = self.load()
        state.links.append(link)
        self.save(state)

    def remove_link(self, link_id: str) -> bool:
        state = self.load()
        before = len(state.links)
        state.links = [l for l in state.links if l.id != link_id]
        state.notified.pop(link_id, None)
        if len(state.links) < before:
            self.save(state)
            return True
        return False

    def update_link(self, link_id: str, url: str | None = None,
                    time_start: time | None = ...,
                    time_end: time | None = ...,
                    label: str | None = None) -> bool:
        """Update link fields. Use None to clear time_start/time_end.
        Use ... (default) to leave unchanged."""
        state = self.load()
        for link in state.links:
            if link.id == link_id:
                if url is not None:
                    link.url = url
                if time_start is not ...:
                    link.time_start = time_start
                if time_end is not ...:
                    link.time_end = time_end
                if label is not None:
                    link.label = label
                # Reset notifications since params changed
                state.notified.pop(link_id, None)
                self.save(state)
                return True
        return False
