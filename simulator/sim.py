import paho.mqtt.client as mqtt
import time
import random
import json

# MQTT broker details
BROKER = "localhost"   # or your broker IP
PORT = 1883
TOPIC = "iot/sensors"

client = mqtt.Client()

def connect_mqtt():
    client.connect(BROKER, PORT, 60)
    print("Connected to MQTT Broker!")

def publish_data():
    while True:
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": round(random.uniform(20.0, 35.0), 2),
            "humidity": round(random.uniform(30.0, 80.0), 2),
            "co2": round(random.uniform(300, 1200), 2)
        }
        client.publish(TOPIC, json.dumps(data))
        print(f"Published: {data}")
        time.sleep(3)  # send every 3 sec

if __name__ == "__main__":
    connect_mqtt()
    publish_data()
