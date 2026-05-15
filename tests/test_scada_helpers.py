from datetime import datetime

import analyst
import config
from gemma_brain import fallback_evaluate
from sensors import SensorReading


def make_reading(**overrides):
    values = {
        "timestamp": 1_789_000_000.0,
        "flow_rate_lpm": config.FLOW_RATE_NOMINAL_LPM,
        "ph": config.PH_TARGET,
        "ec_ms": config.EC_TARGET_MS,
        "water_temp_f": 70.0,
        "reservoir_1_gal": 4.0,
        "reservoir_2_gal": 4.0,
        "pump_running": True,
        "ambient_temp_f": 78.0,
        "humidity_pct": 65.0,
    }
    values.update(overrides)
    return SensorReading(**values)


def test_sensor_reading_formats_prompt_and_dict():
    reading = make_reading(
        flow_rate_lpm=2.345,
        ph=5.95,
        ec_ms=1.456,
        pump_running=False,
        humidity_pct=64.6,
    )

    prompt = reading.to_prompt_string()

    assert "Flow Rate: 2.35 L/min" in prompt
    assert "pH: 6.0" in prompt
    assert "EC: 1.46 mS/cm" in prompt
    assert "Pump: OFF" in prompt
    assert "Humidity: 65%" in prompt
    assert reading.to_dict()["reservoir_1_gal"] == 4.0


def test_fallback_evaluate_shuts_off_pump_when_reservoir_is_critical():
    calls = fallback_evaluate(
        make_reading(reservoir_1_gal=config.RESERVOIR_CRITICAL_GAL - 0.1)
    )

    assert calls == [
        {
            "name": "set_pump",
            "arguments": {
                "state": False,
                "reason": "Reservoir 1 critically low \u2014 pump would run dry",
            },
        },
        {
            "name": "alert_farmer",
            "arguments": {
                "message": "CRITICAL: Reservoir 1 at 0.4 gal. Pump shut off. Refill immediately.",
                "severity": "critical",
            },
        },
    ]


def test_fallback_evaluate_reports_clog_before_secondary_warnings():
    calls = fallback_evaluate(
        make_reading(
            flow_rate_lpm=config.FLOW_RATE_MIN_LPM - 0.2,
            water_temp_f=config.WATER_TEMP_CRITICAL_F + 5,
            ph=config.PH_MAX + 0.4,
            pump_running=True,
        )
    )

    assert len(calls) == 1
    assert calls[0]["name"] == "alert_farmer"
    assert calls[0]["arguments"]["severity"] == "critical"
    assert "Possible clog or pump failure" in calls[0]["arguments"]["message"]


def test_fallback_evaluate_combines_non_critical_warnings():
    calls = fallback_evaluate(
        make_reading(
            water_temp_f=config.WATER_TEMP_MAX_F + 1,
            ph=config.PH_MIN - 0.3,
            reservoir_1_gal=config.RESERVOIR_LOW_GAL - 0.2,
        )
    )

    assert [call["name"] for call in calls] == [
        "alert_farmer",
        "alert_farmer",
        "alert_farmer",
    ]
    severities = [call["arguments"]["severity"] for call in calls]
    assert severities == ["warning", "warning", "warning"]
    assert "Water temp" in calls[0]["arguments"]["message"]
    assert "pH at" in calls[1]["arguments"]["message"]
    assert "Refill soon" in calls[2]["arguments"]["message"]


def test_fallback_evaluate_returns_no_action_for_nominal_reading():
    calls = fallback_evaluate(make_reading())

    assert calls == [
        {
            "name": "no_action",
            "arguments": {
                "status_summary": "All nominal. Flow 3.5 L/min, pH 6.0, temp 70F.",
            },
        }
    ]


def test_load_recent_csv_handles_missing_file(tmp_path):
    missing_path = tmp_path / "missing.csv"

    assert analyst.load_recent_csv(str(missing_path)) == "No sensor data available yet."


def test_load_recent_csv_filters_old_and_bad_rows(tmp_path, monkeypatch):
    fixed_now = datetime(2026, 5, 11, 1, 0, 0).timestamp()
    monkeypatch.setattr(analyst.time, "time", lambda: fixed_now)

    csv_path = tmp_path / "sensor_data.csv"
    csv_path.write_text(
        "\n".join(
            [
                "timestamp,flow_lpm,ph,ec_ms,water_temp_f,res1_gal,res2_gal,"
                "pump,ambient_f,humidity_pct",
                "2026-05-11T00:45:00,3.50,6.0,1.50,70.0,4.0,4.1,1,78.0,65.0",
                "2026-05-10T20:00:00,9.90,9.0,4.00,90.0,0.1,0.1,0,99.0,99.0",
                "not-a-timestamp,2.00,5.5,1.00,65.0,3.0,3.1,1,72.0,60.0",
            ]
        )
        + "\n"
    )

    result = analyst.load_recent_csv(str(csv_path), hours=1)

    assert "Last 1.0 hours (1 readings)" in result
    assert "00:45:00" in result
    assert "20:00:00" not in result
    assert "not-a-timestamp" not in result
    assert "Flow:  min=3.50  max=3.50  avg=3.50 L/min" in result
