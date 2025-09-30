import paho.mqtt.client as mqtt
import json

# MQTT settings
broker = "localhost"   # Same broker as publisher
port = 1883
topic = "iot/sensor"

# Callback when connection is successful
def on_connect(client, userdata, flags, rc):
    print("✅ Connected to broker with result code", rc)
    client.subscribe(topic)

# Callback when a message is received
def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    print(f"📥 Received -> Temperature: {data['temperature']}°C | "
          f"Humidity: {data['humidity']}% | "
          f"CO₂: {data['co2']} ppm")

# MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker, port, 60)
client.loop_forever()
