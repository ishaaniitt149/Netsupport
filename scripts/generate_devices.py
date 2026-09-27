# Device Generator
"""Generate synthetic Cisco-like device inventory and write to CSV.

The generator is deterministic – you can control the number of devices,
random seed and the start date for the "last_patch_date" field.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker
from pydantic import ValidationError

from app.models.device import DeviceRecord


def _random_firmware() -> str:
    """Return a Cisco‑style firmware version string.
    For simplicity we mimic Cisco IOS like ``15.2(3)E6``.
    """
    major = random.randint(12, 16)
    minor = random.randint(0, 4)
    build = random.randint(0, 9)
    suffix_letter = random.choice(["A", "B", "C", "D", "E"])
    suffix_num = random.randint(0, 20)
    return f"{major}.{minor}({build}){suffix_letter}{suffix_num}"


def _random_serial() -> str:
    # 10‑12 alphanumeric characters
    return "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=12))


def generate_devices(
    number_of_devices: int = 100,
    random_seed: int = 42,
    start_date: date = date(2023, 1, 1),
) -> list[DeviceRecord]:
    random.seed(random_seed)
    fake = Faker()
    Faker.seed(random_seed)

    devices: list[DeviceRecord] = []
    device_types = ["router", "switch", "firewall", "wireless"]
    for i in range(number_of_devices):
        vendor = "Cisco"
        device_type = random.choice(device_types)
        criticality = random.choices(
            population=["HIGH", "MEDIUM", "LOW"],
            weights=[0.2, 0.5, 0.3],
        )[0]
        hostname = f"{fake.city().replace(' ', '')[:5].lower()}-{device_type[:3]}-{i+1:04d}"
        device = DeviceRecord(
            device_id=f"dev-{i+1:04d}",
            hostname=hostname,
            vendor=vendor,
            model=f"{vendor[:3].upper()}-{random.randint(1000,9999)}",
            serial_number=_random_serial(),
            firmware_version=_random_firmware(),
            location=fake.street_address(),
            region=random.choice(["us-east-1", "us-west-2", "eu-central-1", "ap-south-1"]),
            device_type=device_type,
            criticality=criticality,
            interface_count=random.randint(2, 64),
            last_patch_date=start_date + timedelta(days=random.randint(0, 365 * 3)),
            customer=f"Acme-{random.randint(1, 99)}",
            network_segment=f"10.{random.randint(0,255)}.{random.randint(0,255)}.0/24",
        )
        devices.append(device)
    return devices


def write_devices_csv(devices: list[DeviceRecord], output_path: Path) -> None:
    """Write a list of DeviceRecord models to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as csvfile:
        fieldnames = list(DeviceRecord.model_fields.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for dev in devices:
            writer.writerow(dev.model_dump())


if __name__ == "__main__":
    devs = generate_devices()
    try:
        # Validate all devices (pydantic does this on creation)
        pass
    except ValidationError as exc:
        print("Validation error while generating devices:", exc)
        raise
    write_devices_csv(devs, Path(__file__).parents[2] / "data" / "synthetic" / "devices.csv")
    print(f"Generated {len(devs)} devices to data/synthetic/devices.csv")
