#include <WiFi.h>
#include <HTTPClient.h>
#include <math.h>
#include "WaterLevel.h"

// ===== WIFI CONFIG =====
const char* ssid = "Esptest";
const char* password = "Gouda#15";

// ===== SERVER CONFIG =====
// Replace with your laptop IP (VERY IMPORTANT)
const char* serverURL = "http://10.226.209.237:5000/api/water-level";

// ===== SENSOR CONFIG =====
#define TRIG_PIN 5
#define ECHO_PIN 18
#define BASE_HEIGHT_CM 40.0   // distance from sensor to bottom
#define MQ4_PIN 34   // connect MQ-4 A0/D0 output to GPIO34
#define MQ135_PIN 35 // connect MQ-135 A0/D0 output to GPIO35

// MQ-4 conversion constants
const float RL_VALUE = 1.0;       // Load resistance in kilo-ohms (adjust to your board)
const float R0_BASELINE = 10.0;   // Your calibrated sensor R0 value in clean air
const float A_MULTIPLIER = 1012.7; // Methane curve multiplier
const float B_EXPONENT = -2.786;  // Methane curve exponent

WaterLevel waterSensor(TRIG_PIN, ECHO_PIN, BASE_HEIGHT_CM);

struct GasSensorReadings {
    uint16_t mq4Raw;
    uint16_t mq135Raw;
    uint16_t mq4Mv;
    uint16_t mq135Mv;
};

GasSensorReadings readGasSensors() {
    GasSensorReadings readings = {0, 0, 0, 0};

    readings.mq4Raw = analogRead(MQ4_PIN);
    readings.mq135Raw = analogRead(MQ135_PIN);
    readings.mq4Mv = analogReadMilliVolts(MQ4_PIN);
    readings.mq135Mv = analogReadMilliVolts(MQ135_PIN);

    return readings;
}

float convertMvToPpm(uint32_t millivolts) {
    float vs = (float)millivolts / 1000.0;
    if (vs >= 5.0) vs = 4.99;
    if (vs <= 0.0) vs = 0.01;

    float rs = ((5.0 - vs) / vs) * RL_VALUE;
    float ratio = rs / R0_BASELINE;
    float ppm = A_MULTIPLIER * pow(ratio, B_EXPONENT);

    return ppm;
}

// Timing
unsigned long lastSendTime = 0;
const long sendInterval = 5000; // send every 5 sec

void setup() {
    Serial.begin(115200);

    analogReadResolution(12);
    analogSetPinAttenuation(MQ4_PIN, ADC_11db);
    analogSetPinAttenuation(MQ135_PIN, ADC_11db);

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
            GasSensorReadings gasReadings = readGasSensors();

            // Create JSON
            float mq4Ppm = convertMvToPpm(gasReadings.mq4Mv);
            float mq135Ppm = convertMvToPpm(gasReadings.mq135Mv);

            String jsonData = "{";
               jsonData += "\"device_id\":" + String(2) + ",";
               jsonData += "\"water_level\":" + String(waterLevel, 2) + ",";
               jsonData += "\"rise_rate\":" + String(riseRate, 4) + ",";
               jsonData += "\"percentage\":" + String(percentage, 2) + ",";
               jsonData += "\"mq4_mv\":" + String(gasReadings.mq4Mv) + ",";
               jsonData += "\"mq135_mv\":" + String(gasReadings.mq135Mv);
               jsonData += "}";

            Serial.println("Sending Data:");
            Serial.println(jsonData);
            Serial.print("MQ-4: ");
            Serial.print(mq4Ppm, 2);
            Serial.print(" ppm | MQ-135: ");
            Serial.print(mq135Ppm, 2);
            Serial.println(" ppm");

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