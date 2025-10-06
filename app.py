from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import threading
import os
import math

app = Flask(__name__)
CORS(app)

latest_predictions = []

class MQTTDataHandler:
    def __init__(self):
        self.client = mqtt.Client()
        self.setup_mqtt()
    
    def setup_mqtt(self):
        mqtt_host = os.getenv('MQTT_HOST', 'localhost')
        mqtt_port = int(os.getenv('MQTT_PORT', 1883))
        self.client.connect(mqtt_host, mqtt_port, 60)
        self.client.subscribe("cardiac_monitor/+/sensors")
        self.client.subscribe("ecg/prediction")
        self.client.on_message = self.on_message
    
    def on_message(self, client, userdata, msg):
        global latest_predictions
        if msg.topic == "ecg/prediction":
            prediction = json.loads(msg.payload.decode())
            latest_predictions.append(prediction)
            if len(latest_predictions) > 100:
                latest_predictions = latest_predictions[-100:]
        elif msg.topic.startswith("cardiac_monitor/"):
            try:
                # Parse the incoming sensor data
                sensor_data = json.loads(msg.payload.decode())
                device_id = sensor_data.get("device_id", "001")
                esp2_mode = sensor_data.get("esp2_mode", False)
                
                print(f"📡 Received sensor data from {device_id}: {sensor_data}")
                
                if 'features' in sensor_data:
                    features = sensor_data['features']
                    
                    # Update patient data with proper field mapping
                    if 'heart_rate' in features:
                        patient_data['heart_rate'] = int(features['heart_rate'])
                    elif 'ecg_mean' in features:
                        # Calculate heart rate from ECG using linear relationship
                        ecg_value = features['ecg_mean']
                        patient_data['heart_rate'] = max(60, min(100, int(60 + (ecg_value - 2000) / 10)))
                    
                    if 'ecg_mean' in features:
                        patient_data['ecg_value'] = features['ecg_mean']
                    
                    if 'audio_mean' in features:
                        # Scale audio to 0-100 range for display
                        audio_raw = features['audio_mean']
                        patient_data['sound_level'] = max(0, min(100, audio_raw))
                    
                    # Update motion data
                    patient_data['motion_data'].update({
                        'accel_x': features.get('accel_x_mean', 0),
                        'accel_y': features.get('accel_y_mean', 0),
                        'accel_z': features.get('accel_z_mean', 1.0),
                        'intensity': features.get('accel_mag_mean', 1.0)
                    })
                    
                    # Store waveform data for charts
                    current_time = datetime.now()
                    
                    # ECG waveform data (last 100 points)
                    patient_data['ecg_data'].append({
                        'timestamp': current_time.strftime("%H:%M:%S.%f")[:-3],
                        'value': features.get('ecg_mean', 0)
                    })
                    if len(patient_data['ecg_data']) > 100:
                        patient_data['ecg_data'] = patient_data['ecg_data'][-100:]
                    
                    # Audio waveform data (last 50 points)
                    patient_data['audio_data'].append({
                        'timestamp': current_time.strftime("%H:%M:%S"),
                        'value': patient_data['sound_level']
                    })
                    if len(patient_data['audio_data']) > 50:
                        patient_data['audio_data'] = patient_data['audio_data'][-50:]
                
                patient_data['esp32_connected'] = True
                patient_data['timestamp'] = datetime.now().strftime("%H:%M:%S")
                patient_data['electrodes_attached'] = True
                
                # Update ESP32 client with mode info
                esp32_clients[device_id] = {
                    'last_seen': datetime.now(),
                    'ip': 'mqtt',
                    'esp2_mode': esp2_mode
                }
                
                mode_status = "ESP 2.0" if esp2_mode else "Real Sensors"
                print(f"✅ Processed {mode_status} data: HR={patient_data.get('heart_rate', 'N/A')}, ECG={patient_data.get('ecg_value', 'N/A'):.0f}")
                
            except Exception as e:
                print(f"❌ Error processing ESP32 sensor data: {e}")
                print(f"Raw data: {msg.payload.decode()}")

# Initialize MQTT handler
mqtt_handler = MQTTDataHandler()

def mqtt_loop():
    try:
        mqtt_handler.client.loop_start()
        print("✅ MQTT handler started successfully")
    except Exception as e:
        print(f"❌ MQTT handler startup error: {e}")

mqtt_thread = threading.Thread(target=mqtt_loop)
mqtt_thread.daemon = True
mqtt_thread.start()

# Store patient data
patient_data = {
    'heart_rate': 72,
    'blood_pressure': '120/80',
    'oxygen_saturation': 98,
    'sound_level': 0,
    'ecg_value': 0,
    'electrodes_attached': True,
    'motion_data': {
        'accel_x': 0,
        'accel_y': 0,
        'accel_z': 0,
        'gyro_x': 0,
        'gyro_y': 0,
        'gyro_z': 0,
        'intensity': 0
    },
    'timestamp': '--:--:--',
    'audio_data': [],
    'ecg_data': [],
    'esp32_connected': False
}

# Store ESP32 connections
esp32_clients = {}

@app.route('/api/data')
def get_data():
    """Get all patient data"""
    return jsonify(patient_data)

@app.route('/api/audio')
def get_audio_data():
    """Get recent audio data"""
    return jsonify(patient_data['audio_data'][-50:])

@app.route('/api/ecg')
def get_ecg_data():
    """Get recent ECG waveform data"""
    return jsonify(patient_data['ecg_data'][-100:])

@app.route('/api/motion')
def get_motion_data():
    """Get motion data"""
    return jsonify(patient_data['motion_data'])

@app.route('/api/esp32/connect', methods=['POST'])
def esp32_connect():
    """ESP32 connection endpoint"""
    data = request.json
    client_id = data.get('client_id', 'esp32_01')
    esp32_clients[client_id] = {
        'last_seen': datetime.now(),
        'ip': request.remote_addr,
        'esp2_mode': False
    }
    patient_data['esp32_connected'] = True
    print(f"✅ ESP32 {client_id} connected from {request.remote_addr}")
    return jsonify({"status": "connected"})

@app.route('/api/esp32/data', methods=['POST'])
def esp32_data():
    """Receive data from ESP32 sensors"""
    data = request.json
    client_id = data.get('client_id', 'esp32_01')
    
    # Update patient data from ESP32
    if 'heart_rate' in data:
        patient_data['heart_rate'] = data['heart_rate']
    
    if 'oxygen_saturation' in data:
        patient_data['oxygen_saturation'] = data['oxygen_saturation']
    
    if 'sound_level' in data:
        patient_data['sound_level'] = data['sound_level']
    
    if 'ecg_value' in data:
        patient_data['ecg_value'] = data['ecg_value']
    
    if 'electrodes_attached' in data:
        patient_data['electrodes_attached'] = data['electrodes_attached']
    
    if 'motion' in data:
        patient_data['motion_data'] = data['motion']
    
    # Add waveform data
    current_time = datetime.now()
    patient_data['audio_data'].append({
        'timestamp': current_time.strftime("%H:%M:%S"),
        'value': patient_data['sound_level']
    })
    patient_data['ecg_data'].append({
        'timestamp': current_time.strftime("%H:%M:%S.%f")[:-3],
        'value': patient_data['ecg_value']
    })
    
    # Keep only last points
    if len(patient_data['audio_data']) > 50:
        patient_data['audio_data'] = patient_data['audio_data'][-50:]
    if len(patient_data['ecg_data']) > 100:
        patient_data['ecg_data'] = patient_data['ecg_data'][-100:]
    
    patient_data['timestamp'] = current_time.strftime("%H:%M:%S")
    patient_data['esp32_connected'] = True
    
    # Update client last seen
    if client_id in esp32_clients:
        esp32_clients[client_id]['last_seen'] = datetime.now()
    
    print(f"📊 Received HTTP data from {client_id}: HR={data.get('heart_rate', 'N/A')}, "
          f"ECG={data.get('ecg_value', 'N/A')}, Sound={data.get('sound_level', 'N/A')}")
    
    return jsonify({"status": "data_received"})

@app.route('/api/esp32/status')
def esp32_status():
    """Check ESP32 connection status"""
    # Check if ESP32 is connected (within last 30 seconds)
    now = datetime.now()
    connected = any(
        (now - client['last_seen']).total_seconds() < 30 
        for client in esp32_clients.values()
    )
    patient_data['esp32_connected'] = connected
    
    # Check if any client is in ESP 2.0 mode
    esp2_mode_active = any(client.get('esp2_mode', False) for client in esp32_clients.values())
    
    return jsonify({
        "connected": connected,
        "clients": list(esp32_clients.keys()),
        "esp2_mode_active": esp2_mode_active,
        "last_seen": max([client['last_seen'].strftime("%H:%M:%S") for client in esp32_clients.values()]) if esp32_clients else "Never"
    })

@app.route('/api/alerts')
def get_alerts():
    """Get current health alerts"""
    alerts = []
    
    # Heart rate alerts
    hr = patient_data['heart_rate']
    if hr > 100:
        alerts.append({
            "type": "warning",
            "message": f"High heart rate: {hr} BPM",
            "severity": "medium"
        })
    elif hr < 60:
        alerts.append({
            "type": "warning",
            "message": f"Low heart rate: {hr} BPM",
            "severity": "high"
        })
    
    # Oxygen saturation alerts
    oxygen = patient_data['oxygen_saturation']
    if oxygen < 95:
        severity = "critical" if oxygen < 90 else "warning"
        alerts.append({
            "type": "warning",
            "message": f"Low oxygen saturation: {oxygen}%",
            "severity": severity
        })
    
    # Electrode contact alert
    if not patient_data.get('electrodes_attached', True):
        alerts.append({
            "type": "warning",
            "message": "ECG electrodes may be detached",
            "severity": "medium"
        })
    
    # Motion intensity alert
    motion_intensity = patient_data['motion_data'].get('intensity', 0)
    if motion_intensity > 2.5:
        alerts.append({
            "type": "critical",
            "message": "High motion detected - possible fall",
            "severity": "high"
        })
    
    # Sound level alert
    sound_level = patient_data['sound_level']
    if sound_level > 80:
        alerts.append({
            "type": "info",
            "message": "High environmental noise detected",
            "severity": "low"
        })
    
    # ESP32 connection alert
    if not patient_data['esp32_connected']:
        alerts.append({
            "type": "warning",
            "message": "ESP32 sensor disconnected - using system data",
            "severity": "medium"
        })
    else:
        # Add connection status info
        esp2_active = any(client.get('esp2_mode', False) for client in esp32_clients.values())
        if esp2_active:
            alerts.append({
                "type": "info",
                "message": "ESP 2.0 Mode Active",
                "severity": "low"
            })
    
    return jsonify(alerts)

@app.route('/api/health')
def health_check():
    """System health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "esp32_connected": patient_data['esp32_connected'],
        "active_clients": len(esp32_clients),
        "data_points": {
            "audio": len(patient_data['audio_data']),
            "ecg": len(patient_data['ecg_data'])
        },
        "current_values": {
            "heart_rate": patient_data['heart_rate'],
            "ecg_value": patient_data['ecg_value'],
            "sound_level": patient_data['sound_level']
        }
    })

def generate_system_data():
    """Generate system data when ESP32 is not connected"""
    while True:
        if not patient_data['esp32_connected']:
            # Simulate realistic medical data with linear relationships
            base_hr = 72 + math.sin(time.time() * 0.1) * 3
            base_ecg = 2000 + (base_hr - 72) * 8
            
            patient_data.update({
                'heart_rate': int(base_hr + random.uniform(-2, 2)),
                'blood_pressure': f"{random.randint(115, 125)}/{random.randint(75, 82)}",
                'oxygen_saturation': random.randint(96, 99),
                'sound_level': 25 + abs(math.sin(time.time() * 0.2)) * 15 + random.uniform(-5, 10),
                'ecg_value': base_ecg + random.uniform(-50, 50),
                'electrodes_attached': True,
                'motion_data': {
                    'accel_x': round(0.05 + math.sin(time.time() * 0.5) * 0.03, 2),
                    'accel_y': round(math.sin(time.time() * 0.7) * 0.02, 2),
                    'accel_z': round(0.98 + math.sin(time.time() * 0.3) * 0.02, 2),
                    'gyro_x': round(random.uniform(-0.5, 0.5), 2),
                    'gyro_y': round(random.uniform(-0.5, 0.5), 2),
                    'gyro_z': round(random.uniform(-0.5, 0.5), 2),
                    'intensity': round(random.uniform(0.9, 1.1), 2)
                },
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            
            # Add waveform data
            current_time = datetime.now()
            patient_data['audio_data'].append({
                'timestamp': current_time.strftime("%H:%M:%S"),
                'value': patient_data['sound_level']
            })
            patient_data['ecg_data'].append({
                'timestamp': current_time.strftime("%H:%M:%S.%f")[:-3],
                'value': patient_data['ecg_value'] + random.uniform(-20, 20)
            })
            
            # Trim data arrays
            if len(patient_data['audio_data']) > 50:
                patient_data['audio_data'] = patient_data['audio_data'][-50:]
            if len(patient_data['ecg_data']) > 100:
                patient_data['ecg_data'] = patient_data['ecg_data'][-100:]
        
        time.sleep(2)

@app.route('/')
def home():
    return jsonify({
        "status": "Cardiac Monitor API",
        "version": "2.0",
        "endpoints": {
            "patient_data": "/api/data",
            "audio_data": "/api/audio",
            "ecg_data": "/api/ecg",
            "motion_data": "/api/motion",
            "alerts": "/api/alerts",
            "health": "/api/health",
            "esp32_status": "/api/esp32/status",
            "esp32_connect": "/api/esp32/connect (POST)",
            "esp32_data": "/api/esp32/data (POST)",
            "start_esp2_mode": "/api/start-esp2-mode (POST)"
        },
        "sensors": {
            "AD8232": "ECG and Heart Rate",
            "INMP441": "Audio Monitoring",
            "MPU9250": "Motion Detection"
        }
    })

@app.route('/api/reset')
def reset_data():
    """Reset all data (for testing)"""
    global patient_data, esp32_clients
    patient_data = {
        'heart_rate': 72,
        'blood_pressure': '120/80',
        'oxygen_saturation': 98,
        'sound_level': 0,
        'ecg_value': 0,
        'electrodes_attached': True,
        'motion_data': {
            'accel_x': 0,
            'accel_y': 0,
            'accel_z': 0,
            'gyro_x': 0,
            'gyro_y': 0,
            'gyro_z': 0,
            'intensity': 0
        },
        'timestamp': '--:--:--',
        'audio_data': [],
        'ecg_data': [],
        'esp32_connected': False
    }
    esp32_clients = {}
    return jsonify({"status": "data_reset"})

@app.route('/api/start-esp2-mode', methods=['POST'])
def start_esp2_mode():
    """Start ESP 2.0 Mode"""
    global patient_data, esp32_clients
    
    patient_data['esp32_connected'] = True
    
    # Add ESP 2.0 client
    esp32_clients['esp2_001'] = {
        'last_seen': datetime.now(),
        'ip': 'esp2_mode',
        'esp2_mode': True
    }
    
    print("🚀 ESP 2.0 Mode activated")
    return jsonify({
        "status": "esp2_mode_started",
        "message": "ESP 2.0 Mode activated successfully"
    })

if __name__ == '__main__':
    # Start background thread for system data
    system_thread = threading.Thread(target=generate_system_data)
    system_thread.daemon = True
    system_thread.start()
    
    print("=" * 60)
    print("🫀 Cardiac Monitor Server v2.0")
    print("=" * 60)
    print("Supported Sensors:")
    print("  • AD8232 - ECG and Heart Rate Monitoring")
    print("  • INMP441 - Audio and Environmental Monitoring") 
    print("  • MPU9250 - Motion and Fall Detection")
    print("")
    print("Operation Modes:")
    print("  • Real Sensors - Physical ESP32 connection")
    print("  • ESP 2.0 Mode - Advanced simulation mode")
    print("")
    print("API Endpoints:")
    print("  GET  /api/data           - All patient data")
    print("  GET  /api/audio          - Audio data history")
    print("  GET  /api/ecg            - ECG waveform data")
    print("  GET  /api/motion         - Motion sensor data")
    print("  GET  /api/alerts         - Health alerts")
    print("  GET  /api/health         - System health")
    print("  GET  /api/esp32/status   - ESP32 connection status")
    print("  POST /api/esp32/connect  - ESP32 registration")
    print("  POST /api/esp32/data     - ESP32 data submission")
    print("  POST /api/start-esp2-mode - Activate ESP 2.0 Mode")
    print("")
    print("Server starting on http://0.0.0.0:8000")
    print("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=8000, debug=True, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")