#!/usr/bin/env python3
"""
Test script for Water Level Monitoring System

This script simulates ESP32 devices sending water level data
to test the server without actual hardware.

Usage:
    python test_system.py
"""

import requests
import time
import random
from datetime import datetime, timedelta
import json

# Configuration
SERVER_URL = "http://localhost:5000"
DEVICE_1_ID = 1
DEVICE_2_ID = 2

# Simulate water levels (cm)
DEVICE_1_WATER = 30.0
DEVICE_2_WATER = 35.0
RISE_RATE = 0.1

def test_api_health():
    """Test if server is running"""
    try:
        response = requests.get(f"{SERVER_URL}/api/latest")
        if response.status_code == 200:
            print("✅ Server is running and responding")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running on localhost:5000?")
        return False

def send_sensor_data(device_id, water_level, rise_rate, percentage):
    """Send sensor data to the server"""
    data = {
        "device_id": device_id,
        "water_level": water_level,
        "rise_rate": rise_rate,
        "percentage": percentage
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/api/water-level", json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Device {device_id}: Water={water_level:.2f}cm, Rise={rise_rate:.3f}cm/s, Fill={percentage:.1f}%")
            return True
        else:
            print(f"❌ Error sending data for Device {device_id}: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def get_latest_data():
    """Get latest data from server"""
    try:
        response = requests.get(f"{SERVER_URL}/api/latest")
        if response.status_code == 200:
            data = response.json()
            print("\n📊 Latest Data:")
            print(f"   Device 1: {data.get('device1', {}).get('water_level', 'N/A'):.2f} cm")
            print(f"   Device 2: {data.get('device2', {}).get('water_level', 'N/A'):.2f} cm")
            print(f"   Difference: {data.get('level_difference', 0):.2f} cm")
            
            if data.get('weather'):
                weather = data['weather']
                print(f"   Rain: {weather.get('rain_mm', 0):.1f} mm")
                print(f"   Rain Probability: {weather.get('rain_hour', 0):.1f}%")
            
            if data.get('prediction'):
                pred = data['prediction']
                print(f"   Flood Risk: {pred.get('flood_prediction', 'UNKNOWN')}")
                print(f"   Blockage Risk: {pred.get('blockage_prediction', 'UNKNOWN')}")
            
            return True
        else:
            print(f"❌ Error fetching latest data: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def get_device_stats(device_id):
    """Get statistics for a device"""
    try:
        response = requests.get(f"{SERVER_URL}/api/device/{device_id}/stats")
        if response.status_code == 200:
            data = response.json()
            if data.get('stats'):
                stats = data['stats']
                print(f"\n📈 Device {device_id} Statistics:")
                print(f"   Readings: {stats.get('count', 0)}")
                print(f"   Avg Level: {stats.get('avg_level', 0):.2f} cm")
                print(f"   Min Level: {stats.get('min_level', 0):.2f} cm")
                print(f"   Max Level: {stats.get('max_level', 0):.2f} cm")
                return True
        return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def get_weather():
    """Get current weather"""
    try:
        response = requests.get(f"{SERVER_URL}/api/weather")
        if response.status_code == 200:
            data = response.json()
            weather = data.get('data', {})
            print(f"\n🌧️  Weather Data:")
            print(f"   Rain: {weather.get('rain_mm', 0):.1f} mm")
            print(f"   Probability: {weather.get('rain_hour', 0):.1f}%")
            print(f"   Temperature: {weather.get('temperature', 0):.1f}°C")
            print(f"   Humidity: {weather.get('humidity', 0):.1f}%")
            return True
        return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def get_prediction():
    """Get flood/blockage prediction"""
    try:
        response = requests.post(f"{SERVER_URL}/api/predict")
        if response.status_code == 200:
            data = response.json()
            pred = data.get('prediction', {})
            print(f"\n⚠️  Prediction Results:")
            print(f"   Flood Risk: {pred.get('flood_risk', 'UNKNOWN')}")
            print(f"   Flood Probability: {pred.get('flood_probability', 0)*100:.1f}%")
            print(f"   Blockage Risk: {pred.get('blockage_risk', 'UNKNOWN')}")
            print(f"   Blockage Probability: {pred.get('blockage_probability', 0)*100:.1f}%")
            return True
        return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def simulate_continuous_data(duration_seconds=30, interval=2):
    """Simulate continuous sensor data for testing"""
    global DEVICE_1_WATER, DEVICE_2_WATER
    
    start_time = time.time()
    count = 0
    
    print(f"\n🔄 Simulating sensor data for {duration_seconds} seconds...")
    print(f"   Sending data every {interval} seconds\n")
    
    while time.time() - start_time < duration_seconds:
        # Simulate rising water levels
        DEVICE_1_WATER += random.uniform(-0.2, 0.5)
        DEVICE_2_WATER += random.uniform(-0.2, 0.5)
        
        # Keep within bounds
        DEVICE_1_WATER = max(0, min(100, DEVICE_1_WATER))
        DEVICE_2_WATER = max(0, min(100, DEVICE_2_WATER))
        
        # Calculate rise rates and percentages
        rise_rate_1 = random.uniform(0.0, 0.5)
        rise_rate_2 = random.uniform(0.0, 0.5)
        percentage_1 = (DEVICE_1_WATER / 100) * 100
        percentage_2 = (DEVICE_2_WATER / 100) * 100
        
        # Send data
        send_sensor_data(DEVICE_1_ID, DEVICE_1_WATER, rise_rate_1, percentage_1)
        send_sensor_data(DEVICE_2_ID, DEVICE_2_WATER, rise_rate_2, percentage_2)
        
        count += 2
        time.sleep(interval)
    
    print(f"\n✅ Sent {count} data points in {duration_seconds} seconds")

def main():
    """Main test function"""
    print("=" * 60)
    print("Water Level Monitoring System - Test Suite")
    print("=" * 60)
    
    # Test 1: Check server health
    print("\n[1/6] Testing server connection...")
    if not test_api_health():
        print("\n❌ Cannot connect to server. Please start the server first:")
        print("   cd c:\\Users\\mayur\\Project\\server")
        print("   python app.py")
        return
    
    # Test 2: Send sample data
    print("\n[2/6] Sending sample sensor data...")
    send_sensor_data(DEVICE_1_ID, 45.2, 0.5, 75.0)
    send_sensor_data(DEVICE_2_ID, 38.5, 0.3, 65.0)
    
    time.sleep(1)
    
    # Test 3: Get latest data
    print("\n[3/6] Fetching latest data...")
    get_latest_data()
    
    # Test 4: Get device statistics
    print("\n[4/6] Getting device statistics...")
    get_device_stats(DEVICE_1_ID)
    
    # Test 5: Get weather (if API is configured)
    print("\n[5/6] Fetching weather data...")
    get_weather()
    
    # Test 6: Get predictions
    print("\n[6/6] Getting predictions...")
    get_prediction()
    
    # Optional: Simulate continuous data
    print("\n" + "=" * 60)
    response = input("Simulate continuous sensor data? (y/n): ").lower()
    if response == 'y':
        duration = input("Duration in seconds (default 30): ")
        try:
            duration = int(duration)
        except:
            duration = 30
        simulate_continuous_data(duration, interval=2)
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("\nAccess the dashboard at: http://localhost:5000")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
