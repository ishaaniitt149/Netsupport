"""Generate synthetic engineer resolutions for correlated incidents."""

import random
from datetime import timedelta
from pathlib import Path

import pandas as pd

from app.models.resolution import Resolution
from app.services.resolution_service import ResolutionService


def generate_resolutions(incidents_parquet: Path, resolutions_parquet: Path):
    if not incidents_parquet.exists():
        print("No incidents found. Run correlation engine first.")
        return

    df = pd.read_parquet(incidents_parquet)
    service = ResolutionService(resolutions_parquet)

    actions = {
        "Interface degradation": ("Replaced faulty SFP module", "Verified light levels and cleared counters"),
        "High CPU": ("Identified and restarted looping control plane process", "Verified CPU usage dropped to normal levels"),
        "Memory pressure": ("Applied software patch for known memory leak", "Verified memory stable over 2 hours"),
        "Routing instability": ("Reset BGP peer and applied updated route-map", "Verified BGP sessions established"),
        "WAN degradation": ("Worked with ISP to fix circuit issue", "Ran iPerf to verify bandwidth"),
        "Device unreachable": ("Performed hard reboot at remote site", "Verified SNMP and SSH connectivity restored")
    }

    engineers = ["Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince"]

    count = 0
    for _, row in df.iterrows():
        # Only resolve incidents that have recovered
        if pd.isna(row.get("recovery_time")):
            continue

        inc_id = row["incident_id"]
        dev_id = row["device_id"]
        start_time = row["start_time"]
        recovery_time = row["recovery_time"]

        # Skip if already exists
        if service.get_resolution(inc_id):
            continue

        rca = row.get("alert_type")
        if rca == "NODE_DOWN":
            rca = "Device unreachable"
        elif rca == "PACKET_LOSS":
            rca = "Interface degradation"

        # Simulate realistic times
        mtta_mins = random.randint(2, 15)
        mttd_mins = random.randint(5, 30)

        ack_time = start_time + timedelta(minutes=mtta_mins)
        diag_time = ack_time + timedelta(minutes=mttd_mins)

        res_action, val_action = actions.get(rca, ("Performed general diagnostic and reboot", "Verified system stable"))

        res = Resolution(
            incident_id=inc_id,
            device_id=dev_id,
            root_cause=f"Simulated {rca}",
            resolution_action=res_action,
            validation_action=val_action,
            resolved_by=random.choice(engineers),
            resolution_timestamp=recovery_time, # Tied to the synthetic recovery time
            acknowledged_at=ack_time,
            diagnosed_at=diag_time,
            resolution_duration=(recovery_time - start_time).total_seconds() / 60.0,
            first_time_resolution=random.random() > 0.15  # 85% FTR
        )

        service.create_resolution(res)
        count += 1

    print(f"Generated {count} synthetic resolutions.")

    # Calculate KPIs
    kpis = service.calculate_kpis(df)
    print("\n--- KPI Baseline Report ---")
    print(f"Total Incidents: {kpis.total_incidents}")
    print(f"MTTA: {kpis.mtta_minutes} mins")
    print(f"MTTD: {kpis.mttd_minutes} mins")
    print(f"MTTR: {kpis.mttr_minutes} mins")
    print(f"FTR Rate: {kpis.ftr_rate}%")


if __name__ == "__main__":
    base_dir = Path(__file__).parents[1]
    inc_parquet = base_dir / "data" / "processed" / "incidents.parquet"
    res_parquet = base_dir / "data" / "processed" / "resolutions.parquet"

    generate_resolutions(inc_parquet, res_parquet)
