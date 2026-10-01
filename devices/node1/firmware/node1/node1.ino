#include <Arduino.h>

const int PIN_TEMP_ANALOG = A0;  // Using standard analog temp or LDR
const int PIN_SMOKE_ANALOG = A1; // Photoresistor / smoke simulator
const int PIN_LED = 8;
const int PIN_BUZZER = 9;

unsigned long lastTelemetry = 0;
const unsigned long INTERVAL = 2000;

void setup() {
  Serial.begin(9600);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_BUZZER, LOW);
}

void loop() {
  // 1. Process Remote RPC / Actuator Commands from Edge
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "CMD:ALARM:ON") {
      digitalWrite(PIN_LED, HIGH);
      digitalWrite(PIN_BUZZER, HIGH);
      Serial.println("ACK:ALARM:ON");
    } else if (cmd == "CMD:ALARM:OFF") {
      digitalWrite(PIN_LED, LOW);
      digitalWrite(PIN_BUZZER, LOW);
      Serial.println("ACK:ALARM:OFF");
    }
  }

  // 2. Transmit Sensor Telemetry
  if (millis() - lastTelemetry >= INTERVAL) {
    lastTelemetry = millis();
    
    // Read and map analog sensors (or use DHT library)
    int rawTemp = analogRead(PIN_TEMP_ANALOG);
    float temperature = (rawTemp * 5.0 / 1024.0) * 100.0; // Scaled to °C (e.g. LM35)
    if (temperature > 80.0 || temperature < 0.0) temperature = 24.5; // Baseline clamp

    int rawSmoke = analogRead(PIN_SMOKE_ANALOG);
    String smokeLevel = (rawSmoke > 600) ? "HIGH" : ((rawSmoke > 300) ? "MEDIUM" : "LOW");
    bool fireDetected = (smokeLevel == "HIGH" || temperature > 50.0);

    // Contract format: temperature=XX.X,smoke_level=LOW,fire_detected=false
    Serial.print("temperature=");
    Serial.print(temperature, 1);
    Serial.print(",smoke_level=");
    Serial.print(smokeLevel);
    Serial.print(",fire_detected=");
    Serial.println(fireDetected ? "true" : "false");
  }
}