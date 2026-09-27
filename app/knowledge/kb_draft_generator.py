"""KB draft generator.

Builds a structured ``KBArticle`` draft from an incident, its RCA result and
resolution record.  Draft content is deterministic — it is derived solely from
observed evidence; nothing is invented.

The draft is always created in ``DRAFT`` status and must go through the
``submit_for_review`` → ``approve`` workflow before being treated as authoritative.
"""

from __future__ import annotations

from app.knowledge.kb_store import KBStore
from app.models.kb_article import KBArticle
from app.models.resolution import Resolution
from app.rca.engine import RCAResult

# ---------------------------------------------------------------------------
# Symptom templates keyed by probable_rca string (deterministic)
# ---------------------------------------------------------------------------

_SYMPTOM_TEMPLATES: dict[str, list[str]] = {
    "Interface degradation": [
        "CRC errors incrementing on uplink interface",
        "Interface flapping observed in syslog",
        "Packet loss increasing ahead of outage",
    ],
    "High CPU": [
        "CPU utilization above 90%",
        "Increased latency on control plane traffic",
        "High-priority process consuming excessive cycles",
    ],
    "Memory pressure": [
        "Memory utilization approaching 100%",
        "Output buffer drops increasing",
        "Packet loss observed during high traffic periods",
    ],
    "Routing instability": [
        "BGP session flapping or in non-ESTABLISHED state",
        "OSPF neighbor not in FULL state",
        "Route table churn observed",
    ],
    "WAN degradation": [
        "High latency to upstream carrier",
        "Packet loss percentage above SLA threshold",
        "Interface in DEGRADED state",
    ],
    "Device unreachable": [
        "Device not responding to ICMP or SNMP",
        "Interface in DOWN state",
        "100% packet loss observed",
    ],
}

_VALIDATION_TEMPLATES: dict[str, list[str]] = {
    "Interface degradation": [
        "Verify CRC counters clear after interface reset",
        "Run EEM/optical Rx power check on SFP",
        "Confirm zero packet loss over 15 min ping test",
    ],
    "High CPU": [
        "Confirm CPU utilization below 60% after fix",
        "Verify no high-priority process storms in 'show processes cpu'",
        "Run sustained traffic test and monitor CPU",
    ],
    "Memory pressure": [
        "Verify free memory stable for 30 mins post-patch",
        "Confirm routing table size within expected range",
        "Check for memory leak process recurrence",
    ],
    "Routing instability": [
        "Verify BGP sessions in ESTABLISHED state with correct prefix count",
        "Confirm OSPF neighbors all in FULL/DR/BDR state",
        "Validate no route flap in BGP MED history for 1 hour",
    ],
    "WAN degradation": [
        "Run iPerf3 throughput test to carrier handoff",
        "Confirm latency within contracted SLA",
        "Monitor packet loss rate for 30 mins",
    ],
    "Device unreachable": [
        "Confirm SNMP and SSH connectivity restored",
        "Verify all interfaces in UP state",
        "Run full interface and routing protocol health check",
    ],
}

_ROLLBACK_TEMPLATES: dict[str, list[str]] = {
    "Interface degradation": [
        "Re-seat original SFP if replacement causes issues",
        "Roll back any interface config changes",
    ],
    "High CPU": [
        "Revert software image if upgrade was applied",
        "Re-enable features disabled during troubleshooting",
    ],
    "Memory pressure": [
        "Roll back software patch if memory continues to grow",
        "Restore previous running config if config change was cause",
    ],
    "Routing instability": [
        "Revert route-map changes and restart BGP process",
        "Restore OSPF timers to pre-change values",
    ],
    "WAN degradation": [
        "Failover traffic to backup circuit if primary is unstable",
        "Revert QoS policy changes",
    ],
    "Device unreachable": [
        "Escalate to on-site engineer if remote reboot fails",
        "Engage hardware replacement process if power issue confirmed",
    ],
}


class KBDraftGenerator:
    """Generates deterministic KB article drafts from incident artefacts."""

    def __init__(self, store: KBStore):
        self.store = store

    def generate_draft(
        self,
        *,
        rca_result: RCAResult,
        resolution: Resolution | None = None,
        created_by: str = "NOIPMP-System",
    ) -> KBArticle:
        """Build and persist a DRAFT KB article.

        Args:
            rca_result: Output from the deterministic RCA engine.
            resolution: Optional engineer resolution record.
            created_by: System or engineer identifier.

        Returns:
            The newly created DRAFT ``KBArticle``.
        """
        rca_label = rca_result.probable_rca

        # Title
        title = f"SOP: {rca_label} on Cisco Network Device"

        # Problem statement derived purely from observed evidence
        evidence_str = "; ".join(f"{k}={v}" for k, v in rca_result.evidence.items())
        problem_statement = (
            f"Device {rca_result.incident_id} experienced a '{rca_label}' incident. "
            f"Observed evidence: {evidence_str}."
        )

        # Deterministic symptom/validation/rollback from templates
        symptoms = _SYMPTOM_TEMPLATES.get(rca_label, ["Refer to RCA evidence"])
        validation_steps = _VALIDATION_TEMPLATES.get(rca_label, ["Confirm system stability"])
        rollback_steps = _ROLLBACK_TEMPLATES.get(rca_label, ["Revert last change"])

        # Resolution steps from the engineer record or default
        if resolution:
            resolution_steps = [
                resolution.resolution_action,
                f"Validated by: {resolution.validation_action}",
            ]
        else:
            resolution_steps = [f"Investigate and address {rca_label} per recommended checks."]
            resolution_steps += rca_result.recommended_checks

        article = self.store.create_kb(
            title=title,
            problem_statement=problem_statement,
            symptoms=symptoms,
            root_cause=rca_result.probable_rca,
            evidence=rca_result.evidence,
            resolution_steps=resolution_steps,
            validation_steps=validation_steps,
            rollback_steps=rollback_steps,
            created_by=created_by,
            source_incident_id=rca_result.incident_id,
            source_rca=rca_result.rule_id,
        )
        return article
