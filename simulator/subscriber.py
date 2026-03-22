import os
import csv
import json
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

# ─── Config ────────────────────────────────────────────────────────────────────
INFLUX_URL    = os.getenv("INFLUX_URL",    "http://localhost:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "iot_sensors")
BROKER        = "localhost"
PORT          = 1883
TOPIC         = "iot/sensor"
CSV_FILE      = r"C:\Users\kunal\IOT-ML\simulator\sensor_data.csv"

# ─── Init InfluxDB ─────────────────────────────────────────────────────────────
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api     = influx_client.write_api(write_options=SYNCHRONOUS)

# ─── Init CSV ──────────────────────────────────────────────────────────────────
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as f:
        csv.writer(f).writerow(["timestamp", "temperature", "humidity", "co2"])


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[MQTT] Connected (rc={reason_code})")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    try:
        data      = json.loads(msg.payload.decode())
        timestamp = datetime.now(timezone.utc)
        temp      = data["temperature"]
        humidity  = data["humidity"]
        co2       = data["co2"]

        print(f"[DATA] {timestamp.strftime('%H:%M:%S')} | "
              f"Temp: {temp}°C  Humidity: {humidity}%  CO₂: {co2} ppm")
    except Exception as e:
        print(f"[ERROR] Failed to parse message: {e}")
        return

    # ── Write to CSV ────────────────────────────────────────────────────────────
    try:
        with open(CSV_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp.isoformat(), temp, humidity, co2])
            f.flush()
    except Exception as e:
        print(f"[ERROR] CSV write failed: {e}")

    # ── Write to InfluxDB ───────────────────────────────────────────────────────
    try:
        point = (
            Point("sensor_readings")
            .field("temperature", float(temp))
            .field("humidity",    float(humidity))
            .field("co2",         float(co2))
            .time(timestamp, WritePrecision.NS)
        )
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
    except Exception as e:
        print(f"[ERROR] InfluxDB write failed: {e}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

print("[MQTT] Waiting for messages...")
client.loop_forever()