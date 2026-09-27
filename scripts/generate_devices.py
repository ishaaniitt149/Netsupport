#!/usr/bin/env python3
"""CLI script to generate synthetic Cisco device inventory CSV."""

import argparse
import sys
from datetime import date
from pathlib import Path

from simulator.device_generator import CiscoDeviceGenerator, DeviceGeneratorConfig


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic Cisco network devices dataset."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of devices to generate (default: 100)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed (default: 42)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2026-01-01",
        help="Reference start date YYYY-MM-DD (default: 2026-01-01)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/synthetic/devices.csv",
        help="Target CSV output path (default: data/synthetic/devices.csv)",
    )

    args = parser.parse_args()

    try:
        start_d = date.fromisoformat(args.start_date)
    except ValueError:
        print(f"Error: Invalid date format for --start-date: {args.start_date}", file=sys.stderr)
        sys.exit(1)

    config = DeviceGeneratorConfig(
        number_of_devices=args.count,
        random_seed=args.seed,
        start_date=start_d,
    )

    generator = CiscoDeviceGenerator(config)
    output_path = Path(args.output)
    print(f"Generating {args.count} synthetic Cisco devices (Seed: {args.seed})...")
    saved_path = generator.generate_csv(output_path)

    devices = generator.generate()
    report = generator.validate_dataset(devices)

    if not report.is_valid:
        print(f"Validation FAILED with {len(report.errors)} errors:", file=sys.stderr)
        for err in report.errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print(f"Success! {len(devices)} devices generated and validated.")
    print(f"CSV file written to: {saved_path.resolve()}")
    print(f"Unique Device IDs: {report.unique_device_ids}")
    print(f"Unique Hostnames:  {report.unique_hostnames}")
    print(f"Unique Serials:    {report.unique_serials}")


if __name__ == "__main__":
    main()
