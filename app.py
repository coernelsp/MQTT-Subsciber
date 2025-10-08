import paho.mqtt.client as mqtt
from flask import Flask, render_template, jsonify, send_file, Response, request
import json
import threading
import time
from collections import deque
import logging
import csv
import os
from datetime import datetime
 
# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
# Flask-Setup
app = Flask(__name__)
 
# Datenstruktur für Sensordaten
class SensorData:
    def __init__(self):
        self.temperature = None
        self.humidity = None
        self.history = deque(maxlen=20)  # Speichert die letzten 20 Messwerte
        self.lock = threading.Lock()
        # CSV-Dateipfad
        self.csv_file = "sensor_data.csv"
        # Standard-Grenzwerte
        self.temp_min = 18.0
        self.temp_max = 26.0
        self.humidity_min = 30.0
        self.humidity_max = 70.0
        # Initialisiere CSV-Datei, falls sie nicht existiert
        self.init_csv_file()
 
    def init_csv_file(self):
        """Initialisiert die CSV-Datei mit Header, falls sie nicht existiert"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Temperature", "Humidity"])
 
    def update(self, temperature, humidity):
        with self.lock:
            self.temperature = temperature
            self.humidity = humidity
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            self.history.append({
                "timestamp": timestamp,
                "temperature": temperature,
                "humidity": humidity
            })
            # Speichere Daten in CSV-Datei
            self.save_to_csv(timestamp, temperature, humidity)
 
    def save_to_csv(self, timestamp, temperature, humidity):
        """Speichert die Daten in der CSV-Datei"""
        try:
            with open(self.csv_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, temperature, humidity])
            logger.info(f"Daten in CSV gespeichert: {timestamp}, {temperature}°C, {humidity}%")
        except Exception as e:
            logger.error(f"Fehler beim Speichern in CSV: {e}")
 
    def get_data(self):
        with self.lock:
            return {
                "temperature": self.temperature,
                "humidity": self.humidity,
                "history": list(self.history),
                "temp_min": self.temp_min,
                "temp_max": self.temp_max,
                "humidity_min": self.humidity_min,
                "humidity_max": self.humidity_max
            }
 
    def get_csv_data(self):
        """Liest alle Daten aus der CSV-Datei"""
        try:
            with open(self.csv_file, 'r') as file:
                reader = csv.reader(file)
                data = list(reader)
            return data
        except Exception as e:
            logger.error(f"Fehler beim Lesen der CSV-Datei: {e}")
            return []
 
    def set_thresholds(self, temp_min, temp_max, humidity_min, humidity_max):
        """Setzt die Temperatur- und Luftfeuchtigkeits-Grenzwerte"""
        with self.lock:
            self.temp_min = temp_min
            self.temp_max = temp_max
            self.humidity_min = humidity_min
            self.humidity_max = humidity_max
 
    def check_thresholds(self):
        """Überprüft, ob die Werte außerhalb der Grenzwerte liegen"""
        with self.lock:
            result = {
                "temperature": None,
                "humidity": None
            }
 
            # Temperatur prüfen
            if self.temperature is not None:
                if self.temperature < self.temp_min:
                    result["temperature"] = {
                        "exceeded": True,
                        "type": "min",
                        "message": f"Temperatur {self.temperature}°C unter dem Mindestwert von {self.temp_min}°C"
                    }
                elif self.temperature > self.temp_max:
                    result["temperature"] = {
                        "exceeded": True,
                        "type": "max",
                        "message": f"Temperatur {self.temperature}°C über dem Höchstwert von {self.temp_max}°C"
                    }
                else:
                    result["temperature"] = {"exceeded": False}
 
            # Luftfeuchtigkeit prüfen
            if self.humidity is not None:
                if self.humidity < self.humidity_min:
                    result["humidity"] = {
                        "exceeded": True,
                        "type": "min",
                        "message": f"Luftfeuchtigkeit {self.humidity}% unter dem Mindestwert von {self.humidity_min}%"
                    }
                elif self.humidity > self.humidity_max:
                    result["humidity"] = {
                        "exceeded": True,
                        "type": "max",
                        "message": f"Luftfeuchtigkeit {self.humidity}% über dem Höchstwert von {self.humidity_max}%"
                    }
                else:
                    result["humidity"] = {"exceeded": False}
 
            return result
 
# Globale Dateninstanz
sensor_data = SensorData()
 
# MQTT-Settings
BROKER = "mosquitto.jdsr.de"
PORT = 1883
MQTT_TOPIC = "sensor/temperature"
RECONNECT_DELAY = 5  # Sekunden
 
# Callback-Funktion für MQTT-Verbindung
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Erfolgreich mit MQTT-Broker verbunden (Code: {rc})")
        client.subscribe(MQTT_TOPIC)
    else:
        logger.error(f"Verbindung zum MQTT-Broker fehlgeschlagen (Code: {rc})")
 
# Callback-Funktion für empfangene Nachrichten
def on_message(client, userdata, message):
    try:
        payload = message.payload.decode().strip()
        logger.info(f"Empfangene Nachricht: {payload}")
 
        # Aufteilen der Nachricht nach dem Komma
        parts = payload.split(",")
        if len(parts) == 2:
            temperature = float(parts[0])
            humidity = float(parts[1])
            sensor_data.update(temperature, humidity)
            logger.info(f"Extrahierte Daten - Temperatur: {temperature}°C, Luftfeuchtigkeit: {humidity}%")
        else:
            logger.warning("Die empfangene Nachricht hat nicht das erwartete Format!")
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten der Nachricht: {e}")
 
# MQTT-Client mit automatischer Wiederverbindung
def mqtt_client_thread():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
 
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            client.loop_forever()
        except Exception as e:
            logger.error(f"MQTT-Verbindungsfehler: {e}")
            logger.info(f"Versuche Verbindung in {RECONNECT_DELAY} Sekunden erneut...")
            time.sleep(RECONNECT_DELAY)
 
# Flask-Routen
@app.route('/')
def index():
    return render_template("index.html")
 
@app.route('/data')
def get_data():
    return jsonify(sensor_data.get_data())
 
@app.route('/thresholds', methods=['GET', 'POST'])
def thresholds():
    if request.method == 'POST':
        data = request.json
        temp_min = float(data.get('temp_min', 18.0))
        temp_max = float(data.get('temp_max', 26.0))
        humidity_min = float(data.get('humidity_min', 30.0))
        humidity_max = float(data.get('humidity_max', 70.0))
        sensor_data.set_thresholds(temp_min, temp_max, humidity_min, humidity_max)
        return jsonify({"success": True})
    else:
        return jsonify({
            "temp_min": sensor_data.temp_min,
            "temp_max": sensor_data.temp_max,
            "humidity_min": sensor_data.humidity_min,
            "humidity_max": sensor_data.humidity_max
        })
 
@app.route('/export/csv')
def export_csv():
    """Exportiert die Sensordaten als CSV-Datei zum Herunterladen"""
    try:
        # Erstelle einen Dateinamen mit Datum und Uhrzeit
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sensor_data_{timestamp}.csv"
 
        # Lese die CSV-Daten
        csv_data = sensor_data.get_csv_data()
 
        # Erstelle eine Response mit den CSV-Daten
        def generate():
            for row in csv_data:
                yield ','.join(row) + '\n'
 
        response = Response(
            generate(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        return response
    except Exception as e:
        logger.error(f"Fehler beim CSV-Export: {e}")
        return jsonify({"error": "Fehler beim Exportieren der Daten"}), 500
 
if __name__ == "__main__":
    # MQTT-Client in einem separaten Thread starten
    mqtt_thread = threading.Thread(target=mqtt_client_thread, daemon=True)
    mqtt_thread.start()
 
    # Flask-Server starten
    app.run(debug=True, host="0.0.0.0", use_reloader=False)