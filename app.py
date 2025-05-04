import streamlit as st
import base64
import os
import json
from modules.file_scanner import scan_model_file
from modules.claude_analyzer import analyze_scan_with_claude
from modules.attacker import generate_attacks
from modules.evaluator import evaluate_response
from anthropic import Anthropic
from dotenv import load_dotenv

# --- CONFIG ---
st.set_page_config(
    page_title="Purple OPS",
    page_icon="🧙",  # Placeholding emoji until real logo embedded
    layout="wide",
)

# --- TOP BAR: Logo + Title ---
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:10px;padding:10px 0 20px 0;border-bottom:2px solid #D1C4E9;">
        <div style="position: relative; width: 60px; height: 30px;">
            <div style="
                width: 40px; 
                height: 20px; 
                background: #6C3483; 
                border-top-left-radius: 20px; 
                border-top-right-radius: 20px;
                position: absolute;
                top: 0;
                left: 10px;
            "></div>
            <div style="
                width: 60px; 
                height: 10px; 
                background: #5B2C6F;
                border-radius: 5px;
                position: absolute;
                bottom: 0;
                left: 0;
            "></div>
        </div>
        <h1 style="display:inline;color:#6C3483;font-size:2rem;margin:0;">Purple OPS - AI Security Assistant</h1>
    </div>
    """,
    unsafe_allow_html=True,
)


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        base64_bytes = base64.b64encode(img_file.read())
        base64_string = base64_bytes.decode()
    return base64_string

# Usage
img_base64 = get_base64_image("A_2D_digital_illustration_features_a_purple_wizard.png")  # Your cleaned hat

st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:10px;padding:10px 0 20px 0;border-bottom:2px solid #D1C4E9;">
        <img src="data:image/png;base64,{img_base64}" width="50" style="border-radius:8px;">
        <h1 style="display:inline;color:#6C3483;font-size:2rem;margin:0;">Purple OPS - AI Security Assistant</h1>
    </div>
    """,
    unsafe_allow_html=True,
)



# --- CUSTOM CSS ---
st.markdown(
    """
    <style>
      body {
        background-color: #F5F3FF;
      }
      .reportview-container .main {
        background-color: #F5F3FF;
      }
      .sidebar .sidebar-content {
        background-color: #D1C4E9;
      }
      h1, h2, h3 {
        color: #6C3483;
      }
      button, .stButton>button {
        background-color: #6C3483;
        color: white;
        border-radius: 8px;
      }
      input, textarea {
        background-color: #EDE7F6;
        border: 1px solid #B39DDB;
        border-radius: 5px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- LOAD API ---
load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- SIDEBAR: Past chats titles ---
with st.sidebar:
    st.header("Purple OPS")
    if "chat_history" in st.session_state:
        for msg in reversed(st.session_state.chat_history[-5:]):
            title = msg['content'][:30] + ('...' if len(msg['content']) > 30 else '')
            st.write(title)

# --- CHAT ENGINE ---
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

    messages = [{"role": "user", "content": user_input}]

    try:
        claude_response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            system="You are Purple OPS, an AI Security Copilot assisting users with CTF cybersecurity challenges. Help, analyze, or trigger tools using <ACTION:...>. Available actions: <ACTION:SCAN_FILE>, <ACTION:RED_TEAM>, or <NONE>.",
            messages=messages
        )
        content = claude_response.content[0].text.strip()
        st.session_state.chat_history.append({"role": "assistant", "content": content})

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

# --- RENDER CHAT ---
for msg in st.session_state.chat_history:
    st.chat_message(msg["role"]).markdown(msg["content"])
