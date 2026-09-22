from threading import Lock
from typing import Optional

from opentelemetry.trace import Span


class AlertSpanRegistry:

    def __init__(self):
        self._spans: dict[str, Span] = {}
        self._lock = Lock()

    def register(
        self,
        fingerprint: str,
        span: Span,
    ) -> None:

        with self._lock:
            self._spans[fingerprint] = span

    def get(
        self,
        fingerprint: str,
    ) -> Optional[Span]:

        with self._lock:
            return self._spans.get(
                fingerprint
            )

    def remove(
        self,
        fingerprint: str,
    ) -> Optional[Span]:

        with self._lock:
            return self._spans.pop(
                fingerprint,
                None,
            )

    def contains(
        self,
        fingerprint: str,
    ) -> bool:

        with self._lock:
            return fingerprint in self._spans


alert_span_registry = AlertSpanRegistry()