# Water Level Monitoring System

A complete IoT solution for measuring water level using the HC-SR04 ultrasonic sensor with an ESP32 microcontroller. Data is transmitted to a Flask server and visualized on a real-time dashboard.

## Project Structure

```
HC-SR04/
├── platformio.ini          # PlatformIO configuration
├── src/
│   └── main.cpp           # ESP32 firmware
└── lib/
    └── WaterLevel/
        ├── WaterLevel.h   # Library header
        └── WaterLevel.cpp # Library implementation

server/
├── app.py                 # Flask server
├── requirements.txt       # Python dependencies
└── dashboard.html         # Web dashboard
```

## Features

### Hardware
- **Sensor**: HC-SR04 Ultrasonic Distance Sensor
- **Microcontroller**: ESP32 DevKit V1
- **WiFi Connectivity**: For real-time data transmission

### Software
- **Firmware Library**: Custom WaterLevel library for accurate distance measurement
- **Backend**: Flask web server with REST API
- **Frontend**: Interactive HTML5 dashboard with real-time charts

### Measurements
- Water level in centimeters
- Rise rate (cm/s) with trend detection
- Container fill percentage
- Statistical analysis (min, max, average)

## Hardware Setup

### Pinout Configuration

```
HC-SR04 Sensor ↔ ESP32
├── VCC         → 5V
├── GND         → GND
├── TRIG        → GPIO 5
└── ECHO        → GPIO 18
```

### Water Level Calculation

```
Water Level (cm) = Base Height - Distance Measured
Base Height = 40 cm (distance from sensor to container bottom)
```

## ESP32 Firmware Setup

### Prerequisites
- PlatformIO IDE or VS Code with PlatformIO extension
- ESP32 USB driver

### Installation

1. **Configure WiFi Credentials**
   
   Edit `src/main.cpp` and update:
   ```cpp
   const char* ssid = "YOUR_SSID";
   const char* password = "YOUR_PASSWORD";
   ```

2. **Configure Server URL**
   
   Update the server address (if not running on 192.168.1.100):
   ```cpp
   const char* serverUrl = "http://YOUR_SERVER_IP:5000/api/water-level";
   ```

3. **Build and Upload**
   
   ```bash
   pio run -t upload
   ```

### Monitoring Serial Output

```bash
pio device monitor --baud 115200
```

### Configuration Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `TRIGGER_PIN` | 5 | GPIO pin for sensor trigger |
| `ECHO_PIN` | 18 | GPIO pin for echo signal |
| `BASE_HEIGHT_CM` | 40.0 | Distance from sensor to container bottom |
| `CONTAINER_HEIGHT_CM` | 100.0 | Total container height |
| `SEND_INTERVAL` | 5000 ms | How often to send data to server |

## Flask Server Setup

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Installation

1. **Install Dependencies**
   
   ```bash
   cd server
   pip install -r requirements.txt
   ```

2. **Run the Server**
   
   ```bash
   python app.py
   ```

   Server will start on `http://localhost:5000`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/water-level` | Receive sensor data from ESP32 |
| `GET` | `/api/data` | Get all stored readings |
| `GET` | `/api/latest` | Get the most recent reading |
| `GET` | `/api/stats` | Get statistics and analysis |
| `POST` | `/api/reset` | Clear all stored data |
| `GET` | `/` | View the dashboard |

### Data Storage

- **Memory Storage**: Readings stored in memory (max 1000 readings)
- **Auto-rollover**: Oldest readings are removed when limit is reached
- **Thread-safe**: Protected with locks for concurrent access

## Dashboard Features

### Real-Time Visualization

1. **Water Level Gauge**
   - Current water level in centimeters
   - Live status indicator

2. **Fill Percentage**
   - Visual gauge showing container fullness
   - Percentage display

3. **Rise Rate Monitor**
   - Real-time rate of change (cm/s)
   - Status indicator (Rising/Falling/Stable)

4. **Statistics Panel**
   - Minimum water level
   - Maximum water level
   - Average water level
   - Total readings count

5. **Trend Chart**
   - Line chart showing water level over time
   - 30-second auto-refresh interval (when enabled)
   - Manual refresh capability

### Control Options

- **Refresh Stats**: Update statistics data
- **Clear Data**: Remove all stored readings
- **Enable Auto-Refresh**: Auto-update charts every 2 seconds

## Usage Example

### 1. Start the Server

```bash
cd server
python app.py
```

Output:
```
Water Level Monitoring Server
==============================
Starting Flask server on http://localhost:5000
...
Waiting for connections...
```

### 2. Upload Firmware to ESP32

Ensure WiFi credentials are configured, then:
```bash
cd HC-SR04
pio run -t upload
```

### 3. Access the Dashboard

Open browser and navigate to:
```
http://localhost:5000
```

### 4. Monitor Data

The dashboard will automatically:
- Receive sensor readings every 5 seconds
- Update all gauges and charts
- Maintain historical data
- Calculate statistics

## Calibration

### To Calibrate the Base Height:

1. Measure the exact distance from the HC-SR04 sensor to the bottom of your container
2. Update `BASE_HEIGHT_CM` in `src/main.cpp`:
   ```cpp
   #define BASE_HEIGHT_CM 40.0  // Update this value
   ```
3. Rebuild and upload firmware

### Testing Calibration:

1. With an empty container, the water level should read 0 cm
2. Add water and verify the reading increases correctly

## Troubleshooting

### ESP32 Not Connecting to WiFi
- Check SSID and password are correct
- Verify WiFi supports 2.4GHz (ESP32 doesn't support 5GHz)
- Check if ESP32 is in range

### No Data Appearing on Dashboard
- Verify Flask server is running
- Check ESP32 serial output for errors
- Ensure server URL is correct in firmware
- Verify firewall isn't blocking port 5000

### Inaccurate Readings
- Check sensor is not obstructed
- Verify HC-SR04 pins are securely connected
- Ensure base height calibration is correct
- Check for reflective surfaces interfering with ultrasonic signal

### Server Port Already in Use
```bash
# On Windows, find and kill process on port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

## Performance Notes

- **Update Rate**: 5-second intervals (configurable)
- **Data Points Stored**: Up to 1000 readings
- **Response Time**: <100ms API response
- **Gauge Update**: Real-time visual updates

## Future Enhancements

- Database storage (SQLite/PostgreSQL)
- Email/SMS alerts on threshold breach
- Historical data export (CSV/JSON)
- Multiple sensor support
- Mobile app integration
- Predictive analytics for water usage

## License

MIT License - Feel free to use and modify for your projects

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review serial monitor output
3. Verify all connections
4. Check API responses in browser console
