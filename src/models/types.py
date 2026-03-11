from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time
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
    desired_time: time  # the time slot the user wants
    label: str = ""  # optional friendly name
    active: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def short_description(self) -> str:
        name = self.label or self.url
        if len(name) > 60:
            name = name[:57] + "..."
        return f"{name} | {self.desired_time.strftime('%H:%M')}"


@dataclass
class AppState:
    links: list[MonitoredLink] = field(default_factory=list)
    # Tracks which (link_id, slot_key) combos we already notified about
    notified: dict[str, list[str]] = field(default_factory=dict)
    monitoring_enabled: bool = True
