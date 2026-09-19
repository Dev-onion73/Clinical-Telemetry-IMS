from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.tracing.exporter import create_otlp_exporter


SERVICE_NAME = "clinical-middleware"


def configure_tracing() -> TracerProvider:
    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
        }
    )

    provider = TracerProvider(
        resource=resource,
    )

    exporter = create_otlp_exporter()

    processor = BatchSpanProcessor(exporter)

    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)

    return provider


def get_tracer(name: str = "clinical-middleware"):
    return trace.get_tracer(name)