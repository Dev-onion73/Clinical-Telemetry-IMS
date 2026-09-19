from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


OTEL_ENDPOINT = "localhost:4319"


def main() -> None:
    resource = Resource.create(
        {
            "service.name": "clinical-trace-test",
            "service.version": "0.1.0",
        }
    )

    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(
        endpoint=OTEL_ENDPOINT,
        insecure=True,
    )

    provider.add_span_processor(
        BatchSpanProcessor(exporter)
    )

    trace.set_tracer_provider(provider)

    tracer = trace.get_tracer("clinical-test")

    with tracer.start_as_current_span("TEST_ENCOUNTER") as encounter:
        encounter.set_attribute(
            "clinical.patient_id",
            "PAT-0001",
        )

        encounter.set_attribute(
            "clinical.encounter_id",
            "E1",
        )

        with tracer.start_as_current_span("TEST_EPISODE") as episode:
            episode.set_attribute(
                "clinical.episode_id",
                "E1_EP1",
            )

            episode.add_event(
                "TEST_JOURNAL_ENTRY",
                {
                    "source_type": "journal",
                    "source_id": "JRN-0002",
                },
            )

            trace_id = format(
                episode.get_span_context().trace_id,
                "032x",
            )

            print(f"Trace ID: {trace_id}")

    provider.shutdown()

    print("Trace exported successfully.")


if __name__ == "__main__":
    main()