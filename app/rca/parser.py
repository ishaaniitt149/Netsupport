"""Cisco RCA output deterministic parser."""

import re
from pathlib import Path

import pandas as pd
from pydantic import BaseModel


class ParsedDiagnostic(BaseModel):
    """Parsed diagnostic output from Cisco RCA text."""
    rca_file_id: str
    raw_command_output: str

    cpu_utilization: float | None = None
    memory_utilization: float | None = None
    packet_loss: float | None = None
    crc_errors: int | None = None
    input_errors: int | None = None
    output_errors: int | None = None
    interface_flaps: int | None = None
    interface_status: str | None = None
    bgp_status: str | None = None
    ospf_status: str | None = None
    temperature: float | None = None
    relevant_logs: str | None = None


class CiscoRCAParser:
    """Deterministic regex-based parser for Cisco RCA emails."""

    def parse(self, rca_file_id: str, raw_text: str) -> ParsedDiagnostic:
        result = ParsedDiagnostic(
            rca_file_id=rca_file_id,
            raw_command_output=raw_text
        )

        # Parse CPU
        m_cpu = re.search(r"CPU utilization:\s*([\d\.]+)%", raw_text, re.IGNORECASE)
        if m_cpu:
            result.cpu_utilization = float(m_cpu.group(1))

        # Parse Memory
        m_mem = re.search(r"Memory utilization:\s*([\d\.]+)%", raw_text, re.IGNORECASE)
        if m_mem:
            result.memory_utilization = float(m_mem.group(1))

        # Parse Interfaces
        # We assume the first block showing "Interface is [STATUS]" and counters
        m_status = re.search(r"Interface is\s+(\w+)", raw_text)
        if m_status:
            result.interface_status = m_status.group(1).upper()

        m_crc = re.search(r"CRC errors:\s*(\d+)", raw_text, re.IGNORECASE)
        if m_crc:
            result.crc_errors = int(m_crc.group(1))

        m_in = re.search(r"Input errors:\s*(\d+)", raw_text, re.IGNORECASE)
        if m_in:
            result.input_errors = int(m_in.group(1))

        m_out = re.search(r"Output errors:\s*(\d+)", raw_text, re.IGNORECASE)
        if m_out:
            result.output_errors = int(m_out.group(1))

        m_flaps = re.search(r"Interface flaps:\s*(\d+)", raw_text, re.IGNORECASE)
        if m_flaps:
            result.interface_flaps = int(m_flaps.group(1))

        m_pkt_loss = re.search(r"packet loss[\s:]*([\d\.]+)%", raw_text, re.IGNORECASE)
        if m_pkt_loss:
            result.packet_loss = float(m_pkt_loss.group(1))

        # Temperature
        m_temp = re.search(r"Temperature:\s*([\d\.]+)C", raw_text, re.IGNORECASE)
        if m_temp:
            result.temperature = float(m_temp.group(1))

        # BGP Status (simple heuristic: look for State/PfxRcd column value in summary)
        if ">> show ip bgp summary" in raw_text:
            # Finding a line that starts with an IP and ends with a state or number
            bgp_block = re.search(r">> show ip bgp summary(.*?)(>>|\Z)", raw_text, re.DOTALL)
            if bgp_block:
                block_str = bgp_block.group(1)
                # Matches simple lines like: 10.0.0.2  4  65001  ...  1 or Idle/Active
                m_bgp_line = re.search(r"^\s*(?:\d{1,3}\.){3}\d{1,3}.*?\s+(\w+|\d+)\s*$", block_str, re.MULTILINE)
                if m_bgp_line:
                    state_val = m_bgp_line.group(1)
                    if state_val.isdigit():
                        result.bgp_status = "ESTABLISHED"
                    else:
                        result.bgp_status = state_val.upper()

        # OSPF Status (look for FULL, 2-WAY, INIT, DOWN)
        if ">> show ip ospf neighbor" in raw_text:
            ospf_block = re.search(r">> show ip ospf neighbor(.*?)(>>|\Z)", raw_text, re.DOTALL)
            if ospf_block:
                block_str = ospf_block.group(1)
                m_ospf = re.search(r"\b(FULL|2-WAY|INIT|DOWN)\b", block_str, re.IGNORECASE)
                if m_ospf:
                    result.ospf_status = m_ospf.group(1).upper()

        # Logs
        if ">> show logging" in raw_text:
            log_block = re.search(r">> show logging\s*\n(.*?)(>>|\Z)", raw_text, re.DOTALL)
            if log_block:
                result.relevant_logs = log_block.group(1).strip()

        return result


def process_directory(rca_dir: Path, output_parquet: Path):
    parser = CiscoRCAParser()
    parsed_results: list[dict] = []

    if rca_dir.exists():
        for rca_file in rca_dir.glob("*_rca.txt"):
            raw_text = rca_file.read_text(encoding="utf-8")
            parsed = parser.parse(rca_file.name, raw_text)
            parsed_results.append(parsed.model_dump())

    if parsed_results:
        df = pd.DataFrame(parsed_results)
        output_parquet.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_parquet, engine="pyarrow")
        print(f"Processed {len(parsed_results)} RCA files into {output_parquet}")
    else:
        print("No RCA files found.")


if __name__ == "__main__":
    base_dir = Path(__file__).parents[2]
    rca_dir = base_dir / "data" / "synthetic" / "rca_emails"
    out_parquet = base_dir / "data" / "processed" / "diagnostics.parquet"

    process_directory(rca_dir, out_parquet)
