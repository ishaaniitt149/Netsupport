"""SolarWinds‑style synthetic event generator.

This script creates a realistic sequence of monitoring events that follow the
workflow described in the requirements:

    DEVICE DEGRADATION → SOLARWIND ALERT → NODE_DOWN / PACKET_LOSS →
    ISSUE RESOLVED → NODE_UP / RECOVERY

Only four event types are emitted (NODE_DOWN, PACKET_LOSS, NODE_UP, RECOVERY)
but the *message* field contains a description that mirrors a typical SolarWinds
alert.

The generator is deterministic – the random seed can be set to obtain repeatable
outputs. Events are written both as JSON Lines (``*.jsonl``) and as CSV.
"""

import csv
import json
import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from app.models.device import DeviceRecord

# ---------------------------------------------------------------------------
# Event definition
# ---------------------------------------------------------------------------

EVENT_TYPES = ["NODE_DOWN", "PACKET_LOSS", "NODE_UP", "RECOVERY"]
SEVERITY_MAP = {
    "NODE_DOWN": "critical",
    "PACKET_LOSS": "warning",
    "NODE_UP": "info",
    "RECOVERY": "info",
}
SOURCE = "SolarWinds"


def _load_devices(csv_path: Path) -> list[DeviceRecord]:
    """Load the synthetic device inventory.

    The CSV is produced by :pymod:`scripts.generate_devices` and matches the
    :class:`app.models.device.DeviceRecord` schema.
    """
    df = pd.read_csv(csv_path)
    return [DeviceRecord(**row.to_dict()) for _, row in df.iterrows()]


def _make_message(event_type: str, device: DeviceRecord) -> str:
    """Create a human‑readable alert message.

    The wording imitates typical SolarWinds alerts while staying generic.
    """
    if event_type == "PACKET_LOSS":
        return (
            f"Packet loss detected on interface Gi0/1 of {device.hostname} ("
            f"{device.device_id}). Loss rate exceeds threshold."
        )
    if event_type == "NODE_DOWN":
        return (
            f"Device {device.hostname} ({device.device_id}) is unreachable. "
            "ICMP ping failed for 5 consecutive minutes."
        )
    if event_type == "RECOVERY":
        return (
            f"Packet loss on {device.hostname} ({device.device_id}) returned to "
            "normal levels."
        )
    if event_type == "NODE_UP":
        return (
            f"Device {device.hostname} ({device.device_id}) is back online. "
            "All health checks passed."
        )
    return ""


def _event_record(event_type: str, device: DeviceRecord, timestamp: datetime) -> dict:
    """Build a single event dictionary.

    ``correlation_key`` is set to the ``device_id`` so that downstream services
    can group events belonging to the same physical asset.
    """
    return {
        "event_id": str(uuid.uuid4()),
        "device_id": device.device_id,
        "event_type": event_type,
        "severity": SEVERITY_MAP[event_type],
        "timestamp": timestamp.isoformat(),
        "source": SOURCE,
        "message": _make_message(event_type, device),
        "correlation_key": device.device_id,
    }


def generate_events(
    devices: list[DeviceRecord],
    start_datetime: datetime = datetime(2023, 1, 1, tzinfo=UTC),
    incident_rate: float = 0.2,
    random_seed: int = 42,
) -> list[dict]:
    """Generate a chronological list of synthetic SolarWinds events.

    Args:
        devices: List of synthetic :class:`Device` objects.
        start_datetime: UTC start of the simulation window.
        incident_rate: Approximate proportion of devices that experience an
            incident during the simulation.
        random_seed: Seed for reproducibility.
    """
    random.seed(random_seed)
    events: list[dict] = []
    total_hours = 90 * 24  # 90‑day window

    for device in devices:
        if random.random() > incident_rate:
            continue  # most devices stay healthy

        # Choose a random hour for the start of degradation
        start_hour = random.randint(0, total_hours - 24)  # leave room for resolution
        base_ts = start_datetime + timedelta(hours=start_hour)

        # 1️⃣ PACKET_LOSS (warning) – occurs a few minutes after degradation start
        pkt_ts = base_ts + timedelta(minutes=random.randint(5, 30))
        events.append(_event_record("PACKET_LOSS", device, pkt_ts))

        # 2️⃣ NODE_DOWN (critical) – a little later
        down_ts = pkt_ts + timedelta(minutes=random.randint(10, 20))
        events.append(_event_record("NODE_DOWN", device, down_ts))

        # 3️⃣ RECOVERY (info) – after the issue is resolved but before the node is fully up
        recovery_ts = down_ts + timedelta(hours=random.randint(1, 4))
        events.append(_event_record("RECOVERY", device, recovery_ts))

        # 4️⃣ NODE_UP (info) – final step
        up_ts = recovery_ts + timedelta(minutes=random.randint(5, 15))
        events.append(_event_record("NODE_UP", device, up_ts))

    # Sort chronologically for deterministic output order
    events.sort(key=lambda e: e["timestamp"])
    return events


def write_events_jsonl(events: list[dict], output_path: Path) -> None:
    """Write events to a JSON Lines file.

    Each line is a compact JSON object. ``output_path`` is created if necessary.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


def write_events_csv(events: list[dict], output_path: Path) -> None:
    """Write events to a CSV file using the same field order for every row.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["event_id", "device_id", "event_type", "severity", "timestamp", "source", "message", "correlation_key"]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ev in events:
            writer.writerow(ev)


if __name__ == "__main__":
    # Load devices generated by the earlier script
    devices_path = Path(__file__).parents[1] / "data" / "synthetic" / "devices.csv"
    devices = _load_devices(devices_path)

    evts = generate_events(devices)
    json_path = Path(__file__).parents[1] / "data" / "synthetic" / "solarwinds_events.jsonl"
    csv_path = Path(__file__).parents[1] / "data" / "synthetic" / "solarwinds_events.csv"

    write_events_jsonl(evts, json_path)
    write_events_csv(evts, csv_path)
    print(f"Generated {len(evts)} events → {json_path.name} & {csv_path.name}")
