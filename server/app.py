from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import mysql.connector
from mysql.connector import Error
import requests
import joblib
import pandas as pd
from threading import Lock
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='.', static_folder='.')
CORS(app)

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'water_level_monitor')
}

# Tomorrow.io API Configuration
TOMORROW_API_KEY = os.getenv('TOMORROW_API_KEY', '')
TOMORROW_API_URL = 'https://api.tomorrow.io/v4/weather/forecast'

# Location coordinates (update with your actual coordinates)
LOCATION_LAT = os.getenv('LOCATION_LAT', '28.7041')
LOCATION_LON = os.getenv('LOCATION_LON', '77.1025')

# Threading lock for database operations
db_lock = Lock()

# Load the ML model
try:
    model = joblib.load('model.joblib')
    print("✓ ML Model loaded successfully")
except Exception as e:
    print(f"⚠ Warning: Could not load ML model: {str(e)}")
    model = None

# ==================== DATABASE SETUP ====================

def get_db_connection():
    """Create a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Database connection error: {str(e)}")
        return None

def init_database():
    """Initialize the database with required tables"""
    connection = get_db_connection()
    if not connection:
        print("Could not initialize database")
        return
    
    cursor = connection.cursor()
    try:
        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        
        # Use the database
        cursor.execute(f"USE {DB_CONFIG['database']}")
        
        # Create sensor data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                device_id INT NOT NULL,
                water_level FLOAT NOT NULL,
                rise_rate FLOAT NOT NULL,
                percentage FLOAT DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX (device_id, timestamp)
            )
        """)
        
        # Create predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                water_level1 FLOAT NOT NULL,
                water_level2 FLOAT NOT NULL,
                level_difference FLOAT NOT NULL,
                rise_rate1 FLOAT NOT NULL,
                rise_rate2 FLOAT NOT NULL,
                rain_mm FLOAT NOT NULL,
                rain_hour FLOAT NOT NULL,
                flood_probability FLOAT DEFAULT 0,
                blockage_probability FLOAT DEFAULT 0,
                flood_prediction VARCHAR(20),
                blockage_prediction VARCHAR(20),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX (timestamp)
            )
        """)
        
        # Create weather data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                rain_mm FLOAT NOT NULL,
                rain_hour FLOAT NOT NULL,
                temperature FLOAT DEFAULT 0,
                humidity FLOAT DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX (timestamp)
            )
        """)
        
        connection.commit()
        print("✓ Database initialized successfully")
    except Error as e:
        print(f"Database initialization error: {str(e)}")
    finally:
        cursor.close()
        connection.close()

# ==================== WEATHER API ====================

def fetch_weather_data():
    """Fetch weather data from Tomorrow.io API"""
    try:
        if not TOMORROW_API_KEY:
            print("Warning: Tomorrow.io API key not configured")
            return {'rain_mm': 0, 'rain_hour': 0, 'temperature': 0, 'humidity': 0}
        
        params = {
            'location': f"{LOCATION_LAT},{LOCATION_LON}",
            'apikey': TOMORROW_API_KEY,
            'units': 'metric',
            'timesteps': 'hourly',
            'fields': 'precipitationSum,rainIntensity,precipitationProbability,temperature,humidity'
        }
        
        response = requests.get(TOMORROW_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract current/next hour precipitation data
        if 'timelines' in data and 'hourly' in data['timelines']:
            hourly_data = data['timelines']['hourly']
            if len(hourly_data) > 0:
                current = hourly_data[0]['values']
                next_hour = hourly_data[1]['values'] if len(hourly_data) > 1 else current
                
                return {
                    'rain_mm': current.get('precipitationSum', 0),
                    'rain_hour': next_hour.get('precipitationProbability', 0),
                    'temperature': current.get('temperature', 0),
                    'humidity': current.get('humidity', 0)
                }
        
        return {'rain_mm': 0, 'rain_hour': 0, 'temperature': 0, 'humidity': 0}
    
    except Exception as e:
        print(f"Weather API error: {str(e)}")
        return {'rain_mm': 0, 'rain_hour': 0, 'temperature': 0, 'humidity': 0}

def store_weather_data(weather_data):
    """Store weather data in database"""
    with db_lock:
        connection = get_db_connection()
        if not connection:
            return False
        
        cursor = connection.cursor()
        try:
            cursor.execute(f"USE {DB_CONFIG['database']}")
            cursor.execute("""
                INSERT INTO weather_data (rain_mm, rain_hour, temperature, humidity)
                VALUES (%s, %s, %s, %s)
            """, (
                weather_data['rain_mm'],
                weather_data['rain_hour'],
                weather_data['temperature'],
                weather_data['humidity']
            ))
            connection.commit()
            return True
        except Error as e:
            print(f"Error storing weather data: {str(e)}")
            return False
        finally:
            cursor.close()
            connection.close()

# ==================== ML PREDICTIONS ====================

def store_prediction(water_level1, water_level2, level_difference, rise_rate1, rise_rate2, rain_mm, rain_hour, prediction_label, proba):
    """Store prediction in database.
    prediction_label: int  0=Normal, 1=Blockage, 2=Flood
    proba: list of 3 probabilities [p_normal, p_blockage, p_flood]
    """
    with db_lock:
        connection = get_db_connection()
        if not connection:
            return False
        
        cursor = connection.cursor()
        try:
            cursor.execute(f"USE {DB_CONFIG['database']}")

            # ---------- Interpret prediction ----------
            if prediction_label == 0:
                flood_risk = 'LOW'
                blockage_risk = 'LOW'
            elif prediction_label == 1:
                flood_risk = 'LOW'
                blockage_risk = 'HIGH'
            elif prediction_label == 2:
                flood_risk = 'HIGH'
                blockage_risk = 'LOW'
            else:
                flood_risk = 'UNKNOWN'
                blockage_risk = 'UNKNOWN'

            # ---------- Probabilities ----------
            flood_probability = float(proba[2]) if len(proba) > 2 else 0
            blockage_probability = float(proba[1]) if len(proba) > 1 else 0

            # ---------- Insert ----------
            cursor.execute("""
                INSERT INTO predictions 
                (water_level1, water_level2, level_difference, rise_rate1, rise_rate2, rain_mm, rain_hour, flood_probability, blockage_probability, flood_prediction, blockage_prediction)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                water_level1, water_level2, level_difference, rise_rate1, rise_rate2, rain_mm, rain_hour,
                flood_probability,
                blockage_probability,
                flood_risk,
                blockage_risk
            ))

            connection.commit()
            return True

        except Error as e:
            print(f"Error storing prediction: {str(e)}")
            return False

        finally:
            cursor.close()
            connection.close()

# ==================== SENSOR DATA ENDPOINTS ====================

@app.route('/')
def index():
    """Serve the HTML dashboard"""
    return render_template('dashboard.html')

@app.route('/api/water-level', methods=['POST'])
def receive_water_level():
    """Receive water level data from ESP32"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Required fields
        device_id = data.get('device_id')
        water_level = data.get('water_level')
        rise_rate = data.get('rise_rate', 0)
        
        if device_id is None or water_level is None:
            return jsonify({'error': 'Missing device_id or water_level'}), 400
        
        # Add timestamp if not present
        if 'timestamp' not in data:
            timestamp = datetime.now()
        else:
            try:
                timestamp = datetime.fromtimestamp(data['timestamp'])
            except:
                timestamp = datetime.now()
        
        percentage = data.get('percentage', 0)
        
        # Store in database
        with db_lock:
            connection = get_db_connection()
            if not connection:
                return jsonify({'error': 'Database connection failed'}), 500
            
            cursor = connection.cursor()
            try:
                cursor.execute(f"USE {DB_CONFIG['database']}")
                cursor.execute("""
                    INSERT INTO sensor_readings (device_id, water_level, rise_rate, percentage)
                    VALUES (%s, %s, %s, %s)
                """, (device_id, water_level, rise_rate, percentage))
                connection.commit()
            except Error as e:
                print(f"Database error: {str(e)}")
                return jsonify({'error': 'Database error'}), 500
            finally:
                cursor.close()
                connection.close()
        
        print(f"[{timestamp.isoformat()}] Device {device_id}: Water Level={water_level}cm, Rise Rate={rise_rate}cm/s")
        
        return jsonify({
            'status': 'success',
            'message': 'Data received',
            'device_id': device_id
        }), 200
    
    except Exception as e:
        print(f"Error processing water level data: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/latest', methods=['GET'])
def get_latest_data():
    """Get the most recent sensor readings for both devices"""
    with db_lock:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(f"USE {DB_CONFIG['database']}")
            
            # Get latest data for device 1
            cursor.execute("""
                SELECT device_id, water_level, rise_rate, percentage, timestamp
                FROM sensor_readings
                WHERE device_id = 1
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            device1_data = cursor.fetchone()
            
            # Get latest data for device 2
            cursor.execute("""
                SELECT device_id, water_level, rise_rate, percentage, timestamp
                FROM sensor_readings
                WHERE device_id = 2
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            device2_data = cursor.fetchone()
            
            # Get latest weather data
            cursor.execute("""
                SELECT rain_mm, rain_hour, temperature, humidity, timestamp
                FROM weather_data
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            weather_data = cursor.fetchone()
            
            # Get latest prediction
            cursor.execute("""
                SELECT flood_probability, blockage_probability, flood_prediction, blockage_prediction, timestamp
                FROM predictions
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            prediction_data = cursor.fetchone()
            
            # Calculate level difference
            level_diff = 0
            if device1_data and device2_data:
                level_diff = abs(device1_data['water_level'] - device2_data['water_level'])
            
            return jsonify({
                'status': 'success',
                'device1': device1_data,
                'device2': device2_data,
                'level_difference': level_diff,
                'weather': weather_data,
                'prediction': prediction_data
            }), 200
        except Error as e:
            print(f"Database error: {str(e)}")
            return jsonify({'error': 'Database error'}), 500
        finally:
            cursor.close()
            connection.close()

@app.route('/api/device/<int:device_id>/stats', methods=['GET'])
def get_device_stats(device_id):
    """Get statistics for a specific device"""
    with db_lock:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(f"USE {DB_CONFIG['database']}")
            cursor.execute("""
                SELECT 
                    COUNT(*) as count,
                    AVG(water_level) as avg_level,
                    MIN(water_level) as min_level,
                    MAX(water_level) as max_level,
                    AVG(rise_rate) as avg_rise_rate,
                    MAX(rise_rate) as max_rise_rate,
                    MIN(rise_rate) as min_rise_rate
                FROM sensor_readings
                WHERE device_id = %s
            """, (device_id,))
            stats = cursor.fetchone()
            
            return jsonify({
                'status': 'success',
                'device_id': device_id,
                'stats': stats
            }), 200
        except Error as e:
            print(f"Database error: {str(e)}")
            return jsonify({'error': 'Database error'}), 500
        finally:
            cursor.close()
            connection.close()

@app.route('/api/weather', methods=['GET'])
def get_weather():
    """Fetch current weather data"""
    weather_data = fetch_weather_data()
    
    # Store in database
    store_weather_data(weather_data)
    
    return jsonify({
        'status': 'success',
        'data': weather_data
    }), 200

@app.route('/api/predict', methods=['GET'])
def predict_flood_blockage():

    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'DB fail'}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"USE {DB_CONFIG['database']}")

        # ===== GET DATA =====
        cursor.execute("""
            SELECT water_level, rise_rate FROM sensor_readings
            WHERE device_id=1 ORDER BY timestamp DESC LIMIT 1
        """)
        d1 = cursor.fetchone() or {'water_level':0,'rise_rate':0}

        cursor.execute("""
            SELECT water_level, rise_rate FROM sensor_readings
            WHERE device_id=2 ORDER BY timestamp DESC LIMIT 1
        """)
        d2 = cursor.fetchone() or {'water_level':0,'rise_rate':0}

        WL1 = float(d1['water_level'])
        WL2 = float(d2['water_level'])
        Rise1 = float(d1['rise_rate'])
        Rise2 = float(d2['rise_rate'])

        Diff = abs(WL1 - WL2)

        # ===== SIMPLE RELIABLE LOGIC =====
        condition = "NORMAL"

        # FLOOD
        if WL1 > 35 or WL2 > 35:
            condition = "FLOOD"

        elif WL1 > 30 and WL2 > 30:
            condition = "FLOOD"

        # BLOCKAGE
        elif Diff > 15:
            condition = "BLOCKAGE"

        elif Rise1 > 2 and Rise2 < 0.5:
            condition = "BLOCKAGE"

        # ===== OPTIONAL ML (secondary) =====
        if model is not None:
            try:
                features = pd.DataFrame([[WL1, WL2, Diff, Rise1, Rise2, 0, 0]],
                    columns=['WL1','WL2','Diff','Rise1','Rise2','Rain_mm','Rain_hr'])

                pred = int(model.predict(features)[0])

                # only use ML if no strong rule triggered
                if condition == "NORMAL":
                    if pred == 1:
                        condition = "BLOCKAGE"
                    elif pred == 2:
                        condition = "FLOOD"

            except:
                pass

        # ===== OUTPUT =====
        return jsonify({
            'status': 'success',
            'condition': condition,
            'WL1': WL1,
            'WL2': WL2,
            'difference': Diff
        })

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get historical data with optional device_id filter"""
    device_id = request.args.get('device_id', type=int)
    hours = request.args.get('hours', default=24, type=int)
    
    with db_lock:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(f"USE {DB_CONFIG['database']}")
            
            if device_id:
                cursor.execute("""
                    SELECT device_id, water_level, rise_rate, percentage, timestamp
                    FROM sensor_readings
                    WHERE device_id = %s AND timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                    ORDER BY timestamp ASC
                """, (device_id, hours))
            else:
                cursor.execute("""
                    SELECT device_id, water_level, rise_rate, percentage, timestamp
                    FROM sensor_readings
                    WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                    ORDER BY timestamp ASC
                """, (hours,))
            
            data = cursor.fetchall()
            
            return jsonify({
                'status': 'success',
                'count': len(data),
                'data': data
            }), 200
        except Error as e:
            print(f"Database error: {str(e)}")
            return jsonify({'error': 'Database error'}), 500
        finally:
            cursor.close()
            connection.close()

@app.route('/api/predict/test', methods=['GET'])
def predict_test():
    """Quick browser test with sample data"""
    import pandas as pd
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    features = pd.DataFrame([[15, 3, 12, 2.0, 0.3, 5, 1]],
        columns=['WL1','WL2','Diff','Rise1','Rise2','Rain_mm','Rain_hr'])
    label = int(model.predict(features)[0])
    proba = model.predict_proba(features)[0].tolist()
    condition = ['NORMAL','BLOCKAGE','FLOOD'][label]
    return jsonify({'condition': condition, 'label': label, 'probabilities': proba})

@app.route('/api/reset', methods=['POST'])
def reset_data():
    """Clear all stored data"""
    with db_lock:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        try:
            cursor.execute(f"USE {DB_CONFIG['database']}")
            cursor.execute("DELETE FROM sensor_readings")
            cursor.execute("DELETE FROM predictions")
            cursor.execute("DELETE FROM weather_data")
            connection.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'All data cleared'
            }), 200
        except Error as e:
            print(f"Database error: {str(e)}")
            return jsonify({'error': 'Database error'}), 500
        finally:
            cursor.close()
            connection.close()

if __name__ == '__main__':
    print("=" * 50)
    print("Water Level Monitoring System - Server")
    print("=" * 50)
    
    # Initialize database
    init_database()
    
    print("\nAPI Endpoints:")
    print("  POST   /api/water-level     - Receive sensor data from ESP32")
    print("  GET    /api/latest          - Get latest readings (both devices)")
    print("  GET    /api/device/<id>/stats - Get device statistics")
    print("  GET    /api/weather         - Get weather data")
    print("  POST   /api/predict         - Get flood/blockage prediction")
    print("  GET    /api/history         - Get historical data")
    print("  POST   /api/reset           - Clear all data")
    print("  GET    /                    - View dashboard")
    print("\nServer Configuration:")
    print(f"  Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    print(f"  Location: {LOCATION_LAT}, {LOCATION_LON}")
    print(f"  ML Model: {'Loaded' if model else 'Not loaded'}")
    print("\nStarting server on http://0.0.0.0:5000\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)