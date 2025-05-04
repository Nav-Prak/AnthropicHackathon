import streamlit as st
import os
import base64
from modules.file_scanner import scan_model_file
from modules.claude_analyzer import analyze_scan_with_claude
from modules.attacker import generate_attacks
from modules.evaluator import evaluate_response
from anthropic import Anthropic
from dotenv import load_dotenv

# === CONFIG ===
st.set_page_config(page_title="Purple OPS", page_icon="🪄", layout="wide")

# === FUNCTIONS ===
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        base64_bytes = base64.b64encode(img_file.read())
        return base64_bytes.decode()

def render_topbar(img_base64):
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;padding:10px 0 20px 0;border-bottom:2px solid #D1C4E9;">
            <img src="data:image/png;base64,{img_base64}" width="70" style="border-radius:8px;">
            <h1 style="display:inline;color:#6C3483;font-size:2rem;margin:0;">Purple OPS - AI Security Assistant</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

# === INITIALIZE SESSION STATES ===
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = [[]]
if "active_chat_index" not in st.session_state:
    st.session_state.active_chat_index = 0
if "latest_file" not in st.session_state:
    st.session_state.latest_file = None

# === LOADS ===
load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
img_base64 = get_base64_image("A_2D_digital_illustration_features_a_purple_wizard.png")

# === UI ===
render_topbar(img_base64)

# === SIDEBAR ===
with st.sidebar:
    if st.button("\u2795 New Chat"):
        st.session_state.chat_sessions.append([])
        st.session_state.active_chat_index = len(st.session_state.chat_sessions) - 1
        st.session_state.latest_file = None

    st.markdown("---")
    for idx, session in enumerate(st.session_state.chat_sessions):
        if session and any(msg["role"] == "user" for msg in session):
            first_user_message = next((msg["content"] for msg in session if msg["role"] == "user"), "New Chat")
            title = first_user_message[:30] + "..." if len(first_user_message) > 30 else first_user_message

            if st.button(title, key=f"chat_{idx}"):
                st.session_state.active_chat_index = idx

# === MAIN AREA ===
current_session = st.session_state.chat_sessions[st.session_state.active_chat_index]

# === INPUT AREA ===
st.markdown("""
<div style="display:flex;align-items:center;gap:10px;">
""", unsafe_allow_html=True)

user_input = st.chat_input("Ask me about AI security, red teaming, or malware analysis...")

uploaded_file = st.file_uploader("", label_visibility="collapsed", key="file_upload", type=None)

st.markdown("""
</div>
""", unsafe_allow_html=True)

if uploaded_file:
    st.session_state.latest_file = uploaded_file
    st.success(f"Uploaded `{uploaded_file.name}`")

if user_input:
    current_session.append({"role": "user", "content": user_input})

    messages = [{"role": "user", "content": user_input}]

    try:
        claude_response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            system="You are Purple OPS, a Red-Teaming Cybersecurity Copilot...",
            messages=messages
        )
        content = claude_response.content[0].text.strip()
        current_session.append({"role": "assistant", "content": content})

        if "<ACTION:SCAN_FILE>" in content and st.session_state.latest_file:
            st.info("\ud83d\udd0d Running file scan...")
            scan = scan_model_file(st.session_state.latest_file)
            analysis = analyze_scan_with_claude(scan)

            summary = f"""
**\ud83d\udcc2 File:** `{scan['filename']}`  
**\ud83d\udcc4 File Type:** `{scan['file_type']}`  
**\ud83e\udde0 Framework:** `{scan['framework']}`  
**\u26a0\ufe0f Risks:** {', '.join(scan['risks_detected']) or 'None'}

**\ud83e\udde0 Claude Analysis:**
- **Severity:** `{analysis['risk_severity']}`
- **Concerns:** {analysis['security_concerns']}
- **Recommendations:** {analysis['recommended_actions']}
"""
            current_session.append({"role": "assistant", "content": summary})

        elif "<ACTION:RED_TEAM>" in content:
            st.info("\ud83c\udfaf Running red-teaming attack...")
            attacks = generate_attacks(user_input)
            results = []
            for atk in attacks:
                eval = evaluate_response(atk["response"])
                results.append(f"**{atk['attack_type']}**\nPrompt: `{atk['mutated_prompt']}`\nScore: `{eval['risk_score']}`\nTags: {', '.join(eval.get('tags', []))}")
            current_session.append({"role": "assistant", "content": "\n\n".join(results)})

    except Exception as e:
        current_session.append({"role": "assistant", "content": f"Claude API error: {e}"})

# === DISPLAY CHAT ===
for msg in current_session:
    st.chat_message(msg["role"]).markdown(msg["content"])
