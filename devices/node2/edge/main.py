from __future__ import annotations

import logging
import signal
import time

from devices.node2.edge.actuator_service import ActuatorService
from devices.node2.edge.config import get_config
from devices.node2.edge.sensor_parser import parse_telemetry_line
from devices.node2.edge.serial_client import SerialClient
from devices.node2.edge.thingsboard_client import ThingsBoardClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("evacuation.node2")


def run() -> None:
    config = get_config()
    serial_client = SerialClient(config.serial_port, config.serial_baud_rate, config.serial_timeout)
    actuators = ActuatorService(config.ack_timeout)
    cloud = ThingsBoardClient(config, actuators)
    running = True
    last_frame = time.monotonic()
    stale_reported = False

    def stop(signum: int, frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    cloud.start()
    logger.info("Node 2 edge started for %s", config.device_id)

    while running:
        try:
            line = serial_client.read_line()
            if line:
                if line.startswith("ACK="):
                    actuators.handle_ack(line)
                    logger.info("Arduino acknowledgement: %s", line)
                elif line.startswith("ERROR="):
                    actuators.handle_error(line)
                    logger.warning("Arduino rejected command: %s", line)
                else:
                    telemetry = parse_telemetry_line(line)
                    if telemetry is not None:
                        last_frame = time.monotonic()
                        stale_reported = False
                        logger.info("Serial telemetry cloud_connected=%s payload=%s", cloud.connected, telemetry)
                        cloud.publish_telemetry(telemetry)
                    else:
                        logger.debug("Arduino message ignored: %s", line)

            # If the Arduino goes quiet (unplugged, crashed), tell the cloud
            # once so rules and the web app do not trust an old reading.
            if not stale_reported and time.monotonic() - last_frame >= config.stale_after:
                logger.warning("No Arduino telemetry for %.0fs; reporting sensor_ok=false", config.stale_after)
                cloud.publish_telemetry({"sensor_ok": False})
                stale_reported = True

            actuators.tick(serial_client)
            time.sleep(config.poll_interval)
        except Exception as error:
            logger.exception("Edge loop recovered from an unexpected error: %s", error)
            time.sleep(1.0)

    cloud.stop()
    serial_client.close()


if __name__ == "__main__":
    run()
