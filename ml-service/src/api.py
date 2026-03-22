import os
import threading
import time
import joblib
import numpy as np
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, jsonify, send_file
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

app = Flask(__name__)

# ─── InfluxDB config (from .env) ───────────────────────────────────────────────
INFLUX_URL    = os.getenv("INFLUX_URL",    "http://localhost:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "iot_sensors")

# ─── Model config ──────────────────────────────────────────────────────────────
RETRAIN_INTERVAL = 300
MIN_SAMPLES      = 50
CONTAMINATION    = 0.07
MODEL_PATH       = "model.pkl"
SCALER_PATH      = "scaler.pkl"

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


# ──────────────────────────────────────────────────────────────────────────────
# Severity helper
# ──────────────────────────────────────────────────────────────────────────────

def get_severity(score: float) -> str:
    if score < -0.6:   return "CRITICAL"
    elif score < -0.4: return "HIGH"
    else:              return "LOW"


# ──────────────────────────────────────────────────────────────────────────────
# Data fetching
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# Model training + persistence
# ──────────────────────────────────────────────────────────────────────────────

def save_model():
    joblib.dump(model,  MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print("[MODEL] Saved to disk.")


def load_model_from_disk():
    global model, scaler
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        model  = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        print("[MODEL] Loaded from disk.")
        return True
    return False


def train_model():
    global model, scaler, last_trained, sample_count
    print("[MODEL] Fetching training data from InfluxDB...")
    data = fetch_training_data(window_minutes=9999)

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
        save_model()
    print(f"[MODEL] Trained on {sample_count} samples at {last_trained.strftime('%H:%M:%S')}")
    return True


last_sample_count = 0

def retrain_loop():
    global last_sample_count
    while True:
        try:
            data = fetch_training_data(window_minutes=9999)
            current_count = len(data)

            # Only retrain if we have new data since last train
            if current_count > last_sample_count and current_count >= MIN_SAMPLES:
                print(f"[MODEL] New data detected ({last_sample_count} → {current_count}), retraining...")
                train_model()
                last_sample_count = current_count
            else:
                print(f"[MODEL] No new data ({current_count} samples). Skipping retrain.")

        except Exception as e:
            print(f"[MODEL] Retrain error: {e}")
        time.sleep(RETRAIN_INTERVAL)


# ──────────────────────────────────────────────────────────────────────────────
# Anomaly logging
# ──────────────────────────────────────────────────────────────────────────────

def log_anomaly(temp, humidity, co2, score, severity, timestamp):
    point = (
        Point("anomalies")
        .tag("severity",      severity)
        .field("temperature",   float(temp))
        .field("humidity",      float(humidity))
        .field("co2",           float(co2))
        .field("anomaly_score", float(score))
        .time(timestamp, WritePrecision.NS)
    )
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

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

        seen_timestamps = set()
        for X, ts, temp, humidity, co2 in readings:
            ts_key = ts.isoformat()
            if ts_key in seen_timestamps:
                continue
            seen_timestamps.add(ts_key)

            X_scaled   = scaler.transform(X)
            prediction = model.predict(X_scaled)
            score      = model.score_samples(X_scaled)[0]

            if prediction[0] == -1:
                severity = get_severity(score)
                anomaly  = {
                    "temperature":   temp,
                    "humidity":      humidity,
                    "co2":           co2,
                    "anomaly_score": round(float(score), 4),
                    "severity":      severity,
                    "timestamp":     ts_key,
                }
                anomalies.append(anomaly)
                log_anomaly(temp, humidity, co2, score, severity, ts)
                print(f"[ANOMALY] [{severity}] score={score:.4f} | Temp={temp} Hum={humidity} CO2={co2}")

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
                "severity":      rec.values.get("severity"),
            })
    return jsonify(rows)


if __name__ == "__main__":
    # Try loading saved model first before waiting to retrain
    load_model_from_disk()

    t = threading.Thread(target=retrain_loop, daemon=True)
    t.start()
    print("[ML-SERVICE] Starting on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)