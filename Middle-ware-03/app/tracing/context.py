from opentelemetry import trace
from opentelemetry.trace import Span


def get_current_span():
    return trace.get_current_span()


def get_current_span_context():
    return get_current_span().get_span_context()


def context_from_span(span: Span):
    return trace.set_span_in_context(span)