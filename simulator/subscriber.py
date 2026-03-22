import paho.mqtt.client as mqtt
import json
import csv
import os
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ─── InfluxDB config ───────────────────────────────────────────────────────────
INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "ayUawvpInUeNmrvpZ9tCdyftTpfYUQCnkHuPdSLtY0Y9BDqP-1xp_v4rEhqXU5FRRFUVsELlJCBXJhD5zDCR7Q=="
INFLUX_ORG   = "IOT_PROJECT"
INFLUX_BUCKET = "iot_sensors"

# ─── MQTT config ───────────────────────────────────────────────────────────────
BROKER = "localhost"
PORT   = 1883
TOPIC  = "iot/sensor"

# ─── CSV config ────────────────────────────────────────────────────────────────
CSV_FILE = CSV_FILE = r"C:\Users\kunal\IOT-ML\simulator\sensor_data.csv"

# ─── Init InfluxDB ─────────────────────────────────────────────────────────────
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api     = influx_client.write_api(write_options=SYNCHRONOUS)

# ─── Init CSV ──────────────────────────────────────────────────────────────────
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as f:
        csv.writer(f).writerow(["timestamp", "temperature", "humidity", "co2"])


def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected (rc={rc})")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    try:
        data      = json.loads(msg.payload.decode())
        timestamp = datetime.now(timezone.utc)

        temp     = data["temperature"]
        humidity = data["humidity"]
        co2      = data["co2"]

        print(f"[DATA] {timestamp.strftime('%H:%M:%S')} | "
              f"Temp: {temp}°C  Humidity: {humidity}%  CO₂: {co2} ppm")

    except Exception as e:
        print(f"[ERROR] Failed to parse message: {e}")
        return
    # ── Write to CSV (separate try so it always runs) ──────────────────────
    try:
        with open(CSV_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp.isoformat(), temp, humidity, co2])
            f.flush()
    except Exception as e:
        print(f"[ERROR] CSV write failed: {e}")

    # ── Write to InfluxDB ───────────────────────────────────────────────────
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

# ─── Start MQTT client ─────────────────────────────────────────────────────────
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

print("[MQTT] Waiting for messages...")
client.loop_forever()