from threading import Lock
from typing import Optional

from opentelemetry.trace import Span


class JournalSpanRegistry:

    def __init__(self):
        self._spans: dict[str, Span] = {}
        self._lock = Lock()

    def register(
        self,
        journal_id: str,
        span: Span,
    ) -> None:

        with self._lock:
            self._spans[journal_id] = span

    def get(
        self,
        journal_id: str,
    ) -> Optional[Span]:

        with self._lock:
            return self._spans.get(journal_id)

    def remove(
        self,
        journal_id: str,
    ) -> Optional[Span]:

        with self._lock:
            return self._spans.pop(
                journal_id,
                None,
            )

    def contains(
        self,
        journal_id: str,
    ) -> bool:

        with self._lock:
            return journal_id in self._spans


journal_span_registry = JournalSpanRegistry()