
import streamlit as st
import json
import os
from modules.attacker import generate_attacks
from modules.evaluator import evaluate_response
from modules.mcp_logger import MCPRecord, save_mcp_record

# Set Streamlit page config
st.set_page_config(page_title="RedSentinel", page_icon="🚨", layout="wide")

st.title("🚨 RedSentinel: AI Safety Red Team Agent")
st.subheader("Adversarial Prompt Attacks + MCP-Compliant Evaluations")

# Sidebar for user input
with st.sidebar:
    st.header("🔍 Input Settings")
    user_prompt = st.text_area("Enter a base prompt to red-team:", height=150)
    attack_intensity = st.selectbox("Attack Intensity", ["Mild", "Moderate", "Aggressive"])
    start_attack = st.button("Start Red Teaming Attack 🚀")

if start_attack and user_prompt:
    st.success("Starting Red Teaming... Please wait ⏳")

    # Step 1: Generate adversarial prompts
    attack_variants = generate_attacks(user_prompt, attack_intensity)

    mcp_records = []

    for attack in attack_variants:
        st.divider()
        st.subheader(f"🎯 Attack Type: {attack['attack_type']}")

        with st.expander("View Mutated Prompt"):
            st.write(attack["mutated_prompt"])

        # Step 2: Get model response
        response_text = attack["response"]

        st.markdown(f"**Model Response:**")
        st.info(response_text)

        # Step 3: Evaluate response
        evaluation = evaluate_response(response_text)

        st.markdown(f"**Risk Score:** {evaluation['risk_score']} / 5")
        st.markdown(f"**Violation Type:** {evaluation['violation_type']}")
        st.markdown(f"**Evaluation Comments:** {evaluation['evaluation_comments']}")

        # Step 4: Save MCP Record
        record = MCPRecord(
            model_name="claude-3-opus-20240229",
            provider="Anthropic",
            original_prompt=user_prompt,
            adversarial_prompt=attack["mutated_prompt"],
            model_response=response_text,
            risk_score=evaluation["risk_score"],
            violation_type=evaluation["violation_type"],
            evaluation_comments=evaluation["evaluation_comments"],
            attack_type=attack["attack_type"],
            tags=evaluation["tags"],
        )
        mcp_records.append(record.to_dict())

    # Step 5: Download full MCP report
    st.divider()
    st.subheader("📦 Download Reports")

    # Save reports temporarily
    mcp_json = json.dumps(mcp_records, indent=4)
    st.download_button("Download MCP JSON Report 📄", data=mcp_json, file_name="redsentinel_mcp_report.json", mime="application/json")

else:
    st.info("👈 Enter a prompt and click 'Start Red Teaming Attack' to begin.")

