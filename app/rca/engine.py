"""Explainable Deterministic RCA Engine."""


from pydantic import BaseModel

from app.core.config import get_settings
from app.rca.parser import ParsedDiagnostic


class RCAResult(BaseModel):
    """Result from the deterministic RCA engine."""
    incident_id: str
    probable_rca: str
    confidence: float
    evidence: dict[str, str]
    rule_id: str
    recommended_checks: list[str]


class DeterministicRCAEngine:
    """Evaluates parsed diagnostic telemetry against deterministic RCA rules."""

    def __init__(self):
        self.settings = get_settings()

    def evaluate(self, incident_id: str, diag: ParsedDiagnostic) -> RCAResult | None:
        """
        Evaluate the parsed diagnostics and return an RCA result if a rule matches.
        Rules are evaluated in order of priority.
        """

        # Rule 6: Device unreachable
        if diag.interface_status == "DOWN" and diag.packet_loss == 100.0:
            return RCAResult(
                incident_id=incident_id,
                probable_rca="Device unreachable",
                confidence=0.95,
                evidence={
                    "interface_status": str(diag.interface_status),
                    "packet_loss": f"{diag.packet_loss}%"
                },
                rule_id="RULE-006-DEVICE-UNREACHABLE",
                recommended_checks=["Verify power status", "Check upstream switch port", "Verify physical cabling"]
            )

        # Rule 3: Memory pressure
        if diag.memory_utilization is not None and diag.memory_utilization > self.settings.memory_critical_pct:
            return RCAResult(
                incident_id=incident_id,
                probable_rca="Memory pressure",
                confidence=0.9,
                evidence={
                    "memory_utilization": f"{diag.memory_utilization}%"
                },
                rule_id="RULE-003-MEMORY-PRESSURE",
                recommended_checks=["Check memory leak bugs", "Review routing table size", "Check running processes"]
            )

        # Rule 2: High CPU
        if diag.cpu_utilization is not None and diag.cpu_utilization > self.settings.cpu_critical_pct:
            return RCAResult(
                incident_id=incident_id,
                probable_rca="High CPU",
                confidence=0.9,
                evidence={
                    "cpu_utilization": f"{diag.cpu_utilization}%"
                },
                rule_id="RULE-002-HIGH-CPU",
                recommended_checks=["Check top CPU processes", "Look for control plane policing drops", "Check interrupt level"]
            )

        # Rule 4: Routing instability
        if diag.bgp_status in ("IDLE", "ACTIVE", "DOWN") or diag.ospf_status in ("INIT", "DOWN"):
            evidence = {}
            if diag.bgp_status:
                evidence["bgp_status"] = str(diag.bgp_status)
            if diag.ospf_status:
                evidence["ospf_status"] = str(diag.ospf_status)

            return RCAResult(
                incident_id=incident_id,
                probable_rca="Routing instability",
                confidence=0.85,
                evidence=evidence,
                rule_id="RULE-004-ROUTING-INSTABILITY",
                recommended_checks=["Check route flaps", "Verify neighbor IP reachability", "Check routing logs"]
            )

        # Rule 1: Interface degradation
        if (diag.crc_errors is not None and diag.crc_errors > self.settings.crc_error_spike_threshold and
            diag.interface_flaps is not None and diag.interface_flaps > self.settings.interface_flaps_threshold):

            # Additional check: shouldn't be high CPU, and BGP should be established (or missing but not down)
            cpu_ok = diag.cpu_utilization is None or diag.cpu_utilization < self.settings.cpu_critical_pct
            bgp_ok = diag.bgp_status in (None, "ESTABLISHED")

            if cpu_ok and bgp_ok:
                evidence = {
                    "crc_errors": str(diag.crc_errors),
                    "interface_flaps": str(diag.interface_flaps)
                }
                if diag.cpu_utilization is not None:
                    evidence["cpu_utilization"] = f"{diag.cpu_utilization}%"
                if diag.bgp_status is not None:
                    evidence["bgp_status"] = str(diag.bgp_status)

                return RCAResult(
                    incident_id=incident_id,
                    probable_rca="Interface degradation",
                    confidence=0.88,
                    evidence=evidence,
                    rule_id="RULE-001-INTERFACE-DEGRADATION",
                    recommended_checks=["Clean fiber optics", "Replace SFP module", "Check patch cable"]
                )

        # Rule 5: WAN degradation
        if (diag.packet_loss is not None and diag.packet_loss > self.settings.packet_loss_critical_pct and
            diag.interface_status == "DEGRADED"):

            return RCAResult(
                incident_id=incident_id,
                probable_rca="WAN degradation",
                confidence=0.85,
                evidence={
                    "packet_loss": f"{diag.packet_loss}%",
                    "interface_status": str(diag.interface_status)
                },
                rule_id="RULE-005-WAN-DEGRADATION",
                recommended_checks=["Open ticket with ISP", "Check QoS drops", "Verify shaping rate"]
            )

        # Default fallback if no rules match
        return None
