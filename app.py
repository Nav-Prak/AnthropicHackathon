# app.py

import streamlit as st
import json
import os
from modules.attacker import generate_attacks
from modules.evaluator import evaluate_response
from modules.mcp_logger import MCPRecord, save_mcp_record
from modules.file_scanner import scan_model_file
from modules.claude_analyzer import analyze_scan_with_claude


# Streamlit Page Settings
st.set_page_config(page_title="RedSentinel", page_icon="🚨", layout="wide")

st.title("🚨 RedSentinel: AI Safety Red Team Agent")
st.subheader("Adversarial Prompt Attacks + Model Artifact Safety Scanner (MCP-Compliant)")

# Sidebar - User Inputs
with st.sidebar:
    st.header("🔍 Choose Red Teaming Mode")
    mode = st.radio("Select Mode", ["Prompt Red-Teaming", "Model File Scanning"])

if mode == "Prompt Red-Teaming":
    with st.sidebar:
        user_prompt = st.text_area("Enter a base prompt to red-team:", height=150)
        attack_intensity = st.selectbox("Attack Intensity", ["Mild", "Moderate", "Aggressive"])
        start_attack = st.button("Start Red Teaming Attack 🚀")

    if start_attack and user_prompt:
        st.success("Starting Red Teaming... Please wait ⏳")

        # Step 1: Generate Attack Variants
        attack_variants = generate_attacks(user_prompt, attack_intensity)
        mcp_records = []

        for attack in attack_variants:
            st.divider()
            st.subheader(f"🎯 Attack Type: {attack['attack_type']}")

            with st.expander("🔹 View Mutated Prompt"):
                st.code(attack["mutated_prompt"], language="markdown")

            # Model's Response
            st.markdown(f"**🧠 Model Response:**")
            st.info(attack["response"])

            # Evaluate Response
            evaluation = evaluate_response(attack["response"])

            st.markdown(f"**🛡️ Risk Score:** `{evaluation['risk_score']} / 5`")
            st.markdown(f"**⚠️ Violation Type:** `{evaluation['violation_type']}`")
            st.markdown(f"**📝 Evaluation Comments:** {evaluation['evaluation_comments']}")

            tags = ", ".join(evaluation.get('tags', []))
            st.markdown(f"**🏷️ Risk Tags:** {tags}")

            # Save as MCP Record
            record = MCPRecord(
                model_name="claude-3-opus-20240229",
                provider="Anthropic",
                original_prompt=user_prompt,
                adversarial_prompt=attack["mutated_prompt"],
                model_response=attack["response"],
                risk_score=evaluation["risk_score"],
                violation_type=evaluation["violation_type"],
                evaluation_comments=evaluation["evaluation_comments"],
                attack_type=attack["attack_type"],
                tags=evaluation.get('tags', [])
            )
            mcp_records.append(record.to_dict())

        # Download MCP Report
        st.divider()
        st.subheader("📦 Download Full MCP Report")

        if mcp_records:
            mcp_json = json.dumps(mcp_records, indent=4)
            st.download_button("📥 Download MCP Report (.json)", data=mcp_json, file_name="redsentinel_mcp_report.json", mime="application/json")

    else:
        st.info("👈 Enter a prompt and click 'Start Red Teaming Attack' to begin.")

# ➡️ NEW BLOCK: Model File Scanner Mode
elif mode == "Model File Scanning":
    st.header("📂 Upload a Model File for Security Scanning")
    uploaded_file = st.file_uploader("Choose a .pkl, .h5, or .pt model file", type=["pkl", "h5", "pt", "pth"])

    if uploaded_file:
        scan_results = scan_model_file(uploaded_file)

        st.success(f"🔍 Scan Complete for `{scan_results['filename']}`")

        # Display Local Scan Results
        st.markdown(f"**File Type:** {scan_results['file_type']}")
        st.markdown(f"**Detected Framework:** {scan_results['framework']}")

        if scan_results["risks_detected"]:
            st.error(f"**Risks Detected:**")
            for risk in scan_results["risks_detected"]:
                st.write(f"- {risk}")
        else:
            st.success("✅ No immediate risks detected.")

        st.divider()

        # ➡️ NEW PART: Claude Risk Analysis
        from modules.claude_analyzer import analyze_scan_with_claude

        st.subheader("🧠 Claude Security Risk Assessment")

        with st.spinner("Asking Claude for security analysis..."):
            claude_risk_assessment = analyze_scan_with_claude(scan_results)

        st.markdown(f"**Risk Severity:** `{claude_risk_assessment['risk_severity']}`")
        st.markdown(f"**Security Concerns:** {claude_risk_assessment['security_concerns']}")
        st.markdown(f"**Recommended Actions:** {claude_risk_assessment['recommended_actions']}")

        st.divider()

        # MCP-Like Combined Report
        final_report = {
            "timestamp": scan_results.get("scan_time", "unknown"),
            "model_filename": scan_results['filename'],
            "file_type": scan_results['file_type'],
            "framework": scan_results['framework'],
            "risks_detected": scan_results['risks_detected'],
            "claude_risk_assessment": claude_risk_assessment
        }

        final_report_json = json.dumps(final_report, indent=4)
        st.download_button("📥 Download Full Model Risk Report (.json)", data=final_report_json, file_name="redsentinel_model_risk_report.json", mime="application/json")

    else:
        st.info("👈 Upload a model file to scan.")

