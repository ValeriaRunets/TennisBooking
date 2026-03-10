from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Optional


@dataclass
class Location:
    slug: str  # e.g. "islington-tennis-centre"
    display_name: str  # e.g. "Islington Tennis Centre"
    activity_slug: str  # e.g. "highbury-tennis"

    def url_for_date(self, d: date) -> str:
        return (
            f"https://bookings.better.org.uk/location/"
            f"{self.slug}/{self.activity_slug}/{d.isoformat()}/by-time"
        )


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
class AvailabilitySnapshot:
    location_slug: str
    query_date: date
    slots: list[TimeSlot]
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def available_slots(self) -> list[TimeSlot]:
        return [s for s in self.slots if s.is_available]


@dataclass
class Watch:
    location_slug: str
    dates: list[date]
    time_start: Optional[time] = None
    time_end: Optional[time] = None
    active: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def matches_slot(self, slot: TimeSlot) -> bool:
        if not slot.is_available:
            return False
        if self.time_start and slot.start_time < self.time_start:
            return False
        if self.time_end and slot.start_time >= self.time_end:
            return False
        return True

    @property
    def short_description(self) -> str:
        date_range = (
            self.dates[0].isoformat()
            if len(self.dates) == 1
            else f"{self.dates[0].isoformat()} — {self.dates[-1].isoformat()}"
        )
        time_range = "any time"
        if self.time_start and self.time_end:
            time_range = f"{self.time_start.strftime('%H:%M')}-{self.time_end.strftime('%H:%M')}"
        elif self.time_start:
            time_range = f"from {self.time_start.strftime('%H:%M')}"
        elif self.time_end:
            time_range = f"until {self.time_end.strftime('%H:%M')}"
        return f"{self.location_slug} | {date_range} | {time_range}"


@dataclass
class AppState:
    watches: list[Watch] = field(default_factory=list)
    last_seen: dict[str, list[str]] = field(default_factory=dict)
    monitoring_enabled: bool = True
