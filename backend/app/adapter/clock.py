from __future__ import annotations

from datetime import date, datetime


class SystemClock:
    """Production Clock adapter (the domain depends only on the Clock port)."""

    def now(self) -> datetime:
        return datetime.now()

    def today(self) -> date:
        return date.today()
