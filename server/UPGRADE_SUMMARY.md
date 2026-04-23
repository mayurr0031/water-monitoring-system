# ✅ Upgrade Complete - Quick Reference

## What's Been Updated

### 1. **app.py** - Complete Backend Rewrite
   ✅ MySQL database integration with auto-table creation
   ✅ Dual ESP32 support (device_id 1 & 2)
   ✅ Water level difference calculation
   ✅ Tomorrow.io weather API integration
   ✅ Random Forest ML model predictions
   ✅ 7 new API endpoints
   ✅ Thread-safe database operations

### 2. **dashboard.html** - New Modern UI
   ✅ Two manhole cards (water level, rise rate, fill %)
   ✅ Weather widget (rain_mm, rain_hour, temp, humidity)
   ✅ Water level difference display
   ✅ Flood/blockage prediction alerts (color-coded)
   ✅ Dual-line trend chart (both manhole levels)
   ✅ Auto-refresh functionality
   ✅ Mobile responsive design

### 3. **requirements.txt** - Updated Dependencies
   - Flask 2.3.3
   - flask-cors 4.0.0
   - mysql-connector-python 8.2.0
   - requests 2.31.0
   - joblib 1.3.2
   - scikit-learn 1.3.2
   - pandas 2.1.3
   - python-dotenv 1.0.0

### 4. **Configuration Files**
   ✅ .env.example - Environment variables template
   ✅ SETUP_GUIDE.md - Comprehensive setup documentation
   ✅ README.md - Updated with new features

---

## 🔧 Setup Steps

### Step 1: Install Dependencies
```bash
cd c:\Users\mayur\Project\server
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
# Copy template
copy .env.example .env

# Edit .env with your settings:
```

Edit `.env` with:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=water_level_monitor

TOMORROW_API_KEY=your_api_key_from_tomorrow.io
LOCATION_LAT=28.7041
LOCATION_LON=77.1025
```

### Step 3: Start MySQL Server
```bash
# MySQL must be running
mysql -u root -p
CREATE USER 'water_user'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON water_level_monitor.* TO 'water_user'@'localhost';
FLUSH PRIVILEGES;
```

### Step 4: Run the Server
```bash
python app.py
```

Server starts on: **http://localhost:5000**

---

## 📡 ESP32 Configuration

Send POST requests to the water-level endpoint:

```python
import requests
import json

# Endpoint
url = "http://YOUR_SERVER_IP:5000/api/water-level"

# Data from sensor
data = {
    "device_id": 1,          # 1 or 2 (Manhole 1 or 2)
    "water_level": 45.2,     # in cm
    "rise_rate": 0.5,        # cm/s
    "percentage": 75.0       # fill percentage (optional)
}

# Send
response = requests.post(url, json=data)
print(response.json())
```

---

## 🌐 Key API Endpoints

### POST /api/water-level
Receive sensor data from ESP32

### GET /api/latest
Get latest readings for both devices + weather + predictions

### GET /api/weather
Fetch weather data from Tomorrow.io

### POST /api/predict
Get flood/blockage predictions

### GET /api/history?device_id=1&hours=24
Get historical data for charting

---

## 🎯 Dashboard Features

| Feature | Details |
|---------|---------|
| **Manhole 1 Card** | Water level, rise rate, fill %, status indicator |
| **Manhole 2 Card** | Same as Manhole 1 |
| **Weather Widget** | Rain (mm), probability (%), temp, humidity |
| **Level Difference** | Absolute difference between two manholes |
| **Predictions** | Flood risk + blockage risk with probabilities |
| **Chart** | 24-hour trend showing both manhole levels |
| **Controls** | Auto-refresh toggle, refresh, clear data buttons |

---

## 🤖 ML Model Details

The `model.joblib` uses these 7 features for prediction:
1. water_level1 (cm)
2. water_level2 (cm)
3. level_difference (cm)
4. rise_rate1 (cm/s)
5. rise_rate2 (cm/s)
6. rain_mm (mm)
7. rain_hour (%)

**Outputs:**
- Flood Risk: LOW, MEDIUM, HIGH
- Blockage Risk: LOW, MEDIUM, HIGH
- Probability scores (0-1)

---

## 📚 Documentation

- **SETUP_GUIDE.md** - Detailed setup instructions
- **README.md** - API documentation and features
- **.env.example** - Configuration template

---

## ⚠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Database error | Check MySQL is running, verify .env credentials |
| No weather data | Get API key from tomorrow.io, add to .env |
| Model not loaded | Ensure model.joblib is in server directory |
| No data in dashboard | Verify ESP32 is POSTing to /api/water-level |
| CORS errors | Already configured with flask-cors |

---

## 🎉 You're All Set!

The system is now ready to:
- ✅ Receive data from 2 ESP32 devices
- ✅ Store in MySQL database
- ✅ Fetch weather from Tomorrow.io
- ✅ Predict flood/blockage with ML model
- ✅ Display real-time dashboard

**Start the server and visit:** http://localhost:5000

---

**Version:** 2.0  
**Date:** April 23, 2026
