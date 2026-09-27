"""Synthetic Cisco RCA Generator.

Generates realistic RCA output files (simulating a second email from SolarWinds)
for each synthetic incident found in solarwinds_events.csv.
"""

import csv
import random
from pathlib import Path


def _generate_interface_counters(scenario: str) -> str:
    if scenario == "PACKET_LOSS":
        return (
            "Interface is UP\n"
            "CRC errors: 1450\n"
            "Input errors: 1510\n"
            "Output errors: 23\n"
            "Interface flaps: 8\n"
        )
    return (
        "Interface is UP\n"
        "CRC errors: 0\n"
        "Input errors: 0\n"
        "Output errors: 0\n"
        "Interface flaps: 0\n"
    )


def _generate_cpu(scenario: str) -> str:
    if scenario == "NODE_DOWN":
        # Simulating possible CPU overload before node down
        val = random.choice([45, 95, 98, 99])
    else:
        val = random.randint(15, 45)
    return f"CPU utilization: {val}%\n"


def _generate_memory(scenario: str) -> str:
    if scenario == "NODE_DOWN":
        val = random.choice([51, 95, 99])
    else:
        val = random.randint(30, 60)
    return f"Memory utilization: {val}%\n"


def generate_rca_text(device_id: str, scenario: str, timestamp: str) -> str:
    """Generate a realistic Cisco RCA text based on the incident scenario."""
    return f"""--------------------------------------------------
RCA Diagnostic Report for {device_id}
Generated at: {timestamp}
--------------------------------------------------

>> show interfaces Gi0/1
{_generate_interface_counters(scenario)}
>> show processes cpu
{_generate_cpu(scenario)}
>> show memory
{_generate_memory(scenario)}
>> show ip bgp summary
BGP router identifier 10.0.0.1, local AS number 65000
BGP table version is 142, main routing table version 142
1 network entries using 144 bytes of memory
1 path entries using 80 bytes of memory
1/1 BGP path/bestpath attribute entries using 144 bytes of memory
0 BGP route-map cache entries using 0 bytes of memory
0 BGP filter-list cache entries using 0 bytes of memory
BGP using 368 total bytes of memory
BGP activity 1/0 prefixes, 1/0 paths, scan interval 60 secs

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.0.2        4        65001    1434    1435      142    0    0 23:14:02        1

>> show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
192.168.1.2       1   FULL/BDR        00:00:32    10.1.1.2        GigabitEthernet0/1

>> show logging
Syslog logging: enabled
    Console logging: level debugging, 120 messages logged, xml disabled
    Monitor logging: level debugging, 0 messages logged, xml disabled
    Buffer logging:  level debugging, 120 messages logged, xml disabled
    Exception Logging: size (4096 bytes)
    Count and timestamp logging messages: disabled

>> show interfaces status
Port      Name               Status       Vlan       Duplex  Speed Type
Gi0/1     Uplink             connected    trunk      a-full a-1000 1000BaseTX
Gi0/2                        notconnect   1          auto   auto   10/100/1000BaseTX
"""


def load_events(csv_path: Path) -> list[dict[str, str]]:
    events = []
    if not csv_path.exists():
        return events
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append(row)
    return events


def extract_incidents(events: list[dict[str, str]]) -> list[dict[str, str]]:
    """Group events by device to find Alert-Recovery pairs."""
    incidents = []
    device_events: dict[str, list[dict[str, str]]] = {}

    for event in events:
        d_id = event["device_id"]
        if d_id not in device_events:
            device_events[d_id] = []
        device_events[d_id].append(event)

    for d_id, evs in device_events.items():
        # Sort by timestamp
        evs.sort(key=lambda x: x["timestamp"])

        # Simple finite state machine to pair alerts and recoveries
        current_alert = None
        for ev in evs:
            etype = ev["event_type"]
            if etype in ("NODE_DOWN", "PACKET_LOSS"):
                if current_alert is None:
                    current_alert = ev
            elif etype in ("NODE_UP", "RECOVERY"):
                if current_alert is not None:
                    inc_id = f"INC-{random.randint(10000, 99999)}"
                    incidents.append({
                        "incident_id": inc_id,
                        "device_id": d_id,
                        "alert_event_id": current_alert["event_id"],
                        "recovery_event_id": ev["event_id"],
                        "scenario": current_alert["event_type"],
                        "timestamp": ev["timestamp"] # RCA runs when device comes back up
                    })
                    current_alert = None

    return incidents


def generate_rcas(events_csv: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    events = load_events(events_csv)
    incidents = extract_incidents(events)

    metadata = []

    for inc in incidents:
        rca_filename = f"{inc['incident_id']}_rca.txt"
        rca_path = out_dir / rca_filename

        rca_text = generate_rca_text(inc["device_id"], inc["scenario"], inc["timestamp"])
        rca_path.write_text(rca_text, encoding="utf-8")

        metadata.append({
            "incident_id": inc["incident_id"],
            "device_id": inc["device_id"],
            "rca_file": rca_filename,
            "alert_event_id": inc["alert_event_id"],
            "recovery_event_id": inc["recovery_event_id"]
        })

    # Write metadata
    meta_path = out_dir / "metadata.csv"
    if metadata:
        with meta_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(metadata[0].keys()))
            writer.writeheader()
            for m in metadata:
                writer.writerow(m)

    return len(metadata)


if __name__ == "__main__":
    events_csv = Path(__file__).parents[1] / "data" / "synthetic" / "solarwinds_events.csv"
    rca_dir = Path(__file__).parents[1] / "data" / "synthetic" / "rca_emails"

    num = generate_rcas(events_csv, rca_dir)
    print(f"Generated {num} RCA emails in {rca_dir}")
