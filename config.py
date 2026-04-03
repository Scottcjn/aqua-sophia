"""
Aqua Elya — NFT Hydroponic SCADA Configuration
Threshold values for 108-cell NFT system with 2x aerated 5-gal buckets.
"""

# --- Sensor Polling ---
POLL_INTERVAL_SEC = 30          # How often to read sensors
DECISION_INTERVAL_SEC = 60      # How often Gemma evaluates

# --- Sensor Source ---
# "stub" = simulated data for testing
# "esp32" = real ESP32 over WiFi
# "serial" = USB serial (Arduino/Nano)
SENSOR_MODE = "stub"
ESP32_URL = "http://192.168.0.200"  # Change to your ESP32 IP
SERIAL_PORT = "/dev/ttyUSB0"
SERIAL_BAUD = 115200

# --- NFT Flow Thresholds ---
FLOW_RATE_MIN_LPM = 1.0        # Minimum L/min — below = clog or pump fail
FLOW_RATE_MAX_LPM = 8.0        # Maximum — above = sensor error or burst
FLOW_RATE_NOMINAL_LPM = 3.5    # Target flow for 108-cell NFT

# --- pH Thresholds (hydroponic) ---
PH_MIN = 5.5                   # Below = too acidic, nutrient lockout
PH_MAX = 6.5                   # Above = iron/manganese lockout
PH_TARGET = 6.0                # Sweet spot for most crops

# --- EC / TDS (nutrient concentration) ---
EC_MIN_MS = 0.8                # Below = underfeeding
EC_MAX_MS = 2.5                # Above = salt burn risk
EC_TARGET_MS = 1.5             # Target for leafy greens

# --- Water Temperature (F) ---
WATER_TEMP_MIN_F = 60          # Below = slow uptake
WATER_TEMP_MAX_F = 74          # Above = root rot / pythium risk
WATER_TEMP_CRITICAL_F = 80     # Emergency — roots dying

# --- Reservoir Levels (gallons) ---
RESERVOIR_CAPACITY_GAL = 5.0
RESERVOIR_LOW_GAL = 1.5        # Alert: refill soon
RESERVOIR_CRITICAL_GAL = 0.5   # Emergency: pump runs dry

# --- Pump ---
PUMP_MAX_CONTINUOUS_MIN = 120  # Max continuous run before forced rest
PUMP_REST_MIN = 10             # Forced rest period

# --- Gemma Model ---
GEMMA_MODEL_PATH = ""          # Path to local GGUF, or empty for API
GEMMA_API_URL = "http://localhost:11434/v1"  # Ollama API (OpenAI-compatible)
GEMMA_MODEL_NAME = "gemma4:e4b"  # Gemma 4 Effective 4B — fits RTX 4070 8GB
GEMMA_TEMPERATURE = 0.3        # Low temp for reliable decisions
GEMMA_MAX_TOKENS = 256         # Keep responses focused

# --- Logging ---
LOG_FILE = "aqua_elya.log"
LOG_LEVEL = "INFO"
DATA_LOG_FILE = "sensor_data.csv"  # CSV for graphing/analysis
