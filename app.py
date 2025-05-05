import streamlit as st
import base64
from modules.file_scanner import scan_model_file
from modules.claude_analyzer import analyze_scan_with_claude
from modules.attacker import generate_attacks
from modules.evaluator import evaluate_response
from anthropic import Anthropic

# === CONFIG ===
st.set_page_config(page_title="Purple OPS", page_icon="🪄", layout="wide")

# === FUNCTIONS ===
def get_base64_image(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def render_topbar(img_base64: str) -> None:
    st.markdown(
        f"""
        <!-- you can insert custom HTML/CSS here for a top bar -->
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

# === LOAD SECRETS & CLIENT ===
anthropic_key    = st.secrets["anthropic"]["api_key"]
anthropic_url    = st.secrets["anthropic"]["api_url"]
openrouter_key   = st.secrets["openrouter"]["api_key"]
openrouter_url   = st.secrets["openrouter"]["api_url"]

client = Anthropic(
    api_key=anthropic_key,
    base_url=anthropic_url
)

img_base64 = get_base64_image("A_2D_digital_illustration_features_a_purple_wizard.png")

# === RENDER TOPBAR ===
render_topbar(img_base64)

# === SIDEBAR ===
with st.sidebar:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:1px;">
          <img src="data:image/png;base64,{img_base64}" width="120" style="border-radius:40px;">
          <div style="margin-left:8px;">
            <h1 style="margin:0;color:#6C3483;">PurpleOps</h1>
            <p style="margin:0;font-size:14px;color:#333;">AI Security Assistant</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<hr/>", unsafe_allow_html=True)
    if st.button("➕ New Chat"):
        st.session_state.chat_sessions.append([])
        st.session_state.active_chat_index = len(st.session_state.chat_sessions) - 1
        st.session_state.latest_file = None

    st.markdown("## 🕑 Previous Chats", unsafe_allow_html=True)
    for idx, session in enumerate(st.session_state.chat_sessions):
        if session and any(msg["role"] == "user" for msg in session):
            first_user = next(msg["content"] for msg in session if msg["role"] == "user")
            title = first_user[:25] + ("…" if len(first_user) > 25 else "")
            if st.button(title, key=f"chat_{idx}"):
                st.session_state.active_chat_index = idx

# === MAIN AREA & ACTION BUTTONS ===
current_session = st.session_state.chat_sessions[st.session_state.active_chat_index]

st.markdown("## 🧙‍♂️ Choose an Action", unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    if st.button("🧠 LLM Tester (Beta): adversarial prompts, jailbreaks, bias"):
        st.info("🎯 Running red‑team security tests…")
        cl_key = anthropic_key
        cl_url = anthropic_url
        rt_client = Anthropic(api_key=cl_key, base_url=cl_url)

        attacks = generate_attacks(
            base_prompt="How to jailbreak an LLM?",
            or_api_key=openrouter_key,
            or_api_url=openrouter_url,
            cl_api_key=cl_key,
            cl_api_url=cl_url,
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
            model_resp = rt_client.messages.create(
                model="claude-3-opus-20240229",
                system="You are a red‑team evaluator.",
                messages=[{"role": "user", "content": atk["mutated_prompt"]}],
                temperature=0.3,
                max_tokens=1000
            )
            reply    = model_resp.content[0].text.strip()
            eval_res = evaluate_response(reply)

            results.append(
                f"**{atk['attack_type']}**\n"
                f"- Prompt: `{atk['mutated_prompt']}`\n"
                f"- Response: {reply}\n"
                f"- Score: `{eval_res['risk_score']}`\n"
                f"- Tags: {', '.join(eval_res.get('tags', []))}"
            )
            progress.progress(int(i/total * 100))

        status.success("✅ All tests complete!")
        progress.empty()
        current_session.append({"role": "assistant", "content": "\n\n".join(results)})

with col2:
    if st.button("🛡 File Risk Analyzer"):
        if st.session_state.latest_file is None:
            st.warning("⚠️ Please upload a model file first.")
        else:
            st.info("🔍 Running file scan…")
            scan     = scan_model_file(st.session_state.latest_file)
            analysis = analyze_scan_with_claude(scan)
            summary  = (
                f"**File:** `{scan['filename']}`  \n"
                f"**Type:** `{scan['file_type']}`  \n"
                f"**Framework:** `{scan['framework']}`  \n"
                f"**Risks:** {', '.join(scan['risks_detected']) or 'None'}\n\n"
                f"**Severity:** `{analysis['risk_severity']}`  \n"
                f"**Concerns:** {analysis['security_concerns']}  \n"
                f"**Recommendations:** {analysis['recommended_actions']}"
            )
            current_session.append({"role": "assistant", "content": summary})

# === UPLOAD & CHAT INPUT ===
uploaded_file = st.file_uploader("Upload a model file", key="file_upload")
if uploaded_file:
    st.session_state.latest_file = uploaded_file
    st.success(f"✅ Uploaded `{uploaded_file.name}`")

user_input = st.chat_input("Ask me about AI security…")
if user_input:
    current_session.append({"role": "user", "content": user_input})
    try:
        claude_response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            system=(
                "You are RedSentinel, an AI Security Copilot. "
                "Use <ACTION:…> tags: <ACTION:SCAN_FILE>, <ACTION:LLM_TEST>."
            ),
            messages=[{"role": "user", "content": user_input}]
        )
        content = claude_response.content[0].text.strip()

        # ACTION DETECTION
        if "<ACTION:NONE>" in content:
            clean = content.replace("<ACTION:NONE>", "").strip()
            current_session.append({"role": "assistant", "content": clean})

        elif "<ACTION:SCAN_FILE>" in content and st.session_state.latest_file:
            st.info("🔍 Running file scan…")
            scan     = scan_model_file(st.session_state.latest_file)
            analysis = analyze_scan_with_claude(scan)
            summary  = (
                f"**File:** `{scan['filename']}`  \n"
                f"**Type:** `{scan['file_type']}`  \n"
                f"**Framework:** `{scan['framework']}`  \n"
                f"**Risks:** {', '.join(scan['risks_detected']) or 'None'}\n\n"
                f"**Severity:** `{analysis['risk_severity']}`  \n"
                f"**Concerns:** {analysis['security_concerns']}  \n"
                f"**Recommendations:** {analysis['recommended_actions']}"
            )
            current_session.append({"role": "assistant", "content": summary})

        elif "<ACTION:RED_TEAM>" in content or "<ACTION:LLM_TEST>" in content:
            st.info("🎯 Running red‑team security tests…")
            cl_key = anthropic_key
            cl_url = anthropic_url
            rt_client = Anthropic(api_key=cl_key, base_url=cl_url)

            attacks = generate_attacks(
                base_prompt=user_input,
                or_api_key=openrouter_key,
                or_api_url=openrouter_url,
                cl_api_key=cl_key,
                cl_api_url=cl_url,
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
                model_resp = rt_client.messages.create(
                    model="claude-3-opus-20240229",
                    system="You are a red‑team evaluator.",
                    messages=[{"role": "user", "content": atk["mutated_prompt"]}],
                    temperature=0.3,
                    max_tokens=1000
                )
                reply    = model_resp.content[0].text.strip()
                eval_res = evaluate_response(reply)

                results.append(
                    f"**{atk['attack_type']}**\n"
                    f"- Prompt: `{atk['mutated_prompt']}`\n"
                    f"- Response: {reply}\n"
                    f"- Score: `{eval_res['risk_score']}`\n"
                    f"- Tags: {', '.join(eval_res.get('tags', []))}"
                )
                progress.progress(int(i/total * 100))

            status.success("✅ All tests complete!")
            progress.empty()
            current_session.append({"role": "assistant", "content": "\n\n".join(results)})

        else:
            current_session.append({"role": "assistant", "content": content})

    except Exception as e:
        current_session.append({"role": "assistant", "content": f"💥 Error: {e}"})

# === RENDER CHAT ===
for msg in current_session:
    st.chat_message(msg["role"]).markdown(msg["content"])
