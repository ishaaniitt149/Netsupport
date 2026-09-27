"""NOIPMP UI Data Layer.

Single source of truth for all UI data access.
All functions are cached to prevent reloading on every Streamlit interaction.
Business logic is here — NOT inside widget callbacks.

Data Sources:
- data/processed/incidents.parquet
- data/processed/telemetry.parquet
- data/processed/resolutions.parquet
- data/processed/kb_articles.json
- data/synthetic/devices.csv
- data/synthetic/cve_dataset.csv
- data/synthetic/firmware_recommendations.csv
"""

from __future__ import annotations

import json
import pathlib

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so `app.*` packages are importable.
# On Streamlit Cloud the working directory may differ from the project root,
# which causes `import app.models.kb_article` to fail.
# ---------------------------------------------------------------------------
import sys as _sys

_PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)

import app.models.kb_article  # noqa: E402
from app.knowledge.kb_store import KBStore  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent
DATA = ROOT / "data" / "synthetic"
PROC = ROOT / "data" / "processed"
KB_STORE_DIR = ROOT / "data" / "knowledge"
kb_store = KBStore(KB_STORE_DIR)

# ---------------------------------------------------------------------------
# Raw loaders — cached indefinitely (reload only on app restart)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_devices() -> pd.DataFrame:
    path = DATA / "devices.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Compute firmware age in days
    if "last_patch_date" in df.columns:
        df["last_patch_date"] = pd.to_datetime(df["last_patch_date"], errors="coerce")
        today = pd.Timestamp.now().normalize()
        df["firmware_age_days"] = (today - df["last_patch_date"]).dt.days
    return df


@st.cache_data(ttl=3600)
def load_incidents() -> pd.DataFrame:
    path = PROC / "incidents.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    for col in ["start_time", "recovery_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


@st.cache_data(ttl=3600)
def load_telemetry() -> pd.DataFrame:
    path = PROC / "telemetry.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@st.cache_data(ttl=3600)
def load_resolutions() -> pd.DataFrame:
    path = PROC / "resolutions.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    for col in ["resolution_timestamp", "acknowledged_at", "diagnosed_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


@st.cache_data(ttl=3600)
def load_kb_articles() -> list[dict]:
    path = PROC / "kb_articles.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def load_cve_dataset() -> pd.DataFrame:
    path = DATA / "cve_dataset.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=3600)
def load_firmware_recommendations() -> pd.DataFrame:
    path = DATA / "firmware_recommendations.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Business logic layer
# ---------------------------------------------------------------------------

def get_device(device_id: str) -> dict | None:
    """Return device record as dict, or None if not found."""
    df = load_devices()
    if df.empty:
        return None
    row = df[df["device_id"] == device_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def get_device_by_hostname(hostname: str) -> dict | None:
    df = load_devices()
    if df.empty:
        return None
    row = df[df["hostname"].str.contains(hostname, case=False, na=False)]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def get_incident(incident_id: str) -> dict | None:
    """Return a single incident by ID."""
    df = load_incidents()
    if df.empty:
        return None
    row = df[df["incident_id"] == incident_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def get_device_incidents_30d(device_id: str) -> pd.DataFrame:
    """All incidents for a device in the last 30 calendar days."""
    df = load_incidents()
    if df.empty:
        return pd.DataFrame()
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=30)
    mask = (df["device_id"] == device_id) & (df["start_time"] >= cutoff)
    return df[mask].sort_values("start_time", ascending=False).reset_index(drop=True)


def get_device_incident_history(device_id: str, days: int = 90) -> pd.DataFrame:
    """All incidents for a device in the last N days."""
    df = load_incidents()
    if df.empty:
        return pd.DataFrame()
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    mask = (df["device_id"] == device_id) & (df["start_time"] >= cutoff)
    return df[mask].sort_values("start_time", ascending=False).reset_index(drop=True)


def get_device_telemetry_30d(device_id: str) -> pd.DataFrame:
    """30-day daily telemetry for a device."""
    df = load_telemetry()
    if df.empty:
        return pd.DataFrame()
    return df[df["device_id"] == device_id].sort_values("date").reset_index(drop=True)


def compute_device_status(device_id: str) -> tuple[str, str]:
    """
    Returns (status, detail) based on most recent incident and telemetry.
    status: 'UP', 'DOWN', 'DEGRADED', 'UNKNOWN'
    """
    incidents = load_incidents()
    if incidents.empty:
        return "UNKNOWN", "No data available"

    dev_incidents = incidents[incidents["device_id"] == device_id].copy()
    if dev_incidents.empty:
        return "UP", "No incidents in history"

    latest = dev_incidents.sort_values("start_time").iloc[-1]
    last_recovery = latest.get("recovery_time")
    last_start = latest.get("start_time")

    now = pd.Timestamp.now(tz="UTC")
    if pd.isnull(last_recovery):
        return "DOWN", f"Active incident since {last_start}"

    minutes_since_recovery = (now - last_recovery).total_seconds() / 60
    if minutes_since_recovery < 60:
        return "DEGRADED", f"Recovered {int(minutes_since_recovery)} min ago"

    return "UP", f"Last incident: {last_recovery.strftime('%d %b %H:%M')} UTC"


def compute_device_risk(device_id: str) -> dict:
    """
    Evidence-based risk score from real data:
    - Incident frequency (30d)
    - Telemetry trend (packet loss, CRC)
    - CVE exposure
    - Firmware age
    """
    incidents_30d = get_device_incidents_30d(device_id)
    telemetry = get_device_telemetry_30d(device_id)
    device = get_device(device_id)
    cves = get_device_cves(device_id)

    score = 0.0
    factors = []

    # Incident frequency (30d) — up to 40 points
    n_inc = len(incidents_30d)
    inc_score = min(40.0, n_inc * 8.0)
    score += inc_score
    if n_inc > 0:
        factors.append(f"{n_inc} incident(s) in last 30 days")

    # Telemetry signals — up to 35 points
    if not telemetry.empty:
        last_7 = telemetry.tail(7)
        avg_pkt_loss = last_7["packet_loss_pct"].mean() if "packet_loss_pct" in last_7.columns else 0
        avg_crc = last_7["crc_errors"].mean() if "crc_errors" in last_7.columns else 0
        avg_flaps = last_7["interface_flaps"].mean() if "interface_flaps" in last_7.columns else 0

        if avg_pkt_loss > 5:
            score += 15
            factors.append(f"Packet loss avg {avg_pkt_loss:.1f}% (7d)")
        elif avg_pkt_loss > 1:
            score += 8
            factors.append(f"Packet loss avg {avg_pkt_loss:.1f}% (7d)")

        if avg_crc > 200:
            score += 15
            factors.append(f"CRC errors avg {avg_crc:.0f}/day (7d)")
        elif avg_crc > 50:
            score += 7
            factors.append(f"CRC errors avg {avg_crc:.0f}/day (7d)")

        if avg_flaps > 3:
            score += 5
        factors.append(f"Interface flaps avg {avg_flaps:.1f}/day (7d)")

    # CVE exposure — up to 15 points
    critical_cves = sum(1 for c in cves if c.get("severity") == "CRITICAL")
    high_cves = sum(1 for c in cves if c.get("severity") == "HIGH")
    cve_score = min(15.0, critical_cves * 5.0 + high_cves * 2.0)
    score += cve_score
    if critical_cves > 0:
        factors.append(f"{critical_cves} critical CVE(s) unpatched")
    if high_cves > 0:
        factors.append(f"{high_cves} high CVE(s) unpatched")

    # Firmware age — up to 10 points
    fw_age = device.get("firmware_age_days", 0) if device else 0
    if fw_age and fw_age > 365:
        score += 10
        factors.append(f"Firmware age {fw_age} days (>1 year)")
    elif fw_age and fw_age > 180:
        score += 5
        factors.append(f"Firmware age {fw_age} days (>6 months)")

    score = min(100.0, round(score, 1))

    if score >= 85:
        level = "CRITICAL"
    elif score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"

    # Identify recurring issue
    recurring_alert = None
    if not incidents_30d.empty and "alert_type" in incidents_30d.columns:
        top = incidents_30d["alert_type"].value_counts()
        if not top.empty and top.iloc[0] >= 2:
            recurring_alert = top.index[0]

    return {
        "score": score,
        "level": level,
        "factors": factors,
        "recurring_alert": recurring_alert,
        "incident_count_30d": n_inc,
        "critical_cves": critical_cves,
        "high_cves": high_cves,
        "firmware_age_days": fw_age,
    }


def get_similar_incidents(
    incident_id: str,
    alert_type: str,
    device_id: str,
    rca_label: str,
    top_n: int = 5,
) -> pd.DataFrame:
    """
    Find historically similar incidents based on:
    - Same alert_type (strong signal)
    - Same rca_label (strong signal)
    - Same device_id (bonus)
    Returns top_n most recent matches excluding the current incident.
    """
    df = load_incidents()
    if df.empty:
        return pd.DataFrame()

    df = df[df["incident_id"] != incident_id].copy()

    def _similarity(row) -> float:
        score = 0.0
        if row.get("alert_type") == alert_type:
            score += 0.5
        if row.get("rca_label") == rca_label:
            score += 0.4
        if row.get("device_id") == device_id:
            score += 0.1
        return round(score * 100)

    df["similarity_pct"] = df.apply(_similarity, axis=1)
    df = df[df["similarity_pct"] > 0].sort_values(
        ["similarity_pct", "start_time"], ascending=[False, False]
    ).head(top_n)
    return df.reset_index(drop=True)


def search_kb_articles(
    rca_label: str | None = None,
    alert_type: str | None = None,
) -> list[dict]:
    """Search KB articles by RCA label or alert type, returning ranked matches."""
    articles = load_kb_articles()
    results = []
    for art in articles:
        score = 0
        if rca_label and rca_label.lower() in art.get("rca_label", "").lower():
            score += 90
        if alert_type and alert_type.lower().replace("_", " ") in art.get("title", "").lower():
            score += 40
        if score > 0:
            results.append({**art, "similarity_pct": min(99, score)})

    # Also include lower-relevance articles
    for art in articles:
        if art not in list(results):
            results.append({**art, "similarity_pct": 20})

    results.sort(key=lambda x: x["similarity_pct"], reverse=True)
    return results


def get_device_cves(device_id: str) -> list[dict]:
    """Return CVEs applicable to this device based on model+firmware. No fabrication."""
    device = get_device(device_id)
    if not device:
        return []

    cve_df = load_cve_dataset()
    if cve_df.empty:
        return []

    fw = str(device.get("firmware_version", "")).strip()
    model = str(device.get("model", "")).replace("Cisco ", "").strip()

    matches = cve_df[
        (cve_df["vendor"].str.lower() == str(device.get("vendor", "")).lower()) &
        (cve_df["device_model"].str.lower() == model.lower()) &
        (cve_df["affected_version"].str.strip() == fw)
    ]
    return matches.to_dict(orient="records")


def get_firmware_recommendation(firmware_version: str) -> str | None:
    """Return recommended upgrade version or None if already current."""
    fw_df = load_firmware_recommendations()
    if fw_df.empty:
        return None
    row = fw_df[fw_df["firmware_version"].str.strip() == firmware_version.strip()]
    if row.empty:
        return None
    rec = row.iloc[0]["recommended_version"]
    if rec == firmware_version:
        return None  # already latest
    return rec


def get_top_risk_devices(top_n: int = 10) -> list[dict]:
    """Compute risk for all devices and return top N."""
    devices = load_devices()
    if devices.empty:
        return []
    results = []
    for _, dev in devices.iterrows():
        risk = compute_device_risk(dev["device_id"])
        results.append({
            "device_id": dev["device_id"],
            "hostname": dev.get("hostname", ""),
            "model": dev.get("model", ""),
            "criticality": dev.get("criticality", ""),
            "firmware_version": dev.get("firmware_version", ""),
            **risk,
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


def compute_kpis() -> dict:
    """Evidence-based KPIs from actual data."""
    incidents = load_incidents()
    resolutions = load_resolutions()

    if incidents.empty:
        return {}

    total_incidents = len(incidents)
    resolved = len(resolutions)

    # MTTA — acknowledged_at - start_time
    mtta_min = None
    if not resolutions.empty and "acknowledged_at" in resolutions.columns:
        merged = resolutions.merge(incidents[["incident_id", "start_time"]], on="incident_id", how="left")
        merged["mtta"] = (
            pd.to_datetime(merged["acknowledged_at"], utc=True) -
            pd.to_datetime(merged["start_time"], utc=True)
        ).dt.total_seconds() / 60
        mtta_min = round(merged["mtta"].dropna().mean(), 1)

    # MTTD — diagnosed_at - start_time
    mttd_min = None
    if not resolutions.empty and "diagnosed_at" in resolutions.columns:
        merged = resolutions.merge(incidents[["incident_id", "start_time"]], on="incident_id", how="left")
        merged["mttd"] = (
            pd.to_datetime(merged["diagnosed_at"], utc=True) -
            pd.to_datetime(merged["start_time"], utc=True)
        ).dt.total_seconds() / 60
        mttd_min = round(merged["mttd"].dropna().mean(), 1)

    # MTTR
    mttr_min = None
    if not resolutions.empty and "resolution_duration" in resolutions.columns:
        mttr_min = round(resolutions["resolution_duration"].dropna().mean(), 1)

    # First-time resolution rate
    ftr_rate = None
    if not resolutions.empty and "first_time_resolution" in resolutions.columns:
        ftr_rate = round(resolutions["first_time_resolution"].mean() * 100, 1)

    # Repeat incidents (same device, same alert within 30d)
    repeat = 0
    if not incidents.empty and "device_id" in incidents.columns and "alert_type" in incidents.columns:
        grp = incidents.groupby(["device_id", "alert_type"]).size()
        repeat = int((grp > 1).sum())

    # RCA automation rate — incidents with rca_label
    rca_auto_rate = None
    if "rca_label" in incidents.columns:
        has_rca = incidents["rca_label"].notna().sum()
        rca_auto_rate = round(has_rca / total_incidents * 100, 1)

    return {
        "total_incidents": total_incidents,
        "resolved_incidents": resolved,
        "mtta_min": mtta_min,
        "mttd_min": mttd_min,
        "mttr_min": mttr_min,
        "ftr_rate_pct": ftr_rate,
        "repeat_incident_device_pairs": repeat,
        "rca_automation_rate_pct": rca_auto_rate,
        "kb_articles": len(load_kb_articles()),
    }

def get_next_best_action(rca_label: str) -> list[str]:
    """Return recommended diagnostic commands for a given RCA label."""
    cmd_map = {
        "Interface degradation": [
            "show interfaces Gi0/1",
            "show interfaces counters errors",
            "show interfaces transceiver",
            "show logging | include Gi0/1",
        ],
        "WAN degradation": [
            "show interfaces <WAN_INT>",
            "show ip interface brief",
            "ping <carrier-handoff-ip> repeat 100 size 1500",
            "traceroute <destination>",
        ],
        "High CPU": [
            "show processes cpu sorted",
            "show processes memory sorted",
            "show ip route summary",
            "show logging | include CPU",
        ],
        "Routing instability": [
            "show ip bgp summary",
            "show ip ospf neighbor",
            "show ip route",
            "show logging | include BGP",
        ],
        "Device unreachable": [
            "ping <device-ip>",
            "show version",
            "show processes cpu",
            "show logging | tail",
        ],
    }
    return cmd_map.get(rca_label, ["show version", "show logging"])

# ---------------------------------------------------------------------------
# KB / SOP Operations
# ---------------------------------------------------------------------------

def create_sop_version(**kwargs) -> app.models.kb_article.KBArticle:
    """Create a new SOP version 1.0."""
    return kb_store.create_kb(**kwargs)

def get_sop_versions(kb_id: str) -> list[app.models.kb_article.KBVersionHistory]:
    """Get the version history for a KB article."""
    return kb_store.get_version_history(kb_id)

def get_current_sop(kb_id: str) -> app.models.kb_article.KBArticle:
    """Get the latest version of a KB article."""
    return kb_store.get_latest_version(kb_id)

def update_sop_version(kb_id: str, updated_by: str, change_summary: str, **field_overrides) -> app.models.kb_article.KBArticle:
    """Create a new version for an existing SOP."""
    # We should track change_summary if KBArticle supported it, but since it might not be a field,
    # we just create the new version.
    return kb_store.create_new_version(kb_id, updated_by, **field_overrides)
