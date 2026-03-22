import time
import random
import json
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT   = 1883
TOPIC  = "iot/sensor"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER, PORT)

print("[SIM] Sending sensor data...")

while True:
    spike = random.random() < 0.10

    temperature = round(random.uniform(55, 70), 1) if spike else round(random.uniform(20, 35), 1)
    humidity    = round(random.uniform(85, 100), 1) if spike else round(random.uniform(30, 70), 1)
    co2         = round(random.uniform(1500, 2000), 1) if spike else round(random.uniform(300, 1200), 1)

    data = {"temperature": temperature, "humidity": humidity, "co2": co2}
    client.publish(TOPIC, json.dumps(data))
    time.sleep(1)