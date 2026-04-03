"""
Aqua Elya — Deep Analyst Brain (Gemma 4 26B MoE)
Runs periodically on accumulated sensor data to find trends,
predict issues, and provide farming recommendations.

The E4B handles fast SCADA decisions (every 30-60s).
The 26B handles deep analysis (every 10-30 minutes).
"""

import csv
import json
import logging
import os
import time
from datetime import datetime, timedelta

import config

log = logging.getLogger("aqua.analyst")

ANALYST_MODEL = "gemma4:26b"  # 26B MoE — runs on CPU, smarter analysis
ANALYST_API_URL = config.GEMMA_API_URL  # Same Ollama instance

ANALYSIS_PROMPT = """\
You are Aqua Elya's deep analyst — an expert hydroponic agronomist reviewing \
sensor data from a 108-cell NFT system with two aerated 5-gallon reservoirs.

You receive a CSV log of recent sensor readings. Analyze for:

1. TRENDS — Is anything drifting toward a problem? pH creeping up? Flow declining?
2. CORRELATIONS — Does temperature rise correlate with pH drift? Flow with reservoir level?
3. PREDICTIONS — Based on current trends, when will something need attention?
4. RECOMMENDATIONS — What should the farmer do in the next few hours?
5. WATER USAGE — How much water has been consumed? Efficiency analysis.

Be specific. Reference actual numbers from the data. Think like a SCADA operator \
reviewing a shift's worth of trend charts.
"""

ANALYST_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analysis_report",
            "description": "Submit a detailed analysis report of sensor trends and recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trends": {
                        "type": "string",
                        "description": "Key trends observed in the data"
                    },
                    "predictions": {
                        "type": "string",
                        "description": "Predicted issues and when they'll occur"
                    },
                    "recommendations": {
                        "type": "string",
                        "description": "Specific actions for the farmer"
                    },
                    "water_efficiency": {
                        "type": "string",
                        "description": "Water consumption analysis"
                    },
                    "overall_health": {
                        "type": "string",
                        "enum": ["excellent", "good", "fair", "poor", "critical"],
                        "description": "Overall system health assessment"
                    }
                },
                "required": ["trends", "predictions", "recommendations", "overall_health"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "urgent_alert",
            "description": "Issue an urgent alert if the analysis reveals a serious emerging problem not caught by the fast SCADA loop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue": {
                        "type": "string",
                        "description": "What the emerging problem is"
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "How soon it will become critical"
                    },
                    "action": {
                        "type": "string",
                        "description": "What to do about it"
                    }
                },
                "required": ["issue", "timeframe", "action"]
            }
        }
    },
]


def load_recent_csv(path: str, hours: float = 1.0) -> str:
    """Load recent CSV data as a formatted string for the analyst."""
    if not os.path.exists(path):
        return "No sensor data available yet."

    rows = []
    cutoff = time.time() - (hours * 3600)

    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = datetime.fromisoformat(row["timestamp"]).timestamp()
                if ts >= cutoff:
                    rows.append(row)
            except (ValueError, KeyError):
                continue

    if not rows:
        return "No recent sensor data in the specified timeframe."

    # Format as readable table
    lines = [f"SENSOR LOG — Last {hours:.1f} hours ({len(rows)} readings):"]
    lines.append(f"{'Time':<20} {'Flow':>6} {'pH':>5} {'EC':>6} {'Temp':>5} {'Res1':>5} {'Res2':>5} {'Pump':>4}")
    lines.append("-" * 75)

    for row in rows[-50:]:  # Last 50 readings max
        ts = row.get("timestamp", "?")
        if "T" in ts:
            ts = ts.split("T")[1][:8]
        lines.append(
            f"{ts:<20} "
            f"{row.get('flow_lpm', '?'):>6} "
            f"{row.get('ph', '?'):>5} "
            f"{row.get('ec_ms', '?'):>6} "
            f"{row.get('water_temp_f', '?'):>5} "
            f"{row.get('res1_gal', '?'):>5} "
            f"{row.get('res2_gal', '?'):>5} "
            f"{row.get('pump', '?'):>4}"
        )

    # Add summary stats
    try:
        flows = [float(r["flow_lpm"]) for r in rows if r.get("flow_lpm")]
        phs = [float(r["ph"]) for r in rows if r.get("ph")]
        temps = [float(r["water_temp_f"]) for r in rows if r.get("water_temp_f")]

        lines.append("")
        lines.append("SUMMARY:")
        if flows:
            lines.append(f"  Flow:  min={min(flows):.2f}  max={max(flows):.2f}  avg={sum(flows)/len(flows):.2f} L/min")
        if phs:
            lines.append(f"  pH:    min={min(phs):.2f}  max={max(phs):.2f}  avg={sum(phs)/len(phs):.2f}")
        if temps:
            lines.append(f"  Temp:  min={min(temps):.1f}  max={max(temps):.1f}  avg={sum(temps)/len(temps):.1f}F")
    except (ValueError, ZeroDivisionError):
        pass

    return "\n".join(lines)


class DeepAnalyst:
    """Gemma 4 26B MoE analyst for long-term trend analysis."""

    def __init__(self):
        try:
            import requests
            self._requests = requests
        except ImportError:
            raise ImportError("pip install requests")

    def analyze(self, csv_path: str = None, hours: float = 1.0) -> dict:
        """
        Run deep analysis on recent sensor data.
        Returns the analysis report dict or None on failure.
        """
        csv_path = csv_path or config.DATA_LOG_FILE
        data_str = load_recent_csv(csv_path, hours)

        log.info(f"Running deep analysis on {hours:.1f}h of data...")

        payload = {
            "model": ANALYST_MODEL,
            "messages": [
                {"role": "system", "content": ANALYSIS_PROMPT},
                {"role": "user", "content": data_str},
            ],
            "tools": ANALYST_TOOLS,
            "tool_choice": "required",
            "temperature": 0.4,
            "max_tokens": 4096,  # 26B uses ~2K reasoning tokens before tool call
        }

        try:
            resp = self._requests.post(
                f"{ANALYST_API_URL}/chat/completions",
                json=payload,
                timeout=300,  # 26B on CPU can take up to 5 minutes
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.error(f"Analyst error: {e}")
            return None

        # Parse tool calls
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        log.info(f"Analyst raw response keys: {list(message.keys())}")
        log.info(f"Analyst content preview: {str(message.get('content', ''))[:200]}")
        log.info(f"Analyst tool_calls: {message.get('tool_calls', 'NONE')}")
        log.info(f"Analyst finish_reason: {choice.get('finish_reason', '?')}")
        tool_calls = message.get("tool_calls", [])

        report = None
        alerts = []

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                continue

            if name == "analysis_report":
                report = args
            elif name == "urgent_alert":
                alerts.append(args)

        # If no tool calls but there's text content, parse it as a text report
        if not report and not alerts:
            content = message.get("content", "")
            if content:
                report = {
                    "trends": content[:500],
                    "predictions": "See full text above",
                    "recommendations": "See full text above",
                    "overall_health": "good",
                }
                log.info("Analyst returned text instead of tool calls — wrapped as report")

        return {
            "report": report,
            "alerts": alerts,
            "timestamp": time.time(),
            "data_hours": hours,
            "model": ANALYST_MODEL,
        }


def print_analysis(result: dict):
    """Pretty-print analysis results."""
    if not result:
        print("\n  ❌ Analysis failed — no result")
        return

    print(f"\n{'═' * 60}")
    print(f"  🔬 DEEP ANALYSIS — Gemma 4 26B MoE")
    print(f"  {datetime.fromtimestamp(result['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Analyzed: {result['data_hours']:.1f} hours of sensor data")
    print(f"{'═' * 60}")

    report = result.get("report")
    if report:
        health = report.get("overall_health", "unknown")
        health_icons = {
            "excellent": "🟢", "good": "🟢", "fair": "🟡",
            "poor": "🟠", "critical": "🔴"
        }
        print(f"\n  {health_icons.get(health, '⚪')} Overall Health: {health.upper()}")
        print(f"\n  📊 Trends:")
        print(f"     {report.get('trends', 'N/A')}")
        print(f"\n  🔮 Predictions:")
        print(f"     {report.get('predictions', 'N/A')}")
        print(f"\n  💡 Recommendations:")
        print(f"     {report.get('recommendations', 'N/A')}")
        if report.get("water_efficiency"):
            print(f"\n  💧 Water Efficiency:")
            print(f"     {report['water_efficiency']}")

    for alert in result.get("alerts", []):
        print(f"\n  🚨 URGENT: {alert.get('issue', '?')}")
        print(f"     Timeframe: {alert.get('timeframe', '?')}")
        print(f"     Action: {alert.get('action', '?')}")

    print(f"\n{'═' * 60}")


# CLI entry point
if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    parser = argparse.ArgumentParser(description="Aqua Elya Deep Analyst")
    parser.add_argument("--hours", type=float, default=1.0, help="Hours of data to analyze")
    parser.add_argument("--csv", default=config.DATA_LOG_FILE, help="Path to sensor CSV")
    args = parser.parse_args()

    print("\n  🔬 Starting deep analysis with Gemma 4 26B MoE...")
    print("  (This runs on CPU — may take 1-3 minutes)\n")

    analyst = DeepAnalyst()
    result = analyst.analyze(csv_path=args.csv, hours=args.hours)
    print_analysis(result)

    # Save report
    if result:
        with open("analysis_report.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n  Report saved: analysis_report.json")
