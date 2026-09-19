from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


def create_otlp_exporter() -> OTLPSpanExporter:
    return OTLPSpanExporter(
        endpoint="localhost:4319",
        insecure=True,
    )