from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Optional


@dataclass
class TimeSlot:
    start_time: time
    end_time: time
    court_name: str
    is_available: bool
    price: Optional[str] = None

    @property
    def key(self) -> str:
        return f"{self.start_time.strftime('%H:%M')}-{self.court_name}"


@dataclass
class MonitoredLink:
    url: str
    time_start: Optional[time] = None  # None means "any"
    time_end: Optional[time] = None
    label: str = ""
    active: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Slot keys already alerted about; a key is dropped when its slot
    # disappears so the slot alerts again if it frees up later.
    notified_keys: set[str] = field(default_factory=set)
    # Consecutive checks where the page yielded no slots at all.
    consecutive_failures: int = 0
    failure_notified: bool = False

    def matches_slot(self, slot: TimeSlot) -> bool:
        if not slot.is_available:
            return False
        if self.time_start and slot.start_time < self.time_start:
            return False
        if self.time_end and slot.start_time >= self.time_end:
            return False
        return True

    @property
    def time_description(self) -> str:
        if self.time_start and self.time_end:
            return f"{self.time_start.strftime('%H:%M')}-{self.time_end.strftime('%H:%M')}"
        elif self.time_start:
            return f"from {self.time_start.strftime('%H:%M')}"
        elif self.time_end:
            return f"until {self.time_end.strftime('%H:%M')}"
        return "any time"

    @property
    def short_description(self) -> str:
        name = self.label or self.url
        if len(name) > 60:
            name = name[:57] + "..."
        return f"{name} | {self.time_description}"


@dataclass
class AppState:
    links: list[MonitoredLink] = field(default_factory=list)
    monitoring_enabled: bool = True
