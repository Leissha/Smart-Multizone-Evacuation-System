const int SOUND_PIN = A0;
const int VIBRATION_PIN = 2;
const int BUZZER_PIN = 3;
const int RELAY_PIN = 4;

bool relayState = false;
bool buzzerState = false;

unsigned long lastSampleTime = 0;
const unsigned long SAMPLE_INTERVAL = 1000;
const unsigned long SOUND_WINDOW_MS = 75;

void setup() {
  Serial.begin(9600);

  // Ball/toggle switch:
  // COM -> D2
  // L1  -> GND
  pinMode(VIBRATION_PIN, INPUT_PULLUP);

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);

  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(RELAY_PIN, LOW);

  Serial.println("Node 3 hardware test started");
  Serial.println("Commands: RELAY_ON, RELAY_OFF, BUZZER_ON, BUZZER_OFF, ALL_ON, ALL_OFF");
}

void loop() {
  processSerialCommands();

  if (millis() - lastSampleTime >= SAMPLE_INTERVAL) {
    lastSampleTime = millis();
    printSensorData();
  }
}

void printSensorData() {
  // Capture the loudest sample in a short window instead of relying on one
  // instantaneous ADC reading each second.
  int soundLevel = 0;
  unsigned long windowStart = millis();
  while (millis() - windowStart < SOUND_WINDOW_MS) {
    soundLevel = max(soundLevel, analogRead(SOUND_PIN));
  }

  // INPUT_PULLUP:
  // switch connected to GND => LOW
  bool vibrationDetected = digitalRead(VIBRATION_PIN) == LOW;

  Serial.print("sound_level=");
  Serial.print(soundLevel);

  Serial.print(", vibration_detected=");
  Serial.print(vibrationDetected ? "true" : "false");

  Serial.print(", relay_state=");
  Serial.print(relayState ? "true" : "false");

  Serial.print(", buzzer_state=");
  Serial.println(buzzerState ? "true" : "false");
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
  else if (command == "BUZZER_ON") {
    setBuzzer(true);
    Serial.println("ACK=BUZZER_ON");
  }
  else if (command == "BUZZER_OFF") {
    setBuzzer(false);
    Serial.println("ACK=BUZZER_OFF");
  }
  else if (command == "ALL_ON") {
    setRelay(true);
    setBuzzer(true);
    Serial.println("ACK=ALL_ON");
  }
  else if (command == "ALL_OFF") {
    setRelay(false);
    setBuzzer(false);
    Serial.println("ACK=ALL_OFF");
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

void setBuzzer(bool enabled) {
  buzzerState = enabled;

  if (enabled) {
    tone(BUZZER_PIN, 532);
  } else {
    noTone(BUZZER_PIN);
  }
}
