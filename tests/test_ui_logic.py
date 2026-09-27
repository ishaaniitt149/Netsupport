"""Tests for NOIPMP UI Data Layer (Business Logic)."""

from datetime import timedelta
from unittest.mock import patch

import pandas as pd

from ui.data_layer import (
    compute_device_risk,
    compute_kpis,
    get_device_cves,
    get_device_incident_history,
    get_firmware_recommendation,
    get_next_best_action,
    get_similar_incidents,
)

# ---------------------------------------------------------------------------
# Mock Data Generators
# ---------------------------------------------------------------------------

def mock_devices():
    return pd.DataFrame([
        {"device_id": "D1", "model": "Catalyst 9300", "vendor": "Cisco", "firmware_version": "17.03.01", "firmware_age_days": 800},
        {"device_id": "D2", "model": "ISR 4451", "vendor": "Cisco", "firmware_version": "17.09.06", "firmware_age_days": 10},
        {"device_id": "D3", "model": "Unknown", "vendor": "Cisco", "firmware_version": "1.0.0", "firmware_age_days": 0},
    ])

def mock_incidents():
    now = pd.Timestamp.now(tz="UTC")
    return pd.DataFrame([
        # D1 has recurring incidents
        {"incident_id": "I1", "device_id": "D1", "start_time": now - timedelta(days=1), "alert_type": "PACKET_LOSS", "rca_label": "WAN degradation"},
        {"incident_id": "I2", "device_id": "D1", "start_time": now - timedelta(days=5), "alert_type": "PACKET_LOSS", "rca_label": "WAN degradation"},
        {"incident_id": "I3", "device_id": "D1", "start_time": now - timedelta(days=10), "alert_type": "PACKET_LOSS", "rca_label": "WAN degradation"},
        # D2 has one incident
        {"incident_id": "I4", "device_id": "D2", "start_time": now - timedelta(days=2), "alert_type": "NODE_DOWN", "rca_label": "Device unreachable"},
        # D3 has no incidents
    ])

def mock_telemetry():
    return pd.DataFrame([
        {"device_id": "D1", "date": pd.Timestamp.now() - timedelta(days=1), "packet_loss_pct": 8.0, "crc_errors": 250, "interface_flaps": 4},
        {"device_id": "D2", "date": pd.Timestamp.now() - timedelta(days=1), "packet_loss_pct": 0.0, "crc_errors": 0, "interface_flaps": 0},
    ])

def mock_resolutions():
    now = pd.Timestamp.now(tz="UTC")
    return pd.DataFrame([
        {"incident_id": "I1", "resolution_duration": 30.0, "acknowledged_at": now - timedelta(minutes=5), "diagnosed_at": now - timedelta(minutes=10), "first_time_resolution": True},
        {"incident_id": "I4", "resolution_duration": 60.0, "acknowledged_at": now - timedelta(minutes=15), "diagnosed_at": now - timedelta(minutes=20), "first_time_resolution": False},
    ])

def mock_cves():
    return pd.DataFrame([
        {"cve_id": "CVE-1", "vendor": "Cisco", "device_model": "Catalyst 9300", "affected_version": "17.03.01", "severity": "CRITICAL"},
        {"cve_id": "CVE-2", "vendor": "Cisco", "device_model": "Catalyst 9300", "affected_version": "17.03.01", "severity": "HIGH"},
    ])

def mock_firmware_recs():
    return pd.DataFrame([
        {"firmware_version": "17.03.01", "recommended_version": "17.09.06"}
    ])

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("ui.data_layer.load_incidents", mock_incidents)
@patch("ui.data_layer.load_telemetry", mock_telemetry)
@patch("ui.data_layer.get_device")
@patch("ui.data_layer.get_device_cves")
def test_device_risk_calculation(mock_get_cves, mock_get_device):
    # Device 1: High risk (recurring incidents, bad telemetry, old firmware, CVEs)
    mock_get_device.return_value = {"firmware_age_days": 800}
    mock_get_cves.return_value = [{"severity": "CRITICAL"}, {"severity": "HIGH"}]

    risk_d1 = compute_device_risk("D1")
    assert risk_d1["score"] > 70
    assert risk_d1["level"] in ["HIGH", "CRITICAL"]
    assert risk_d1["recurring_alert"] == "PACKET_LOSS"
    assert risk_d1["incident_count_30d"] == 3
    assert risk_d1["critical_cves"] == 1

    # Device 2: Low risk (one incident, clean telemetry, no CVEs, new firmware)
    mock_get_device.return_value = {"firmware_age_days": 10}
    mock_get_cves.return_value = []

    risk_d2 = compute_device_risk("D2")
    assert risk_d2["score"] < 40
    assert risk_d2["level"] == "LOW"
    assert risk_d2["incident_count_30d"] == 1
    assert risk_d2["recurring_alert"] is None

    # Device 3: No incidents, no telemetry
    risk_d3 = compute_device_risk("D3")
    assert risk_d3["score"] < 20
    assert risk_d3["incident_count_30d"] == 0

@patch("ui.data_layer.load_incidents", mock_incidents)
def test_30_day_incident_history():
    history_d1 = get_device_incident_history("D1", days=30)
    assert len(history_d1) == 3

    history_d2 = get_device_incident_history("D2", days=30)
    assert len(history_d2) == 1

    history_d3 = get_device_incident_history("D3", days=30)
    assert len(history_d3) == 0

@patch("ui.data_layer.load_incidents", mock_incidents)
@patch("ui.data_layer.load_resolutions", mock_resolutions)
@patch("ui.data_layer.load_kb_articles")
def test_kpi_calculations(mock_kb):
    mock_kb.return_value = []
    kpis = compute_kpis()

    # 4 incidents total, 2 resolved
    assert kpis["total_incidents"] == 4
    assert kpis["resolved_incidents"] == 2

    # MTTR is avg of [30, 60]
    assert kpis["mttr_min"] == 45.0

    # First-time resolution avg [True, False] -> 50%
    assert kpis["ftr_rate_pct"] == 50.0

    # D1 has 3 PACKET_LOSS incidents -> 1 repeat pair
    assert kpis["repeat_incident_device_pairs"] == 1

@patch("ui.data_layer.load_incidents", mock_incidents)
def test_historical_similarity():
    sim = get_similar_incidents(
        incident_id="I1",
        alert_type="PACKET_LOSS",
        device_id="D1",
        rca_label="WAN degradation"
    )
    # I1 should be excluded, I2 and I3 should match
    assert len(sim) == 2
    assert "I1" not in sim["incident_id"].values
    assert "I2" in sim["incident_id"].values

    # No match scenario
    sim_none = get_similar_incidents("I99", "UNKNOWN", "D99", "UNKNOWN")
    assert sim_none.empty

@patch("ui.data_layer.get_device")
@patch("ui.data_layer.load_cve_dataset", mock_cves)
def test_cve_matching(mock_get_device):
    # Match Catalyst 9300 / 17.03.01
    mock_get_device.return_value = {"vendor": "Cisco", "model": "Catalyst 9300", "firmware_version": "17.03.01"}
    cves = get_device_cves("D1")
    assert len(cves) == 2

    # No match (different version)
    mock_get_device.return_value = {"vendor": "Cisco", "model": "Catalyst 9300", "firmware_version": "17.09.06"}
    cves_empty = get_device_cves("D2")
    assert len(cves_empty) == 0

    # No match (different model)
    mock_get_device.return_value = {"vendor": "Cisco", "model": "ISR 4451", "firmware_version": "17.03.01"}
    cves_empty_model = get_device_cves("D2")
    assert len(cves_empty_model) == 0

@patch("ui.data_layer.load_firmware_recommendations", mock_firmware_recs)
def test_firmware_recommendations():
    rec = get_firmware_recommendation("17.03.01")
    assert rec == "17.09.06"

    # Already latest (not in mapping, or maps to itself)
    rec_none = get_firmware_recommendation("17.09.06")
    assert rec_none is None

def test_next_best_action():
    cmds = get_next_best_action("Interface degradation")
    assert "show interfaces transceiver" in cmds

    cmds_default = get_next_best_action("Unknown Issue")
    assert "show logging" in cmds_default

@patch("ui.data_layer.load_incidents", return_value=pd.DataFrame())
@patch("ui.data_layer.load_resolutions", return_value=pd.DataFrame())
def test_empty_data_handling(mock_res, mock_inc):
    kpis = compute_kpis()
    assert kpis == {}

    hist = get_device_incident_history("D1")
    assert hist.empty

    sim = get_similar_incidents("I1", "ALERT", "D1", "RCA")
    assert sim.empty
