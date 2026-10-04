import os
import json
import time
import serial
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()

TB_HOST = os.getenv("THINGSBOARD_HOST", "thingsboard.cloud")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "txIk3AMKU9hoQUC4Gyhr")
SERIAL_PORT = os.getenv("SERIAL_PORT", "COM3")
BAUD_RATE = int(os.getenv("BAUD_RATE", 9600))

# Open serial connection to Arduino
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)

client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected to ThingsBoard with result code {rc}")
    # Subscribe to remote procedure calls (RPC)
    client.subscribe("v1/devices/me/rpc/request/+")

def on_message(client, userdata, msg):
    print(f"[RPC Received] {msg.topic}: {msg.payload.decode()}")
    req_id = msg.topic.split('/')[-1]
    try:
        data = json.loads(msg.payload.decode())
        method = data.get("method")
        params = data.get("params", False)

        if method == "setAlarm":
            cmd = "CMD:ALARM:ON\n" if params else "CMD:ALARM:OFF\n"
            ser.write(cmd.encode())

            # Wait for Arduino ACK
            ack = ser.readline().decode().strip()
            print(f"[MCU Response] {ack}")

            # Acknowledge back to ThingsBoard
            response_topic = f"v1/devices/me/rpc/response/{req_id}"
            client.publish(response_topic, json.dumps({"status": "SUCCESS", "ack": ack}))
    except Exception as e:
        print(f"Error handling RPC: {e}")

client.on_connect = on_connect
client.on_message = on_message

print(f"Connecting to {TB_HOST}...")
client.connect(TB_HOST, 1883, 60)
client.loop_start()

try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if "temperature=" in line and "smoke_level=" in line:
                payload = {}
                parts = line.split(",")
                for part in parts:
                    k, v = part.split("=")
                    if k == "temperature":
                        payload[k] = float(v)
                    elif k == "fire_detected":
                        payload[k] = (v.lower() == "true")
                    else:
                        payload[k] = v

                client.publish("v1/devices/me/telemetry", json.dumps(payload))
                print(f"[Telemetry Published] {payload}")
        time.sleep(0.1)
except KeyboardInterrupt:
    ser.close()
    client.loop_stop()
    client.disconnect()