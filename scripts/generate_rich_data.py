"""Rich synthetic data generator for NOIPMP demo.

Generates 90-day dataset with:
- 100 devices (Cisco fleet)
- 500+ incidents with realistic recurring patterns
- Telemetry with gradual degradation curves
- Multiple RCA types
- Resolutions and KB articles
- CVE relationships tied to real firmware versions

Run: python scripts/generate_rich_data.py
"""

from __future__ import annotations

import pathlib
import random
import uuid
from datetime import UTC, date, datetime, timedelta

import pandas as pd

ROOT = pathlib.Path(__file__).parents[1]
DATA = ROOT / "data" / "synthetic"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

RNG = random.Random(42)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
START = datetime(2026, 6, 28, tzinfo=UTC)   # 90 days ago from ~Sep 27 2026
END   = datetime(2026, 9, 27, tzinfo=UTC)
DAYS  = (END - START).days  # 91

ALERT_TYPES = ["NODE_DOWN", "PACKET_LOSS", "INTERFACE_ERROR", "HIGH_CPU", "ROUTING_INSTABILITY"]
RCA_LABELS  = {
    "NODE_DOWN":            "Device unreachable",
    "PACKET_LOSS":          "WAN degradation",
    "INTERFACE_ERROR":      "Interface degradation",
    "HIGH_CPU":             "High CPU",
    "ROUTING_INSTABILITY":  "Routing instability",
}
SEVERITIES = {
    "NODE_DOWN":            "critical",
    "PACKET_LOSS":          "warning",
    "INTERFACE_ERROR":      "warning",
    "HIGH_CPU":             "high",
    "ROUTING_INSTABILITY":  "high",
}
RESOLUTION_ACTIONS = {
    "Device unreachable":   "Performed hard reboot at remote site",
    "WAN degradation":      "Escalated to ISP; carrier provisioned new circuit",
    "Interface degradation":"Replaced faulty SFP transceiver and fiber patch cable",
    "High CPU":             "Identified and terminated runaway BGP scanner process",
    "Routing instability":  "Corrected misconfigured route-map and reset BGP session",
}
VALIDATION_ACTIONS = {
    "Device unreachable":   "Verified SNMP and SSH connectivity restored",
    "WAN degradation":      "Confirmed packet loss <0.1% for 30 minutes",
    "Interface degradation":"Verified CRC counters cleared; zero packet loss",
    "High CPU":             "Confirmed CPU <60% sustained for 15 minutes",
    "Routing instability":  "Verified BGP in ESTABLISHED state with expected prefix count",
}

ENGINEERS = ["Alice Chen", "Bob Patel", "Carlos Rivera", "Diana Prince", "Elena Kowalski"]

# Firmware versions and their recommended upgrades (used for CVE matching)
FIRMWARE_VERSIONS = [
    "17.03.01",  # old — has CVEs
    "17.06.04",
    "17.09.03",
    "17.09.06",  # recommended latest
]

# ---------------------------------------------------------------------------
# Device profiles — governs incident behavior
# ---------------------------------------------------------------------------
# Each device gets a 'profile' that determines its 90-day incident pattern

PROFILES = [
    # (profile_name, n_incidents_approx, primary_alert, degrading, weight)
    ("healthy",       0,  "NODE_DOWN",           False, 0.25),
    ("occasional",    4,  "PACKET_LOSS",         False, 0.20),
    ("recurring",     12, "INTERFACE_ERROR",     True,  0.35),
    ("deteriorating", 18, "NODE_DOWN",           True,  0.15),
    ("vulnerable",    2,  "ROUTING_INSTABILITY", False, 0.05),
]

PROFILE_WEIGHTS = [p[4] for p in PROFILES]


def _pick_profile() -> tuple:
    return RNG.choices(PROFILES, weights=PROFILE_WEIGHTS, k=1)[0]


# ---------------------------------------------------------------------------
# Generate devices
# ---------------------------------------------------------------------------
DEVICE_MODELS = [
    ("Catalyst 9300", "Access Switch",        "17.09.06"),
    ("Catalyst 9300", "Access Switch",        "17.06.04"),
    ("Catalyst 9300", "Access Switch",        "17.03.01"),   # old firmware — CVEs
    ("Catalyst 9500", "Distribution Switch",  "17.09.06"),
    ("ASR 1001-X",    "WAN Router",           "17.09.03"),
    ("ISR 4451",      "Branch Router",        "17.09.06"),
    ("ISR 4451",      "Branch Router",        "17.03.01"),   # old firmware — CVEs
    ("Nexus 9300",    "Data Center Switch",   "9.3.10"),
    ("Firepower 2130","Firewall",             "7.4.1"),
]

LOCATIONS = [
    "New York Data Center", "London Edge", "Sydney Edge Facility",
    "Singapore Hub", "Chicago Core", "Frankfurt PoP",
    "Mumbai Regional", "Toronto Branch", "Los Angeles Branch",
]
REGIONS = ["AMER-EAST", "AMER-WEST", "EMEA", "APAC-NORTH", "APAC-SOUTH"]
CUSTOMERS = [
    "Zenith Retail Group", "Solaria Renewable Power", "NovaTech Industries",
    "ClearWave Telecom", "Frontier Logistics",
]
SEGMENTS = ["CORE-BACKBONE", "BRANCH-OFFICE", "DATA-CENTER", "WAN-EDGE", "DMZ"]


def generate_devices(n: int = 100) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        model_entry = RNG.choice(DEVICE_MODELS)
        model_name, dev_type, fw = model_entry
        loc = RNG.choice(LOCATIONS)
        region = RNG.choice(REGIONS)
        criticality = RNG.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        patch_days_ago = RNG.randint(30, 730)
        patch_date = (date.today() - timedelta(days=patch_days_ago)).isoformat()
        rows.append({
            "device_id":        f"DEV-CSCO-{i:04d}",
            "hostname":         f"csco-{dev_type.lower().replace(' ','-')}-{i:03d}.corp.internal",
            "vendor":           "Cisco",
            "model":            f"Cisco {model_name}",
            "serial_number":    f"SN{RNG.randint(1000000,9999999)}",
            "firmware_version": fw,
            "location":         loc,
            "region":           region,
            "device_type":      dev_type,
            "criticality":      criticality,
            "interface_count":  RNG.choice([8, 24, 48]),
            "last_patch_date":  patch_date,
            "customer":         RNG.choice(CUSTOMERS),
            "network_segment":  RNG.choice(SEGMENTS),
            # non-schema extras (used by UI)
            "ip_address":       f"10.{RNG.randint(1,254)}.{RNG.randint(1,254)}.{RNG.randint(1,254)}",
            "profile":          _pick_profile()[0],
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Generate telemetry (30-day summary per device, hourly trend data)
# ---------------------------------------------------------------------------

def _base_metrics(profile: str) -> dict:
    """Baseline healthy metrics for a given profile."""
    if profile == "healthy":
        return dict(cpu=RNG.uniform(20, 45), mem=RNG.uniform(30, 55),
                    pkt_loss=RNG.uniform(0, 0.2), crc=RNG.randint(0, 5),
                    flaps=0, latency=RNG.uniform(1, 5))
    if profile == "occasional":
        return dict(cpu=RNG.uniform(30, 60), mem=RNG.uniform(40, 65),
                    pkt_loss=RNG.uniform(0.1, 1.0), crc=RNG.randint(5, 50),
                    flaps=RNG.randint(0, 2), latency=RNG.uniform(2, 10))
    if profile == "recurring":
        return dict(cpu=RNG.uniform(40, 70), mem=RNG.uniform(50, 75),
                    pkt_loss=RNG.uniform(1.0, 5.0), crc=RNG.randint(50, 300),
                    flaps=RNG.randint(2, 5), latency=RNG.uniform(5, 20))
    if profile == "deteriorating":
        return dict(cpu=RNG.uniform(55, 80), mem=RNG.uniform(60, 85),
                    pkt_loss=RNG.uniform(3.0, 10.0), crc=RNG.randint(200, 800),
                    flaps=RNG.randint(5, 12), latency=RNG.uniform(15, 50))
    # vulnerable
    return dict(cpu=RNG.uniform(25, 50), mem=RNG.uniform(35, 60),
                pkt_loss=RNG.uniform(0.1, 0.5), crc=RNG.randint(0, 20),
                flaps=0, latency=RNG.uniform(1, 6))


def generate_telemetry(devices_df: pd.DataFrame) -> pd.DataFrame:
    """Generate daily summary telemetry for each device over 90 days.

    Telemetry is correlated with the device profile:
    - Deteriorating: metrics worsen progressively over time
    - Recurring: periodic spikes around the midpoint
    - Healthy: flat with small noise
    """
    rows = []
    today = date.today()
    TELEMETRY_DAYS = 90
    for _, dev in devices_df.iterrows():
        profile = dev.get("profile", "healthy")
        base = _base_metrics(profile)
        for day in range(TELEMETRY_DAYS):
            days_from_start = day  # 0 = 90 days ago, 89 = yesterday
            ts = today - timedelta(days=TELEMETRY_DAYS - 1 - day)

            # Deterioration factor: deteriorating devices get worse towards day 90
            if profile == "deteriorating":
                factor = 1.0 + (0.04 * days_from_start)
                factor = min(factor, 4.0)
            elif profile == "recurring":
                # Periodic spikes every ~15 days simulating recurring bursts
                spike = 1.5 if (days_from_start % 15 < 3) else 1.0
                factor = spike
            else:
                factor = 1.0

            # Node-down: availability zeroes on deteriorating devices near the end
            availability = 1.0
            if profile == "deteriorating" and days_from_start > 75:
                availability = 0.0 if RNG.random() < 0.15 else 1.0

            rows.append({
                "device_id":        dev["device_id"],
                "date":             ts.isoformat(),
                "cpu_pct":          min(100, round(base["cpu"] * factor + RNG.gauss(0, 3), 1)),
                "memory_pct":       min(100, round(base["mem"] * factor + RNG.gauss(0, 2), 1)),
                "packet_loss_pct":  min(100, round(max(0, base["pkt_loss"] * factor + RNG.gauss(0, 0.3)), 2)),
                "crc_errors":       max(0, int(base["crc"] * factor + RNG.gauss(0, 5))),
                "interface_flaps":  max(0, int(base["flaps"] * factor + RNG.gauss(0, 0.5))),
                "latency_ms":       max(0, round(base["latency"] * factor + RNG.gauss(0, 1), 1)),
                "availability":     availability,
                "is_synthetic":     True,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Generate incidents with recurring patterns
# ---------------------------------------------------------------------------

def generate_incidents(devices_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate 500+ incidents with realistic recurring per-device patterns."""
    incidents = []
    resolutions = []

    for _, dev in devices_df.iterrows():
        profile = dev.get("profile", "healthy")
        n_incidents = {
            "healthy":       RNG.randint(0, 1),
            "occasional":    RNG.randint(3, 6),
            "recurring":     RNG.randint(8, 14),
            "deteriorating": RNG.randint(12, 20),
            "vulnerable":    RNG.randint(1, 4),
        }.get(profile, 0)

        # Pick primary alert type for this device (creates recurring pattern)
        primary_alert = {
            "healthy":       "NODE_DOWN",
            "occasional":    RNG.choice(["PACKET_LOSS", "NODE_DOWN"]),
            "recurring":     RNG.choice(["INTERFACE_ERROR", "PACKET_LOSS"]),
            "deteriorating": "NODE_DOWN",
            "vulnerable":    RNG.choice(["ROUTING_INSTABILITY", "HIGH_CPU"]),
        }.get(profile, "NODE_DOWN")

        for _ in range(n_incidents):
            # Random start within 90-day window
            offset_days = RNG.randint(0, DAYS - 1)
            start_ts = START + timedelta(days=offset_days,
                                         hours=RNG.randint(0, 23),
                                         minutes=RNG.randint(0, 59))
            duration_min = RNG.randint(15, 240)
            recovery_ts = start_ts + timedelta(minutes=duration_min)

            # 80% recurring primary type, 20% random
            alert_type = primary_alert if RNG.random() < 0.8 else RNG.choice(ALERT_TYPES)
            rca_label = RCA_LABELS[alert_type]
            inc_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

            inc = {
                "incident_id":          inc_id,
                "device_id":            dev["device_id"],
                "hostname":             dev["hostname"],
                "start_time":           start_ts.isoformat(),
                "recovery_time":        recovery_ts.isoformat(),
                "duration_minutes":     duration_min,
                "alert_type":           alert_type,
                "severity":             SEVERITIES[alert_type],
                "rca_label":            rca_label,
                "rca_confidence":       round(RNG.uniform(0.75, 0.98), 2),
                "rca_rule_id":          f"RULE-{RNG.randint(1,10):03d}",
                "crc_errors":           RNG.randint(100, 2000) if alert_type == "INTERFACE_ERROR" else RNG.randint(0, 50),
                "packet_loss_pct":      round(RNG.uniform(5, 25), 1) if alert_type in ["PACKET_LOSS", "NODE_DOWN"] else round(RNG.uniform(0, 2), 1),
                "interface_flaps":      RNG.randint(3, 15) if alert_type == "INTERFACE_ERROR" else 0,
                "cpu_pct":              RNG.randint(85, 99) if alert_type == "HIGH_CPU" else RNG.randint(20, 60),
                "is_synthetic":         True,
            }
            incidents.append(inc)

            # Resolution (80% of incidents get resolved)
            if RNG.random() < 0.80:
                resolved_at = recovery_ts + timedelta(minutes=RNG.randint(5, 30))
                engineer = RNG.choice(ENGINEERS)
                resolutions.append({
                    "incident_id":          inc_id,
                    "device_id":            dev["device_id"],
                    "root_cause":           rca_label,
                    "resolution_action":    RESOLUTION_ACTIONS[rca_label],
                    "validation_action":    VALIDATION_ACTIONS[rca_label],
                    "resolved_by":          engineer,
                    "resolution_timestamp": resolved_at.isoformat(),
                    "acknowledged_at":      (start_ts + timedelta(minutes=RNG.randint(2, 15))).isoformat(),
                    "diagnosed_at":         (start_ts + timedelta(minutes=RNG.randint(10, 30))).isoformat(),
                    "resolution_duration":  int((resolved_at - start_ts).total_seconds() / 60),
                    "first_time_resolution":RNG.random() < 0.75,
                    "is_synthetic":         True,
                })

    df_inc = pd.DataFrame(incidents)
    df_res = pd.DataFrame(resolutions)

    if not df_inc.empty:
        df_inc["start_time"] = pd.to_datetime(df_inc["start_time"], utc=True)
        df_inc["recovery_time"] = pd.to_datetime(df_inc["recovery_time"], utc=True)
        df_inc = df_inc.sort_values("start_time").reset_index(drop=True)

    return df_inc, df_res


# ---------------------------------------------------------------------------
# Generate CVE dataset (expanded)
# ---------------------------------------------------------------------------

CVE_DATASET = [
    # Catalyst 9300 — 17.03.01 (old firmware, multiple CVEs)
    {"cve_id": "CVE-2023-20169", "vendor": "Cisco", "device_model": "Catalyst 9300",
     "affected_version": "17.03.01", "fixed_version": "17.06.01",
     "severity": "CRITICAL", "description": "Remote code execution via crafted RESTCONF request."},
    {"cve_id": "CVE-2023-20198", "vendor": "Cisco", "device_model": "Catalyst 9300",
     "affected_version": "17.03.01", "fixed_version": "17.06.01",
     "severity": "CRITICAL", "description": "Privilege escalation in IOS XE web UI."},
    {"cve_id": "CVE-2023-20273", "vendor": "Cisco", "device_model": "Catalyst 9300",
     "affected_version": "17.03.01", "fixed_version": "17.06.02",
     "severity": "HIGH", "description": "Command injection via crafted HTTP request."},
    {"cve_id": "CVE-2022-20919", "vendor": "Cisco", "device_model": "Catalyst 9300",
     "affected_version": "17.03.01", "fixed_version": "17.06.01",
     "severity": "HIGH", "description": "DoS via malformed Cisco Discovery Protocol packet."},
    # ISR 4451 — 17.03.01
    {"cve_id": "CVE-2023-20227", "vendor": "Cisco", "device_model": "ISR 4451",
     "affected_version": "17.03.01", "fixed_version": "17.06.03",
     "severity": "CRITICAL", "description": "Memory exhaustion in IOS XE NAT."},
    {"cve_id": "CVE-2023-20231", "vendor": "Cisco", "device_model": "ISR 4451",
     "affected_version": "17.03.01", "fixed_version": "17.06.01",
     "severity": "HIGH", "description": "BGP session termination via crafted UPDATE message."},
    # Catalyst 9300 — 17.06.04 (minor CVEs)
    {"cve_id": "CVE-2023-20195", "vendor": "Cisco", "device_model": "Catalyst 9300",
     "affected_version": "17.06.04", "fixed_version": "17.09.01",
     "severity": "MEDIUM", "description": "Information disclosure via SNMP."},
]

FIRMWARE_RECOMMENDATIONS = {
    "17.03.01": "17.09.06",
    "17.06.04": "17.09.06",
    "17.09.03": "17.09.06",
    "17.09.06": "17.09.06",  # already latest
    "9.3.10":   "9.3.12",
    "7.4.1":    "7.4.2",
}


def generate_cve_dataset() -> pd.DataFrame:
    return pd.DataFrame(CVE_DATASET)


# ---------------------------------------------------------------------------
# Generate KB articles (seed data — real KB store used for new ones)
# ---------------------------------------------------------------------------

KB_SEED = [
    {
        "kb_id": "KB-0001", "version": "1.2", "status": "APPROVED",
        "title": "SOP: Interface Degradation Troubleshooting",
        "rca_label": "Interface degradation",
        "problem_statement": "Uplink interface experiencing CRC errors and packet loss, indicating physical layer degradation.",
        "symptoms": ["CRC errors incrementing", "Interface flapping", "Packet loss above threshold"],
        "resolution_steps": [
            "Run: show interfaces Gi0/1",
            "Check CRC error counters",
            "Run: show interfaces transceiver",
            "Inspect optical power levels",
            "Replace SFP transceiver if Rx power is below -14 dBm",
            "Replace fiber patch cable if transceiver tests clean",
            "Clear counters and monitor for 15 minutes",
        ],
        "validation_steps": ["Verify CRC counters clear", "Confirm packet loss <0.1%", "Monitor for 30 minutes"],
        "created_by": "Alice Chen",
        "applicable_devices": "Cisco Catalyst 9300, ISR 4451",
        "applicable_rca": "Interface degradation",
        "reuse_count": 47,
        "related_cves": [],
    },
    {
        "kb_id": "KB-0002", "version": "1.1", "status": "APPROVED",
        "title": "SOP: WAN Packet Loss Investigation",
        "rca_label": "WAN degradation",
        "problem_statement": "Device reporting sustained packet loss on WAN interface above SLA threshold.",
        "symptoms": ["Packet loss >1% sustained", "Latency increase", "Interface in DEGRADED state"],
        "resolution_steps": [
            "Run: show interfaces <WAN_INT>",
            "Verify interface input/output error counters",
            "Run traceroute to carrier handoff",
            "Open carrier ticket if loss is consistent at first hop",
            "Escalate to ISP with packet loss data",
        ],
        "validation_steps": ["Confirm <0.1% packet loss", "Verify SLA compliance"],
        "created_by": "Bob Patel",
        "applicable_devices": "All WAN-facing devices",
        "applicable_rca": "WAN degradation",
        "reuse_count": 32,
        "related_cves": [],
    },
    {
        "kb_id": "KB-0003", "version": "1.0", "status": "APPROVED",
        "title": "SOP: Device Unreachable / NODE_DOWN Recovery",
        "rca_label": "Device unreachable",
        "problem_statement": "Device not responding to ICMP, SNMP, or SSH. SolarWinds reports NODE_DOWN.",
        "symptoms": ["100% packet loss to device", "SNMP polling failure", "SSH timeout"],
        "resolution_steps": [
            "Verify management VLAN reachability from jump host",
            "Attempt out-of-band console access",
            "If no OOB: dispatch on-site engineer",
            "Perform hard power cycle if unresponsive",
            "Verify process table after recovery: show processes cpu",
            "Check for crashinfo: show version | include crashinfo",
        ],
        "validation_steps": ["Verify SNMP and SSH connectivity", "Check routing table integrity"],
        "created_by": "Diana Prince",
        "applicable_devices": "All Cisco IOS XE devices",
        "applicable_rca": "Device unreachable",
        "reuse_count": 28,
        "related_cves": [],
    },
    {
        "kb_id": "KB-0004", "version": "1.0", "status": "APPROVED",
        "title": "SOP: High CPU Troubleshooting",
        "rca_label": "High CPU",
        "problem_statement": "Device CPU utilization above 90% causing control-plane processing delays.",
        "symptoms": ["CPU >90%", "OSPF/BGP adjacency instability", "SSH login delays"],
        "resolution_steps": [
            "Run: show processes cpu sorted",
            "Identify top offending process",
            "Check for routing table churn: show ip route summary",
            "Check for BGP scanner anomaly: show ip bgp summary",
            "If routing loop suspected: traceroute to identify loop",
            "Consider process restart as last resort",
        ],
        "validation_steps": ["Confirm CPU <60%", "Verify all routing adjacencies stable"],
        "created_by": "Carlos Rivera",
        "applicable_devices": "All Cisco IOS XE devices",
        "applicable_rca": "High CPU",
        "reuse_count": 19,
        "related_cves": [],
    },
    {
        "kb_id": "KB-0005", "version": "1.0", "status": "APPROVED",
        "title": "SOP: Routing Instability / BGP Flap Investigation",
        "rca_label": "Routing instability",
        "problem_statement": "BGP or OSPF neighbor relationships flapping causing traffic disruption.",
        "symptoms": ["BGP session not ESTABLISHED", "OSPF neighbor not in FULL state", "Route table churn"],
        "resolution_steps": [
            "Run: show ip bgp summary",
            "Run: show ip ospf neighbor",
            "Check for MTU mismatch: show interfaces | include MTU",
            "Verify BGP timers are consistent with peer",
            "Check for route-map errors: show ip bgp route-map",
            "Clear BGP session if configuration corrected: clear ip bgp <peer>",
        ],
        "validation_steps": ["Verify BGP ESTABLISHED", "Check prefix count matches expected", "Monitor for 1 hour"],
        "created_by": "Elena Kowalski",
        "applicable_devices": "All Cisco IOS XE routing devices",
        "applicable_rca": "Routing instability",
        "reuse_count": 14,
        "related_cves": [],
    },
]


def generate_kb_articles() -> pd.DataFrame:
    return pd.DataFrame(KB_SEED)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Generating rich synthetic dataset...")

    # Devices
    devices_df = generate_devices(100)
    devices_df.to_csv(DATA / "devices.csv", index=False)
    print(f"  ✓ {len(devices_df)} devices")

    # Telemetry
    tel_df = generate_telemetry(devices_df)
    tel_df.to_parquet(PROC / "telemetry.parquet", index=False)
    print(f"  ✓ {len(tel_df)} telemetry rows (90d daily per device)")

    # Incidents + resolutions
    inc_df, res_df = generate_incidents(devices_df)
    inc_df.to_parquet(PROC / "incidents.parquet", index=False)
    res_df.to_parquet(PROC / "resolutions.parquet", index=False)
    print(f"  ✓ {len(inc_df)} incidents, {len(res_df)} resolutions")

    # CVEs
    cve_df = generate_cve_dataset()
    cve_df.to_csv(DATA / "cve_dataset.csv", index=False)
    print(f"  ✓ {len(cve_df)} CVE entries")

    # KB articles (seed)
    kb_df = generate_kb_articles()
    kb_df.to_json(PROC / "kb_articles.json", orient="records", indent=2)
    print(f"  ✓ {len(kb_df)} KB articles")

    # Firmware recommendations
    fw_rec = pd.DataFrame([
        {"firmware_version": k, "recommended_version": v}
        for k, v in FIRMWARE_RECOMMENDATIONS.items()
    ])
    fw_rec.to_csv(DATA / "firmware_recommendations.csv", index=False)
    print(f"  ✓ {len(fw_rec)} firmware recommendations")

    print("\nAll data written to data/synthetic/ and data/processed/")
    print(f"  Incidents range: {inc_df['start_time'].min().date()} → {inc_df['start_time'].max().date()}")


if __name__ == "__main__":
    main()
