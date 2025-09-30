import time
import random
import json
import paho.mqtt.client as mqtt

# MQTT settings
broker = "localhost"   # Replace with your broker IP if not local
port = 1883
topic = "iot/sensor"

# MQTT client
client = mqtt.Client()
client.connect(broker, port)

# Keep generating and publishing data
while True:
    # Simulated sensor values
    temperature = round(random.uniform(20, 35), 1)
    humidity = round(random.uniform(30, 70), 1)
    co2 = round(random.uniform(300, 1200), 1)

    # Package as JSON
    data = {
        "temperature": temperature,
        "humidity": humidity,
        "co2": co2
    }

    # Publish to MQTT
    client.publish(topic, json.dumps(data))

    # Wait 1 second before next reading
    time.sleep(1)
