import streamlit as st
import os
import base64
import anthropic
from modules.file_scanner import scan_model_file
from modules.claude_analyzer import analyze_scan_with_claude
from modules.attacker import generate_attacks
from modules.evaluator import evaluate_response
from anthropic import Anthropic
from dotenv import load_dotenv

# === CONFIG ===
st.set_page_config(page_title="Purple OPS", page_icon="🪄", layout="wide")

# === FUNCTIONS ===
def get_base64_image(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def render_topbar(img_base64: str) -> None:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;
                    padding:10px 0 20px 0;
                    border-bottom:2px solid #D1C4E9;">
            <img src="data:image/png;base64,{img_base64}" width="70"
                 style="border-radius:8px;">
            <h1 style="display:inline;color:#6C3483;
                       font-size:2rem;margin:0;">
              Purple OPS - AI Security Assistant
            </h1>
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
# instantiate main Claude client with optional base_url override
client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com")
)
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
            first_user = next(msg["content"] for msg in session if msg["role"] == "user")
            title = (first_user[:30] + "...") if len(first_user) > 30 else first_user
            if st.button(title, key=f"chat_{idx}"):
                st.session_state.active_chat_index = idx

# === MAIN AREA ===
current_session = st.session_state.chat_sessions[st.session_state.active_chat_index]

# === INPUT AREA ===
st.markdown("""<div style="display:flex;align-items:center;gap:10px;">""", unsafe_allow_html=True)

user_input = st.chat_input("Ask me about AI security, red teaming, or malware analysis...")
uploaded_file = st.file_uploader(
    "Upload a model file",
    label_visibility="collapsed",
    key="file_upload",
    type=None
)

st.markdown("</div>", unsafe_allow_html=True)

if uploaded_file is not None:
    st.session_state.latest_file = uploaded_file
    st.success(f"Uploaded `{uploaded_file.name}`")

if user_input:
    # add user message
    current_session.append({"role": "user", "content": user_input})

    # call Claude
    try:
        claude_response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            system=(
                "You are RedSentinel, an AI Security Copilot assisting a user "
                "in a cybersecurity CTF. Based on their requests, either answer "
                "directly or decide whether to trigger tools using <ACTION:...> tags. "
                "Actions: <ACTION:SCAN_FILE>, <ACTION:RED_TEAM>, or <NONE>."
            ),
            messages=[{"role": "user", "content": user_input}]
        )
        content = claude_response.content[0].text.strip()
        current_session.append({"role": "assistant", "content": content})

        # 🔁 MCP Action Detection
        if "<ACTION:SCAN_FILE>" in content and st.session_state.latest_file:
            st.info("🔍 Running file scan...")
            scan = scan_model_file(st.session_state.latest_file)
            analysis = analyze_scan_with_claude(scan)
            summary = (
                f"**📂 File:** `{scan['filename']}`  \n"
                f"**📄 File Type:** `{scan['file_type']}`  \n"
                f"**🧠 Framework:** `{scan['framework']}`  \n"
                f"**⚠️ Risks:** {', '.join(scan['risks_detected']) or 'None'}\n\n"
                "**🧠 Claude Analysis:**\n"
                f"- **Severity:** `{analysis['risk_severity']}`\n"
                f"- **Concerns:** {analysis['security_concerns']}\n"
                f"- **Recommendations:** {analysis['recommended_actions']}"
            )
            current_session.append({"role": "assistant", "content": summary})

        elif "<ACTION:RED_TEAM>" in content:
            st.info("🎯 Prepare your red‑team attack")
            with st.form(key="red_team_form"):
                target = st.text_input(
                    "Target to attack",
                    placeholder="e.g. https://api.myservice.com/v1/endpoint"
                )
                api_key_input = st.text_input(
                    "Claude API Key",
                    type="password",
                    help="Paste your Anthropic/Claude API key here"
                )
                api_url_input = st.text_input(
                    "API Endpoint",
                    value="https://api.anthropic.com/v1/complete",
                    help="Override endpoint if needed"
                )
                run = st.form_submit_button("Run Red Team Attack")

            if run:
                if not (target and api_key_input):
                    st.error("⚠️ You must specify both a target and your API key.")
                else:
                    with st.spinner(f"Attacking `{target}`…"):
                        rt_client = anthropic.Client(
                            api_key=api_key_input,
                            base_url=api_url_input
                        )
                        attacks = generate_attacks(
                            base_prompt=user_input,
                            target=target,
                            cl_api_key=api_key_input,
                            cl_api_url=api_url_input
                        )
                        results = []
                        for atk in attacks:
                            resp = rt_client.completions.create(
                                model="claude-3-opus-20240229",
                                prompt=atk["mutated_prompt"],
                                max_tokens_to_sample=0
                            )
                            eval_res = evaluate_response(resp.completion)
                            results.append(
                                f"**{atk['attack_type']}**\n"
                                f"Prompt: `{atk['mutated_prompt']}`\n"
                                f"Score: `{eval_res['risk_score']}`\n"
                                f"Tags: {', '.join(eval_res.get('tags', []))}"
                            )
                        current_session.append({
                            "role": "assistant",
                            "content": "\n\n".join(results)
                        })

    except Exception as e:
        current_session.append({
            "role": "assistant",
            "content": f"💥 Claude API error: {e}"
        })

# === DISPLAY CHAT ===
for msg in current_session:
    st.chat_message(msg["role"]).markdown(msg["content"])
