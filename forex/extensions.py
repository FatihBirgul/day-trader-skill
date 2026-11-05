"""Public-safe analytical extension ABI; private bridges are deployed separately."""
from typing import Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field
from .contracts import Snapshot

ABI_VERSION = 'forex-extension-1'


class Evidence(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True, allow_inf_nan=False)
    source: str = Field(min_length=1, max_length=120)
    event_id: str = Field(min_length=1, max_length=160)
    category: Literal['trend', 'momentum', 'structure', 'pattern', 'mtf', 'volume', 'news', 'volatility']
    direction: Literal['BUY', 'SELL', 'NEUTRAL']
    known_at: float
    confirmed: bool


class ExtensionResult(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True, allow_inf_nan=False)
    abi_version: Literal['forex-extension-1'] = ABI_VERSION
    source_sha: str = Field(pattern=r'^[0-9a-f]{40}$')
    bridge_version: str = Field(min_length=1, max_length=100)
    snapshot_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    status: Literal['AVAILABLE', 'PARTIAL', 'UNAVAILABLE']
    data_json: str = '{}'


class AnalyticalExtension(Protocol):
    source_sha: str

    def evaluate(self, snapshot: Snapshot, *, context_json: str) -> ExtensionResult: ...


def context_evidence(items, as_of):
    """Conservative veto context, not a calibrated weighted confluence engine.

    All OHLC-derived categories share one correlation group. Pattern, MTF and
    volatility remain context only. Cross-category event reuse never adds votes.
    Conflicts are retained instead of choosing a winner by an arbitrary score.
    """
    seen = set()
    retained, rejected = [], []
    for item in items:
        e = Evidence.model_validate(item)
        if e.known_at > as_of or not e.confirmed:
            rejected.append(e.event_id)
            continue
        key = (e.event_id, e.direction)
        if key not in seen:
            seen.add(key)
            retained.append(e.model_dump())
    price = {e['direction'] for e in retained
             if e['category'] in ('trend', 'momentum', 'structure') and e['direction'] != 'NEUTRAL'}
    conflicts = sorted(price) if len(price) > 1 else []
    return {'status': 'CONTEXT_ONLY', 'version': 'forex-context-veto-1',
            'independent_price_groups': 1 if price else 0,
            'evidence': retained, 'rejected_events': sorted(set(rejected)),
            'conflicts': conflicts, 'score': None, 'success_probability': None}
