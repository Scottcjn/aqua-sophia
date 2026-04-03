/*
 * Aqua Elya — ESP32 NFT Sensor Hub
 * Reads hydroponic sensors, serves JSON over WiFi HTTP.
 * Laptop runs Gemma 4 brain, ESP32 is the field I/O.
 *
 * Wiring:
 *   GPIO 34 (ADC1_6) ← Soil/water moisture or pH analog
 *   GPIO 35 (ADC1_7) ← EC/TDS analog
 *   GPIO 4           ← DS18B20 water temperature (OneWire)
 *   GPIO 27          ← YF-S201 flow meter (pulse interrupt)
 *   GPIO 32 (ADC1_4) ← Ultrasonic echo (reservoir 1 level)
 *   GPIO 33 (ADC1_5) ← Ultrasonic echo (reservoir 2 level)
 *   GPIO 26          → Relay CH1 (main pump)
 *   GPIO 25          → Relay CH2 (spare / pH dosing pump)
 *   GPIO 14          ← DHT22 ambient temp/humidity
 *
 * Endpoints:
 *   GET  /sensors    → JSON with all readings
 *   POST /actuate    → {"pump": true/false, "dose": true/false}
 *   GET  /health     → {"ok": true, "uptime_ms": ...}
 */

#include <WiFi.h>
#include <WebServer.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <DHT.h>

// ─── WiFi Config ───────────────────────────────────────
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASS";

// ─── Pin Assignments ───────────────────────────────────
#define PIN_PH_ANALOG    34   // pH probe via analog board
#define PIN_EC_ANALOG    35   // EC/TDS probe via analog board
#define PIN_WATER_TEMP    4   // DS18B20 OneWire
#define PIN_FLOW_METER   27   // YF-S201 pulse output
#define PIN_RES1_TRIG    15   // HC-SR04 trigger (reservoir 1)
#define PIN_RES1_ECHO    32   // HC-SR04 echo (reservoir 1)
#define PIN_RES2_TRIG    16   // HC-SR04 trigger (reservoir 2)
#define PIN_RES2_ECHO    33   // HC-SR04 echo (reservoir 2)
#define PIN_RELAY_PUMP   26   // Relay channel 1 — main pump
#define PIN_RELAY_DOSE   25   // Relay channel 2 — pH dose pump
#define PIN_DHT          14   // DHT22 ambient sensor

// ─── Sensor Objects ────────────────────────────────────
OneWire oneWire(PIN_WATER_TEMP);
DallasTemperature waterTemp(&oneWire);
DHT dht(PIN_DHT, DHT22);
WebServer server(80);

// ─── Flow Meter ────────────────────────────────────────
volatile unsigned long flowPulseCount = 0;
unsigned long lastFlowCheck = 0;
float flowRateLPM = 0.0;

// YF-S201: ~7.5 pulses per liter
#define FLOW_CALIBRATION 7.5

void IRAM_ATTR flowPulseISR() {
    flowPulseCount++;
}

// ─── Relay State ───────────────────────────────────────
bool pumpState = false;
bool doseState = false;

// ─── Reservoir Level (HC-SR04) ─────────────────────────
// Bucket is 5 gal ≈ 14" tall. Sensor at top measures distance to water.
#define BUCKET_HEIGHT_CM 35.5   // ~14 inches
#define BUCKET_CAPACITY_GAL 5.0

float readReservoirGal(int trigPin, int echoPin) {
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    long duration = pulseIn(echoPin, HIGH, 30000); // 30ms timeout
    if (duration == 0) return -1.0; // No echo — sensor error

    float distanceCM = duration * 0.034 / 2.0;
    float waterHeightCM = BUCKET_HEIGHT_CM - distanceCM;
    if (waterHeightCM < 0) waterHeightCM = 0;

    // Linear approximation (good enough for cylindrical bucket)
    float gallons = (waterHeightCM / BUCKET_HEIGHT_CM) * BUCKET_CAPACITY_GAL;
    return gallons;
}

// ─── pH Reading ────────────────────────────────────────
// Analog pH board outputs 0-3.3V for pH 0-14
// Calibrate these for your specific board
#define PH_OFFSET 0.0
#define PH_SLOPE  (14.0 / 4095.0)  // 12-bit ADC

float readPH() {
    int raw = analogRead(PIN_PH_ANALOG);
    // Average 10 readings for stability
    float sum = raw;
    for (int i = 1; i < 10; i++) {
        sum += analogRead(PIN_PH_ANALOG);
        delay(10);
    }
    float avg = sum / 10.0;
    return (avg * PH_SLOPE) + PH_OFFSET;
}

// ─── EC Reading ────────────────────────────────────────
// TDS meter analog output — calibrate for your board
#define EC_OFFSET 0.0
#define EC_SLOPE  (5.0 / 4095.0)  // 0-5 mS/cm range

float readEC() {
    int raw = analogRead(PIN_EC_ANALOG);
    float sum = raw;
    for (int i = 1; i < 10; i++) {
        sum += analogRead(PIN_EC_ANALOG);
        delay(10);
    }
    float avg = sum / 10.0;
    return (avg * EC_SLOPE) + EC_OFFSET;
}

// ─── Flow Rate Calculation ─────────────────────────────
void updateFlowRate() {
    unsigned long now = millis();
    unsigned long elapsed = now - lastFlowCheck;

    if (elapsed >= 1000) { // Update every second
        noInterrupts();
        unsigned long pulses = flowPulseCount;
        flowPulseCount = 0;
        interrupts();

        // L/min = (pulses / calibration) * (60000 / elapsed_ms)
        flowRateLPM = (pulses / FLOW_CALIBRATION) * (60000.0 / elapsed);
        lastFlowCheck = now;
    }
}

// ─── HTTP Handlers ─────────────────────────────────────

void handleSensors() {
    waterTemp.requestTemperatures();
    float waterTempF = waterTemp.getTempFByIndex(0);
    float ph = readPH();
    float ec = readEC();
    float res1 = readReservoirGal(PIN_RES1_TRIG, PIN_RES1_ECHO);
    float res2 = readReservoirGal(PIN_RES2_TRIG, PIN_RES2_ECHO);
    float ambientF = dht.readTemperature(true); // Fahrenheit
    float humidity = dht.readHumidity();

    // Build JSON
    String json = "{";
    json += "\"flow_lpm\":" + String(flowRateLPM, 2) + ",";
    json += "\"ph\":" + String(ph, 2) + ",";
    json += "\"ec_ms\":" + String(ec, 2) + ",";
    json += "\"water_temp_f\":" + String(waterTempF, 1) + ",";
    json += "\"res1_gal\":" + String(res1, 2) + ",";
    json += "\"res2_gal\":" + String(res2, 2) + ",";
    json += "\"pump\":" + String(pumpState ? "true" : "false") + ",";
    json += "\"dose\":" + String(doseState ? "true" : "false") + ",";
    json += "\"ambient_f\":" + String(ambientF, 1) + ",";
    json += "\"humidity\":" + String(humidity, 1);
    json += "}";

    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(200, "application/json", json);
}

void handleActuate() {
    if (server.method() != HTTP_POST) {
        server.send(405, "text/plain", "POST only");
        return;
    }

    String body = server.arg("plain");

    // Simple JSON parsing (no ArduinoJson dependency)
    if (body.indexOf("\"pump\":true") >= 0 || body.indexOf("\"pump\": true") >= 0) {
        pumpState = true;
        digitalWrite(PIN_RELAY_PUMP, HIGH);
    } else if (body.indexOf("\"pump\":false") >= 0 || body.indexOf("\"pump\": false") >= 0) {
        pumpState = false;
        digitalWrite(PIN_RELAY_PUMP, LOW);
    }

    if (body.indexOf("\"dose\":true") >= 0 || body.indexOf("\"dose\": true") >= 0) {
        doseState = true;
        digitalWrite(PIN_RELAY_DOSE, HIGH);
    } else if (body.indexOf("\"dose\":false") >= 0 || body.indexOf("\"dose\": false") >= 0) {
        doseState = false;
        digitalWrite(PIN_RELAY_DOSE, LOW);
    }

    String json = "{\"pump\":" + String(pumpState ? "true" : "false");
    json += ",\"dose\":" + String(doseState ? "true" : "false") + "}";

    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(200, "application/json", json);
}

void handleHealth() {
    String json = "{\"ok\":true,\"uptime_ms\":" + String(millis());
    json += ",\"ip\":\"" + WiFi.localIP().toString() + "\"}";
    server.send(200, "application/json", json);
}

void handleCORS() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
    server.send(204);
}

// ─── Setup ─────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    Serial.println("\n=== Aqua Elya ESP32 Sensor Hub ===");

    // Pin modes
    pinMode(PIN_RELAY_PUMP, OUTPUT);
    pinMode(PIN_RELAY_DOSE, OUTPUT);
    pinMode(PIN_RES1_TRIG, OUTPUT);
    pinMode(PIN_RES2_TRIG, OUTPUT);
    pinMode(PIN_RES1_ECHO, INPUT);
    pinMode(PIN_RES2_ECHO, INPUT);
    pinMode(PIN_FLOW_METER, INPUT_PULLUP);

    // Start sensors
    waterTemp.begin();
    dht.begin();

    // Flow meter interrupt
    attachInterrupt(digitalPinToInterrupt(PIN_FLOW_METER), flowPulseISR, RISING);
    lastFlowCheck = millis();

    // Relays off at boot
    digitalWrite(PIN_RELAY_PUMP, LOW);
    digitalWrite(PIN_RELAY_DOSE, LOW);

    // WiFi
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("Connecting to WiFi");
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 30) {
        delay(500);
        Serial.print(".");
        retries++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected!");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\nWiFi FAILED — running in offline mode");
    }

    // HTTP routes
    server.on("/sensors", HTTP_GET, handleSensors);
    server.on("/actuate", HTTP_POST, handleActuate);
    server.on("/actuate", HTTP_OPTIONS, handleCORS);
    server.on("/health", HTTP_GET, handleHealth);
    server.begin();

    Serial.println("HTTP server started on port 80");
    Serial.println("Endpoints: GET /sensors, POST /actuate, GET /health");
}

// ─── Main Loop ─────────────────────────────────────────

void loop() {
    server.handleClient();
    updateFlowRate();

    // Reconnect WiFi if dropped
    static unsigned long lastWifiCheck = 0;
    if (millis() - lastWifiCheck > 10000) {
        lastWifiCheck = millis();
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("WiFi lost — reconnecting...");
            WiFi.reconnect();
        }
    }
}
