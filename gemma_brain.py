"""
AquaSophia — Gemma 4 Decision Engine with Function Calling
Sends sensor readings to Gemma, gets back structured SCADA decisions.
Compatible with any OpenAI-compatible API (llama.cpp, Ollama, vLLM, etc).
"""

import json
import time
import logging
from typing import Optional

import config

log = logging.getLogger("aqua.brain")

# ---------------------------------------------------------------------------
# Tool definitions — these are the "SCADA functions" Gemma can call
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_pump",
            "description": "Turn the main circulation pump on or off. Use when flow needs to start, stop, or when emergency shutdown is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "boolean",
                        "description": "true = pump ON, false = pump OFF"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this action is being taken"
                    }
                },
                "required": ["state", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "alert_farmer",
            "description": "Send an alert to the farmer. Use for conditions that need human attention — refills, maintenance, crop issues spotted by camera.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Clear, actionable message for the farmer"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["info", "warning", "critical"],
                        "description": "info=FYI, warning=act soon, critical=act now"
                    }
                },
                "required": ["message", "severity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_flow_target",
            "description": "Adjust the target flow rate for the NFT channels. Use when conditions suggest more or less flow is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_lpm": {
                        "type": "number",
                        "description": "New target flow rate in liters per minute"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why flow rate is being adjusted"
                    }
                },
                "required": ["target_lpm", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_observation",
            "description": "Log an observation or trend for the farmer's records. Use for noting patterns, predictions, or non-urgent findings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "observation": {
                        "type": "string",
                        "description": "What was observed or predicted"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["trend", "anomaly", "maintenance", "growth", "water_usage"],
                        "description": "Category of observation"
                    }
                },
                "required": ["observation", "category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_image",
            "description": "Request a fresh camera image of the crops. Use when sensor readings suggest stress but you want visual confirmation before acting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why visual confirmation is needed"
                    }
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "no_action",
            "description": "System is nominal — no action needed. Always call this when everything looks good.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status_summary": {
                        "type": "string",
                        "description": "Brief summary of why no action is needed"
                    }
                },
                "required": ["status_summary"]
            }
        }
    },
]

SYSTEM_PROMPT = """\
You are AquaSophia, an intelligent SCADA controller for a 108-cell NFT hydroponic system \
with two aerated 5-gallon reservoir buckets. You monitor sensor readings and make \
real-time decisions to protect the crops and conserve water.

Your priorities (in order):
1. PROTECT THE CROP — never let roots dry out or drown
2. PROTECT THE EQUIPMENT — don't let pumps run dry
3. CONSERVE WATER — minimize waste while keeping plants healthy
4. INFORM THE FARMER — explain what's happening in plain language

Decision rules:
- Flow rate below {flow_min} L/min with pump running = possible clog → alert critical
- pH outside {ph_min}-{ph_max} range = nutrient lockout risk → alert warning
- Water temp above {temp_max}F = root rot risk → alert warning, consider pump cycling
- Water temp above {temp_crit}F = emergency → alert critical, cycle pump for cooling
- Reservoir below {res_low} gal = refill needed → alert warning
- Reservoir below {res_crit} gal = pump will run dry → shut pump OFF, alert critical
- If everything is normal, call no_action with a brief status

You MUST call at least one function. Analyze the readings and act.\
""".format(
    flow_min=config.FLOW_RATE_MIN_LPM,
    ph_min=config.PH_MIN,
    ph_max=config.PH_MAX,
    temp_max=config.WATER_TEMP_MAX_F,
    temp_crit=config.WATER_TEMP_CRITICAL_F,
    res_low=config.RESERVOIR_LOW_GAL,
    res_crit=config.RESERVOIR_CRITICAL_GAL,
)


# ---------------------------------------------------------------------------
# Gemma API client
# ---------------------------------------------------------------------------

class GemmaBrain:
    """Sends sensor data to Gemma 4 and parses function call responses."""

    def __init__(self, api_url: str = None, model: str = None):
        self.api_url = (api_url or config.GEMMA_API_URL).rstrip("/")
        self.model = model or config.GEMMA_MODEL_NAME
        self.history = []  # Rolling context of recent decisions
        try:
            import requests
            self._requests = requests
        except ImportError:
            raise ImportError("pip install requests")

    def evaluate(self, sensor_prompt: str, image_b64: str = None) -> list[dict]:
        """
        Send sensor readings (and optionally a crop image) to Gemma.
        Returns: [{"name": "set_pump", "arguments": {"state": false, "reason": "..."}}]
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Include last 3 decisions for continuity
        for h in self.history[-3:]:
            messages.append({"role": "user", "content": h["reading"]})
            messages.append({"role": "assistant", "content": h["response"]})

        # Build user message — text only or multimodal (text + image)
        if image_b64:
            user_content = [
                {"type": "text", "text": sensor_prompt + "\n\nAttached: current crop image. Check for wilting, yellowing, algae, root discoloration, or other visual issues."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ]
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": sensor_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "required",
            "temperature": config.GEMMA_TEMPERATURE,
            "max_tokens": config.GEMMA_MAX_TOKENS,
        }

        try:
            resp = self._requests.post(
                f"{self.api_url}/chat/completions",
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.error(f"Gemma API error: {e}")
            return [{"name": "alert_farmer", "arguments": {
                "message": f"SCADA brain offline: {e}. Manual monitoring required.",
                "severity": "critical"
            }}]

        # Parse function calls from response
        calls = []
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {"raw": fn.get("arguments", "")}
                calls.append({"name": name, "arguments": args})
        else:
            # Fallback: if model returned text instead of tool calls
            content = message.get("content", "")
            if content:
                calls.append({"name": "log_observation", "arguments": {
                    "observation": content,
                    "category": "anomaly"
                }})

        # Save to history
        self.history.append({
            "reading": sensor_prompt,
            "response": json.dumps(calls),
            "timestamp": time.time(),
        })

        # Trim history
        if len(self.history) > 20:
            self.history = self.history[-10:]

        return calls


# ---------------------------------------------------------------------------
# Offline fallback — rule-based decisions when Gemma is unavailable
# ---------------------------------------------------------------------------

def fallback_evaluate(reading) -> list[dict]:
    """
    Pure rule-based SCADA logic. No LLM needed.
    This is the safety net — if Gemma is down, the system still protects crops.
    """
    calls = []

    # Critical: reservoir empty
    if reading.reservoir_1_gal < config.RESERVOIR_CRITICAL_GAL:
        calls.append({"name": "set_pump", "arguments": {
            "state": False, "reason": "Reservoir 1 critically low — pump would run dry"
        }})
        calls.append({"name": "alert_farmer", "arguments": {
            "message": f"CRITICAL: Reservoir 1 at {reading.reservoir_1_gal:.1f} gal. "
                       f"Pump shut off. Refill immediately.",
            "severity": "critical"
        }})
        return calls

    # Critical: flow stopped with pump on
    if reading.pump_running and reading.flow_rate_lpm < config.FLOW_RATE_MIN_LPM:
        calls.append({"name": "alert_farmer", "arguments": {
            "message": f"Flow rate {reading.flow_rate_lpm:.1f} L/min with pump ON. "
                       f"Possible clog or pump failure. Check NFT inlet.",
            "severity": "critical"
        }})
        return calls

    # Warning: temperature
    if reading.water_temp_f > config.WATER_TEMP_CRITICAL_F:
        calls.append({"name": "alert_farmer", "arguments": {
            "message": f"Water temp {reading.water_temp_f:.0f}F — root rot danger. "
                       f"Add ice or shade the reservoir.",
            "severity": "critical"
        }})
    elif reading.water_temp_f > config.WATER_TEMP_MAX_F:
        calls.append({"name": "alert_farmer", "arguments": {
            "message": f"Water temp {reading.water_temp_f:.0f}F creeping high. "
                       f"Monitor closely.",
            "severity": "warning"
        }})

    # Warning: pH drift
    if reading.ph < config.PH_MIN or reading.ph > config.PH_MAX:
        calls.append({"name": "alert_farmer", "arguments": {
            "message": f"pH at {reading.ph:.1f} — outside {config.PH_MIN}-{config.PH_MAX} range. "
                       f"Adjust nutrients.",
            "severity": "warning"
        }})

    # Warning: reservoir low
    if reading.reservoir_1_gal < config.RESERVOIR_LOW_GAL:
        calls.append({"name": "alert_farmer", "arguments": {
            "message": f"Reservoir 1 at {reading.reservoir_1_gal:.1f} gal. Refill soon.",
            "severity": "warning"
        }})

    if not calls:
        calls.append({"name": "no_action", "arguments": {
            "status_summary": f"All nominal. Flow {reading.flow_rate_lpm:.1f} L/min, "
                              f"pH {reading.ph:.1f}, temp {reading.water_temp_f:.0f}F."
        }})

    return calls
