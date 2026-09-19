from opentelemetry import trace
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
)


def get_current_span():
    return trace.get_current_span()


def get_current_span_context():
    return get_current_span().get_span_context()


def context_from_span(span):
    return trace.set_span_in_context(span)


def serialize_span_context(span) -> dict[str, str]:
    span_context = span.get_span_context()

    return {
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
    }


def context_from_ids(
    trace_id: str,
    span_id: str,
):
    span_context = SpanContext(
        trace_id=int(trace_id, 16),
        span_id=int(span_id, 16),
        is_remote=False,
        trace_flags=TraceFlags(0x01),
    )

    parent_span = NonRecordingSpan(span_context)

    return trace.set_span_in_context(parent_span)