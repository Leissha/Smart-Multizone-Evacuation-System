/*
  Node 4 - Command Center
  SWE30011 Assignment 4 - Rajneesh Sharma

  Hardware:
    Push button     D2 -> switch -> GND, INPUT_PULLUP    manual emergency trigger
    Passive buzzer   D3                                   master alarm (tone())
    16x2 I2C LCD    SDA -> A4, SCL -> A5, 5V, GND         status display

  Sends one telemetry line per second, comma-separated key=value pairs -
  the same wire format as Node 3, not JSON:
    manual_emergency=false, display_state=SAFE, master_buzzer=false

  Accepts serial commands and replies with a matching ACK, same pattern
  as Node 3:
    LOCKDOWN_ON  -> ACK=LOCKDOWN_ON
    LOCKDOWN_OFF -> ACK=LOCKDOWN_OFF
    BUZZER_ON    -> ACK=BUZZER_ON
    BUZZER_OFF   -> ACK=BUZZER_OFF

  Library required (Library Manager): LiquidCrystal I2C (Frank de Brabander,
  or an equivalent hd44780 driver).
*/

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

const int BUTTON_PIN = 2;
const int BUZZER_PIN = 3;
const unsigned long SAMPLE_INTERVAL = 1000;

LiquidCrystal_I2C lcd(0x27, 16, 2);  // change to 0x3F if 0x27 doesn't work

bool manualEmergency = false;
bool masterBuzzer = false;
String displayState = "SAFE";

unsigned long lastSampleTime = 0;

void setup() {
  Serial.begin(9600);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  lcd.init();
  lcd.backlight();
  showDisplay();

  Serial.println("Node 4 hardware test started");
  Serial.println("Commands: LOCKDOWN_ON, LOCKDOWN_OFF, BUZZER_ON, BUZZER_OFF");
}

void loop() {
  processSerialCommands();

  bool pressed = (digitalRead(BUTTON_PIN) == LOW);
  if (pressed != manualEmergency) {
    manualEmergency = pressed;
    if (manualEmergency) {
      applyLockdown(true);
    }
  }

  if (millis() - lastSampleTime >= SAMPLE_INTERVAL) {
    lastSampleTime = millis();
    printSensorData();
  }
}

void printSensorData() {
  Serial.print("manual_emergency=");
  Serial.print(manualEmergency ? "true" : "false");

  Serial.print(", display_state=");
  Serial.print(displayState);

  Serial.print(", master_buzzer=");
  Serial.println(masterBuzzer ? "true" : "false");
}

void processSerialCommands() {
  if (!Serial.available()) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "LOCKDOWN_ON") {
    applyLockdown(true);
    Serial.println("ACK=LOCKDOWN_ON");
  }
  else if (command == "LOCKDOWN_OFF") {
    applyLockdown(false);
    Serial.println("ACK=LOCKDOWN_OFF");
  }
  else if (command == "BUZZER_ON") {
    setBuzzer(true);
    Serial.println("ACK=BUZZER_ON");
  }
  else if (command == "BUZZER_OFF") {
    setBuzzer(false);
    Serial.println("ACK=BUZZER_OFF");
  }
  else if (command.length() > 0) {
    Serial.print("ERROR=UNKNOWN_COMMAND:");
    Serial.println(command);
  }
}

void applyLockdown(bool active) {
  displayState = active ? "LOCKDOWN" : "SAFE";
  setBuzzer(active);
  showDisplay();
}

void setBuzzer(bool enabled) {
  masterBuzzer = enabled;
  if (enabled) {
    tone(BUZZER_PIN, 532);
  } else {
    noTone(BUZZER_PIN);
  }
}

void showDisplay() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Node4 Command Ctr");
  lcd.setCursor(0, 1);
  lcd.print(displayState);
}
