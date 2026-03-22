from flask import Flask, jsonify
import numpy as np
import threading
import time
from datetime import datetime, timezone
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

app = Flask(__name__)

# ─── InfluxDB config ───────────────────────────────────────────────────────────
INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "ayUawvpInUeNmrvpZ9tCdyftTpfYUQCnkHuPdSLtY0Y9BDqP-1xp_v4rEhqXU5FRRFUVsELlJCBXJhD5zDCR7Q=="
INFLUX_ORG    = "IOT_PROJECT"
INFLUX_BUCKET = "iot_sensors"

# ─── Model config ──────────────────────────────────────────────────────────────
RETRAIN_INTERVAL = 300
MIN_SAMPLES      = 50
CONTAMINATION    = 0.07

# ─── InfluxDB clients ──────────────────────────────────────────────────────────
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api     = influx_client.query_api()
write_api     = influx_client.write_api(write_options=SYNCHRONOUS)

# ─── Global model state ────────────────────────────────────────────────────────
model        = None
scaler       = StandardScaler()
model_lock   = threading.Lock()
last_trained = None
sample_count = 0


def fetch_training_data(window_minutes=60):
    query = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{window_minutes}m)
      |> filter(fn: (r) => r._measurement == "sensor_readings")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    """
    tables = query_api.query(org=INFLUX_ORG, query=query)
    rows = []
    for table in tables:
        for rec in table.records:
            t = rec.values.get("temperature")
            h = rec.values.get("humidity")
            c = rec.values.get("co2")
            if t is not None and h is not None and c is not None:
                rows.append([float(t), float(h), float(c)])
    return np.array(rows) if rows else np.array([]).reshape(0, 3)


def fetch_latest_readings(n=5):
    query = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -30s)
      |> filter(fn: (r) => r._measurement == "sensor_readings")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {n})
    """
    tables = query_api.query(org=INFLUX_ORG, query=query)
    rows = []
    for table in tables:
        for rec in table.records:
            t  = rec.values.get("temperature")
            h  = rec.values.get("humidity")
            c  = rec.values.get("co2")
            ts = rec.get_time()
            if t and h and c:
                rows.append((np.array([[float(t), float(h), float(c)]]), ts, t, h, c))
    return rows


def train_model():
    global model, scaler, last_trained, sample_count
    print("[MODEL] Fetching training data from InfluxDB...")
    data = fetch_training_data(window_minutes=60)

    if len(data) < MIN_SAMPLES:
        print(f"[MODEL] Not enough data yet ({len(data)}/{MIN_SAMPLES} samples). Waiting...")
        return False

    print(f"[MODEL] Training on {len(data)} samples...")
    with model_lock:
        scaler      = StandardScaler()
        data_scaled = scaler.fit_transform(data)
        model = IsolationForest(
            n_estimators=100,
            contamination=CONTAMINATION,
            random_state=42,
            n_jobs=-1
        )
        model.fit(data_scaled)
        last_trained = datetime.now(timezone.utc)
        sample_count = len(data)
    print(f"[MODEL] Trained on {sample_count} samples at {last_trained.strftime('%H:%M:%S')}")
    return True


def retrain_loop():
    while True:
        try:
            train_model()
        except Exception as e:
            print(f"[MODEL] Retrain error: {e}")
        time.sleep(RETRAIN_INTERVAL)


def log_anomaly(temp, humidity, co2, score, timestamp):
    point = (
        Point("anomalies")
        .field("temperature",   float(temp))
        .field("humidity",      float(humidity))
        .field("co2",           float(co2))
        .field("anomaly_score", float(score))
        .time(timestamp, WritePrecision.NS)
    )
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":        "ok",
        "model_trained": model is not None,
        "last_trained":  last_trained.isoformat() if last_trained else None,
        "trained_on":    sample_count
    })


@app.route("/latest", methods=["GET"])
def latest():
    readings = fetch_latest_readings(n=1)
    if not readings:
        return jsonify({})
    _, ts, temp, humidity, co2 = readings[0]
    return jsonify({"temperature": temp, "humidity": humidity, "co2": co2})


@app.route("/history", methods=["GET"])
def history():
    query = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "sensor_readings")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    """
    tables = query_api.query(org=INFLUX_ORG, query=query)
    rows = []
    for table in tables:
        for rec in table.records:
            rows.append({
                "time":        rec.get_time().isoformat(),
                "temperature": rec.values.get("temperature"),
                "humidity":    rec.values.get("humidity"),
                "co2":         rec.values.get("co2"),
            })
    return jsonify(rows)


@app.route("/detect", methods=["GET"])
def detect():
    anomalies = []
    with model_lock:
        if model is None:
            return jsonify({
                "anomalies":  [],
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "note":       f"Model not trained yet. Need {MIN_SAMPLES} samples."
            })

        readings = fetch_latest_readings(n=5)
        if not readings:
            return jsonify({"anomalies": [], "checked_at": datetime.now(timezone.utc).isoformat()})

        for X, ts, temp, humidity, co2 in readings:
            X_scaled   = scaler.transform(X)
            prediction = model.predict(X_scaled)
            score      = model.score_samples(X_scaled)[0]

            if prediction[0] == -1:
                anomaly = {
                    "temperature":   temp,
                    "humidity":      humidity,
                    "co2":           co2,
                    "anomaly_score": round(float(score), 4),
                    "timestamp":     ts.isoformat(),
                }
                anomalies.append(anomaly)
                log_anomaly(temp, humidity, co2, score, ts)
                print(f"[ANOMALY] score={score:.4f} | Temp={temp} Hum={humidity} CO2={co2}")

    return jsonify({
        "anomalies":  anomalies,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "model_info": {
            "trained_on":   sample_count,
            "last_trained": last_trained.isoformat() if last_trained else None
        }
    })


@app.route("/model-status", methods=["GET"])
def model_status():
    return jsonify({
        "trained":      model is not None,
        "sample_count": sample_count,
        "last_trained": last_trained.isoformat() if last_trained else None,
        "min_samples":  MIN_SAMPLES,
        "ready_in":     max(0, MIN_SAMPLES - sample_count) if model is None else 0
    })


@app.route("/anomaly-history", methods=["GET"])
def anomaly_history():
    query = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "anomalies")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
    """
    tables = query_api.query(org=INFLUX_ORG, query=query)
    rows = []
    for table in tables:
        for rec in table.records:
            rows.append({
                "time":          rec.get_time().isoformat(),
                "temperature":   rec.values.get("temperature"),
                "humidity":      rec.values.get("humidity"),
                "co2":           rec.values.get("co2"),
                "anomaly_score": rec.values.get("anomaly_score"),
            })
    return jsonify(rows)


if __name__ == "__main__":
    t = threading.Thread(target=retrain_loop, daemon=True)
    t.start()
    print("[ML-SERVICE] Starting on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)