"""Synthetic Network Telemetry Generator.

Generates realistic, temporal, multi-variate telemetry time-series for Cisco
network devices over a configurable window (e.g., 90 days hourly = 2,160 steps).

Incorporates realistic baseline diurnal cycles and 6 progressive failure
scenarios exhibiting gradual deterioration prior to failure (critical for
predictive maintenance ML).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

import numpy as np
import pandas as pd


class FailureScenarioType(StrEnum):
    NORMAL = "normal"
    INTERFACE_DEGRADATION = "interface_degradation"
    CPU_OVERLOAD = "cpu_overload"
    MEMORY_PRESSURE = "memory_pressure"
    ROUTING_INSTABILITY = "routing_instability"
    WAN_DEGRADATION = "wan_degradation"
    DEVICE_UNREACHABLE = "device_unreachable"


@dataclass
class TelemetryGeneratorConfig:
    """Configuration for synthetic telemetry generation."""

    days: int = 90
    interval_hours: int = 1
    start_timestamp: datetime = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    random_seed: int = 42
    # Incidents occur on day incident_day (e.g., day 80 of 90)
    incident_day: int = 80
    deterioration_lead_days: int = 7


# Specific device mappings for the 6 failure scenarios (deterministic)
SCENARIO_DEVICE_MAP: dict[str, FailureScenarioType] = {
    "DEV-CSCO-0001": FailureScenarioType.INTERFACE_DEGRADATION,
    "DEV-CSCO-0007": FailureScenarioType.INTERFACE_DEGRADATION,
    "DEV-CSCO-0002": FailureScenarioType.CPU_OVERLOAD,
    "DEV-CSCO-0010": FailureScenarioType.CPU_OVERLOAD,
    "DEV-CSCO-0003": FailureScenarioType.MEMORY_PRESSURE,
    "DEV-CSCO-0016": FailureScenarioType.MEMORY_PRESSURE,
    "DEV-CSCO-0004": FailureScenarioType.ROUTING_INSTABILITY,
    "DEV-CSCO-0014": FailureScenarioType.ROUTING_INSTABILITY,
    "DEV-CSCO-0005": FailureScenarioType.WAN_DEGRADATION,
    "DEV-CSCO-0019": FailureScenarioType.WAN_DEGRADATION,
    "DEV-CSCO-0008": FailureScenarioType.DEVICE_UNREACHABLE,
    "DEV-CSCO-0020": FailureScenarioType.DEVICE_UNREACHABLE,
}


class NetworkTelemetryGenerator:
    """Generates 90-day hourly synthetic network telemetry with realistic temporal deterioration."""

    def __init__(self, config: TelemetryGeneratorConfig | None = None) -> None:
        self.config = config or TelemetryGeneratorConfig()
        self.total_hours = self.config.days * 24
        self.incident_hour = self.config.incident_day * 24
        self.deterioration_start_hour = (
            self.config.incident_day - self.config.deterioration_lead_days
        ) * 24

    def generate_for_devices(self, device_ids: list[str]) -> pd.DataFrame:
        """Generate complete telemetry DataFrame for all provided device IDs."""
        # Pre-compute time index
        timestamps = [
            self.config.start_timestamp + timedelta(hours=h) for h in range(self.total_hours)
        ]
        hours_of_day = np.array([ts.hour for ts in timestamps])
        day_indices = np.array([h // 24 for h in range(self.total_hours)])

        # Diurnal curve: peaks at 14:00-15:00 UTC, troughs at 03:00 UTC
        diurnal_factor = np.sin((hours_of_day - 6) * np.pi / 12.0)

        frames: list[pd.DataFrame] = []

        for dev_id in device_ids:
            scenario = SCENARIO_DEVICE_MAP.get(dev_id, FailureScenarioType.NORMAL)
            dev_seed = (
                self.config.random_seed
                + int(dev_id.split("-")[-1])
                if dev_id.startswith("DEV-CSCO-")
                else self.config.random_seed
            )
            dev_rng = np.random.default_rng(dev_seed)

            df_dev = self._generate_device_series(
                device_id=dev_id,
                scenario=scenario,
                timestamps=timestamps,
                hours_of_day=hours_of_day,
                day_indices=day_indices,
                diurnal_factor=diurnal_factor,
                rng=dev_rng,
            )
            frames.append(df_dev)

        full_df = pd.concat(frames, ignore_index=True)
        return full_df

    def _generate_device_series(
        self,
        device_id: str,
        scenario: FailureScenarioType,
        timestamps: list[datetime],
        hours_of_day: np.ndarray,
        day_indices: np.ndarray,
        diurnal_factor: np.ndarray,
        rng: np.random.Generator,
    ) -> pd.DataFrame:
        """Generate temporal telemetry series for an individual device."""
        n = self.total_hours

        # Baseline healthy telemetry with diurnal oscillations
        base_cpu = 22.0 + (8.0 * diurnal_factor) + rng.normal(0, 1.5, n)
        base_mem = 40.0 + (2.0 * diurnal_factor) + rng.normal(0, 0.5, n)
        base_latency = 4.0 + (1.2 * diurnal_factor) + rng.normal(0, 0.3, n)
        base_packet_loss = np.clip(rng.exponential(0.01, n), 0.0, 0.05)
        base_temp = 36.0 + (3.0 * diurnal_factor) + rng.normal(0, 0.4, n)

        # Baseline counters
        crc_errors = np.zeros(n, dtype=np.int64)
        input_errors = np.zeros(n, dtype=np.int64)
        output_errors = np.zeros(n, dtype=np.int64)
        interface_flaps = np.zeros(n, dtype=np.int64)
        interface_status = ["UP"] * n
        bgp_status = ["ESTABLISHED"] * n
        ospf_status = ["FULL"] * n
        availability = np.full(n, 100.0, dtype=np.float64)

        # Apply specific failure scenario profiles
        if scenario == FailureScenarioType.INTERFACE_DEGRADATION:
            self._apply_interface_degradation(
                n, crc_errors, input_errors, base_packet_loss, interface_flaps, interface_status, rng
            )

        elif scenario == FailureScenarioType.CPU_OVERLOAD:
            self._apply_cpu_overload(
                n, base_cpu, base_latency, base_packet_loss, base_temp, rng
            )

        elif scenario == FailureScenarioType.MEMORY_PRESSURE:
            self._apply_memory_pressure(
                n, base_mem, output_errors, base_packet_loss, availability, interface_status, rng
            )

        elif scenario == FailureScenarioType.ROUTING_INSTABILITY:
            self._apply_routing_instability(
                n, base_latency, base_packet_loss, bgp_status, ospf_status, rng
            )

        elif scenario == FailureScenarioType.WAN_DEGRADATION:
            self._apply_wan_degradation(
                n, base_latency, base_packet_loss, interface_status, rng
            )

        elif scenario == FailureScenarioType.DEVICE_UNREACHABLE:
            self._apply_device_unreachable(
                n, base_temp, base_packet_loss, availability, interface_status, rng
            )

        # Enforce realistic bounds across all metrics
        cpu_util = np.clip(np.round(base_cpu, 2), 0.0, 100.0)
        mem_util = np.clip(np.round(base_mem, 2), 0.0, 100.0)
        latency = np.clip(np.round(base_latency, 2), 0.1, 2000.0)
        pkt_loss = np.clip(np.round(base_packet_loss, 2), 0.0, 100.0)
        temp = np.clip(np.round(base_temp, 1), 15.0, 120.0)
        avail = np.clip(np.round(availability, 2), 0.0, 100.0)

        df = pd.DataFrame(
            {
                "timestamp": [ts.isoformat() for ts in timestamps],
                "device_id": device_id,
                "cpu_utilization": cpu_util,
                "memory_utilization": mem_util,
                "latency_ms": latency,
                "packet_loss_percent": pkt_loss,
                "crc_errors": crc_errors,
                "input_errors": input_errors,
                "output_errors": output_errors,
                "interface_flaps": interface_flaps,
                "interface_status": interface_status,
                "bgp_status": bgp_status,
                "ospf_status": ospf_status,
                "temperature": temp,
                "availability_percent": avail,
            }
        )
        return df

    def _apply_interface_degradation(
        self,
        n: int,
        crc_errors: np.ndarray,
        input_errors: np.ndarray,
        packet_loss: np.ndarray,
        interface_flaps: np.ndarray,
        interface_status: list[str],
        rng: np.random.Generator,
    ) -> None:
        """Scenario 1: SFP Laser / Optical Patch cable degradation.

        Deterioration:
        - Day -5: slight packet loss (0.2-0.8%)
        - Day -3: CRC errors start accumulating (+10-40/hr)
        - Day -2: Flapping starts (1-3 flaps/hr), interface DEGRADED
        - Day -1: High packet loss (8-20%), heavy CRC (>100/hr)
        - Day 0: Interface drops DOWN completely
        """
        h_inc = self.incident_hour
        h_start = self.deterioration_start_hour

        cum_crc = 0
        cum_in_err = 0

        for h in range(h_start, n):
            hours_to_inc = h_inc - h
            days_to_inc = hours_to_inc / 24.0

            if days_to_inc > 5:
                # Day -7 to -5: baseline
                pass
            elif 3 < days_to_inc <= 5:
                # Day -5: slight loss
                packet_loss[h] = rng.uniform(0.2, 0.8)
                cum_crc += rng.integers(1, 4)
            elif 2 < days_to_inc <= 3:
                # Day -3: CRC errors climbing
                packet_loss[h] = rng.uniform(1.0, 3.0)
                cum_crc += rng.integers(15, 45)
                cum_in_err += rng.integers(20, 60)
            elif 1 < days_to_inc <= 2:
                # Day -2: Flapping and degraded state
                packet_loss[h] = rng.uniform(3.0, 7.5)
                cum_crc += rng.integers(50, 120)
                cum_in_err += rng.integers(60, 150)
                interface_flaps[h] = rng.integers(1, 4)
                interface_status[h] = "DEGRADED"
            elif 0 < days_to_inc <= 1:
                # Day -1: Critical degradation
                packet_loss[h] = rng.uniform(10.0, 28.0)
                cum_crc += rng.integers(150, 350)
                cum_in_err += rng.integers(180, 400)
                interface_flaps[h] = rng.integers(3, 8)
                interface_status[h] = "DEGRADED"
            elif days_to_inc <= 0 and h < h_inc + 24:
                # Day 0: Failure window (outage)
                packet_loss[h] = 100.0
                interface_status[h] = "DOWN"
                interface_flaps[h] = rng.integers(5, 12)
            else:
                # Post-incident recovery (maintenance applied)
                packet_loss[h] = rng.uniform(0.0, 0.04)
                interface_status[h] = "UP"

            crc_errors[h] = cum_crc
            input_errors[h] = cum_in_err

    def _apply_cpu_overload(
        self,
        n: int,
        cpu: np.ndarray,
        latency: np.ndarray,
        packet_loss: np.ndarray,
        temp: np.ndarray,
        rng: np.random.Generator,
    ) -> None:
        """Scenario 2: Control plane loop / CPU overload."""
        h_inc = self.incident_hour
        h_start = self.deterioration_start_hour

        for h in range(h_start, n):
            hours_to_inc = h_inc - h
            days_to_inc = hours_to_inc / 24.0

            if 3 < days_to_inc <= 5:
                # Day -5 to -4: CPU drifting to 55-65%
                cpu[h] = rng.uniform(55.0, 68.0)
                latency[h] += rng.uniform(8.0, 15.0)
            elif 1 < days_to_inc <= 3:
                # Day -3 to -2: CPU reaches 75-88%
                cpu[h] = rng.uniform(75.0, 88.0)
                latency[h] += rng.uniform(25.0, 60.0)
                packet_loss[h] = rng.uniform(1.5, 4.5)
                temp[h] += 4.0
            elif 0 < days_to_inc <= 1:
                # Day -1: Near 100% saturation
                cpu[h] = rng.uniform(92.0, 98.5)
                latency[h] += rng.uniform(80.0, 220.0)
                packet_loss[h] = rng.uniform(8.0, 22.0)
                temp[h] += 8.0
            elif days_to_inc <= 0 and h < h_inc + 12:
                # Day 0: 100% pegged, control plane drop
                cpu[h] = 100.0
                latency[h] = rng.uniform(350.0, 800.0)
                packet_loss[h] = rng.uniform(60.0, 95.0)
                temp[h] += 12.0

    def _apply_memory_pressure(
        self,
        n: int,
        mem: np.ndarray,
        output_errors: np.ndarray,
        packet_loss: np.ndarray,
        availability: np.ndarray,
        interface_status: list[str],
        rng: np.random.Generator,
    ) -> None:
        """Scenario 3: Monotonic memory leak leading to crash."""
        h_inc = self.incident_hour
        leak_start_hour = max(0, h_inc - (14 * 24))  # 14-day progressive leak

        for h in range(leak_start_hour, n):
            hours_since_leak = h - leak_start_hour
            hours_to_inc = h_inc - h

            if hours_to_inc > 0:
                # Steady monotonic growth from 45% to ~98%
                leak_fraction = min(1.0, hours_since_leak / (14 * 24))
                mem[h] = 45.0 + (53.0 * leak_fraction) + rng.normal(0, 0.2)

                if hours_to_inc <= 48:
                    # Day -2 to -1: Buffer allocation failures
                    output_errors[h] = rng.integers(10, 80)
                    packet_loss[h] = rng.uniform(2.0, 10.0)
            elif 0 <= (h - h_inc) < 6:
                # Day 0: Crash & reboot outage window
                availability[h] = 0.0
                packet_loss[h] = 100.0
                interface_status[h] = "DOWN"
                mem[h] = 0.0
            else:
                # Recovered after reboot: normal memory
                mem[h] = 38.0 + rng.normal(0, 1.0)

    def _apply_routing_instability(
        self,
        n: int,
        latency: np.ndarray,
        packet_loss: np.ndarray,
        bgp_status: list[str],
        ospf_status: list[str],
        rng: np.random.Generator,
    ) -> None:
        """Scenario 4: BGP / OSPF routing flaps."""
        h_inc = self.incident_hour
        h_start = self.deterioration_start_hour

        for h in range(h_start, n):
            hours_to_inc = h_inc - h
            days_to_inc = hours_to_inc / 24.0

            if 2 < days_to_inc <= 5:
                # Day -5 to -3: Occasional route flaps
                if rng.random() < 0.25:
                    bgp_status[h] = "ACTIVE"
                    ospf_status[h] = "INIT"
                    packet_loss[h] = rng.uniform(2.0, 6.0)
                    latency[h] += rng.uniform(15.0, 40.0)
            elif 0 < days_to_inc <= 2:
                # Day -2 to -1: Frequent flaps
                if rng.random() < 0.6:
                    bgp_status[h] = rng.choice(["ACTIVE", "IDLE"])
                    ospf_status[h] = "2-WAY"
                    packet_loss[h] = rng.uniform(10.0, 30.0)
                    latency[h] += rng.uniform(40.0, 120.0)
            elif days_to_inc <= 0 and h < h_inc + 18:
                # Day 0: Complete session teardown
                bgp_status[h] = "DOWN"
                ospf_status[h] = "DOWN"
                packet_loss[h] = 100.0

    def _apply_wan_degradation(
        self,
        n: int,
        latency: np.ndarray,
        packet_loss: np.ndarray,
        interface_status: list[str],
        rng: np.random.Generator,
    ) -> None:
        """Scenario 5: Transit carrier degradation / severe jitter and delay."""
        h_inc = self.incident_hour
        h_start = self.deterioration_start_hour

        for h in range(h_start, n):
            hours_to_inc = h_inc - h
            days_to_inc = hours_to_inc / 24.0

            if 4 < days_to_inc <= 7:
                # Day -7 to -5: Mild latency creep
                latency[h] = 45.0 + rng.uniform(10.0, 25.0)
                packet_loss[h] = rng.uniform(0.1, 0.4)
            elif 2 < days_to_inc <= 4:
                # Day -4 to -3: Latency 90-160ms
                latency[h] = 120.0 + rng.uniform(20.0, 60.0)
                packet_loss[h] = rng.uniform(1.5, 4.0)
            elif 0 < days_to_inc <= 2:
                # Day -2 to -1: Latency 250-450ms, loss 8-20%
                latency[h] = 320.0 + rng.uniform(50.0, 150.0)
                packet_loss[h] = rng.uniform(8.0, 22.0)
                interface_status[h] = "DEGRADED"
            elif days_to_inc <= 0 and h < h_inc + 24:
                # Day 0: Circuit SLA breach / circuit loss
                latency[h] = 850.0 + rng.uniform(100.0, 300.0)
                packet_loss[h] = rng.uniform(70.0, 100.0)
                interface_status[h] = "DEGRADED"

    def _apply_device_unreachable(
        self,
        n: int,
        temp: np.ndarray,
        packet_loss: np.ndarray,
        availability: np.ndarray,
        interface_status: list[str],
        rng: np.random.Generator,
    ) -> None:
        """Scenario 6: Thermal runaway leading to thermal emergency shutdown."""
        h_inc = self.incident_hour
        h_start = max(0, h_inc - (4 * 24))  # 4-day thermal climb

        for h in range(h_start, n):
            hours_to_inc = h_inc - h
            days_to_inc = hours_to_inc / 24.0

            if 1 < days_to_inc <= 4:
                # Day -4 to -2: Thermal climb from 40°C -> 68°C
                fraction = 1.0 - (days_to_inc / 4.0)
                temp[h] = 40.0 + (30.0 * fraction) + rng.normal(0, 0.5)
            elif 0 < days_to_inc <= 1:
                # Day -1: Critical thermal alarm (78-85°C), CPU throttling
                temp[h] = rng.uniform(78.0, 85.0)
                packet_loss[h] = rng.uniform(4.0, 12.0)
            elif days_to_inc <= 0 and h < h_inc + 16:
                # Day 0: Emergency thermal shutdown
                availability[h] = 0.0
                packet_loss[h] = 100.0
                interface_status[h] = "DOWN"
                temp[h] = 25.0  # Cooling off powered down

    def save_parquet(self, df: pd.DataFrame, output_path: Path | str) -> Path:
        """Write DataFrame to Parquet format using snappy compression."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False, engine="pyarrow", compression="snappy")
        return path

    def save_sample_csv(
        self, df: pd.DataFrame, output_path: Path | str, sample_rows: int = 5000
    ) -> Path:
        """Write a representative subset to CSV for quick inspection."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        sample_df = df.head(sample_rows)
        sample_df.to_csv(path, index=False)
        return path
