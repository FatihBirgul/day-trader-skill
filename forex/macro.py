"""Explicit, provenance-preserving macro ingestion; no hidden network or trade vote."""
from datetime import datetime, timezone
from typing import Literal, Protocol
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MacroEvent(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)
    event_id: str = Field(min_length=1, max_length=150)
    source: str = Field(min_length=1, max_length=150)
    url: str = Field(max_length=2048)
    published_at: datetime
    release_at: datetime
    retrieved_at: datetime
    currency: Literal['USD', 'EUR', 'GBP', 'JPY']
    event_type: Literal['FED', 'FOMC', 'CPI', 'NFP', 'INTEREST_RATE', 'ECB', 'BOE', 'BOJ', 'GDP', 'UNEMPLOYMENT', 'GOLD', 'OTHER']
    importance: Literal['HIGH', 'MEDIUM', 'LOW', 'UNKNOWN'] = 'UNKNOWN'
    actual: float | None = None
    forecast: float | None = None
    previous: float | None = None
    unit: str | None = Field(default=None, max_length=80)

    @field_validator('url')
    @classmethod
    def source_url(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('public source URL required')
        return value

    @field_validator('published_at', 'release_at', 'retrieved_at')
    @classmethod
    def utc_stamp(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('timezone required')
        return value.astimezone(timezone.utc)


class InformationProvider(Protocol):
    name: str
    def events(self, as_of: datetime) -> list[MacroEvent]: ...


class SuppliedCalendar:
    """User-supplied records; declarations are not authenticated source verification."""
    name = 'caller-supplied-calendar'
    def __init__(self, events):
        self._events = tuple(MacroEvent.model_validate(event) for event in events)
    def events(self, as_of):
        return list(self._events)


def information_context(provider=None, *, as_of=None, max_age_seconds=86400):
    now = as_of if as_of is not None else datetime.now(timezone.utc)
    if now.tzinfo is None or type(max_age_seconds) is not int or max_age_seconds <= 0:
        raise ValueError('aware as-of and positive freshness policy required')
    result = {'schema_version': 'forex-macro-1', 'data_status': 'DATA_UNAVAILABLE',
              'provider': None if provider is None else provider.name, 'events': [],
              'event_filter_verified': False, 'directional_permission': False,
              'reason': 'verified macro source not configured'}
    if provider is None:
        return result
    try:
        rows = provider.events(now)
        if not isinstance(rows, (list, tuple)) or len(rows) > 500:
            raise ValueError('bounded event batch required')
        events = {}
        for raw in rows:
            event = MacroEvent.model_validate(raw)
            if event.published_at > now or event.retrieved_at > now or event.retrieved_at < event.published_at:
                raise ValueError('event provenance is not known as of analysis')
            if event.actual is not None and event.release_at > now:
                raise ValueError('future release cannot have an actual value')
            if (now-event.retrieved_at).total_seconds() > max_age_seconds:
                raise ValueError('stale calendar snapshot')
            key = (event.source, event.event_id)
            if key in events and events[key] != event:
                raise ValueError('conflicting source event revisions')
            events[key] = event
        result.update(data_status='DECLARED_SOURCE', reason='source provenance declared; event coverage unverified',
                      events=[e.model_dump(mode='json') for e in sorted(events.values(), key=lambda e: (e.release_at, e.event_id))])
    except Exception:
        result['reason'] = 'macro provider unavailable or invalid provenance'
    return result
