"""Streamlit engineer-facing prototype UI."""


import pandas as pd
import streamlit as st

# Page config
st.set_page_config(page_title="NOIPMP Engineer UI", layout="wide", page_icon="🔧")

# Header
st.title("Network Operations Intelligence Platform")
st.subheader("Engineer Workspace")

# Sidebar
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Incident Investigation", "Device Health", "Vulnerability & Knowledge", "Demo Scenario"])

st.sidebar.divider()
st.sidebar.markdown("**Current Role:** Tier 2 Engineer")
st.sidebar.markdown("**Environment:** Production Prototype")

# -----------------------------------------------------------------------------
# Incident Investigation Page
# -----------------------------------------------------------------------------
if page == "Incident Investigation":
    st.header("Incident Search")

    col1, col2, col3 = st.columns(3)
    search_query = col1.text_input("Search by ID, Device, or Status", "INC-00042")
    status_filter = col2.selectbox("Status", ["All", "Open", "In Progress", "Resolved"])
    severity_filter = col3.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low"])

    st.divider()

    # Mock data showing the requested specific format
    if "00042" in search_query:
        st.header("Incident Detail: INC-00042")

        # Meta info
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Device", "Cisco RTR001")
        m_col2.metric("Alert Type", "NODE_DOWN")
        m_col3.metric("Severity", "Critical")
        m_col4.metric("Status", "Resolved")

        st.markdown("---")

        # Timeline
        st.subheader("Incident Timeline")
        st.info("🕒 **10:14** Alert (NODE_DOWN) ➔ **10:15** RCA Engine ➔ **10:20** Diagnosis ➔ **10:45** Resolution")

        st.markdown("---")

        # Two columns for RCA and Predictive Risk
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("RCA Output")
            st.warning("**Root Cause:** Interface degradation")

            st.markdown("**Evidence:**")
            st.code("""
CRC Errors: 1450
Interface Flaps: 8
Packet Loss: 17%
            """)

            st.markdown("**RCA Explanation (AI):**")
            st.write("Rule RULE-001 fired with 88% confidence. Observed evidence of 1450 CRC errors and 17% packet loss strongly indicates severe interface degradation on the uplink port.")

        with c2:
            st.subheader("Predictive Risk Profiling")
            st.error("**Risk Score:** 87% (CRITICAL)")

            st.markdown("**Recommended Action:**")
            st.write("Inspect interface, transceiver, and physical fiber link.")

            st.markdown("**Preventive Action Status:**")
            st.write("🟢 COMPLETED (Prior incident prevented)")

        st.markdown("---")

        # Resolution & KB
        st.subheader("Resolution & Knowledge Base")

        r1, r2 = st.columns(2)
        with r1:
            st.markdown("**Resolution Action Applied:**")
            st.success("Replaced fiber and cleaned optical transceiver.")

        with r2:
            st.markdown("**Linked SOP/KB:**")
            st.write("📖 **[KB-0047 v1.0] Troubleshooting Interface Degradation**")

        st.markdown("---")

        # Generate KB button
        st.subheader("Knowledge Management")
        if st.button("Generate SOP Draft from Incident"):
            with st.spinner("Generating KB Draft..."):
                # Mock generation
                st.success("Draft created successfully!")
                with st.expander("Preview KB-0048 (DRAFT)"):
                    st.write("**PROBLEM STATEMENT:** Device RTR001 experienced Interface degradation.")
                    st.write("**SYMPTOMS:** 1450 CRC Errors, 17% Packet loss.")
                    st.write("**RESOLUTION STEPS:** Replaced fiber and cleaned optical transceiver.")
                    st.button("Submit for Review")

    else:
        st.info("No matching incidents found.")

# -----------------------------------------------------------------------------
# Device Health Page
# -----------------------------------------------------------------------------
elif page == "Device Health":
    st.header("Device Health & Predictive Maintenance")

    st.subheader("Top High-Risk Devices")

    # Mock dataframe
    df = pd.DataFrame([
        {"Device": "RTR001", "Risk Level": "CRITICAL", "Failure Prob": "87%", "Predicted Issue": "Interface degradation", "Action": "Inspect fiber/transceiver"},
        {"Device": "SW002", "Risk Level": "HIGH", "Failure Prob": "71%", "Predicted Issue": "Memory leak", "Action": "Schedule firmware patch"},
        {"Device": "FW005", "Risk Level": "HIGH", "Failure Prob": "68%", "Predicted Issue": "High CPU", "Action": "Investigate routing loop"},
    ])

    st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# Vulnerability Page
# -----------------------------------------------------------------------------
elif page == "Vulnerability & Knowledge":
    st.header("Vulnerability Intelligence")

    c1, c2, c3 = st.columns(3)
    c1.metric("Exposed Devices", "14")
    c2.metric("Critical CVEs", "3")
    c3.metric("Average Firmware Age", "214 Days")

    st.subheader("CVE Information")
    st.write("**CVE-2023-0001** (Critical) - Cisco Catalyst 9300 (17.3.1)")
    st.write("Recommended: Upgrade to 17.3.3")

    st.divider()

    st.header("Knowledge Base Versions")
    kb_df = pd.DataFrame([
        {"KB ID": "KB-0047", "Title": "Interface Degradation SOP", "Version": "v1.1", "Status": "APPROVED", "Reuse Count": 42},
        {"KB ID": "KB-0047", "Title": "Interface Degradation SOP", "Version": "v1.0", "Status": "RETIRED", "Reuse Count": 15},
        {"KB ID": "KB-0048", "Title": "Memory Leak Resolution", "Version": "v1.0", "Status": "DRAFT", "Reuse Count": 0},
    ])
    st.table(kb_df)
# -----------------------------------------------------------------------------
# Demo Scenario Page
# -----------------------------------------------------------------------------
elif page == "Demo Scenario":
    import time
    st.header("End-to-End Incident Lifecycle Simulator")

    st.markdown("""
    This demo simulates the complete lifecycle of a network incident on **RTR-DEMO-001**,
    demonstrating the predictive, diagnostic, and knowledge-generation capabilities.
    """)

    if st.button("RUN DEMO SCENARIO"):
        st.divider()

        status_text = st.empty()
        progress_bar = st.progress(0)

        # Helper to update progress and UI state
        def advance_stage(stage_num, total_stages, title, content_fn):
            status_text.markdown(f"### Stage {stage_num}: {title}")
            progress_bar.progress(stage_num / total_stages)
            with st.container():
                content_fn()
            time.sleep(2)

        stages = 11

        # Stage 1
        def stage1():
            st.success("🟢 Device operating normally. CPU: 42%, Memory: 51%, CRC Errors: 0, Packet Loss: 0%")
        advance_stage(1, stages, "Normal Operations", stage1)

        # Stage 2
        def stage2():
            st.warning("🟡 Predictive Warning: Packet loss starts increasing (1% -> 3%)")
        advance_stage(2, stages, "Packet Loss Increase", stage2)

        # Stage 3
        def stage3():
            st.warning("🟠 Predictive Warning: CRC errors increasing (15 errors/hr)")
        advance_stage(3, stages, "CRC Errors Increase", stage3)

        # Stage 4
        def stage4():
            st.error("🔴 Predictive Warning: Interface flaps detected (3 flaps/hr)")
        advance_stage(4, stages, "Interface Flaps Increase", stage4)

        # Stage 5
        def stage5():
            st.error("🚨 **PREDICTIVE RISK: HIGH (82%)**")
            st.write("**Top Risk Factors:**")
            st.write("- CRC errors increasing at 15 errors/hr")
            st.write("- Packet loss averaged 3% over 24h")
        advance_stage(5, stages, "Predictive Risk Triggered", stage5)

        # Stage 6
        def stage6():
            st.info("📋 **PREVENTIVE ACTION RECOMMENDED:**")
            st.write("Inspect interface, transceiver and physical link.")
            st.write("Status: RECOMMENDED")
        advance_stage(6, stages, "Preventive Action Recommended", stage6)

        # Stage 7
        def stage7():
            st.error("💥 **INCIDENT OCCURRED:** NODE_DOWN on RTR-DEMO-001")
            st.write("Severity: CRITICAL")
            st.write("Status: OPEN")
        advance_stage(7, stages, "Incident Occurs (NODE_DOWN)", stage7)

        # Stage 8
        def stage8():
            st.write("🤖 **RCA Engine Analysis Complete:**")
            st.write("**Root Cause:** Interface degradation")
            st.write("**Confidence:** 94%")
            st.code("Evidence:\nCRC Errors: 1450\nInterface Flaps: 8\nPacket Loss: 17%")
        advance_stage(8, stages, "Generate RCA", stage8)

        # Stage 9
        def stage9():
            st.success("✅ **RESOLUTION:**")
            st.write("Engineer replaced faulty fiber and cleaned optical transceiver.")
            st.write("Status: RESOLVED")
            st.write("MTTR: 22 Minutes")
        advance_stage(9, stages, "Engineer Resolution", stage9)

        # Stage 10
        def stage10():
            st.info("📖 **KNOWLEDGE BASE:**")
            st.write("Generating SOP Draft...")
            st.write("**KB-0048 (DRAFT) Created:** Troubleshooting Interface Degradation on RTR-DEMO-001")
        advance_stage(10, stages, "Generate KB Draft", stage10)

        # Stage 11
        def stage11():
            st.success("🧠 **HISTORICAL KNOWLEDGE UPDATED:**")
            st.write("- New KB article available for future incidents")
            st.write("- Resolution metrics updated (First-Time Resolution: TRUE)")
            st.write("- Predictive model retrained with new incident data")

            st.balloons()
            st.success("🏁 **DEMO COMPLETE**")
        advance_stage(11, stages, "Knowledge Cycle Complete", stage11)
