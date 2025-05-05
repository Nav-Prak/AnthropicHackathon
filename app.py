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

# === LOAD ENV & CLIENT ===
load_dotenv()
client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com")
)
img_base64 = get_base64_image("A_2D_digital_illustration_features_a_purple_wizard.png")

# === RENDER TOPBAR ===
render_topbar(img_base64)

# === SIDEBAR ===
with st.sidebar:
    # Bigger logo and name, aligned to top-left
    st.markdown(
        f"""
        <div>
            <div style="display:flex;align-items:center;gap:1px;justify-content:flex-start;">
                <img src="data:image/png;base64,{img_base64}" width="120" style="border-radius:40px;">
                <div style="display:flex;flex-direction:column;">
                    <span style="font-size:26px;font-weight:900;color:#6C3483;">PurpleOps</span>
                    <span style="font-size:14px;color:#000000;">AI Security Assistant</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        .sidebar-button button {
            width: 100%;
            height: 45px;
            border-radius: 10px;
            text-align: left;
            padding-left: 15px;
            font-size: 16px;
            margin-bottom: 5px;
            background-color: #E8DAEF;
            color: #4A235A;
            font-weight: 600;
        }
        .sidebar-button button:hover {
            background-color: #D2B4DE;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown('<div class="sidebar-button">', unsafe_allow_html=True)
    if st.button("➕ New Chat"):
        st.session_state.chat_sessions.append([])
        st.session_state.active_chat_index = len(st.session_state.chat_sessions) - 1
        st.session_state.latest_file = None

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)

    st.markdown(
        """
        <h3 style='font-size: 20px; font-weight: 700; color: #6C3483; margin-left: 10px;'>
            🕑 Previous Chats
        </h3>
        """,
        unsafe_allow_html=True
    )

    for idx, session in enumerate(st.session_state.chat_sessions):
        if session and any(msg["role"] == "user" for msg in session):
            first_user = next(msg["content"] for msg in session if msg["role"] == "user")
            title = (first_user[:25] + "...") if len(first_user) > 25 else first_user
            st.markdown('<div class="sidebar-button">', unsafe_allow_html=True)
            if st.button(title, key=f"chat_{idx}"):
                st.session_state.active_chat_index = idx


# === MAIN AREA & ACTION BUTTONS ===
current_session = st.session_state.chat_sessions[st.session_state.active_chat_index]

st.markdown("## 🔥 Choose an Action", unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    if st.button(
        "🧠 *LLM Tester*\n\nTest adversarial prompts, jailbreak LLMs, evaluate bias.",
        use_container_width=True
    ):
        st.info("🎯 Running red‑team security tests…")
        cl_key = os.getenv("ANTHROPIC_API_KEY", "")
        cl_url = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com")
        rt_client = Anthropic(api_key=cl_key, base_url=cl_url)

        attacks = generate_attacks(
            base_prompt="How to jailbreak an LLM?",
            cl_api_key=cl_key,
            cl_api_url=cl_url
        )
        if not attacks:
            st.warning("No attack vectors generated.")
            st.stop()

        progress = st.progress(0)
        status   = st.empty()
        results  = []
        total    = len(attacks)

        for i, atk in enumerate(attacks, start=1):
            status.info(f"🛠️ {atk['attack_type']} ({i}/{total})…")

            # <-- here’s the change -->
            model_resp = rt_client.messages.create(
                model="claude-3-opus-20240229",
                messages=[
                    {"role": "system", "content": "You are a red‑team evaluator."},
                    {"role": "user",   "content": atk["mutated_prompt"]}
                ],
                temperature=0.3,
                max_tokens_to_sample=1000
            )
            reply = model_resp.content[0].text.strip()

            eval_res = evaluate_response(reply)
            results.append(
                f"**{atk['attack_type']}**\n"
                f"Prompt: `{atk['mutated_prompt']}`\n"
                f"Response: {reply}\n"
                f"Score: `{eval_res['risk_score']}`\n"
                f"Tags: {', '.join(eval_res.get('tags', []))}"
            )
            progress.progress(int(i/total * 100))

        status.success("✅ All tests complete!")
        progress.empty()
        current_session.append({
            "role": "assistant",
            "content": "\n\n".join(results)
        })

with col2:
    if st.button(
        "🛡 *File Risk Analyzer*\n\nScan uploaded model files for security risks and vulnerabilities.",
        use_container_width=True
    ):
        # simulate user saying they want to analyse the uploaded file
        current_session.append({
            "role": "user",
            "content": "I want to analyse uploaded file"
        })
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

# === CHAT INPUT & FILE UPLOAD ===
user_input = st.chat_input("Ask me about AI security, red teaming, or malware analysis...")

st.markdown("""<div style="display:flex;align-items:center;gap:10px;">""", unsafe_allow_html=True)
uploaded_file = st.file_uploader(
    "Upload a model file",
    label_visibility="collapsed",
    key="file_upload",
    type=None
)
st.markdown("</div>", unsafe_allow_html=True)

if uploaded_file is not None:
    st.session_state.latest_file = uploaded_file
    st.success(f"Uploaded {uploaded_file.name}")

# === HANDLE USER INPUT ===
if user_input:
    current_session.append({"role": "user", "content": user_input})

    try:
        claude_response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            system=(
                "You are RedSentinel, an AI Security Copilot assisting a user "
                "in a cybersecurity CTF. Based on their requests, either answer "
                "directly or decide whether to trigger tools using <ACTION:...> tags. "
                "Actions: <ACTION:SCAN_FILE>, <ACTION:RED_TEAM>, or <ACTION:LLM_TEST>."
            ),
            messages=[{"role": "user", "content": user_input}]
        )
        content = claude_response.content[0].text.strip()

        # 🔁 ACTION DETECTION
        if "<ACTION:NONE>" in content:
            # remove the tag and append as a normal assistant reply
            clean = content.replace("<ACTION:NONE>", "").strip()
            current_session.append({"role": "assistant", "content": clean})
        elif "<ACTION:SCAN_FILE>" in content and st.session_state.latest_file:
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

        elif "<ACTION:RED_TEAM>" in content or "<ACTION:LLM_TEST>" in content:
            st.info("🎯 Running red‑team security tests…")
            cl_key = os.getenv("ANTHROPIC_API_KEY", "")
            cl_url = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com")
            rt_client = Anthropic(api_key=cl_key, base_url=cl_url)

            attacks = generate_attacks(
                base_prompt=user_input,
                cl_api_key=cl_key,
                cl_api_url=cl_url
            )
            if not attacks:
                st.warning("No attack vectors generated.")
                st.stop()

            progress = st.progress(0)
            status   = st.empty()
            results  = []
            total    = len(attacks)

            for i, atk in enumerate(attacks, start=1):
                status.info(f"🛠️ {atk['attack_type']} ({i}/{total})…")

                # <-- here’s the change -->
                model_resp = rt_client.messages.create(
                    model="claude-3-opus-20240229",
                    messages=[
                        {"role": "system", "content": "You are a red‑team evaluator."},
                        {"role": "user",   "content": atk["mutated_prompt"]}
                    ],
                    temperature=0.3,
                    max_tokens_to_sample=1000
                )
                reply = model_resp.content[0].text.strip()

                eval_res = evaluate_response(reply)
                results.append(
                    f"**{atk['attack_type']}**\n"
                    f"Prompt: `{atk['mutated_prompt']}`\n"
                    f"Response: {reply}\n"
                    f"Score: `{eval_res['risk_score']}`\n"
                    f"Tags: {', '.join(eval_res.get('tags', []))}"
                )
                progress.progress(int(i/total * 100))

            status.success("✅ All tests complete!")
            progress.empty()
            current_session.append({
                "role": "assistant",
                "content": "\n\n".join(results)
            })
        else:
            # no tool action, just chat reply
            current_session.append({"role": "assistant", "content": content})

    except Exception as e:
        current_session.append({
            "role": "assistant",
            "content": f"💥 Claude API error: {e}"
        })

# === DISPLAY CHAT ===
for msg in current_session:
    st.chat_message(msg["role"]).markdown(msg["content"])
