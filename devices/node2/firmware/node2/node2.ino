/*
  Node 2 - Hallway / Exit Monitoring
  SWE30011 IoT Programming - Abdul Muqtadir

  Watches the hallway exit with an ultrasonic sensor and tells people
  whether the exit route is clear (green LED) or blocked (red LED).

  Hardware (Arduino Uno):
    HC-SR04 ultrasonic   VCC -> 5V, TRIG -> D4, ECHO -> D3, GND -> GND
    Green LED            D5 -> LED -> 220 ohm -> GND     exit clear / "this way"
    Red LED              D6 -> LED -> 220 ohm -> GND     exit blocked / closed
    Passive buzzer       + -> 5V, - -> NPN collector     local warning
    NPN transistor       base <- 1k ohm <- D2, emitter -> GND
                         (PN2222 / S8050 from the kit, or BC337)

  Local rule (runs even if the PC/cloud is offline):
    exit_blocked = distance stays below threshold_cm for BLOCK_HOLD_MS.
    It clears only after the distance stays at/above the threshold for
    CLEAR_HOLD_MS, so a person walking past does not trigger an alarm.

  Telemetry, one line per second (key=value, same wire format as Node 3/4):
    distance_cm=123.4, exit_blocked=false, threshold_cm=50, evacuation_mode=false, exit_closed=false, buzzer_state=false, sensor_ok=true

  Serial commands -> acknowledgement:
    EVAC_ON / EVAC_OFF       -> ACK=EVAC_ON / ACK=EVAC_OFF       evacuation guidance mode
    EXIT_CLOSE / EXIT_OPEN   -> ACK=EXIT_CLOSE / ACK=EXIT_OPEN   command centre closes this route
    BUZZER_ON / BUZZER_OFF   -> ACK=BUZZER_ON / ACK=BUZZER_OFF   manual buzzer
    THRESHOLD=<5..300>       -> ACK=THRESHOLD=<value>            remote configuration (saved to EEPROM)
*/

#include <EEPROM.h>

const int TRIG_PIN = 4;
const int ECHO_PIN = 3;
const int GREEN_LED_PIN = 5;
const int RED_LED_PIN = 6;
const int BUZZER_PIN = 2;  // drives the transistor base

const unsigned long REPORT_INTERVAL = 1000;
const unsigned long MEASURE_INTERVAL = 100;
const unsigned long BLOCK_HOLD_MS = 3000;
const unsigned long CLEAR_HOLD_MS = 2000;
const unsigned long ECHO_TIMEOUT_US = 25000;  // ~4 m, the HC-SR04 maximum
const float MAX_RANGE_CM = 400.0;
const int MIN_THRESHOLD_CM = 5;
const int MAX_THRESHOLD_CM = 300;
const int DEFAULT_THRESHOLD_CM = 50;
const int SAMPLE_COUNT = 5;
const int NO_ECHO_CLEAR_COUNT = 10;   // 1 s of no echo -> nothing in range
const int NO_ECHO_FAULT_COUNT = 50;   // 5 s of no echo -> sensor_ok=false
const int EEPROM_ADDRESS = 0;
const int EEPROM_MAGIC = 0x4E32;  // "N2" - marks a valid saved threshold

int thresholdCm = DEFAULT_THRESHOLD_CM;
float distanceCm = MAX_RANGE_CM;
float lastValidCm = MAX_RANGE_CM;
bool sensorOk = true;
bool exitBlocked = false;
bool evacuationMode = false;
bool exitClosed = false;
bool manualBuzzer = false;
bool buzzerOn = false;

float samples[SAMPLE_COUNT];
int sampleIndex = 0;
int failedReadings = 0;
unsigned long belowSince = 0;
unsigned long aboveSince = 0;
unsigned long lastMeasure = 0;
unsigned long lastReport = 0;

struct SavedSettings {
  int magic;
  int threshold;
};

void loadThreshold();
void saveThreshold();
void measureDistance();
float medianOfSamples();
void updateBlockedState(unsigned long now);
void updateOutputs(unsigned long now);
void printTelemetry();
void processSerialCommands();

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(50);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(TRIG_PIN, LOW);

  loadThreshold();
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    samples[i] = MAX_RANGE_CM;
  }

  Serial.println("Node 2 exit monitor started");
  Serial.println("Commands: EVAC_ON, EVAC_OFF, EXIT_CLOSE, EXIT_OPEN, BUZZER_ON, BUZZER_OFF, THRESHOLD=<cm>");
}

void loop() {
  processSerialCommands();

  unsigned long now = millis();
  if (now - lastMeasure >= MEASURE_INTERVAL) {
    lastMeasure = now;
    measureDistance();
    updateBlockedState(now);
  }

  updateOutputs(now);

  if (now - lastReport >= REPORT_INTERVAL) {
    lastReport = now;
    printTelemetry();
  }
}

// ---------- sensing ----------

float readDistanceOnce() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  if (duration == 0) {
    return -1.0;  // no echo
  }
  return duration * 0.0343 / 2.0;
}

void measureDistance() {
  float reading = readDistanceOnce();
  if (reading >= 0) {
    failedReadings = 0;
    lastValidCm = min(reading, MAX_RANGE_CM);
  } else {
    failedReadings++;
    if (lastValidCm < thresholdCm) {
      // The last echo was close, so the object has most likely moved right
      // up to (or is covering) the sensor - closer than its ~3 cm minimum.
      // Treat it as still blocking instead of "nothing there".
      reading = lastValidCm;
    } else if (failedReadings >= NO_ECHO_CLEAR_COUNT) {
      // Silence for a while after a far reading: nothing within 4 m.
      reading = MAX_RANGE_CM;
    } else {
      return;  // a single missed echo - ignore it
    }
  }
  // Long silence usually means a loose Trig/Echo/5V wire, not an empty hall.
  sensorOk = failedReadings < NO_ECHO_FAULT_COUNT;

  samples[sampleIndex] = reading;
  sampleIndex = (sampleIndex + 1) % SAMPLE_COUNT;
  distanceCm = medianOfSamples();
}

float medianOfSamples() {
  // Median of the last 5 readings removes single-reading spikes.
  float sorted[SAMPLE_COUNT];
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    sorted[i] = samples[i];
  }
  for (int i = 1; i < SAMPLE_COUNT; i++) {
    float key = sorted[i];
    int j = i - 1;
    while (j >= 0 && sorted[j] > key) {
      sorted[j + 1] = sorted[j];
      j--;
    }
    sorted[j + 1] = key;
  }
  return sorted[SAMPLE_COUNT / 2];
}

void updateBlockedState(unsigned long now) {
  if (distanceCm < thresholdCm) {
    aboveSince = 0;
    if (belowSince == 0) belowSince = now;
    if (!exitBlocked && now - belowSince >= BLOCK_HOLD_MS) exitBlocked = true;
  } else {
    belowSince = 0;
    if (aboveSince == 0) aboveSince = now;
    if (exitBlocked && now - aboveSince >= CLEAR_HOLD_MS) exitBlocked = false;
  }
}

// ---------- actuators ----------

void updateOutputs(unsigned long now) {
  bool flash = (now / 400) % 2 == 0;
  bool green;
  bool red;
  bool alarm = false;

  if (exitClosed) {
    // Command centre has closed this route: never show green.
    green = false;
    red = evacuationMode ? flash : true;
  } else if (exitBlocked) {
    green = false;
    red = true;
    alarm = evacuationMode;  // blocked exit during an evacuation is urgent
  } else {
    green = evacuationMode ? flash : true;  // flashing green = "exit this way"
    red = false;
  }

  digitalWrite(GREEN_LED_PIN, green ? HIGH : LOW);
  digitalWrite(RED_LED_PIN, red ? HIGH : LOW);

  bool wantBuzzer = manualBuzzer || (alarm && flash);
  if (wantBuzzer != buzzerOn) {
    buzzerOn = wantBuzzer;
    if (buzzerOn) tone(BUZZER_PIN, 880);
    else noTone(BUZZER_PIN);
  }
}

// ---------- serial protocol ----------

void printTelemetry() {
  Serial.print("distance_cm=");
  Serial.print(distanceCm, 1);
  Serial.print(", exit_blocked=");
  Serial.print(exitBlocked ? "true" : "false");
  Serial.print(", threshold_cm=");
  Serial.print(thresholdCm);
  Serial.print(", evacuation_mode=");
  Serial.print(evacuationMode ? "true" : "false");
  Serial.print(", exit_closed=");
  Serial.print(exitClosed ? "true" : "false");
  Serial.print(", buzzer_state=");
  Serial.print(manualBuzzer ? "true" : "false");
  Serial.print(", sensor_ok=");
  Serial.println(sensorOk ? "true" : "false");
}

void processSerialCommands() {
  if (!Serial.available()) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "EVAC_ON") {
    evacuationMode = true;
    Serial.println("ACK=EVAC_ON");
  }
  else if (command == "EVAC_OFF") {
    evacuationMode = false;
    Serial.println("ACK=EVAC_OFF");
  }
  else if (command == "EXIT_CLOSE") {
    exitClosed = true;
    Serial.println("ACK=EXIT_CLOSE");
  }
  else if (command == "EXIT_OPEN") {
    exitClosed = false;
    Serial.println("ACK=EXIT_OPEN");
  }
  else if (command == "BUZZER_ON") {
    manualBuzzer = true;
    Serial.println("ACK=BUZZER_ON");
  }
  else if (command == "BUZZER_OFF") {
    manualBuzzer = false;
    Serial.println("ACK=BUZZER_OFF");
  }
  else if (command.startsWith("THRESHOLD=")) {
    int value = command.substring(10).toInt();
    if (value >= MIN_THRESHOLD_CM && value <= MAX_THRESHOLD_CM) {
      thresholdCm = value;
      saveThreshold();
      Serial.print("ACK=THRESHOLD=");
      Serial.println(thresholdCm);
    } else {
      Serial.print("ERROR=THRESHOLD_OUT_OF_RANGE:");
      Serial.println(command);
    }
  }
  else if (command.length() > 0) {
    Serial.print("ERROR=UNKNOWN_COMMAND:");
    Serial.println(command);
  }
}

// ---------- settings ----------

void loadThreshold() {
  SavedSettings saved;
  EEPROM.get(EEPROM_ADDRESS, saved);
  if (saved.magic == EEPROM_MAGIC &&
      saved.threshold >= MIN_THRESHOLD_CM && saved.threshold <= MAX_THRESHOLD_CM) {
    thresholdCm = saved.threshold;
  }
}

void saveThreshold() {
  SavedSettings saved = { EEPROM_MAGIC, thresholdCm };
  EEPROM.put(EEPROM_ADDRESS, saved);
}
