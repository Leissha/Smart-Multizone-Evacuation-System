const int SOUND_PIN = A0;
const int VIBRATION_PIN = 2;
const int RELAY_PIN = 4;

// Normal state: the relay powers the demonstration equipment load.
bool relayState = true;

unsigned long lastSampleTime = 0;
const unsigned long SAMPLE_INTERVAL = 1000;
int soundPeak = 0;
bool vibrationSeen = false;

void setup() {
  Serial.begin(9600);

  // Ball/toggle switch:
  // COM -> D2
  // L1  -> GND
  pinMode(VIBRATION_PIN, INPUT_PULLUP);

  pinMode(RELAY_PIN, OUTPUT);

  digitalWrite(RELAY_PIN, HIGH);

  Serial.println("Node 3 hardware test started");
  Serial.println("Commands: RELAY_ON, RELAY_OFF, EQUIPMENT_ALARM_ON, EQUIPMENT_ALARM_OFF");
}

void loop() {
  processSerialCommands();

  // Sample continuously so short sound and vibration events are not missed.
  soundPeak = max(soundPeak, analogRead(SOUND_PIN));
  if (digitalRead(VIBRATION_PIN) == LOW) {
    vibrationSeen = true;
  }

  if (millis() - lastSampleTime >= SAMPLE_INTERVAL) {
    lastSampleTime = millis();
    printSensorData(soundPeak, vibrationSeen);
    soundPeak = 0;
    vibrationSeen = false;
  }
}

void printSensorData(int soundLevel, bool vibrationDetected) {
  Serial.print("sound_level=");
  Serial.print(soundLevel);

  Serial.print(", vibration_detected=");
  Serial.print(vibrationDetected ? "true" : "false");

  Serial.print(", relay_state=");
  Serial.println(relayState ? "true" : "false");
}

void processSerialCommands() {
  if (!Serial.available()) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "RELAY_ON") {
    setRelay(true);
    Serial.println("ACK=RELAY_ON");
  }
  else if (command == "RELAY_OFF") {
    setRelay(false);
    Serial.println("ACK=RELAY_OFF");
  }
  else if (command == "EQUIPMENT_ALARM_ON") {
    // Emergency state: isolate the demonstration equipment power.
    setRelay(false);
    Serial.println("ACK=EQUIPMENT_ALARM_ON");
  }
  else if (command == "EQUIPMENT_ALARM_OFF") {
    // Normal state: restore the demonstration equipment power.
    setRelay(true);
    Serial.println("ACK=EQUIPMENT_ALARM_OFF");
  }
  else if (command.length() > 0) {
    Serial.print("ERROR=UNKNOWN_COMMAND:");
    Serial.println(command);
  }
}

void setRelay(bool enabled) {
  relayState = enabled;

  // According to your kit documentation:
  // HIGH = relay closed
  // LOW  = relay open
  digitalWrite(RELAY_PIN, enabled ? HIGH : LOW);
}
