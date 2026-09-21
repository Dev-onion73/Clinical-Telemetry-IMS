from app.messaging.kafka import KafkaProducer
from app.services.alert_injector import (
    AlertInjectorService,
)
from app.services.alert_scenarios import (
    AlertScenarioService,
)
from app.services.stable_vitals import (
    StableVitalsService,
)


kafka_producer = KafkaProducer()


stable_vitals_service = StableVitalsService(
    kafka_producer=kafka_producer,
)


alert_scenario_service = AlertScenarioService(
    kafka_producer=kafka_producer,
)


alert_injector_service = AlertInjectorService(
    kafka_producer=kafka_producer,
    alert_scenario_service=alert_scenario_service,
)