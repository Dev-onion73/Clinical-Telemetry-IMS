from app.messaging.kafka import KafkaProducer
from app.services.stable_vitals import StableVitalsService


kafka_producer = KafkaProducer()

stable_vitals_service = StableVitalsService(
    kafka_producer=kafka_producer,
)