from threading import Lock
from typing import Optional

from opentelemetry.trace import Span


class EpisodeSpanRegistry:

    def __init__(self):
        self._spans: dict[str, Span] = {}
        self._lock = Lock()

    def register(
        self,
        episode_id: str,
        span: Span,
    ) -> None:

        with self._lock:
            self._spans[episode_id] = span

    def get(
        self,
        episode_id: str,
    ) -> Optional[Span]:

        with self._lock:
            return self._spans.get(
                episode_id
            )

    def remove(
        self,
        episode_id: str,
    ) -> Optional[Span]:

        with self._lock:
            return self._spans.pop(
                episode_id,
                None,
            )

    def contains(
        self,
        episode_id: str,
    ) -> bool:

        with self._lock:
            return episode_id in self._spans


episode_span_registry = EpisodeSpanRegistry()