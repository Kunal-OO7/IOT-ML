import paho.mqtt.client as mqtt
import json
import csv
import os

# MQTT settings
broker = "localhost"   # Same broker as publisher
port = 1883
topic = "iot/sensor"

#csv file instantiation
csv_file = "sensor_data.csv"

if not os.path.exists(csv_file):
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["temperature", "humidity", "co2"])
# Callback when connection is successful
def on_connect(client, userdata, flags, rc):
    print("Connected to broker with result code", rc)
    client.subscribe(topic)

# Callback when a message is received
def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    print(f"Received -> Temperature: {data['temperature']}°C | "
          f"Humidity: {data['humidity']}% | "
          f"CO₂: {data['co2']} ppm")
    
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([data['temperature'], data['humidity'], data['co2']])

# MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker, port, 60)
client.loop_forever()
