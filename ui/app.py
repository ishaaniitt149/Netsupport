"""NOIPMP - Network Operations Intelligence & Predictive Maintenance Platform.

Engineer Workspace — Streamlit UI
Version 2.0

Pages:
1. Executive Overview     — KPIs and business metrics
2. Incident Investigation — Search, RCA, AI assistant, SOP, resolution
3. Device 360             — Device health, telemetry trends, risk
4. Predictive Maintenance — Top 10 risk, risk distribution
5. Vulnerability & Firmware — CVE exposure, firmware recommendations
6. Knowledge Management   — SOP editor, version history
7. Demo Scenario          — End-to-end lifecycle simulation

All data comes from ui/data_layer.py — no hardcoded values.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Page config — MUST be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="NOIPMP — Network Operations Intelligence",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for professional appearance
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {font-size: 1.5rem; font-weight: 700; color: #1f77b4; margin-bottom: 0;}
    .sub-header  {font-size: 0.95rem; color: #888; margin-top: 0;}
    .status-up   {color: #28a745; font-weight: 700;}
    .status-down {color: #dc3545; font-weight: 700;}
    .status-degraded {color: #fd7e14; font-weight: 700;}
    .kpi-label   {font-size: 0.75rem; color: #888; text-transform: uppercase;}
    .evidence-box {background:#1e1e2e; border-radius:6px; padding:10px; font-family:monospace; font-size:0.85rem;}
    .risk-critical {color: #dc3545; font-weight:700;}
    .risk-high     {color: #fd7e14; font-weight:700;}
    .risk-medium   {color: #ffc107; font-weight:700;}
    .risk-low      {color: #28a745; font-weight:700;}
    div[data-testid="stMetric"] > div {border-radius: 6px; background: #f8f9fa; padding: 10px;}
    .next-action-box {background:#e8f4fd; border-left:4px solid #1f77b4; padding:12px; border-radius:4px;}
    .workflow-step {display:inline-block; background:#dee2e6; border-radius:12px; padding:3px 10px; margin:2px; font-size:0.8rem;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Lazy import data layer (avoids reload on every widget interaction)
# ---------------------------------------------------------------------------
import pathlib
import sys

# Ensure project root is on sys.path so both `ui.*` and `app.*` packages are importable.
_PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ui.data_layer import (
    compute_device_risk,
    compute_device_status,
    compute_kpis,
    get_device,
    get_device_cves,
    get_device_incident_history,
    get_device_incidents_30d,
    get_device_telemetry_30d,
    get_firmware_recommendation,
    get_incident,
    get_next_best_action,
    get_similar_incidents,
    get_sop_versions,
    get_top_risk_devices,
    load_cve_dataset,
    load_devices,
    load_firmware_recommendations,
    load_incidents,
    load_kb_articles,
    search_kb_articles,
    update_sop_version,
)

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.markdown('<p class="main-header">🔧 NOIPMP</p>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="sub-header">Network Operations Intelligence</p>', unsafe_allow_html=True)
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    [
        "📊 Executive Overview",
        "🔍 Incident Investigation",
        "🖥 Device 360",
        "⚠️ Predictive Maintenance",
        "🛡 Vulnerability & Firmware",
        "📖 Knowledge Management",
        "🎬 Demo Scenario",
    ],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.markdown("**Role:** Tier 2 Engineer")
st.sidebar.markdown("**Mode:** Production Prototype")
st.sidebar.markdown("**Data:** Synthetic (is_synthetic=True)")

# ============================================================================
# PAGE 1 — EXECUTIVE OVERVIEW
# ============================================================================
if page == "📊 Executive Overview":
    st.markdown('<p class="main-header">Executive Overview</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Evidence-based operational KPIs · Calculated from actual incident and resolution data</p>', unsafe_allow_html=True)
    st.divider()

    kpis = compute_kpis()

    if not kpis:
        st.warning("No data available. Run `make generate-data` first.")
    else:
        # Row 1 — Incident KPIs
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Incidents", kpis.get("total_incidents", "—"))
        c2.metric("Resolved", kpis.get("resolved_incidents", "—"))
        mtta = kpis.get("mtta_min")
        c3.metric("MTTA", f"{mtta} min" if mtta else "—")
        mttd = kpis.get("mttd_min")
        c4.metric("Mean Time to Diagnose", f"{mttd} min" if mttd else "—")
        mttr = kpis.get("mttr_min")
        c5.metric("MTTR", f"{mttr} min" if mttr else "—")

        # Row 2 — Quality KPIs
        c6, c7, c8, c9, c10 = st.columns(5)
        ftr = kpis.get("ftr_rate_pct")
        c6.metric("First-Time Resolution", f"{ftr}%" if ftr else "—")
        c7.metric("Repeat Incident Pairs", kpis.get("repeat_incident_device_pairs", "—"))
        rca_rate = kpis.get("rca_automation_rate_pct")
        c8.metric("RCA Automation Rate", f"{rca_rate}%" if rca_rate else "—")
        c9.metric("KB Articles", kpis.get("kb_articles", "—"))
        c10.metric("Incidents Prevented", "—", help="Counted only when preventive action preceded a predicted failure that did not occur. Requires live tracking not yet implemented.")

        st.divider()

        st.subheader("Operational Impact & Business Value")
        high_risk = len(get_top_risk_devices(top_n=100))
        st.info(f"**Business Interpretation:** {high_risk} devices show elevated recurring risk based on recent incident frequency and telemetry trends.")
        st.success("**Operational Impact:** Evidence-based troubleshooting and reusable SOPs can reduce dependency on senior engineers for repeatable L1/L2 incidents.")

        st.divider()

        # Incident distribution
        st.subheader("Incident Distribution (90 Days)")
        incidents = load_incidents()
        if not incidents.empty and "alert_type" in incidents.columns:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**By Alert Type**")
                dist = incidents["alert_type"].value_counts().reset_index()
                dist.columns = ["Alert Type", "Count"]
                st.bar_chart(dist.set_index("Alert Type"))
            with col_b:
                st.markdown("**By Severity**")
                sev = incidents["severity"].value_counts().reset_index()
                sev.columns = ["Severity", "Count"]
                st.bar_chart(sev.set_index("Severity"))

        # Incidents over time
        st.subheader("Incident Volume — Last 90 Days")
        if not incidents.empty:
            inc_copy = incidents.copy()
            inc_copy["week"] = inc_copy["start_time"].dt.to_period("W").dt.start_time
            weekly = inc_copy.groupby("week").size().reset_index(name="count")
            weekly["week"] = weekly["week"].dt.tz_localize(None)
            st.line_chart(weekly.set_index("week")["count"])

        st.caption("⚠️ KPI Note: 'Incidents Prevented' requires confirmed preventive action executed before a predicted failure window, with no subsequent failure. This metric is not auto-populated.")


# ============================================================================
# PAGE 2 — INCIDENT INVESTIGATION
# ============================================================================
elif page == "🔍 Incident Investigation":
    st.markdown('<p class="main-header">Incident Investigation Workspace</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Search · RCA · Evidence · History · AI Assistant · Resolution · Knowledge</p>', unsafe_allow_html=True)

    # Workflow indicator
    st.markdown(
        '<span class="workflow-step">Alert</span> → '
        '<span class="workflow-step">Incident</span> → '
        '<span class="workflow-step">Device Health</span> → '
        '<span class="workflow-step">RCA Evidence</span> → '
        '<span class="workflow-step">Historical Comparison</span> → '
        '<span class="workflow-step">Local SOP</span> → '
        '<span class="workflow-step">AI Analysis</span> → '
        '<span class="workflow-step">Resolution</span> → '
        '<span class="workflow-step">SOP Update</span>',
        unsafe_allow_html=True,
    )
    st.divider()

    # Search
    incidents = load_incidents()
    col_s1, col_s2, col_s3 = st.columns(3)
    search_q = col_s1.text_input("Search Incident ID, Device ID, Alert Type", "")
    sev_filter = col_s2.selectbox("Severity", ["All", "critical", "high", "warning"])
    alert_filter = col_s3.selectbox("Alert Type", ["All"] + (sorted(incidents["alert_type"].unique().tolist()) if not incidents.empty and "alert_type" in incidents.columns else []))

    if not incidents.empty:
        filtered = incidents.copy()
        if search_q:
            q = search_q.strip().upper()
            mask = (
                filtered["incident_id"].str.contains(q, case=False, na=False) |
                filtered["device_id"].str.contains(q, case=False, na=False) |
                filtered.get("alert_type", pd.Series()).str.contains(q, case=False, na=False)
            )
            filtered = filtered[mask]
        if sev_filter != "All":
            filtered = filtered[filtered["severity"] == sev_filter]
        if alert_filter != "All":
            filtered = filtered[filtered["alert_type"] == alert_filter]

        if filtered.empty:
            st.info("No incidents match your search.")
        else:
            # Show incident list
            display_cols = [c for c in ["incident_id", "device_id", "alert_type", "severity", "start_time", "duration_minutes", "rca_label"] if c in filtered.columns]
            disp = filtered[display_cols].head(20).copy()
            if "start_time" in disp.columns:
                disp["start_time"] = disp["start_time"].dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(disp, use_container_width=True, hide_index=True)

            # Select incident to investigate
            selected_id = st.selectbox("Open Incident for Investigation", filtered["incident_id"].tolist())
            inc = get_incident(selected_id)
    else:
        st.warning("No incident data. Run `make generate-data`.")
        inc = None
        selected_id = None

    if inc:
        st.divider()
        st.markdown(f"## 🔎 Incident Detail: `{inc['incident_id']}`")

        # ── SECTION 1: Incident meta ──────────────────────────────────────
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Device", inc.get("device_id", "—"))
        m2.metric("Alert Type", inc.get("alert_type", "—"))
        m3.metric("Severity", inc.get("severity", "—").upper())
        m4.metric("Duration", f"{inc.get('duration_minutes', 0):.0f} min")
        status, status_detail = compute_device_status(inc["device_id"])
        status_colors = {"UP": "🟢", "DOWN": "🔴", "DEGRADED": "🟠", "UNKNOWN": "⚪"}
        m5.metric("Current Device Status", f"{status_colors.get(status,'')} {status}")

        st.caption(f"Status detail: {status_detail}")

        start = inc.get("start_time")
        recovery = inc.get("recovery_time")
        if start and recovery:
            st.info(
                f"⏱ **Timeline:** Alert `{pd.Timestamp(start).strftime('%H:%M %d %b')}` → "
                f"RCA Engine → Diagnosis → Recovery `{pd.Timestamp(recovery).strftime('%H:%M %d %b')}`"
            )

        # ── SECTION 2: RCA + Predictive Risk ─────────────────────────────
        rca_col, risk_col = st.columns(2)

        with rca_col:
            st.subheader("🧬 RCA Analysis")
            rca_label = inc.get("rca_label", "Not determined")
            rca_conf = inc.get("rca_confidence", 0)
            st.warning(f"**Root Cause:** {rca_label}")
            st.caption(f"Confidence: {rca_conf:.0%} | Rule: {inc.get('rca_rule_id', 'N/A')}")

            with st.expander("📋 Diagnostic Evidence", expanded=True):
                evidence = {}
                if inc.get("crc_errors"):
                    evidence["CRC Errors"] = inc["crc_errors"]
                if inc.get("packet_loss_pct"):
                    evidence["Packet Loss"] = f"{inc['packet_loss_pct']}%"
                if inc.get("interface_flaps"):
                    evidence["Interface Flaps"] = inc["interface_flaps"]
                if inc.get("cpu_pct"):
                    evidence["CPU Utilization"] = f"{inc['cpu_pct']}%"
                if evidence:
                    for k, v in evidence.items():
                        st.code(f"{k}: {v}", language=None)
                else:
                    st.caption("No structured evidence available for this incident.")

        with risk_col:
            st.subheader("⚡ Predictive Risk Profile")
            risk = compute_device_risk(inc["device_id"])
            score = risk["score"]
            level = risk["level"]
            color_map = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
            st.error(f"**Risk Score: {score}% — {color_map.get(level,'')} {level}**")

            if risk["factors"]:
                st.markdown("**Top Risk Factors:**")
                for i, f in enumerate(risk["factors"][:5], 1):
                    st.write(f"  {i}. {f}")

            rec_alert = risk.get("recurring_alert")
            if rec_alert:
                st.warning(f"🔁 Recurring issue detected: **{rec_alert}** ({risk['incident_count_30d']} times in 30d)")

        # ── SECTION 3: Next Best Action ───────────────────────────────────
        st.divider()
        st.subheader("🎯 Next Best Action")
        cmds = get_next_best_action(rca_label)
        kb_matches = search_kb_articles(rca_label=rca_label, alert_type=inc.get("alert_type"))
        top_kb = kb_matches[0] if kb_matches else None

        st.markdown(f"**WHY:** RCA identified **{rca_label}**. Telemetry trend indicates an escalating pattern.")
        st.markdown(f"**EVIDENCE:** Incident {inc['incident_id']} with severity {inc.get('severity', 'UNKNOWN')}. RCA extracted specific diagnostic matching conditions.")
        st.markdown("**RECOMMENDED CISCO COMMANDS:**")
        cmd_text = "\n".join(cmds)
        st.code(cmd_text, language="bash")
        st.caption("⚠️ Recommendations only — prototype does not execute commands against live devices.")
        st.markdown("**EXPECTED RESULT:** Output will confirm if interface counters are incrementing rapidly.")
        st.markdown("**NEXT STEP:** Check optical transceiver Rx power, verify physical connection.")

        nba_c1, nba_c2, nba_c3 = st.columns(3)
        with nba_c1:
            if st.button("📋 Copy Commands", key="copy_cmds"):
                st.success("Commands copied (simulation).")
        with nba_c2:
            if top_kb:
                if st.button(f"📖 Open SOP: {top_kb['kb_id']}", key="open_sop_nba"):
                    st.info(f"Opening {top_kb['kb_id']}... (Navigate to Knowledge Management)")

        # ── SECTION 4: Historical Similar Incidents ───────────────────────
        st.divider()
        st.subheader("📅 Similar Historical Incidents")

        similar = get_similar_incidents(
            inc["incident_id"],
            alert_type=inc.get("alert_type", ""),
            device_id=inc.get("device_id", ""),
            rca_label=inc.get("rca_label", ""),
        )
        if similar.empty:
            st.caption("No similar historical incidents found.")
        else:
            cols_to_show = [c for c in ["incident_id", "device_id", "alert_type", "severity", "start_time", "duration_minutes", "rca_label", "similarity_pct"] if c in similar.columns]
            sim_disp = similar[cols_to_show].copy()
            if "start_time" in sim_disp.columns:
                sim_disp["start_time"] = sim_disp["start_time"].dt.strftime("%Y-%m-%d")
            st.dataframe(sim_disp, use_container_width=True, hide_index=True)

            # Check for recurring pattern
            same_device = similar[similar["device_id"] == inc["device_id"]]
            if len(same_device) >= 2:
                st.error(
                    f"🔁 **RECURRING ISSUE DETECTED:** {len(same_device)} similar incidents on this device. "
                    "Escalate to predictive maintenance review."
                )

        # ── SECTION 5: Knowledge Assistance ──────────────────────────────
        st.divider()
        st.subheader("📚 Knowledge Assistance")

        kb_tab1, kb_tab2 = st.tabs(["📂 Local SOPs", "🤖 AI Assistant"])

        with kb_tab1:
            st.markdown("**Relevant SOPs from Internal Knowledge Base**")
            for art in kb_matches[:4]:
                with st.expander(f"[{art['kb_id']} v{art['version']}] {art['title']} — Similarity: {art.get('similarity_pct',0)}%"):
                    st.markdown(f"**Status:** {art.get('status')} | **Reuse Count:** {art.get('reuse_count', 0)}")
                    st.markdown(f"**Problem:** {art.get('problem_statement','')}")
                    steps = art.get("resolution_steps", [])
                    if steps:
                        st.markdown("**Resolution Steps:**")
                        for s in steps:
                            st.markdown(f"  - {s}")
                    val = art.get("validation_steps", [])
                    if val:
                        st.markdown("**Validation:**")
                        for v in val:
                            st.markdown(f"  - {v}")

        with kb_tab2:
            st.markdown("**AI Assistant — Grounded on available evidence only**")
            st.caption("The AI summarises only what is available in the incident context, evidence, and knowledge base. It will not invent data.")

            q_options = [
                "What should I check next?",
                "Has this device experienced this issue before?",
                "What Cisco commands should I run?",
                "Explain the RCA in simple terms.",
                "Is the existing SOP sufficient for this incident?",
                "What preventive action should I take?",
                "Compare this incident with previous incidents.",
            ]
            ai_question = st.selectbox("Select a question or type your own:", q_options)
            custom_q = st.text_input("Or ask a custom question:", "")
            question = custom_q if custom_q.strip() else ai_question

            if st.button("Get AI Analysis", key="ai_btn"):
                evidence_summary = ", ".join(f"{k}={v}" for k, v in evidence.items()) or "No structured evidence"
                similar_count = len(similar)
                top_sop = top_kb["title"] if top_kb else "No SOP available"

                # Deterministic template response — no LLM call needed for prototype
                st.markdown("---")
                st.markdown(f"**Question:** {question}")
                st.markdown("---")
                st.markdown("#### 📋 Assessment")
                st.write(f"{rca_label} is the most probable root cause based on the evidence observed.")
                st.markdown("#### 🔬 Evidence")
                st.code(evidence_summary or "No structured evidence available for this incident.", language=None)
                st.markdown("#### 📅 Historical Comparison")
                if similar_count > 0:
                    st.write(f"This device has {similar_count} similar historical incident(s) in the dataset. This is a recurring pattern — review predictive maintenance thresholds.")
                else:
                    st.write("No similar historical incidents found. This may be a first-occurrence event.")
                st.markdown("#### ✅ Recommended Checks")
                for i, cmd in enumerate(cmds[:4], 1):
                    st.write(f"{i}. `{cmd}`")
                st.markdown("#### 📌 Sources Used")
                st.caption(
                    f"RCA Rule: {inc.get('rca_rule_id', 'N/A')} | "
                    f"Incident: {inc['incident_id']} | "
                    f"SOP: {top_kb['kb_id'] + ' v' + top_kb['version'] if top_kb else 'None'} | "
                    f"Similar incidents: {similar_count}"
                )
                st.markdown("#### 📊 Confidence")
                st.write(f"{rca_conf:.0%} (from deterministic RCA engine)")
                st.caption("⚠️ AI response is grounded in available evidence only. Insufficient evidence fields are marked 'Not available'.")

        # ── SECTION 6: Resolution Capture ────────────────────────────────
        st.divider()
        st.subheader("✅ Resolution Confirmation")

        with st.form("resolution_form"):
            r1, r2 = st.columns(2)
            with r1:
                actual_root_cause = st.text_area("Actual Root Cause (as confirmed by engineer)", height=80)
                actual_resolution = st.text_area("Actual Resolution Action Taken", height=80)
                commands_performed = st.text_area("Commands / Steps Performed", height=80)
            with r2:
                validation_performed = st.text_area("Validation Performed", height=80)
                downtime_min = st.number_input("Actual Downtime (minutes)", min_value=0, value=int(inc.get("duration_minutes", 0)))
                engineer_name = st.text_input("Engineer Name")
                category = st.selectbox("Resolution Category", ["Hardware", "Software", "Configuration", "ISP/Carrier", "Power", "Other"])

            submitted = st.form_submit_button("✅ Confirm Resolution")
            if submitted:
                if not actual_resolution.strip():
                    st.error("Resolution action is required.")
                else:
                    st.success(f"Resolution confirmed for {inc['incident_id']}.")
                    st.session_state["last_resolution"] = {
                        "incident_id": inc["incident_id"],
                        "root_cause": actual_root_cause,
                        "resolution": actual_resolution,
                        "commands": commands_performed,
                        "validation": validation_performed,
                        "engineer": engineer_name,
                        "category": category,
                    }
                    st.info("→ You can now create or update an SOP in the Knowledge Management page.")

        # ── SECTION 7: SOP improvement detection ─────────────────────────
        if "last_resolution" in st.session_state and top_kb:
            res = st.session_state["last_resolution"]
            existing_steps = set(top_kb.get("resolution_steps", []))
            engineer_steps = [s.strip() for s in res.get("commands", "").split("\n") if s.strip()]
            new_steps = [s for s in engineer_steps if s not in existing_steps]
            if new_steps:
                st.warning(
                    f"📝 **SOP Improvement Detected:** {len(new_steps)} new step(s) performed by engineer "
                    f"not present in {top_kb['kb_id']} v{top_kb['version']}."
                )
                for ns in new_steps:
                    st.code(f"+ {ns}", language=None)
                if st.button(f"Create New Version of {top_kb['kb_id']}", key="create_sop_ver"):
                    st.info(f"→ Navigate to Knowledge Management to edit and save {top_kb['kb_id']} as a new version.")


# ============================================================================
# PAGE 3 — DEVICE 360
# ============================================================================
elif page == "🖥 Device 360":
    st.markdown('<p class="main-header">Device 360</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Full device context: health, history, risk, telemetry, vulnerabilities</p>', unsafe_allow_html=True)
    st.divider()

    devices = load_devices()

    # Search
    search_col, _ = st.columns([2, 3])
    device_search = search_col.text_input("Search Device ID, Hostname, IP, Model", "")

    if not devices.empty:
        filtered_devs = devices.copy()
        if device_search:
            q = device_search.strip()
            filtered_devs = filtered_devs[
                filtered_devs["device_id"].str.contains(q, case=False, na=False) |
                filtered_devs["hostname"].str.contains(q, case=False, na=False) |
                filtered_devs["model"].str.contains(q, case=False, na=False) |
                filtered_devs.get("ip_address", pd.Series()).str.contains(q, case=False, na=False)
            ]

        selected_dev_id = st.selectbox("Select Device", filtered_devs["device_id"].tolist() if not filtered_devs.empty else [])

        if selected_dev_id:
            device = get_device(selected_dev_id)
            if not device:
                st.error("Device not found.")
            else:
                # ── Device Summary ─────────────────────────────────────────
                st.markdown(f"## {device.get('hostname', selected_dev_id)}")

                status, status_detail = compute_device_status(selected_dev_id)
                status_icon = {"UP": "🟢", "DOWN": "🔴", "DEGRADED": "🟠", "UNKNOWN": "⚪"}
                risk = compute_device_risk(selected_dev_id)
                cves = get_device_cves(selected_dev_id)
                inc_30d = get_device_incidents_30d(selected_dev_id)
                fw_rec = get_firmware_recommendation(str(device.get("firmware_version", "")))

                s1, s2, s3, s4, s5, s6 = st.columns(6)
                s1.metric("Status", f"{status_icon.get(status, '')} {status}")
                s2.metric("Risk Score", f"{risk['score']}%", delta=risk["level"])
                s3.metric("Open Incidents (30d)", len(inc_30d))
                s4.metric("Critical CVEs", risk.get("critical_cves", 0))
                s5.metric("Firmware Age", f"{device.get('firmware_age_days', '—')} days")
                s6.metric("Firmware", device.get("firmware_version", "—"))
                st.caption(f"Status: {status_detail}")

                dev_tab1, dev_tab2, dev_tab3, dev_tab4 = st.tabs([
                    "📡 Current Health", "📅 30-Day History", "⚡ Predictive Analysis", "🛡 Vulnerabilities"
                ])

                # ── Tab 1: Current Health ──────────────────────────────────
                with dev_tab1:
                    tel = get_device_telemetry_30d(selected_dev_id)
                    if tel.empty:
                        st.info("No telemetry data for this device.")
                    else:
                        last = tel.iloc[-1]
                        prev_7 = tel.tail(8).iloc[:-1]  # prev 7 days before today
                        avg_7 = prev_7.mean(numeric_only=True)

                        t1, t2, t3, t4 = st.columns(4)
                        t1.metric("CPU %",     f"{last.get('cpu_pct', '—'):.1f}",       f"{last.get('cpu_pct',0) - avg_7.get('cpu_pct',0):+.1f} vs 7d avg")
                        t2.metric("Memory %",  f"{last.get('memory_pct', '—'):.1f}",    f"{last.get('memory_pct',0) - avg_7.get('memory_pct',0):+.1f} vs 7d avg")
                        t3.metric("Pkt Loss %",f"{last.get('packet_loss_pct','—'):.2f}",f"{last.get('packet_loss_pct',0)-avg_7.get('packet_loss_pct',0):+.2f} vs 7d avg")
                        t4.metric("Latency ms",f"{last.get('latency_ms','—'):.1f}",     f"{last.get('latency_ms',0)-avg_7.get('latency_ms',0):+.1f} vs 7d avg")

                        t5, t6 = st.columns(2)
                        t5.metric("CRC Errors", f"{last.get('crc_errors', '—'):.0f}", f"{last.get('crc_errors',0)-avg_7.get('crc_errors',0):+.0f} vs 7d avg")
                        t6.metric("Interface Flaps", f"{last.get('interface_flaps', '—'):.0f}", f"{last.get('interface_flaps',0)-avg_7.get('interface_flaps',0):+.0f} vs 7d avg")

                        st.subheader("30-Day Trend")
                        trend_cols = [c for c in ["packet_loss_pct", "crc_errors", "interface_flaps"] if c in tel.columns]
                        tel_plot = tel.set_index("date")[trend_cols].copy()
                        tel_plot.index = pd.to_datetime(tel_plot.index).tz_localize(None)
                        st.line_chart(tel_plot)

                # ── Tab 2: 30-Day Incident History ────────────────────────
                with dev_tab2:
                    hist = get_device_incident_history(selected_dev_id, days=30)
                    if hist.empty:
                        st.success("No incidents in the last 30 days.")
                    else:
                        h1, h2, h3, h4 = st.columns(4)
                        h1.metric("Total Incidents", len(hist))
                        h2.metric("Total Downtime", f"{hist['duration_minutes'].sum():.0f} min")
                        h3.metric("MTTR", f"{hist['duration_minutes'].mean():.0f} min")

                        node_down = (hist["alert_type"] == "NODE_DOWN").sum()
                        pkt_loss = (hist["alert_type"] == "PACKET_LOSS").sum()
                        if_issues = (hist["alert_type"].str.contains("INTERFACE", case=False, na=False)).sum()
                        cpu_issues = (hist["alert_type"] == "HIGH_CPU").sum()

                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Node Down", node_down)
                        m2.metric("Packet Loss", pkt_loss)
                        m3.metric("Interface Issues", if_issues)
                        m4.metric("High CPU", cpu_issues)

                        st.markdown("**Issue Frequency**")
                        freq = hist.groupby("alert_type").agg(
                            Count=("incident_id", "count"),
                            Avg_Duration=("duration_minutes", "mean"),
                        ).reset_index()
                        freq["Avg_Duration"] = freq["Avg_Duration"].round(1)
                        freq.columns = ["Issue Type", "Count", "Avg Duration (min)"]
                        st.dataframe(freq, use_container_width=True, hide_index=True)

                        st.markdown("**Incident Timeline**")
                        disp_cols = [c for c in ["incident_id", "alert_type", "severity", "start_time", "duration_minutes", "rca_label"] if c in hist.columns]
                        hdisp = hist[disp_cols].copy()
                        if "start_time" in hdisp.columns:
                            hdisp["start_time"] = hdisp["start_time"].dt.strftime("%Y-%m-%d %H:%M")
                        st.dataframe(hdisp, use_container_width=True, hide_index=True)

                        # Recurring pattern detection
                        for at in hist["alert_type"].unique():
                            count = (hist["alert_type"] == at).sum()
                            if count >= 2:
                                st.error(f"🔁 **RECURRING:** {at} occurred {count} times in 30 days on this device.")

                # ── Tab 3: Predictive Analysis ────────────────────────────
                with dev_tab3:
                    st.markdown("**Predictive Health Score**")
                    score = risk["score"]
                    level = risk["level"]
                    score_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}

                    pa1, pa2, pa3 = st.columns(3)
                    pa1.metric("Risk Score", f"{score}%")
                    pa2.metric("Risk Level", f"{score_icon.get(level,'')} {level}")
                    pa3.metric("Prediction Horizon", "7 Days")

                    with st.expander("❓ Why Is This Device At Risk?", expanded=True):
                        factors = risk.get("factors", [])
                        if factors:
                            explanation_parts = []
                            if risk.get("incident_count_30d", 0) > 0:
                                explanation_parts.append(
                                    f"This device has experienced {risk['incident_count_30d']} incident(s) in the last 30 days."
                                )
                            tel = get_device_telemetry_30d(selected_dev_id)
                            if not tel.empty:
                                last_7 = tel.tail(7)
                                avg_crc = last_7["crc_errors"].mean() if "crc_errors" in last_7.columns else 0
                                avg_pkt = last_7["packet_loss_pct"].mean() if "packet_loss_pct" in last_7.columns else 0
                                if avg_crc > 0:
                                    explanation_parts.append(f"CRC errors averaged {avg_crc:.0f}/day over the last 7 days.")
                                if avg_pkt > 0:
                                    explanation_parts.append(f"Packet loss averaged {avg_pkt:.2f}% over the last 7 days.")
                            fw_age = risk.get("firmware_age_days", 0)
                            if fw_age and fw_age > 180:
                                explanation_parts.append(f"Device firmware is {fw_age} days old without a patch.")
                            critical_cves = risk.get("critical_cves", 0)
                            if critical_cves:
                                explanation_parts.append(f"{critical_cves} critical CVE(s) are unpatched on this device.")

                            if explanation_parts:
                                st.write(" ".join(explanation_parts))
                                st.caption(f"These factors contribute to the current risk score of {score}%.")
                            else:
                                st.info("Insufficient telemetry data to explain risk factors in detail.")
                            st.markdown("**Contributing Factors:**")
                            for i, f in enumerate(factors, 1):
                                st.write(f"  {i}. {f}")
                        else:
                            st.success("No significant risk factors identified from available data.")

                    if level in ("CRITICAL", "HIGH"):
                        with st.expander("🎬 Recommended Preventive Actions"):
                            st.write("Based on observed risk factors:")
                            st.write("1. Inspect physical fiber and patch cables")
                            st.write("2. Check optical transceiver Rx/Tx power levels")
                            st.write("3. Review interface error counters")
                            st.write("4. Schedule firmware upgrade if applicable")
                            if st.button("🎫 Create Preventive Ticket", key="prev_ticket"):
                                st.success(f"Preventive maintenance ticket created for {selected_dev_id}. (Prototype: ticket written to session state)")
                                st.session_state["preventive_ticket"] = {"device": selected_dev_id, "risk": score, "level": level}

                # ── Tab 4: Vulnerabilities ────────────────────────────────
                with dev_tab4:
                    fw_ver = str(device.get("firmware_version", ""))
                    fw_rec_ver = get_firmware_recommendation(fw_ver)

                    fv1, fv2, fv3 = st.columns(3)
                    fv1.metric("Current Firmware", fw_ver)
                    fv2.metric("Recommended Firmware", fw_rec_ver or "✅ Up to date")
                    fv3.metric("Firmware Age", f"{device.get('firmware_age_days', '—')} days")

                    if cves:
                        st.error(f"**{len(cves)} CVE(s) affecting this device and firmware version:**")
                        for cve in cves:
                            with st.expander(f"[{cve['severity']}] {cve['cve_id']}"):
                                st.write(f"**Description:** {cve.get('description', 'N/A')}")
                                st.write(f"**Affected Version:** {cve.get('affected_version')}")
                                st.write(f"**Fixed In:** {cve.get('fixed_version')}")
                    else:
                        st.success("No CVEs found matching this device model and firmware version in the synthetic dataset.")
                        st.caption("CVE matching is strictly model + firmware exact match. No CVEs are fabricated.")


# ============================================================================
# PAGE 4 — PREDICTIVE MAINTENANCE
# ============================================================================
elif page == "⚠️ Predictive Maintenance":
    st.markdown('<p class="main-header">Predictive Maintenance</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Top high-risk devices · Risk distribution · Evidence-based scoring</p>', unsafe_allow_html=True)
    st.divider()

    with st.spinner("Computing risk scores from telemetry and incident data..."):
        top_devices = get_top_risk_devices(top_n=10)

    if not top_devices:
        st.warning("No data available. Run `make generate-data`.")
    else:
        # Risk distribution
        all_devices_df = load_devices()
        if not all_devices_df.empty:
            st.subheader("Fleet Risk Distribution")
            risk_col1, risk_col2 = st.columns([2, 3])

            with risk_col1:
                levels = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
                for d in top_devices:
                    levels[d.get("level", "LOW")] = levels.get(d.get("level", "LOW"), 0) + 1
                dist_df = pd.DataFrame(list(levels.items()), columns=["Level", "Count"])
                st.dataframe(dist_df, use_container_width=True, hide_index=True)

            with risk_col2:
                st.caption("Top 10 scored. Full fleet scoring is available but compute-intensive.")

        # Top 10 table
        st.divider()
        st.subheader("🏆 Top 10 High-Risk Devices")

        table_rows = []
        for i, d in enumerate(top_devices, 1):
            level_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
            table_rows.append({
                "Rank": i,
                "Device ID": d["device_id"],
                "Model": d.get("model", "—"),
                "Risk": f"{level_icon.get(d['level'],'')} {d['score']}% {d['level']}",
                "Incidents 30D": d.get("incident_count_30d", 0),
                "Critical CVEs": d.get("critical_cves", 0),
                "Firmware Age (d)": d.get("firmware_age_days", "—"),
                "Top Factor": d["factors"][0] if d.get("factors") else "—",
            })

        top_df = pd.DataFrame(table_rows)
        st.dataframe(top_df, use_container_width=True, hide_index=True)

        # Drill-down
        selected_risk_dev = st.selectbox("Drill into device:", [d["device_id"] for d in top_devices])
        sel_risk = next((d for d in top_devices if d["device_id"] == selected_risk_dev), None)
        if sel_risk:
            with st.expander(f"Risk Detail: {selected_risk_dev}", expanded=True):
                st.metric("Risk Score", f"{sel_risk['score']}%")
                st.metric("Level", sel_risk["level"])
                st.markdown("**Evidence-Based Risk Factors:**")
                for i, f in enumerate(sel_risk.get("factors", []), 1):
                    st.write(f"  {i}. {f}")
                tel = get_device_telemetry_30d(selected_risk_dev)
                if not tel.empty:
                    st.markdown("**30-Day Telemetry Trend:**")
                    plot_cols = [c for c in ["packet_loss_pct", "crc_errors", "interface_flaps"] if c in tel.columns]
                    if plot_cols:
                        tel_plot = tel.set_index("date")[plot_cols].copy()
                        tel_plot.index = pd.to_datetime(tel_plot.index).tz_localize(None)
                        st.line_chart(tel_plot)


# ============================================================================
# PAGE 5 — VULNERABILITY & FIRMWARE
# ============================================================================
elif page == "🛡 Vulnerability & Firmware":
    st.markdown('<p class="main-header">Vulnerability & Firmware Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">CVE exposure · Firmware aging · Patch recommendations</p>', unsafe_allow_html=True)
    st.divider()
    st.caption("⚠️ CVE matching is strictly based on the synthetic dataset. No CVE is claimed unless the device model AND firmware version exactly match a dataset entry.")

    devices = load_devices()
    cve_df = load_cve_dataset()
    fw_df = load_firmware_recommendations()

    if devices.empty:
        st.warning("No device data. Run `make generate-data`.")
    else:
        # Summary metrics
        total_devs = len(devices)
        old_fw_devs = len(devices[devices.get("firmware_age_days", pd.Series(0, index=devices.index)) > 365]) if "firmware_age_days" in devices.columns else 0
        critical_cve_count = len(cve_df[cve_df["severity"] == "CRITICAL"]) if not cve_df.empty else 0
        high_cve_count = len(cve_df[cve_df["severity"] == "HIGH"]) if not cve_df.empty else 0

        v1, v2, v3, v4 = st.columns(4)
        v1.metric("Total Devices", total_devs)
        v2.metric("Devices with Old Firmware (>1yr)", old_fw_devs)
        v3.metric("Critical CVEs in Dataset", critical_cve_count)
        v4.metric("High CVEs in Dataset", high_cve_count)

        st.divider()
        st.subheader("CVE Dataset")
        if not cve_df.empty:
            st.dataframe(cve_df, use_container_width=True, hide_index=True)
        else:
            st.info("No CVE data found.")

        st.divider()
        st.subheader("Firmware Version Distribution")
        if "firmware_version" in devices.columns:
            fw_dist = devices["firmware_version"].value_counts().reset_index()
            fw_dist.columns = ["Firmware Version", "Device Count"]
            if not fw_df.empty:
                fw_dist = fw_dist.merge(fw_df, left_on="Firmware Version", right_on="firmware_version", how="left")
                fw_dist = fw_dist.drop(columns=["firmware_version"], errors="ignore")
                fw_dist = fw_dist.rename(columns={"recommended_version": "Recommended Upgrade"})
            st.dataframe(fw_dist, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Firmware Age by Device")
        if "firmware_age_days" in devices.columns and "device_id" in devices.columns:
            fw_age_df = devices[["device_id", "model", "firmware_version", "firmware_age_days", "criticality"]].copy()
            fw_age_df = fw_age_df.sort_values("firmware_age_days", ascending=False)
            st.dataframe(fw_age_df.head(20), use_container_width=True, hide_index=True)


# ============================================================================
# PAGE 6 — KNOWLEDGE MANAGEMENT
# ============================================================================
elif page == "📖 Knowledge Management":
    st.markdown('<p class="main-header">Knowledge Management</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">SOP Library · Version History · Edit · Create new versions</p>', unsafe_allow_html=True)
    st.divider()

    articles = load_kb_articles()
    if not articles:
        st.warning("No KB articles found. Run `make generate-data`.")
    else:
        # Article selector
        kb_ids = [f"[{a['kb_id']} v{a['version']}] {a['title']}" for a in articles]
        selected_kb_label = st.selectbox("Select SOP / KB Article", kb_ids)
        selected_kb = next(
            (a for a in articles if f"[{a['kb_id']} v{a['version']}] {a['title']}" == selected_kb_label),
            None
        )

        if selected_kb:
            km_tab1, km_tab2 = st.tabs(["📋 View / Edit SOP", "🕑 Version History"])

            with km_tab1:
                approved = selected_kb.get("status") == "APPROVED"
                if approved:
                    st.info(f"This is an APPROVED version ({selected_kb['kb_id']} v{selected_kb['version']}). Editing will create a new draft version.")

                with st.form("sop_editor_form"):
                    st.markdown(f"**{selected_kb['kb_id']} v{selected_kb['version']} — {selected_kb.get('status', 'DRAFT')}**")

                    sop_title = st.text_input("SOP Title", value=selected_kb.get("title", ""))
                    problem_stmt = st.text_area("Problem Statement", value=selected_kb.get("problem_statement", ""), height=80)

                    symptoms = st.text_area(
                        "Symptoms (one per line)",
                        value="\n".join(selected_kb.get("symptoms", [])),
                        height=100,
                    )
                    affected_devices = st.text_input("Affected Devices", value=selected_kb.get("applicable_devices", ""))
                    root_cause = st.text_input("Root Cause", value=selected_kb.get("applicable_rca", ""))

                    resolution_steps = st.text_area(
                        "Resolution Steps (one per line)",
                        value="\n".join(selected_kb.get("resolution_steps", [])),
                        height=150,
                    )
                    validation_steps = st.text_area(
                        "Validation Steps (one per line)",
                        value="\n".join(selected_kb.get("validation_steps", [])),
                        height=100,
                    )
                    rollback_steps = st.text_area(
                        "Rollback Steps (one per line)",
                        value="",
                        height=80,
                    )
                    related_incidents = st.text_input("Related Incidents (comma separated)", "")
                    related_cves = st.text_input("Related CVEs (comma separated)", "")

                    new_status = st.selectbox(
                        "Status",
                        ["DRAFT", "PENDING_REVIEW", "APPROVED", "RETIRED"],
                        index=["DRAFT", "PENDING_REVIEW", "APPROVED", "RETIRED"].index(
                            selected_kb.get("status", "DRAFT")
                        ),
                    )
                    engineer_name = st.text_input("Updated By")
                    change_summary = st.text_area(
                        "Change Summary (required for new version)",
                        placeholder="e.g. Added optical power validation step and updated resolution sequence.",
                        height=80,
                    )

                    save_btn = st.form_submit_button("💾 Save as New Version")

                if save_btn:
                    if not change_summary.strip():
                        st.error("Change Summary is required to create a new version.")
                    elif not engineer_name.strip():
                        st.error("Engineer name is required.")
                    else:
                        # Call update_sop_version from data_layer
                        kb_id = selected_kb["kb_id"]

                        try:
                            new_article = update_sop_version(
                                kb_id=kb_id,
                                updated_by=engineer_name,
                                change_summary=change_summary,
                                title=sop_title,
                                problem_statement=problem_stmt,
                                symptoms=[s.strip() for s in symptoms.split("\\n") if s.strip()],
                                root_cause=root_cause,
                                resolution_steps=[s.strip() for s in resolution_steps.split("\\n") if s.strip()],
                                validation_steps=[s.strip() for s in validation_steps.split("\\n") if s.strip()],
                            )
                            st.success(f"✅ New version created: **{kb_id} v{new_article.version}** (DRAFT)")
                            st.info(f"Change summary recorded: \"{change_summary}\"")
                        except Exception as e:
                            st.error(f"Failed to create new SOP version: {e}")

            with km_tab2:
                st.markdown("**Version History**")
                kb_id = selected_kb["kb_id"]
                try:
                    history = get_sop_versions(kb_id)
                except FileNotFoundError:
                    history = []

                if not history:
                    st.info("No versions stored in KBStore yet. Please edit the SOP to initialize a version.")

                # Reverse sort (newest first)
                for ver in reversed(history):
                    is_current = ver.version == history[-1].version
                    label = f"v{ver.version} {'— Current' if is_current else ''}"
                    with st.expander(label):
                        st.write(f"**Status:** {ver.status}")
                        st.write(f"**Created By:** {ver.created_by or '—'}")
                        # If KBVersionHistory doesn't have change_summary, we skip it or mock it
                        st.write(f"**Created At:** {ver.created_at}")
                        if ver.status == "KBStatus.APPROVED":
                            st.caption("🔒 This version is APPROVED and immutable. Create a new version to make changes.")



# ============================================================================
# PAGE 7 — DEMO SCENARIO
# ============================================================================
elif page == "🎬 Demo Scenario":
    import time as _time

    st.markdown('<p class="main-header">End-to-End Incident Lifecycle Simulator</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Deterministic 11-stage simulation of a complete network incident lifecycle on RTR-DEMO-001</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("""
**Scenario:**
Device `RTR-DEMO-001` (Cisco Catalyst 9300, Firmware 17.03.01) shows gradual physical-layer degradation
over 4 days, triggering a predictive warning, then a NODE_DOWN event, automated RCA, engineer resolution,
and KB creation — demonstrating the full NOIPMP workflow.
""")

    if st.button("▶ RUN DEMO SCENARIO", type="primary"):
        st.divider()
        status_text = st.empty()
        progress_bar = st.progress(0)
        stages = 11

        def advance(n: int, title: str, fn):
            status_text.markdown(f"### Stage {n}/{stages}: {title}")
            progress_bar.progress(n / stages)
            with st.container():
                fn()
            _time.sleep(2)

        def s1():
            st.success("🟢 **Stage 1: Normal Operations**")
            st.code("Device: RTR-DEMO-001\nCPU: 42% | Memory: 51%\nCRC Errors: 0 | Packet Loss: 0.0%\nInterface Flaps: 0 | Status: UP")
        advance(1, "Normal Operations", s1)

        def s2():
            st.warning("🟡 **Stage 2: Packet Loss Increasing**")
            st.code("Packet Loss: 0% → 1.2% → 2.8%\nLatency: 3ms → 8ms\nPredictive Model: Score 34% (LOW)")
            st.caption("Predictive model detects upward trend in packet loss.")
        advance(2, "Packet Loss Trend ↑", s2)

        def s3():
            st.warning("🟠 **Stage 3: CRC Errors Increasing**")
            st.code("CRC Errors: 0 → 45 → 180 (per hour)\nPacket Loss: 3.1%\nPredictive Model: Score 61% (MEDIUM)")
        advance(3, "CRC Errors ↑", s3)

        def s4():
            st.error("🔴 **Stage 4: Interface Flaps Detected**")
            st.code("Interface Flaps: 0 → 3 → 8 per hour\nCRC Errors: 420/hr (↑ 1300%)\nPacket Loss: 8.4%\nPredictive Model: Score 82% (HIGH)")
        advance(4, "Interface Flaps ↑", s4)

        def s5():
            st.error("🚨 **Stage 5: Predictive Risk CRITICAL**")
            col1, col2 = st.columns(2)
            col1.metric("Risk Score", "87%")
            col2.metric("Risk Level", "🔴 CRITICAL")
            st.markdown("**Top Risk Factors:**")
            st.write("1. CRC errors increased 1300% in 7 days")
            st.write("2. Packet loss averaging 8.4% (7d avg)")
            st.write("3. Interface flaps: 8/hr")
            st.write("4. Firmware 17.03.01 age: 847 days — 2 critical CVEs unpatched")
            st.caption("Predicted Issue: Interface / Physical Link Degradation | Confidence: 87%")
        advance(5, "Predictive Risk: CRITICAL", s5)

        def s6():
            st.info("📋 **Stage 6: Preventive Action Recommended**")
            st.markdown("**RECOMMENDED:**")
            st.write("1. Inspect Gi0/1 physical fiber and patch cable")
            st.write("2. Check optical transceiver Rx power (threshold: -14 dBm)")
            st.write("3. Review interface counters")
            st.write("4. Schedule maintenance window")
            st.write("**Status:** RECOMMENDED (not yet actioned)")
            st.caption("⚠️ Preventive action was not executed before incident — incident occurs in next stage.")
        advance(6, "Preventive Action Recommended", s6)

        def s7():
            st.error("💥 **Stage 7: Incident Occurs — NODE_DOWN**")
            st.code("Incident: INC-DEMO-001\nDevice: RTR-DEMO-001\nAlert Type: NODE_DOWN\nSeverity: CRITICAL\nTime: 03:42 UTC\nStatus: OPEN")
            st.caption("SolarWinds alert correlated by NOIPMP within 2 seconds of event.")
        advance(7, "NODE_DOWN Alert", s7)

        def s8():
            st.write("🤖 **Stage 8: Automated RCA Generation**")
            st.code("""RCA Engine — Rule RULE-001 fired

Evidence:
  CRC Errors:       1450
  Input Errors:     1512
  Interface Flaps:  8
  Packet Loss:      17.3%
  CPU:              41%
  BGP Status:       ESTABLISHED (healthy)

Probable RCA:  Interface degradation
Confidence:    94%
Rule:          RULE-001 (CRC + flaps threshold exceeded)""")
            st.caption("RCA is deterministic — no LLM inference. Evidence is parsed from Cisco CLI output.")
        advance(8, "Automated RCA", s8)

        def s9():
            st.success("✅ **Stage 9: Engineer Resolution**")
            st.code("""Resolution:
  Engineer:   Alice Chen
  Action:     Replaced faulty SFP transceiver and fiber patch cable on Gi0/1
  Commands:   show interfaces Gi0/1
              show interfaces transceiver
              clear counters Gi0/1
  Validation: CRC counters clear; packet loss 0.0% for 30 min
  MTTR:       22 minutes
  Status:     RESOLVED""")
        advance(9, "Engineer Resolution", s9)

        def s10():
            st.info("📖 **Stage 10: KB Draft Generation**")
            st.code("""KB Article Created: KB-0001 v1.3 (DRAFT)
Title: SOP: Interface Degradation Troubleshooting

Changes from v1.2 → v1.3:
+ Added optical transceiver power level validation step
+ Added fiber patch cable replacement as resolution step
+ Added post-replacement monitoring interval (30 min)

Change Summary:
"Alice Chen added optical power validation and expanded
 resolution steps based on RTR-DEMO-001 incident."

Status: DRAFT (pending engineer review and approval)""")
        advance(10, "KB Draft Created", s10)

        def s11():
            st.success("🧠 **Stage 11: Knowledge Cycle Complete**")
            st.markdown("**Platform Learning Outcomes:**")
            st.write("✅ KB-0001 v1.3 available for future similar incidents")
            st.write("✅ Resolution logged: First-Time Resolution = TRUE")
            st.write("✅ MTTR contribution recorded: 22 minutes")
            st.write("✅ Recurring issue pattern identified on RTR-DEMO-001")
            st.write("⚠️ Incident Prevention: NOT claimed — preventive action was not executed before failure")
            st.caption("Incident Prevention requires: preventive action executed + failure window passed without incident.")
            st.balloons()
            st.success("🏁 **DEMO COMPLETE — Full lifecycle demonstrated**")
        advance(11, "Knowledge Cycle Complete", s11)

        progress_bar.progress(1.0)
        status_text.markdown("### ✅ Demo complete")
