"""Incident Correlation Engine."""

import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel


class CorrelatedIncident(BaseModel):
    """Correlated Incident Pydantic model."""

    incident_id: str
    device_id: str
    start_time: datetime
    recovery_time: datetime | None = None
    duration_minutes: float | None = None
    alert_type: str
    severity: str
    rca_source: str | None = None
    correlation_confidence: float = 0.0


class CorrelationEngine:
    def __init__(self, events_csv: Path, rca_meta_csv: Path, output_parquet: Path):
        self.events_csv = events_csv
        self.rca_meta_csv = rca_meta_csv
        self.output_parquet = output_parquet

    def load_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        events_df = pd.read_csv(self.events_csv, parse_dates=["timestamp"])
        events_df.sort_values(by="timestamp", inplace=True)

        if self.rca_meta_csv.exists():
            rca_df = pd.read_csv(self.rca_meta_csv)
        else:
            rca_df = pd.DataFrame(columns=["incident_id", "device_id", "rca_file", "alert_event_id", "recovery_event_id"])

        return events_df, rca_df

    def correlate(self) -> list[CorrelatedIncident]:
        events_df, rca_df = self.load_data()

        # Build RCA lookup mapping
        # Maps alert_event_id -> rca_file
        rca_alert_map = {}
        # Maps recovery_event_id -> rca_file
        rca_recovery_map = {}
        for _, row in rca_df.iterrows():
            if pd.notna(row.get("alert_event_id")):
                rca_alert_map[row["alert_event_id"]] = row["rca_file"]
            if pd.notna(row.get("recovery_event_id")):
                rca_recovery_map[row["recovery_event_id"]] = row["rca_file"]

        incidents: list[CorrelatedIncident] = []

        # Group by device
        for device_id, group in events_df.groupby("device_id"):
            current_incident = None
            alert_ids = set()

            for _, event in group.iterrows():
                etype = event["event_type"]
                ts = event["timestamp"]
                ev_id = event["event_id"]
                severity = event.get("severity", "Critical")

                if etype in ("NODE_DOWN", "PACKET_LOSS"):
                    if current_incident is None:
                        current_incident = {
                            "incident_id": f"INC-{uuid.uuid4().hex[:8]}",
                            "device_id": device_id,
                            "start_time": ts,
                            "alert_type": etype,
                            "severity": severity,
                        }
                        alert_ids = {ev_id}
                    else:
                        # Multiple alerts for same device before recovery
                        # E.g., PACKET_LOSS then NODE_DOWN
                        alert_ids.add(ev_id)
                        if etype == "NODE_DOWN":
                            current_incident["alert_type"] = "NODE_DOWN"
                            current_incident["severity"] = "critical"

                elif etype in ("NODE_UP", "RECOVERY"):
                    if current_incident is not None:
                        current_incident["recovery_time"] = ts
                        dur = (ts - current_incident["start_time"]).total_seconds() / 60.0
                        current_incident["duration_minutes"] = round(dur, 2)

                        # Check RCA
                        rca_source = None
                        for aid in alert_ids:
                            if aid in rca_alert_map:
                                rca_source = rca_alert_map[aid]
                        if ev_id in rca_recovery_map:
                            rca_source = rca_recovery_map[ev_id]

                        current_incident["rca_source"] = rca_source

                        # Confidence
                        if rca_source:
                            confidence = 1.0
                        else:
                            confidence = 0.8

                        current_incident["correlation_confidence"] = confidence
                        incidents.append(CorrelatedIncident(**current_incident))

                        current_incident = None
                        alert_ids = set()

            # Missing recovery
            if current_incident is not None:
                current_incident["correlation_confidence"] = 0.5

                # check RCA even if no recovery yet
                rca_source = None
                for aid in alert_ids:
                    if aid in rca_alert_map:
                        rca_source = rca_alert_map[aid]
                current_incident["rca_source"] = rca_source

                incidents.append(CorrelatedIncident(**current_incident))

        return incidents

    def run(self):
        incidents = self.correlate()
        if not incidents:
            print("No incidents found.")
            return []

        # Write to parquet
        df = pd.DataFrame([inc.model_dump() for inc in incidents])
        self.output_parquet.parent.mkdir(parents=True, exist_ok=True)
        # Ensure timestamp columns are properly tz-aware or naive consistently
        df.to_parquet(self.output_parquet, engine="pyarrow")
        return incidents


if __name__ == "__main__":
    base_dir = Path(__file__).parents[2]
    engine = CorrelationEngine(
        events_csv=base_dir / "data" / "synthetic" / "solarwinds_events.csv",
        rca_meta_csv=base_dir / "data" / "synthetic" / "rca_emails" / "metadata.csv",
        output_parquet=base_dir / "data" / "processed" / "incidents.parquet"
    )
    res = engine.run()
    print(f"Correlated {len(res)} incidents and saved to parquet.")
