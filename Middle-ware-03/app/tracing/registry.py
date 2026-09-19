from threading import Lock
from typing import Optional

from opentelemetry.trace import Span


class EncounterSpanRegistry:

    def __init__(self):
        self._spans: dict[str, Span] = {}
        self._lock = Lock()

    def register(
        self,
        encounter_id: str,
        span: Span,
    ) -> None:
        with self._lock:
            self._spans[encounter_id] = span

    def get(
        self,
        encounter_id: str,
    ) -> Optional[Span]:
        with self._lock:
            return self._spans.get(encounter_id)

    def remove(
        self,
        encounter_id: str,
    ) -> Optional[Span]:
        with self._lock:
            return self._spans.pop(encounter_id, None)

    def contains(
        self,
        encounter_id: str,
    ) -> bool:
        with self._lock:
            return encounter_id in self._spans


encounter_span_registry = EncounterSpanRegistry()