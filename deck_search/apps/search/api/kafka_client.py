import json
import logging
from kafka import KafkaProducer, KafkaConsumer
from django.conf import settings

logger = logging.getLogger(__name__)

producer = None

def get_kafka_producer():
    global producer
    if not getattr(settings, 'KAFKA_ENABLED', False):
        logger.info("Kafka is disabled in settings - skipping producer initialization")
        return None
    if producer is None:
        try:
            producer = KafkaProducer(
                bootstrap_servers=getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', ['localhost:9092']),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=3,
                request_timeout_ms=30000,
                max_block_ms=30000
            )
            logger.info("Kafka Producer for deck_search connected successfully.")
        except Exception as e:
            logger.warning(f"Could not connect Kafka Producer: {e}")
            producer = None
    return producer

def send_kafka_request_and_wait(topic, value, response_topic, timeout=5):
    producer = get_kafka_producer()
    if not producer:
        logger.debug("Kafka Producer is not available. Message not sent.")
        return None
    try:
        key = str(value.get("slug") or value.get("id") or "").encode()
        producer.send(topic, key=key, value=value)
        producer.flush()
        # Listen for response
        consumer = KafkaConsumer(
            response_topic,
            bootstrap_servers=getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', ['localhost:9092']),
            group_id=None,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            consumer_timeout_ms=timeout * 1000
        )
        for message in consumer:
            data = message.value
            if data.get('slug') == value.get('slug'):
                consumer.close()
                return data
        consumer.close()
    except Exception as e:
        logger.error(f"Kafka request/response failed: {e}")
    return None
