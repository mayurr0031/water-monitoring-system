#include <WiFi.h>
#include <HTTPClient.h>
#include "WaterLevel.h"

// ===== WIFI CONFIG =====
const char* ssid = "RCB";
const char* password = "Java@007";

// ===== SERVER CONFIG =====
// Replace with your laptop IP (VERY IMPORTANT)
const char* serverURL = "http://192.168.31.222:5000/api/water-level";

// ===== SENSOR CONFIG =====
#define TRIG_PIN 5
#define ECHO_PIN 18
#define BASE_HEIGHT_CM 40.0   // distance from sensor to bottom

WaterLevel waterSensor(TRIG_PIN, ECHO_PIN, BASE_HEIGHT_CM);

// Timing
unsigned long lastSendTime = 0;
const long sendInterval = 5000; // send every 5 sec

void setup() {
    Serial.begin(115200);

    // Initialize sensor
    waterSensor.begin();

    // Connect to WiFi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nConnected!");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
}

void loop() {
    waterSensor.update();

    unsigned long currentMillis = millis();

    if (currentMillis - lastSendTime >= sendInterval) {
        lastSendTime = currentMillis;

        if (WiFi.status() == WL_CONNECTED) {
            HTTPClient http;

            http.begin(serverURL);
            http.addHeader("Content-Type", "application/json");

            // Get sensor values
            float waterLevel = waterSensor.getWaterLevel();
            float riseRate = waterSensor.getRiseRate();
            float percentage = waterSensor.getPercentageFilled(BASE_HEIGHT_CM);

            // Create JSON
            String jsonData = "{";
               jsonData += "\"device_id\":2,";
               jsonData += "\"water_level\":" + String(waterLevel, 2) + ",";
               jsonData += "\"rise_rate\":" + String(riseRate, 4) + ",";
               jsonData += "\"percentage\":" + String(percentage, 2);
               jsonData += "}";

            Serial.println("Sending Data:");
            Serial.println(jsonData);

            int httpResponseCode = http.POST(jsonData);

            if (httpResponseCode > 0) {
                String response = http.getString();
                Serial.print("Response: ");
                Serial.println(response);
            } else {
                Serial.print("Error: ");
                Serial.println(httpResponseCode);
            }

            http.end();
        } else {
            Serial.println("WiFi Disconnected!");
        }
    }
}