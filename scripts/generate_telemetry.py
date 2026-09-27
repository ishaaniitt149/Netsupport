"""Telemetry Generator
Generate 90 days of hourly synthetic telemetry for devices defined in ``data/synthetic/devices.csv``.
The generator creates realistic temporal patterns and injects six failure scenarios with gradual deterioration.
"""

import csv
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from app.models.device import Device
from app.models.telemetry import InterfaceStatus, RoutingProtocolStatus, TelemetryRecord


def _load_devices(csv_path: Path) -> list[Device]:
    df = pd.read_csv(csv_path)
    devices = []
    for _, row in df.iterrows():
        devices.append(Device(**row.to_dict()))
    return devices


def _baseline_telemetry(device: Device, ts: datetime) -> dict:
    """Generate a baseline (healthy) telemetry record.
    Values are centered around realistic means with small random noise.
    """
    cpu = max(0, min(100, random.gauss(30, 5)))
    mem = max(0, min(100, random.gauss(45, 7)))
    latency = max(0, random.gauss(5, 1))
    pkt_loss = max(0, min(100, random.gauss(0.1, 0.2)))
    crc = max(0, int(random.gauss(0, 1)))
    inp_err = max(0, int(random.gauss(0, 1)))
    out_err = max(0, int(random.gauss(0, 1)))
    flaps = max(0, int(random.gauss(0, 0.5)))
    return {
        "timestamp": ts,
        "device_id": device.device_id,
        "cpu_utilization": round(cpu, 2),
        "memory_utilization": round(mem, 2),
        "latency_ms": round(latency, 2),
        "packet_loss_percent": round(pkt_loss, 3),
        "crc_errors": crc,
        "input_errors": inp_err,
        "output_errors": out_err,
        "interface_flaps": flaps,
        "interface_status": InterfaceStatus.UP.value,
        "bgp_status": RoutingProtocolStatus.ESTABLISHED.value,
        "ospf_status": RoutingProtocolStatus.ESTABLISHED.value,
        "temperature": round(random.gauss(35, 2), 1),
        "availability_percent": 100.0,
    }


def _apply_failure_scenario(record: dict, device: Device, hour_index: int, scenario: str) -> dict:
    """Mutate a baseline record according to a failure scenario. """
    # hour_index is 0..2159 for 90 days * 24h
    # Define deterioration windows: 7 days before failure (168h)
    # We will start degradation at hour_index == failure_start - 168
    # For simplicity, this function assumes we already are in the degradation window.
    if scenario == "interface_degradation":
        # Gradual increase in interface flaps and eventual status down
        base = max(0, (hour_index % 168) - 100)  # start worsening after ~100h before failure
        record["interface_flaps"] = min(20, record["interface_flaps"] + base // 10)
        if hour_index % 24 == 0:  # every day, possibly flip status
            record["interface_status"] = InterfaceStatus.DEGRADED.value
        if hour_index % 1 == 0 and hour_index > 150:
            record["interface_status"] = InterfaceStatus.DOWN.value
    elif scenario == "cpu_overload":
        record["cpu_utilization"] = min(100, record["cpu_utilization"] + random.uniform(20, 40))
        if record["cpu_utilization"] > 90:
            record["availability_percent"] = max(0, record["availability_percent"] - random.uniform(5, 15))
    elif scenario == "memory_pressure":
        record["memory_utilization"] = min(100, record["memory_utilization"] + random.uniform(20, 35))
    elif scenario == "routing_instability":
        # Flap BGP/OSPF status
        if random.random() < 0.3:
            record["bgp_status"] = random.choice([RoutingProtocolStatus.FLOP.value, RoutingProtocolStatus.DOWN.value])
        if random.random() < 0.3:
            record["ospf_status"] = random.choice([RoutingProtocolStatus.FLOP.value, RoutingProtocolStatus.DOWN.value])
    elif scenario == "wan_degradation":
        record["latency_ms"] = min(500, record["latency_ms"] + random.uniform(10, 100))
        record["packet_loss_percent"] = min(100, record["packet_loss_percent"] + random.uniform(1, 5))
    elif scenario == "device_unreachable":
        # Zero availability and high packet loss
        record["availability_percent"] = 0.0
        record["packet_loss_percent"] = 100.0
        record["interface_status"] = InterfaceStatus.DOWN.value
        record["bgp_status"] = RoutingProtocolStatus.DOWN.value
        record["ospf_status"] = RoutingProtocolStatus.DOWN.value
    return record


def generate_telemetry(
    devices: list[Device],
    start_datetime: datetime = datetime(2023, 1, 1, tzinfo=UTC),
    hours: int = 90 * 24,
    failure_rate: float = 0.05,
    random_seed: int = 42,
) -> list[TelemetryRecord]:
    """Generate telemetry for the given devices.

    Args:
        devices: List of Device models.
        start_datetime: UTC start timestamp.
        hours: Number of hourly records per device.
        failure_rate: Proportion of devices that will experience each failure scenario.
        random_seed: Seed for reproducibility.
    """
    random.seed(random_seed)
    telemetry: list[TelemetryRecord] = []

    # Determine which devices get which scenario (could be overlapping for realism)
    scenario_names = [
        "interface_degradation",
        "cpu_overload",
        "memory_pressure",
        "routing_instability",
        "wan_degradation",
        "device_unreachable",
    ]
    device_scenarios: dict[str, list[str]] = {}
    for dev in devices:
        assigned = []
        for scen in scenario_names:
            if random.random() < failure_rate:
                assigned.append(scen)
        device_scenarios[dev.device_id] = assigned

    for dev in devices:
        for h in range(hours):
            ts = start_datetime + timedelta(hours=h)
            record_dict = _baseline_telemetry(dev, ts)
            # Apply any scenarios assigned to this device
            for scen in device_scenarios[dev.device_id]:
                # Determine if we are within degradation window (last 7 days before failure)
                # Choose a random failure hour per device per scenario
                # For simplicity, we schedule a single failure hour at a random point
                failure_hour = random.randint(7 * 24, hours - 1)  # ensure at least 7 days before end
                if h >= failure_hour - 7 * 24:
                    record_dict = _apply_failure_scenario(record_dict, dev, h - (failure_hour - 7 * 24), scen)
                if h == failure_hour:
                    # At exact failure hour, make the condition severe
                    record_dict = _apply_failure_scenario(record_dict, dev, 7 * 24, scen)
            try:
                telemetry.append(TelemetryRecord(**record_dict))
            except ValidationError as exc:
                # In case of unexpected values, log and skip
                print(f"Validation error for device {dev.device_id} at {ts}: {exc}")
    return telemetry


def write_telemetry_csv(telemetry: list[TelemetryRecord], output_path: Path) -> None:
    """Write telemetry records to a CSV file matching the TelemetryRecord fields."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=TelemetryRecord.__fields__.keys())
        writer.writeheader()
        for rec in telemetry:
            writer.writerow(rec.dict())


if __name__ == "__main__":
    devices_path = Path(__file__).parents[2] / "data" / "synthetic" / "devices.csv"
    devices = _load_devices(devices_path)
    telemetry = generate_telemetry(devices)
    out_path = Path(__file__).parents[2] / "data" / "synthetic" / "telemetry.csv"
    write_telemetry_csv(telemetry, out_path)
    print(f"Generated {len(telemetry)} telemetry rows to {out_path}")
