import time
import random
import json
import paho.mqtt.client as mqtt

# MQTT settings
broker = "localhost"
port = 1883
topic = "iot/sensor"

# MQTT client
client = mqtt.Client()
client.connect(broker, port)

# Keep generating and publishing data
while True:
    # 10% chance of a spike
    spike = random.random() < 0.10

    temperature = round(random.uniform(55, 70), 1) if spike else round(random.uniform(20, 35), 1)
    humidity    = round(random.uniform(85, 100), 1) if spike else round(random.uniform(30, 70), 1)
    co2         = round(random.uniform(1500, 2000), 1) if spike else round(random.uniform(300, 1200), 1)

    data = {
        "temperature": temperature,
        "humidity": humidity,
        "co2": co2
    }

    client.publish(topic, json.dumps(data))
    time.sleep(1)