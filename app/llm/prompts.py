"""Grounded prompt templates for all LLM tasks.

Every prompt contains an explicit system-level grounding contract that
instructs the model to:

  - use ONLY the evidence supplied in the context block
  - never invent Cisco command output
  - never invent CVEs or firmware versions
  - clearly state when information is unavailable
  - distinguish observed evidence from recommendations

The grounding contract is the FIRST thing in every system prompt so it cannot
be overridden by malformed user input (prompt injection mitigation).
"""

from __future__ import annotations

from app.llm.schemas import LLMContext, LLMTask

# ---------------------------------------------------------------------------
# Shared grounding contract (injected into every system prompt)
# ---------------------------------------------------------------------------

_GROUNDING_CONTRACT = """\
GROUNDING CONTRACT — READ BEFORE GENERATING ANY OUTPUT
======================================================
You are an AI assistant embedded in a Network Operations Intelligence Platform.
Your sole purpose is to EXPLAIN and SUMMARISE information that has ALREADY been
determined by deterministic, rule-based engineering systems.

YOU MUST FOLLOW THESE RULES WITHOUT EXCEPTION:

1. Use ONLY the evidence provided in the CONTEXT block below.
2. Do NOT invent Cisco CLI command outputs, counters, or log lines.
3. Do NOT invent CVE identifiers, firmware versions, or patch dates.
4. Do NOT invent IP addresses, hostnames, or interface names.
5. If a value is marked as "Not available", state clearly that the information
   is not available — do NOT guess or estimate.
6. Clearly distinguish OBSERVED EVIDENCE (from diagnostics) from
   RECOMMENDATIONS (from rule engine / engineering judgment).
7. Do NOT make claims about percentage improvements unless they are provided
   in the context.
8. Your output must be accurate to the context or silent — never fabricated.
"""

# ---------------------------------------------------------------------------
# Context serialiser
# ---------------------------------------------------------------------------

def _fmt_optional(label: str, value, unit: str = "") -> str:
    if value is None:
        return f"  {label}: Not available"
    return f"  {label}: {value}{unit}"


def _build_context_block(ctx: LLMContext) -> str:
    evidence_lines = "\n".join(f"  {k}: {v}" for k, v in ctx.rca_evidence.items()) or "  (none)"
    checks_lines = "\n".join(f"  - {c}" for c in ctx.rca_recommended_checks) or "  (none)"

    resolution_block = ""
    if ctx.root_cause:
        resolution_block = f"""
RESOLUTION HISTORY:
  Root cause recorded by engineer: {ctx.root_cause}
  Resolution action: {ctx.resolution_action or 'Not available'}
  Validation action: {ctx.validation_action or 'Not available'}
  Resolved by: {ctx.resolved_by or 'Not available'}
  Resolution duration: {f'{ctx.resolution_duration_minutes:.1f} min' if ctx.resolution_duration_minutes else 'Not available'}
  First-time resolution: {ctx.first_time_resolution if ctx.first_time_resolution is not None else 'Not available'}
"""

    base_block = f"""
CONTEXT (all values below are observed facts — do not alter them)
================================================================

INCIDENT:
  Incident ID: {ctx.incident_id}
  Device ID:   {ctx.device_id}
  Alert type:  {ctx.alert_type}
  Severity:    {ctx.severity}
  Start time:  {ctx.start_time.isoformat()}
  Recovery:    {ctx.recovery_time.isoformat() if ctx.recovery_time else 'Not yet recovered'}
  Duration:    {f'{ctx.duration_minutes:.1f} min' if ctx.duration_minutes else 'Not available'}

RCA ENGINE RESULT:
  Probable RCA: {ctx.probable_rca}
  Confidence:   {ctx.rca_confidence:.0%}
  Rule fired:   {ctx.rca_rule_id}

OBSERVED EVIDENCE (from Cisco diagnostics — do not alter these values):
{evidence_lines}

FULL DIAGNOSTIC SNAPSHOT:
{_fmt_optional('CPU utilization', ctx.cpu_utilization, '%')}
{_fmt_optional('Memory utilization', ctx.memory_utilization, '%')}
{_fmt_optional('Packet loss', ctx.packet_loss, '%')}
{_fmt_optional('CRC errors', ctx.crc_errors)}
{_fmt_optional('Input errors', ctx.input_errors)}
{_fmt_optional('Output errors', ctx.output_errors)}
{_fmt_optional('Interface flaps', ctx.interface_flaps)}
{_fmt_optional('Interface status', ctx.interface_status)}
{_fmt_optional('BGP status', ctx.bgp_status)}
{_fmt_optional('OSPF status', ctx.ospf_status)}
{_fmt_optional('Temperature', ctx.temperature, '°C')}

RULE ENGINE RECOMMENDED CHECKS:
{checks_lines}
{resolution_block}"""

    if ctx.raw_command_output:
        base_block += f"""\n
RAW INFRASTRUCTURE DATA (Treated as Sensitive - Allowed by Config):
{ctx.raw_command_output}
"""
    return base_block


# ---------------------------------------------------------------------------
# Per-task prompt builders
# ---------------------------------------------------------------------------

def build_prompt(ctx: LLMContext) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the given task context."""
    context_block = _build_context_block(ctx)

    if ctx.task == LLMTask.INCIDENT_SUMMARY:
        system = _GROUNDING_CONTRACT + """
You are writing an executive incident summary for a network operations team.
Write 3 concise paragraphs:
  1. What happened (based on incident metadata only).
  2. What the diagnostics showed (based on OBSERVED EVIDENCE only).
  3. Current status and next steps (based on resolution history and recommended checks only).
Do NOT add any information not present in the context.
"""
        user = f"Write the incident summary for the following context:\n{context_block}"

    elif ctx.task == LLMTask.RCA_EXPLANATION:
        system = _GROUNDING_CONTRACT + """
You are explaining a Root Cause Analysis result to a network engineer.
Explain in plain English:
  - Which rule fired and why (use rule ID and evidence values verbatim).
  - What the observed evidence means technically.
  - What is NOT known (use "Not available" where applicable).
Do NOT explain causes that are not supported by the evidence.
"""
        user = f"Explain the RCA result for the following context:\n{context_block}"

    elif ctx.task == LLMTask.TROUBLESHOOTING_SUMMARY:
        system = _GROUNDING_CONTRACT + """
You are writing a concise, step-by-step troubleshooting summary for a field engineer.
Structure your output as:
  SYMPTOMS OBSERVED: (list from evidence only)
  PROBABLE CAUSE: (from RCA engine result only)
  RECOMMENDED CHECKS: (from rule engine only — do not add extra steps)
  RESOLUTION (if available): (from resolution history only)
Each section must be clearly labelled.
"""
        user = f"Write the troubleshooting summary for the following context:\n{context_block}"

    elif ctx.task == LLMTask.KB_DRAFT:
        system = _GROUNDING_CONTRACT + """
You are drafting a Knowledge Base / SOP article for a network operations team.
Structure the article with these exact headings:
  PROBLEM STATEMENT
  SYMPTOMS
  ROOT CAUSE
  EVIDENCE (list verbatim from context)
  RESOLUTION STEPS (from resolution history; if unavailable, use recommended checks)
  VALIDATION STEPS
  ROLLBACK STEPS
  NOTES
Do NOT mark the article as approved. It is a DRAFT only.
"""
        user = f"Draft the KB/SOP article for the following context:\n{context_block}"

    elif ctx.task == LLMTask.PREVENTIVE_ACTION:
        system = _GROUNDING_CONTRACT + """
You are explaining preventive maintenance actions to reduce the risk of recurrence.
Base your explanation ONLY on the RCA result, recommended checks, and resolution history.
Do NOT recommend actions that are not grounded in the provided context.
Format as a numbered list.
"""
        user = f"Write the preventive actions for the following context:\n{context_block}"

    else:
        raise ValueError(f"Unknown LLM task: {ctx.task}")

    return system, user
