# Water Level Monitoring System

A comprehensive water level monitoring system for dual manhole water detection with machine learning-based flood and blockage prediction.

## Features

✅ **Dual ESP32 Device Support** - Monitor two manhole water levels simultaneously  
✅ **MySQL Database** - Persistent storage of all sensor readings and predictions  
✅ **Weather Integration** - Real-time weather data from Tomorrow.io API  
✅ **ML Predictions** - Flood and blockage risk prediction using Random Forest model  
✅ **Real-time Dashboard** - Live web-based monitoring interface  
✅ **Auto-refresh** - Continuous data updates every 5 seconds  
✅ **Historical Charts** - Visualize water level trends over time  

## System Architecture

```
ESP32 (Device 1)  ──┐
                    ├─→ Flask API Server ──→ MySQL Database
ESP32 (Device 2)  ──┤                    ├─→ Tomorrow.io API
                    └─→ ML Model (model.joblib)
                    
Web Browser ←─────── Dashboard (HTML/JS)
```

## Prerequisites

- **Python 3.8+**
- **MySQL Server** (5.7 or 8.0+)
- **ESP32 Microcontrollers** (×2)
- **Tomorrow.io API Key** (free tier available)
- **model.joblib** - Pre-trained Random Forest model file

## Installation

### 1. Install Dependencies

```bash
cd c:\Users\mayur\Project\server
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=water_level_monitor

TOMORROW_API_KEY=your_tomorrow_io_key
LOCATION_LAT=28.7041
LOCATION_LON=77.1025
```

### 3. MySQL Setup

Start MySQL and create the database (the app will auto-create tables):

```sql
CREATE USER 'water_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON water_level_monitor.* TO 'water_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Run the Server

```bash
python app.py
```

Server will start on: **http://localhost:5000**

Access the dashboard: **http://localhost:5000/**

## ESP32 Configuration

### Sending Data to the Server

Each ESP32 should send HTTP POST requests to `/api/water-level`:

```python
import requests
import json

# Send sensor data
url = "http://YOUR_SERVER_IP:5000/api/water-level"

data = {
    "device_id": 1,  # 1 for Manhole 1, 2 for Manhole 2
    "water_level": 45.2,  # in cm
    "rise_rate": 0.5,  # cm/s
    "percentage": 75.0  # fill percentage (optional)
}

response = requests.post(url, json=data)
print(response.json())
```

## API Endpoints

### Receive Sensor Data
```
POST /api/water-level
Content-Type: application/json

{
    "device_id": 1,
    "water_level": 45.2,
    "rise_rate": 0.5,
    "percentage": 75.0,
    "timestamp": 1234567890  // optional, unix timestamp
}
```

### Get Latest Data (All Devices)
```
GET /api/latest

Response:
{
    "status": "success",
    "device1": { water_level, rise_rate, percentage, timestamp },
    "device2": { water_level, rise_rate, percentage, timestamp },
    "level_difference": 12.5,
    "weather": { rain_mm, rain_hour, temperature, humidity },
    "prediction": { flood_probability, blockage_probability, ... }
}
```

### Get Device Statistics
```
GET /api/device/<device_id>/stats

Example: /api/device/1/stats
```

### Get Weather Data
```
GET /api/weather

Fetches and caches weather data from Tomorrow.io
```

### Get Predictions
```
POST /api/predict

Optional body: { water_level1, water_level2, rise_rate1, rise_rate2, rain_mm, rain_hour }
If not provided, uses latest sensor data
```

### Get Historical Data
```
GET /api/history?device_id=1&hours=24

Parameters:
- device_id: 1 or 2 (optional, gets both if omitted)
- hours: number of hours to retrieve (default: 24)
```

### Clear All Data
```
POST /api/reset

Clears all sensor readings, weather data, and predictions
```

## ML Model Integration

The system uses `model.joblib` (Random Forest classifier) trained on:

### Input Features
- `water_level1` - Water level in Manhole 1 (cm)
- `water_level2` - Water level in Manhole 2 (cm)
- `level_difference` - Absolute difference between two levels (cm)
- `rise_rate1` - Water rise rate in Manhole 1 (cm/s)
- `rise_rate2` - Water rise rate in Manhole 2 (cm/s)
- `rain_mm` - Precipitation (mm)
- `rain_hour` - Rain probability (%)

### Outputs
- Flood Risk: LOW, MEDIUM, HIGH, UNKNOWN
- Blockage Risk: LOW, MEDIUM, HIGH, UNKNOWN
- Probability scores (0-1)

## Dashboard Features

### Manhole Cards
- Current water level (cm)
- Rise rate (cm/s)
- Fill percentage
- Last update timestamp
- Connection status indicator

### Weather Widget
- Rain precipitation (mm)
- Rain probability (%)
- Temperature (°C)
- Humidity (%)

### Water Level Difference
- Absolute difference between two manhole levels
- Useful for detecting flow blockage

### Predictions
- Real-time flood and blockage risk assessment
- Probability percentages
- Color-coded risk levels

### Chart
- Dual-line chart showing both manhole water levels
- 24-hour historical view (adjustable)
- Auto-refresh capability

## Database Schema

### sensor_readings
```
id, device_id, water_level, rise_rate, percentage, timestamp
```

### predictions
```
id, water_level1, water_level2, level_difference, rise_rate1, rise_rate2,
rain_mm, rain_hour, flood_probability, blockage_probability,
flood_prediction, blockage_prediction, timestamp
```

### weather_data
```
id, rain_mm, rain_hour, temperature, humidity, timestamp
```

## Troubleshooting

### Database Connection Error
```
Error: Database connection error
Solution: Check MySQL is running, verify .env credentials
```

### Tomorrow.io API Error
```
Warning: Tomorrow.io API key not configured
Solution: Get API key from https://www.tomorrow.io/, add to .env
```

### ML Model Not Loading
```
Warning: Could not load ML model
Solution: Ensure model.joblib is in the server directory
```

### No Data in Dashboard
```
Issue: Dashboard shows dashes
Solution: 
1. Check ESP32 is sending data to /api/water-level
2. Verify server URL and port are correct
3. Check MySQL tables are created: SHOW TABLES;
```

## Development Tips

### Enable Debug Mode
The server runs with `debug=True` by default. Disable for production:

```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

### Test API Endpoints
```bash
# Get latest data
curl http://localhost:5000/api/latest

# Simulate ESP32 data
curl -X POST http://localhost:5000/api/water-level \
  -H "Content-Type: application/json" \
  -d '{"device_id": 1, "water_level": 50, "rise_rate": 0.5}'

# Get prediction
curl -X POST http://localhost:5000/api/predict
```

## Performance Optimization

For production deployments:

1. **Use Gunicorn instead of Flask dev server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Enable database connection pooling** in app.py

3. **Add Redis caching** for weather data

4. **Implement data retention policy** to manage database size

5. **Use reverse proxy** (Nginx) for load balancing

## License

[Your License Here]

## Support

For issues or questions, please open an issue on GitHub.

---

**Last Updated:** April 2026
**Version:** 2.0
