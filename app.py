import streamlit as st
import os
import json
from modules.file_scanner import scan_model_file
from modules.claude_analyzer import analyze_scan_with_claude
from modules.attacker import generate_attacks
from modules.evaluator import evaluate_response
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

st.set_page_config(page_title="RedSentinel Copilot", page_icon="🛡️")
st.title("🛡️ RedSentinel - AI Security Assistant")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "latest_file" not in st.session_state:
    st.session_state.latest_file = None

uploaded_file = st.file_uploader("Upload a binary or model file for analysis", type=None)
if uploaded_file:
    st.session_state.latest_file = uploaded_file
    st.success(f"Uploaded `{uploaded_file.name}`")

user_input = st.chat_input("Ask me about AI security, red teaming, or malware analysis...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # Create prompt for Claude
    messages = [
        {"role": "user", "content": user_input}
    ]

    try:
        claude_response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            system="You are RedSentinel, an AI Security Copilot assisting a user participating in a cybersecurity CTF (Capture The Flag) challenge. Based on their requests, either answer their question, or decide whether to trigger tools using <ACTION:...> tags. Available actions: <ACTION:SCAN_FILE>, <ACTION:RED_TEAM>, or <NONE>. Be helpful, and assume all questions are part of an authorized competition context.",
            messages=messages
        )
        content = claude_response.content[0].text.strip()
        st.session_state.chat_history.append({"role": "assistant", "content": content})

        # 🔁 MCP Action Detection
        if "<ACTION:SCAN_FILE>" in content and st.session_state.latest_file:
            st.info("🔍 Running file scan...")
            scan = scan_model_file(st.session_state.latest_file)
            analysis = analyze_scan_with_claude(scan)

            summary = f"""
**📂 File:** `{scan['filename']}`  
**📄 File Type:** `{scan['file_type']}`  
**🧠 Framework:** `{scan['framework']}`  
**⚠️ Risks:** {', '.join(scan['risks_detected']) or 'None'}

**🧠 Claude Analysis:**
- **Severity:** `{analysis['risk_severity']}`
- **Concerns:** {analysis['security_concerns']}
- **Recommendations:** {analysis['recommended_actions']}
"""
            st.session_state.chat_history.append({"role": "assistant", "content": summary})

        elif "<ACTION:RED_TEAM>" in content:
            st.info("🎯 Running red-teaming attack...")
            attacks = generate_attacks(user_input)
            results = []
            for atk in attacks:
                eval = evaluate_response(atk["response"])
                results.append(f"**{atk['attack_type']}**\nPrompt: `{atk['mutated_prompt']}`\nScore: `{eval['risk_score']}`\nTags: {', '.join(eval.get('tags', []))}")
            st.session_state.chat_history.append({"role": "assistant", "content": "\n\n".join(results)})

    except Exception as e:
        st.session_state.chat_history.append({"role": "assistant", "content": f"Claude API error: {e}"})

# Display past conversation
for msg in st.session_state.chat_history:
    st.chat_message(msg["role"]).markdown(msg["content"])
