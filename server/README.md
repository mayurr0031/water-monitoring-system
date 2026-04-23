# Water Level Monitoring System - Server

A comprehensive Flask REST API server for dual manhole water level monitoring with machine learning-based flood and blockage prediction.

## 🚀 Quick Start

### Installation

```bash
# Navigate to server directory
cd server

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your MySQL and Tomorrow.io credentials
# DB_HOST, DB_USER, DB_PASSWORD, TOMORROW_API_KEY, LOCATION_LAT, LOCATION_LON

# Run the server
python app.py
```

Server will start on `http://localhost:5000`  
Dashboard: `http://localhost:5000/`

## 📋 Requirements

- Python 3.8+
- MySQL Server 5.7+
- model.joblib (Random Forest model)
- Tomorrow.io API Key (free: https://www.tomorrow.io/)

## 🏗️ System Features

### Data Collection
- ✅ Receive water level data from 2 ESP32 devices
- ✅ Calculate water level difference between manholes
- ✅ Track rise rates for flood detection
- ✅ Store all data in MySQL database

### Weather Integration
- ✅ Fetch real-time weather from Tomorrow.io API
- ✅ Get precipitation (rain_mm) and rain probability (rain_hour)
- ✅ Display weather widget on dashboard

### ML Predictions
- ✅ Predict flood risk (LOW/MEDIUM/HIGH)
- ✅ Predict blockage risk (LOW/MEDIUM/HIGH)
- ✅ Uses features: water levels, rise rates, rain data
- ✅ Probability-based risk assessment

### Real-time Dashboard
- ✅ Live monitoring of both manhole water levels
- ✅ Weather widget similar to Google weather
- ✅ Water level difference display
- ✅ Flood/blockage predictions
- ✅ 24-hour trend chart
- ✅ Auto-refresh every 5 seconds

## 🔌 API Endpoints

### Receive Sensor Data
```
POST /api/water-level
Content-Type: application/json

{
    "device_id": 1,           // 1 or 2 for Manhole 1/2
    "water_level": 45.2,      // in cm
    "rise_rate": 0.5,         // cm/s
    "percentage": 75.0,       // fill % (optional)
    "timestamp": 1234567890   // unix timestamp (optional)
}

Response:
{
    "status": "success",
    "message": "Data received",
    "device_id": 1
}
```

### Get Latest Data
```
GET /api/latest

Response:
{
    "status": "success",
    "device1": {
        "device_id": 1,
        "water_level": 45.2,
        "rise_rate": 0.5,
        "percentage": 75.0,
        "timestamp": "2026-04-23T10:30:00"
    },
    "device2": { ... },
    "level_difference": 12.5,
    "weather": {
        "rain_mm": 0.5,
        "rain_hour": 45.0,
        "temperature": 28.5,
        "humidity": 65.0
    },
    "prediction": {
        "flood_probability": 0.25,
        "blockage_probability": 0.10,
        "flood_prediction": "LOW",
        "blockage_prediction": "LOW"
    }
}
```

### Get Device Statistics
```
GET /api/device/<device_id>/stats

Example: /api/device/1/stats

Response:
{
    "status": "success",
    "device_id": 1,
    "stats": {
        "count": 500,
        "avg_level": 42.5,
        "min_level": 25.0,
        "max_level": 85.0,
        "avg_rise_rate": 0.3,
        ...
    }
}
```

### Get Weather Data
```
GET /api/weather

Fetches latest weather from Tomorrow.io and stores in DB
```

### Get Predictions
```
POST /api/predict

Optional body:
{
    "water_level1": 45.2,
    "water_level2": 32.7,
    "rise_rate1": 0.5,
    "rise_rate2": 0.3,
    "rain_mm": 0.5,
    "rain_hour": 45.0
}

If body is empty, uses latest sensor and weather data
```

### Get Historical Data
```
GET /api/history?device_id=1&hours=24

Response:
{
    "status": "success",
    "count": 288,
    "data": [
        {
            "device_id": 1,
            "water_level": 45.2,
            "rise_rate": 0.5,
            "percentage": 75.0,
            "timestamp": "2026-04-23T10:00:00"
        },
        ...
    ]
}
```

### Clear All Data
```
POST /api/reset

Deletes all sensor readings, weather data, and predictions
```

## 🗄️ Database Schema

### sensor_readings
```sql
CREATE TABLE sensor_readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    water_level FLOAT NOT NULL,
    rise_rate FLOAT NOT NULL,
    percentage FLOAT DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX (device_id, timestamp)
);
```

### weather_data
```sql
CREATE TABLE weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rain_mm FLOAT NOT NULL,
    rain_hour FLOAT NOT NULL,
    temperature FLOAT DEFAULT 0,
    humidity FLOAT DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX (timestamp)
);
```

### predictions
```sql
CREATE TABLE predictions (
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
);
```

## 🤖 ML Model

The `model.joblib` file is a Random Forest classifier trained to predict:
- **Flood Risk**: Based on water levels, rise rates, and rain data
- **Blockage Risk**: Based on level differences and rise rate anomalies

### Model Input Features
1. `water_level1` - Manhole 1 water level (cm)
2. `water_level2` - Manhole 2 water level (cm)
3. `level_difference` - Absolute difference (cm)
4. `rise_rate1` - Manhole 1 rise rate (cm/s)
5. `rise_rate2` - Manhole 2 rise rate (cm/s)
6. `rain_mm` - Precipitation (mm)
7. `rain_hour` - Rain probability (%)

### Model Output
- Risk Level: LOW, MEDIUM, HIGH
- Probability: 0.0 - 1.0 (confidence score)

## 📝 Configuration

Create a `.env` file:

```env
# MySQL Database
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=water_level_monitor

# Tomorrow.io API
TOMORROW_API_KEY=your_api_key

# Location (for weather API)
LOCATION_LAT=28.7041
LOCATION_LON=77.1025
```

## 🐛 Troubleshooting

**Database Connection Failed**
- Ensure MySQL is running
- Verify credentials in .env
- Check database user has proper permissions

**No data in dashboard**
- Verify ESP32 is sending POST requests to `/api/water-level`
- Check server IP and port in ESP32 code
- Monitor network connectivity

**Weather API error**
- Verify Tomorrow.io API key in .env
- Check internet connectivity
- Ensure location coordinates are valid

**Model loading error**
- Ensure `model.joblib` is in the server directory
- Verify scikit-learn and joblib versions match training environment

## 📊 Dashboard

Access the interactive dashboard at `http://localhost:5000/`

Features:
- 📍 **Manhole Cards**: Water level, rise rate, fill %, status
- 🌧️ **Weather Widget**: Rainfall, probability, temperature, humidity
- 📊 **Level Difference**: Visual difference between two manhole levels
- ⚠️ **Predictions**: Flood/blockage risk with color-coded alerts
- 📈 **Trend Chart**: 24-hour historical water level graph
- 🔄 **Auto-refresh**: Updates every 5 seconds (can be toggled)

## 🚀 Production Deployment

For production, use Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Use Nginx as reverse proxy for load balancing and SSL.

---

**See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed installation and configuration instructions.**

**GET** `/api/data`

Retrieve all stored sensor readings.

**Response:**
```json
{
    "status": "success",
    "count": 42,
    "data": [
        {
            "distance": 30.5,
            "waterLevel": 9.5,
            "riseRate": 0.05,
            "percentage": 9.5,
            "timestamp": "2024-04-22T10:30:45.123456"
        },
        ...
    ]
}
```

### 3. Get Latest Reading

**GET** `/api/latest`

Get the most recent sensor reading.

**Response:**
```json
{
    "status": "success",
    "data": {
        "distance": 30.5,
        "waterLevel": 9.5,
        "riseRate": 0.05,
        "percentage": 9.5,
        "timestamp": "2024-04-22T10:30:45.123456"
    }
}
```

### 4. Get Statistics

**GET** `/api/stats`

Get statistical analysis of collected data.

**Response:**
```json
{
    "status": "success",
    "total_readings": 42,
    "waterLevel": {
        "min": 0.0,
        "max": 15.5,
        "avg": 8.2,
        "current": 9.5
    },
    "percentage": {
        "min": 0.0,
        "max": 15.5,
        "avg": 8.2,
        "current": 9.5
    },
    "riseRate": {
        "min": -0.5,
        "max": 0.8,
        "avg": 0.05,
        "current": 0.05
    }
}
```

### 5. Clear All Data

**POST** `/api/reset`

Remove all stored sensor readings.

**Response:**
```json
{
    "status": "success",
    "message": "All data cleared"
}
```

### 6. Dashboard

**GET** `/`

View the interactive web dashboard.

## Configuration

### Server Settings

Edit `app.py` to modify:

```python
MAX_READINGS = 1000        # Maximum readings to store
```

### Data Storage

- **Current**: In-memory storage (cleared on server restart)
- **Type**: Deque with max length (FIFO rollover)
- **Thread-safe**: Protected with locks

### Future: Database Integration

```python
# Could be extended with SQLAlchemy:
# from flask_sqlalchemy import SQLAlchemy
# db = SQLAlchemy(app)
```

## Usage Examples

### Using curl

**Send sensor data:**
```bash
curl -X POST http://localhost:5000/api/water-level \
  -H "Content-Type: application/json" \
  -d '{
    "distance": 30.5,
    "waterLevel": 9.5,
    "riseRate": 0.05,
    "percentage": 9.5,
    "timestamp": 12345
  }'
```

**Get latest reading:**
```bash
curl http://localhost:5000/api/latest
```

**Get statistics:**
```bash
curl http://localhost:5000/api/stats
```

### Using Python requests

```python
import requests
import json

# Send data
data = {
    "distance": 30.5,
    "waterLevel": 9.5,
    "riseRate": 0.05,
    "percentage": 9.5,
    "timestamp": 12345
}

response = requests.post(
    'http://localhost:5000/api/water-level',
    json=data
)
print(response.json())

# Get latest reading
response = requests.get('http://localhost:5000/api/latest')
print(response.json())

# Get statistics
response = requests.get('http://localhost:5000/api/stats')
print(response.json())
```

### Using JavaScript/Fetch API

```javascript
// Send data
fetch('/api/water-level', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        distance: 30.5,
        waterLevel: 9.5,
        riseRate: 0.05,
        percentage: 9.5,
        timestamp: Date.now() / 1000
    })
})
.then(response => response.json())
.then(data => console.log('Success:', data));

// Get latest reading
fetch('/api/latest')
    .then(response => response.json())
    .then(data => console.log('Latest:', data.data));
```

## Hosting Options

### Local Testing
```bash
python app.py
# Access: http://localhost:5000
```

### Production with Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t water-level-server .
docker run -p 5000:5000 water-level-server
```

### Cloud Deployment

#### Heroku
```bash
heroku create water-level-app
git push heroku main
heroku open
```

#### AWS EC2 / DigitalOcean
1. SSH into server
2. Clone repo
3. Install dependencies
4. Run with Gunicorn
5. Configure nginx as reverse proxy

## Debugging

### Enable Debug Mode
```python
app.run(debug=True, host='0.0.0.0', port=5000)
```

### Check Flask Logs
```bash
python app.py 2>&1 | tee server.log
```

### Test Endpoints
```bash
# Using Flask's test client
python -c "
from app import app
with app.test_client() as client:
    resp = client.get('/api/latest')
    print(resp.get_json())
"
```

## Performance Tips

1. **Limit Data Points**: Reduce MAX_READINGS if memory is an issue
2. **Archive Old Data**: Implement periodic export to database
3. **Use CDN**: For dashboard static files in production
4. **Database**: Switch to persistent storage for long-term operation
5. **Caching**: Add Redis for frequently accessed stats

## Security Considerations

For production deployment:

1. **API Authentication**: Add API keys or JWT
2. **HTTPS**: Use SSL/TLS certificates
3. **CORS**: Restrict allowed origins
4. **Rate Limiting**: Prevent abuse
5. **Input Validation**: Validate all incoming data

## Troubleshooting

### Port 5000 Already in Use

**Windows:**
```bash
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**Linux/Mac:**
```bash
lsof -i :5000
kill -9 <PID>
```

### Module Not Found

```bash
pip install -r requirements.txt
```

### CORS Issues

The server already includes CORS headers. Check:
- Browser console for specific errors
- Server logs for request details
- Ensure correct server URL in frontend

## Dependencies

- **Flask**: Web framework
- **flask-cors**: Cross-origin support
- **ArduinoJson**: (For ESP32 firmware only)

## File Structure

```
server/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── dashboard.html         # Web dashboard (served as template)
└── README.md             # This file
```

## License

MIT License - Free to use and modify

## Next Steps

1. Start the server: `python app.py`
2. Configure ESP32 firmware with server URL
3. Upload firmware to ESP32
4. View dashboard at `http://localhost:5000`
5. Monitor API responses in network tab
