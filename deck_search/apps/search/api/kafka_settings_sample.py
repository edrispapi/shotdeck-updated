# Add these to your Django settings for Kafka integration
KAFKA_ENABLED = True
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
KAFKA_SIMILAR_IMAGES_REQUEST_TOPIC = 'similar_images_request'
KAFKA_SIMILAR_IMAGES_RESPONSE_TOPIC = 'similar_images_response'
# You may need to adjust topic names and server addresses as per your Kafka setup
