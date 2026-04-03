#!/usr/bin/env python3
"""
AquaSophia — Main SCADA Loop
NFT Hydroponic Monitoring & Control with Gemma 4 Function Calling

Usage:
    python3 scada_loop.py                  # Run with stub sensors (demo mode)
    python3 scada_loop.py --mode esp32     # Run with real ESP32 sensors
    python3 scada_loop.py --mode serial    # Run with USB serial sensors
    python3 scada_loop.py --no-gemma       # Rule-based only (no LLM needed)
    python3 scada_loop.py --once           # Single reading + decision, then exit
    python3 scada_loop.py --fast           # 5-second intervals for demo
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import config
from sensors import SensorReading, create_sensor
from gemma_brain import GemmaBrain, fallback_evaluate
from camera import create_camera

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE),
    ],
)
log = logging.getLogger("aqua.scada")


# ---------------------------------------------------------------------------
# Action executor — turns Gemma's function calls into real actions
# ---------------------------------------------------------------------------

class ActionExecutor:
    """Executes SCADA actions from Gemma's function calls."""

    def __init__(self, sensor_backend):
        self.sensor = sensor_backend
        self.action_log = []

    def execute(self, calls: list[dict], reading: SensorReading):
        """Execute a list of function calls from Gemma."""
        for call in calls:
            name = call["name"]
            args = call.get("arguments", {})
            ts = datetime.now().strftime("%H:%M:%S")

            if name == "set_pump":
                state = args.get("state", False)
                reason = args.get("reason", "no reason given")
                self.sensor.set_pump(state)
                icon = "🟢" if state else "🔴"
                print(f"\n  {icon} PUMP {'ON' if state else 'OFF'}: {reason}")
                log.info(f"ACTION set_pump={state}: {reason}")

            elif name == "alert_farmer":
                msg = args.get("message", "")
                sev = args.get("severity", "info")
                icons = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
                icon = icons.get(sev, "📋")
                print(f"\n  {icon} ALERT [{sev.upper()}]: {msg}")
                log.warning(f"ALERT {sev}: {msg}")

            elif name == "adjust_flow_target":
                target = args.get("target_lpm", config.FLOW_RATE_NOMINAL_LPM)
                reason = args.get("reason", "")
                print(f"\n  🔧 FLOW TARGET → {target:.1f} L/min: {reason}")
                log.info(f"ACTION adjust_flow={target}: {reason}")

            elif name == "log_observation":
                obs = args.get("observation", "")
                cat = args.get("category", "trend")
                print(f"\n  📝 [{cat.upper()}]: {obs}")
                log.info(f"OBSERVATION {cat}: {obs}")

            elif name == "request_image":
                reason = args.get("reason", "visual check requested")
                print(f"\n  📷 IMAGE REQUESTED: {reason}")
                log.info(f"ACTION request_image: {reason}")

            elif name == "no_action":
                summary = args.get("status_summary", "nominal")
                print(f"\n  ✅ OK: {summary}")
                log.debug(f"NO_ACTION: {summary}")

            else:
                log.warning(f"Unknown function call: {name}({args})")

            self.action_log.append({
                "timestamp": time.time(),
                "function": name,
                "arguments": args,
            })


# ---------------------------------------------------------------------------
# CSV data logger
# ---------------------------------------------------------------------------

def init_csv(path: str):
    """Create CSV with headers if it doesn't exist."""
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "flow_lpm", "ph", "ec_ms", "water_temp_f",
                "res1_gal", "res2_gal", "pump", "ambient_f", "humidity_pct",
            ])


def log_csv(path: str, reading: SensorReading):
    """Append a sensor reading to CSV."""
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.fromtimestamp(reading.timestamp).isoformat(),
            reading.flow_rate_lpm,
            reading.ph,
            reading.ec_ms,
            reading.water_temp_f,
            reading.reservoir_1_gal,
            reading.reservoir_2_gal,
            int(reading.pump_running),
            reading.ambient_temp_f,
            reading.humidity_pct,
        ])


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════╗
║              AquaSophia — NFT SCADA Monitor               ║
║         108-Cell Hydroponic System + Gemma 4 Brain        ║
║                     Elyan Labs 2026                       ║
╚═══════════════════════════════════════════════════════════╝
    """)


def print_reading(reading: SensorReading, tick: int):
    """Pretty-print sensor readings to terminal."""
    ts = datetime.fromtimestamp(reading.timestamp).strftime("%H:%M:%S")

    # Color coding helper
    def color_val(num, low, high, fmt=".1f", unit=""):
        s = f"{num:{fmt}}"
        if num < low or num > high:
            return f"\033[91m{s}{unit}\033[0m"  # Red
        return f"\033[92m{s}{unit}\033[0m"  # Green

    print(f"\n{'─' * 55}")
    print(f"  Reading #{tick}  |  {ts}")
    print(f"{'─' * 55}")
    print(f"  Flow:    {color_val(reading.flow_rate_lpm, config.FLOW_RATE_MIN_LPM, config.FLOW_RATE_MAX_LPM, '.2f', ' L/min')}"
          f"   (target: {config.FLOW_RATE_NOMINAL_LPM})")
    print(f"  pH:      {color_val(reading.ph, config.PH_MIN, config.PH_MAX)}"
          f"         (range: {config.PH_MIN}-{config.PH_MAX})")
    print(f"  EC:      {color_val(reading.ec_ms, config.EC_MIN_MS, config.EC_MAX_MS, '.2f', ' mS/cm')}"
          f"  (target: {config.EC_TARGET_MS})")
    print(f"  W.Temp:  {color_val(reading.water_temp_f, config.WATER_TEMP_MIN_F, config.WATER_TEMP_MAX_F, '.1f', 'F')}"
          f"      (max: {config.WATER_TEMP_MAX_F}F)")
    print(f"  Res 1:   {color_val(reading.reservoir_1_gal, config.RESERVOIR_LOW_GAL, 5.0, '.1f', ' gal')}"
          f"     Res 2: {reading.reservoir_2_gal:.1f} gal")
    print(f"  Pump:    {'🟢 ON' if reading.pump_running else '🔴 OFF'}"
          f"       Ambient: {reading.ambient_temp_f:.0f}F / {reading.humidity_pct:.0f}%")


# ---------------------------------------------------------------------------
# Main SCADA loop
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AquaSophia NFT SCADA Monitor")
    parser.add_argument("--mode", choices=["stub", "esp32", "serial"],
                        default=config.SENSOR_MODE, help="Sensor backend")
    parser.add_argument("--no-gemma", action="store_true",
                        help="Use rule-based fallback only (no LLM)")
    parser.add_argument("--once", action="store_true",
                        help="Single reading + decision, then exit")
    parser.add_argument("--fast", action="store_true",
                        help="5-second intervals for demo")
    parser.add_argument("--api-url", default=config.GEMMA_API_URL,
                        help="Gemma API endpoint")
    parser.add_argument("--no-camera", action="store_true",
                        help="Disable camera (no crop images)")
    parser.add_argument("--camera-interval", type=int, default=5,
                        help="Capture image every N readings (default: 5)")
    args = parser.parse_args()

    print_banner()

    # Init sensor
    sensor = create_sensor(args.mode)
    executor = ActionExecutor(sensor)

    # Init Gemma brain (unless --no-gemma)
    brain = None
    if not args.no_gemma:
        try:
            brain = GemmaBrain(api_url=args.api_url)
            print(f"  Gemma brain: {args.api_url}")
        except Exception as e:
            log.warning(f"Gemma unavailable ({e}), using fallback rules")
            brain = None
    else:
        print("  Mode: Rule-based (no LLM)")

    # Init camera
    cam = None
    if not args.no_camera:
        cam = create_camera("stub" if args.mode == "stub" else "auto")
        print(f"  Camera: {'active' if cam else 'disabled'} (every {args.camera_interval} readings)")
    else:
        print("  Camera: disabled")

    print(f"  Sensors: {args.mode}")
    print(f"  Logging: {config.DATA_LOG_FILE}")

    interval = 5 if args.fast else config.DECISION_INTERVAL_SEC
    print(f"  Interval: {interval}s")
    print()

    # Init CSV
    init_csv(config.DATA_LOG_FILE)

    tick = 0
    try:
        while True:
            tick += 1

            # 1. Read sensors
            reading = sensor.read()

            # 2. Display
            print_reading(reading, tick)

            # 3. Log to CSV
            log_csv(config.DATA_LOG_FILE, reading)

            # 4. Capture image periodically
            image_b64 = None
            if cam and tick % args.camera_interval == 0:
                capture = cam.capture()
                if capture:
                    image_b64 = capture["image_b64"]
                    if capture.get("path"):
                        print(f"\n  📷 Captured: {capture['path']}")

            # 5. Ask Gemma (or fallback)
            prompt = reading.to_prompt_string()
            if brain:
                if image_b64:
                    print("\n  🧠 Gemma evaluating (with crop image)...")
                else:
                    print("\n  🧠 Gemma evaluating...")
                calls = brain.evaluate(prompt, image_b64=image_b64)
            else:
                calls = fallback_evaluate(reading)

            # 6. Execute actions
            executor.execute(calls, reading)

            if args.once:
                break

            # 7. Wait
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n  AquaSophia shutting down. Crops are on their own now.")
        if cam:
            cam.release()
        # Save action log
        if executor.action_log:
            with open("action_log.json", "w") as f:
                json.dump(executor.action_log, f, indent=2)
            print(f"  Action log saved: action_log.json ({len(executor.action_log)} actions)")
        print()


if __name__ == "__main__":
    main()
