"""
AquaSophia — Sensor Interface Layer
Supports: stub (simulated), ESP32 (WiFi/HTTP), serial (USB).
Swap modes in config.py — the SCADA loop doesn't care which backend.
"""

import time
import json
import random
import logging
from dataclasses import dataclass, asdict
from typing import Optional

import config

log = logging.getLogger("aqua.sensors")


@dataclass
class SensorReading:
    """Single snapshot of all NFT system sensors."""
    timestamp: float
    flow_rate_lpm: float        # Liters per minute through NFT channels
    ph: float                   # Nutrient solution pH
    ec_ms: float                # Electrical conductivity (mS/cm)
    water_temp_f: float         # Reservoir water temperature
    reservoir_1_gal: float      # Bucket 1 level
    reservoir_2_gal: float      # Bucket 2 level
    pump_running: bool          # Current pump state
    ambient_temp_f: float       # Air temperature near system
    humidity_pct: float         # Relative humidity

    def to_prompt_string(self) -> str:
        """Format readings for Gemma's context window."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))
        return (
            f"SENSOR READINGS at {ts}:\n"
            f"  Flow Rate: {self.flow_rate_lpm:.2f} L/min "
            f"(normal: {config.FLOW_RATE_NOMINAL_LPM})\n"
            f"  pH: {self.ph:.1f} (target: {config.PH_TARGET})\n"
            f"  EC: {self.ec_ms:.2f} mS/cm (target: {config.EC_TARGET_MS})\n"
            f"  Water Temp: {self.water_temp_f:.1f}F "
            f"(max safe: {config.WATER_TEMP_MAX_F}F)\n"
            f"  Reservoir 1: {self.reservoir_1_gal:.1f} gal\n"
            f"  Reservoir 2: {self.reservoir_2_gal:.1f} gal\n"
            f"  Pump: {'RUNNING' if self.pump_running else 'OFF'}\n"
            f"  Ambient: {self.ambient_temp_f:.1f}F, "
            f"Humidity: {self.humidity_pct:.0f}%"
        )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Stub sensor — simulated data with realistic drift for testing
# ---------------------------------------------------------------------------

class StubSensor:
    """Simulates an NFT hydroponic system with gradual drift and events."""

    def __init__(self):
        self._ph = 6.0
        self._ec = 1.5
        self._water_temp = 70.0
        self._res1 = 4.5
        self._res2 = 4.2
        self._flow = config.FLOW_RATE_NOMINAL_LPM
        self._pump = True
        self._tick = 0

    def read(self) -> SensorReading:
        self._tick += 1

        # Gradual drift — pH creeps up, reservoirs drain, temp rises
        self._ph += random.gauss(0.02, 0.05)
        self._ec += random.gauss(-0.01, 0.03)
        self._water_temp += random.gauss(0.1, 0.3)
        self._res1 -= random.uniform(0.01, 0.05)
        self._res2 -= random.uniform(0.01, 0.04)

        # Flow varies with pump state
        if self._pump:
            self._flow = config.FLOW_RATE_NOMINAL_LPM + random.gauss(0, 0.3)
        else:
            self._flow = 0.0

        # Occasional events (every ~20 ticks, simulate a problem)
        if self._tick % 20 == 0:
            event = random.choice(["clog", "ph_spike", "temp_spike", "low_res", "normal"])
            if event == "clog":
                self._flow *= 0.3
                log.info("[STUB] Simulating clog event — flow dropped")
            elif event == "ph_spike":
                self._ph += 0.8
                log.info("[STUB] Simulating pH spike")
            elif event == "temp_spike":
                self._water_temp += 8.0
                log.info("[STUB] Simulating temperature spike")
            elif event == "low_res":
                self._res1 = 0.4
                log.info("[STUB] Simulating low reservoir")

        # Clamp to realistic ranges
        self._ph = max(4.0, min(9.0, self._ph))
        self._ec = max(0.2, min(4.0, self._ec))
        self._water_temp = max(55.0, min(95.0, self._water_temp))
        self._res1 = max(0.0, min(5.0, self._res1))
        self._res2 = max(0.0, min(5.0, self._res2))
        self._flow = max(0.0, self._flow)

        return SensorReading(
            timestamp=time.time(),
            flow_rate_lpm=round(self._flow, 2),
            ph=round(self._ph, 2),
            ec_ms=round(self._ec, 2),
            water_temp_f=round(self._water_temp, 1),
            reservoir_1_gal=round(self._res1, 2),
            reservoir_2_gal=round(self._res2, 2),
            pump_running=self._pump,
            ambient_temp_f=round(85.0 + random.gauss(0, 2), 1),
            humidity_pct=round(70.0 + random.gauss(0, 5), 1),
        )

    def set_pump(self, state: bool):
        self._pump = state
        log.info(f"[STUB] Pump set to {'ON' if state else 'OFF'}")


# ---------------------------------------------------------------------------
# ESP32 sensor — reads from ESP32 WiFi HTTP endpoint
# ---------------------------------------------------------------------------

class ESP32Sensor:
    """Reads sensors from ESP32 running a simple HTTP JSON server."""

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or config.ESP32_URL).rstrip("/")
        try:
            import requests
            self._requests = requests
        except ImportError:
            raise ImportError("pip install requests — needed for ESP32 WiFi mode")

    def read(self) -> SensorReading:
        resp = self._requests.get(f"{self.base_url}/sensors", timeout=5)
        resp.raise_for_status()
        d = resp.json()
        return SensorReading(
            timestamp=time.time(),
            flow_rate_lpm=d.get("flow_lpm", 0),
            ph=d.get("ph", 7.0),
            ec_ms=d.get("ec_ms", 0),
            water_temp_f=d.get("water_temp_f", 70),
            reservoir_1_gal=d.get("res1_gal", 0),
            reservoir_2_gal=d.get("res2_gal", 0),
            pump_running=d.get("pump", False),
            ambient_temp_f=d.get("ambient_f", 80),
            humidity_pct=d.get("humidity", 50),
        )

    def set_pump(self, state: bool):
        self._requests.post(
            f"{self.base_url}/actuate",
            json={"pump": state},
            timeout=5,
        )


# ---------------------------------------------------------------------------
# Serial sensor — reads from Arduino/Nano over USB serial
# ---------------------------------------------------------------------------

class SerialSensor:
    """Reads JSON lines from a serial device (Arduino/Nano)."""

    def __init__(self, port: str = None, baud: int = None):
        try:
            import serial
            self._ser = serial.Serial(
                port or config.SERIAL_PORT,
                baud or config.SERIAL_BAUD,
                timeout=2,
            )
        except ImportError:
            raise ImportError("pip install pyserial — needed for serial mode")

    def read(self) -> SensorReading:
        # Send read command, expect JSON line back
        self._ser.write(b"READ\n")
        line = self._ser.readline().decode().strip()
        d = json.loads(line)
        return SensorReading(
            timestamp=time.time(),
            flow_rate_lpm=d.get("flow_lpm", 0),
            ph=d.get("ph", 7.0),
            ec_ms=d.get("ec_ms", 0),
            water_temp_f=d.get("water_temp_f", 70),
            reservoir_1_gal=d.get("res1_gal", 0),
            reservoir_2_gal=d.get("res2_gal", 0),
            pump_running=d.get("pump", False),
            ambient_temp_f=d.get("ambient_f", 80),
            humidity_pct=d.get("humidity", 50),
        )

    def set_pump(self, state: bool):
        cmd = b"PUMP_ON\n" if state else b"PUMP_OFF\n"
        self._ser.write(cmd)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_sensor(mode: str = None):
    """Create sensor backend based on config."""
    mode = mode or config.SENSOR_MODE
    if mode == "stub":
        log.info("Using STUB sensor (simulated data)")
        return StubSensor()
    elif mode == "esp32":
        log.info(f"Using ESP32 sensor at {config.ESP32_URL}")
        return ESP32Sensor()
    elif mode == "serial":
        log.info(f"Using Serial sensor at {config.SERIAL_PORT}")
        return SerialSensor()
    else:
        raise ValueError(f"Unknown sensor mode: {mode}")
