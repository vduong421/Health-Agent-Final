import os
import json
import base64
from pathlib import Path
from typing import Any, Dict, List

import requests
import streamlit as st
from dotenv import load_dotenv

# =========================
# ENV / Secrets
# =========================
load_dotenv()
API_KEY = os.getenv("IBM_CLOUD_API_KEY")
DEPLOYMENT_URL = os.getenv("WATSONX_AGENT_URL")  # Public .../ai_service?version=2021-05-01
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

if not API_KEY or not DEPLOYMENT_URL:
    raise SystemExit(
        "Missing IBM_CLOUD_API_KEY or WATSONX_AGENT_URL in .env. "
        "Put .env next to app.py with those two keys."
    )

# =========================
# Shared helpers: backgrounds
# =========================
def _set_fullscreen_video_bg(b64_video: str):
    st.markdown(
        f"""
        <style>
        html, body, .stApp {{
            height: 100%;
        }}

        .stApp {{
            background: transparent;
        }}

        /* Dark overlay so text is readable */
        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.45);
            z-index: -1;
        }}

        #video-bg {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            z-index: -2;
        }}

        .block-container {{
            background: transparent;
        }}

        [data-testid="stSidebar"] > div {{
            # background: rgba(0,0,0,0.88);
            background: #181a21;
        }}

        [data-testid="stChatInput"] > div {{
            background: #14151a;
            border-radius: 999px;
            padding: 0.25rem 0.5rem;
        }}

        .stChatInputContainer, footer {{
            background: transparent !important;
        }}
        </style>

        <video autoplay loop muted playsinline id="video-bg">
            <source src="data:video/mp4;base64,{b64_video}" type="video/mp4">
        </video>
        """,
        unsafe_allow_html=True,
    )


def _set_fullscreen_image_bg(b64_img: str):
    st.markdown(
        f"""
        <style>
        html, body, .stApp {{
            height: 100%;
        }}

        .stApp {{
            background: transparent;
        }}

        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            background-image: url("data:image/png;base64,{b64_img}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            filter: brightness(0.55);
            z-index: -1;
        }}

        .block-container {{
            background: transparent;
        }}

        [data-testid="stSidebar"] > div {{
            background: rgba(0,0,0,0.88);
        }}

        [data-testid="stChatInput"] > div {{
            background: #14151a;
            border-radius: 999px;
            padding: 0.25rem 0.5rem;
        }}

        .stChatInputContainer, footer {{
            background: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _apply_stock_background(folder: Path):
    """
    Prefer a small mp4, else one image, else no-op.
    """
    if not folder.exists():
        return

    MAX_INLINE_BYTES = 6 * 1024 * 1024  # 6 MB safety cap

    # Prefer mp4
    video_files = sorted(folder.glob("*.mp4"))
    if video_files:
        vf = video_files[0]
        if vf.stat().st_size <= MAX_INLINE_BYTES:
            with open(vf, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            _set_fullscreen_video_bg(b64)
            return

    # Else fallback to image
    img_path = None
    for ext in ("png", "jpg", "jpeg"):
        files = sorted(folder.glob(f"*.{ext}"))
        if files:
            img_path = files[0]
            break

    if not img_path:
        return

    if img_path.stat().st_size > MAX_INLINE_BYTES:
        return

    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    _set_fullscreen_image_bg(b64)


# Public helpers: which folder to use
def set_background_from_stock():
    """Chat page background from /stock."""
    _apply_stock_background(Path("stock"))


def set_base_background_from_stock():
    """Base + description page background from /stock/base or gradient fallback."""
    base_folder = Path("stock/base")
    if base_folder.exists():
        _apply_stock_background(base_folder)
    else:
        st.markdown(
            """
            <style>
            html, body, .stApp {
                height: 100%;
            }
            .stApp {
                background: radial-gradient(circle at top left, #222 0%, #050608 55%, #000 100%);
            }
            .block-container {
                background: transparent;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

# =========================
# IAM token (cached)
# =========================
@st.cache_data(ttl=300)
def get_iam_token(api_key: str) -> str:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key,
    }
    r = requests.post(IAM_TOKEN_URL, headers=headers, data=data, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

# =========================
# Helpers
# =========================
def num_from_str(s: str, default: float | None = None):
    try:
        return float("".join(ch for ch in s if (ch.isdigit() or ch == ".")))
    except Exception:
        return default


def build_profile(side: Dict[str, Any]) -> Dict[str, Any]:
    prof = {
        "age": side.get("age"),
        "sex": side.get("sex"),
        "height_cm": num_from_str(side.get("height", "")),
        "weight_kg": num_from_str(side.get("weight", "")),
        "activity": side.get("activity"),
        "goal": side.get("goal"),
    }
    return {k: v for k, v in prof.items() if v is not None}


def quick_start_plan_prompt(profile: Dict[str, Any]) -> str:
    if not profile:
        return (
            "Make my plan for today. I am 22, 175 cm, 78 kg, male, "
            "moderate, goal lose weight, vegetarian, budget on."
        )

    age = int(profile.get("age", 22))
    h = int(profile.get("height_cm", 175))
    w = int(profile.get("weight_kg", 78))
    sex = profile.get("sex", "male")
    activity = profile.get("activity", "moderate")
    goal = profile.get("goal", "lose")

    goal_phrase = {
        "lose": "goal lose weight",
        "maintain": "goal maintain weight",
        "gain": "goal gain weight",
    }.get(goal, "goal lose weight")

    return (
        f"Make my plan for today. I am {age}, {h} cm, {w} kg, {sex}, "
        f"{activity}, {goal_phrase}, vegetarian, budget on."
    )

# =========================
# Response extractor
# =========================
def extract_text(j: Any) -> str:
    if isinstance(j, dict):
        # Agent-style
        out = j.get("output")
        if isinstance(out, dict):
            if isinstance(out.get("text"), str) and out["text"].strip():
                return out["text"]

            gen = out.get("generic")
            if isinstance(gen, list):
                texts = [
                    it.get("text")
                    for it in gen
                    if isinstance(it, dict) and isinstance(it.get("text"), str)
                ]
                if texts:
                    return "\n\n".join(texts)

            msgs = out.get("messages")
            if isinstance(msgs, list):
                buf: List[str] = []
                for m in msgs:
                    for c in (m.get("content") or []):
                        if isinstance(c, dict) and isinstance(c.get("text"), str):
                            buf.append(c["text"])
                if buf:
                    return "\n\n".join(buf)

        # FM chat-style
        choices = j.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {})
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(content, list):
                texts = [
                    b.get("text")
                    for b in content
                    if isinstance(b, dict) and isinstance(b.get("text"), str)
                ]
                if texts:
                    return "\n\n".join(texts)

        # FM text-style
        res = j.get("results")
        if isinstance(res, list):
            for it in res:
                if isinstance(it, dict):
                    txt = it.get("generated_text") or it.get("output") or it.get("text")
                    if isinstance(txt, str) and txt.strip():
                        return txt

    return json.dumps(j, ensure_ascii=False, indent=2)

# =========================
# Payload candidates
# =========================
def candidate_payloads(user_text: str, variables: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"input": {"messages": [{"role": "user", "content": user_text}], "variables": variables}},
        {
            "input": {
                "messages": [
                    {"role": "user", "content": [{"type": "input_text", "text": user_text}]}
                ],
                "variables": variables,
            }
        },
        {
            "input": {
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": user_text}]}
                ],
                "variables": variables,
            }
        },
        {"input": [{"role": "user", "content": user_text}], "variables": variables},
        {
            "input": [
                {"role": "user", "content": [{"type": "text", "text": user_text}]}
            ],
            "variables": variables,
        },
        {"messages": [{"role": "user", "content": user_text}], "variables": variables},
        {"input": {"text": user_text, "variables": variables}},
    ]

# =========================
# Call Agent
# =========================
def call_agent(user_text: str, profile_vars: Dict[str, Any], send_profile: bool) -> str:
    token = get_iam_token(API_KEY)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    variables: Dict[str, Any] = {}
    if send_profile and profile_vars:
        variables["profile"] = profile_vars

    last_payload, last_error = None, None

    for payload in candidate_payloads(user_text, variables):
        last_payload = payload
        r = requests.post(DEPLOYMENT_URL, headers=headers, json=payload, timeout=90)

        if r.ok:
            try:
                return extract_text(r.json())
            except Exception:
                return r.text

        try:
            last_error = {"status_code": r.status_code, "body": r.json()}
        except Exception:
            last_error = {"status_code": r.status_code, "body": r.text[:1500]}

    raise RuntimeError(
        "Agent call failed (payload shapes tried). URL: "
        f"{DEPLOYMENT_URL}\nLast payload: {json.dumps(last_payload, ensure_ascii=False)}\n"
        f"Response: {json.dumps(last_error, ensure_ascii=False)}"
    )

# =========================
# Streamlit page setup
# =========================
st.set_page_config(
    page_title="SJSU Spartan Health Agent",
    page_icon="💪",
    layout="wide",
)

if "page" not in st.session_state:
    st.session_state["page"] = "home"
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "profile_vars" not in st.session_state:
    st.session_state["profile_vars"] = {}
if "queued_input" not in st.session_state:
    st.session_state["queued_input"] = None
if "quick_used" not in st.session_state:
    st.session_state["quick_used"] = bool(st.session_state["messages"])


def go(page: str):
    st.session_state["page"] = page
    st.rerun()

# =========================
# Page renderers
# =========================
def render_nav_bar():
    cols = st.columns([1, 1, 6])
    with cols[0]:
        if st.button("🏠 Home", use_container_width=True):
            go("home")
    with cols[1]:
        if st.button("ℹ️ Description", use_container_width=True):
            go("description")


def render_home():
    set_base_background_from_stock()

    # Slight vertical offset so it feels centered but always visible
    st.markdown(
        """
        <div style="margin-top:12vh;">
          <h1 style="color:#ffffff; font-weight:700; margin-bottom:0.2rem;">
            SJSU Spartan Health Agent Demo
          </h1>
          <p style="color:#f5f5f5; max-width:720px; font-size:0.98rem;">
            This landing page shows how any commercial website can embed an IBM watsonx.ai powered
            assistant. Choose a page below to explore.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 Chat with AI Agent", use_container_width=True, type="primary"):
            go("chat")
    with col2:
        if st.button("ℹ️ About this Project", use_container_width=True):
            go("description")

    st.write("")
    st.markdown(
        """
        <div style="color:#eeeeee; max-width:780px; font-size:0.9rem; margin-top:2rem;">
          In a real client deployment, this screen could be your product page, clinic site,
          campus portal, or e-commerce homepage. The <b>Chat with AI Agent</b> button launches
          a dedicated assistant that understands your users, your data, and your brand.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_description():
    set_base_background_from_stock()
    render_nav_bar()

    st.markdown(
        """
        <h2 style="color:#ffffff; font-weight:650; margin-bottom:0.5rem; margin-top:1.5rem;">
          About the SJSU Spartan Health Agent
        </h2>
        <p style="color:#f5f5f5; font-size:0.95rem; max-width:900px;">
          This demo showcases how an <b>IBM watsonx.ai</b>-powered agent can be embedded into any
          modern website as a smart assistant for health, fitness, or wellness services.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <ul style="color:#eeeeee; font-size:0.9rem; max-width:900px;">
          <li><b>Front-end:</b> Streamlit single-page experience with a landing menu and dedicated chat UI.</li>
          <li><b>Brand-ready:</b> The base page can be customized with your logo, colors, and media in
              <code>./stock/base</code> (video or image).</li>
          <li><b>Secure integration:</b> Uses an IBM Cloud API key and deployment URL from <code>.env</code>,
              never hard-coded secrets.</li>
          <li><b>Personalization:</b> Optional user profile (age, height, weight, activity, goal) is sent as
              structured variables to the agent so responses can be tailored.</li>
          <li><b>Robust calling logic:</b> Multiple payload formats are tried automatically so the same UI can
              adapt to different watsonx.ai / Agent deployments without code changes.</li>
          <li><b>Drop-in widget concept:</b> In a production website, the “Chat with AI Agent” button becomes a
              floating chat bubble or sidebar assistant that supports customers 24/7.</li>
        </ul>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <p style="color:#cccccc; font-size:0.9rem; max-width:900px; margin-top:1.5rem;">
          This is an <b>agent integration pattern</b>:
          your landing page (product, clinic, campus, store, etc.) plus a connected AI
          powered by IBM watsonx.ai that can use profiles and internal data securely.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button("👉 Jump into the live Agent Chat", type="primary"):
        go("chat")


def render_chat():
    set_background_from_stock()
    render_nav_bar()

    st.markdown(
        """
        <h1 style="color:#ffffff; font-weight:700; margin-bottom:0.2rem; margin-top:1.5rem;">
          SJSU Spartan Health Agent
        </h1>
        <p style="color:#f5f5f5; margin-top:0;">
          Chat with your IBM watsonx.ai health agent.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar profile
    with st.sidebar:
        st.subheader("Optional profile (sent as Agent variables)")
        age = st.number_input("Age", min_value=10, max_value=100, value=22)
        sex = st.selectbox("Sex", ["male", "female"], index=0)
        height = st.text_input("Height (e.g., 175 cm)", "175 cm")
        weight = st.text_input("Weight (e.g., 78 kg)", "78 kg")
        activity = st.selectbox(
            "Activity",
            ["sedentary", "light", "moderate", "active", "very_active"],
            index=2,
        )
        goal = st.selectbox("Goal", ["lose", "maintain", "gain"], index=0)
        send_profile = st.checkbox(
            "Send profile to Agent as variables.profile",
            value=True,
        )

        if st.button("Save profile"):
            st.session_state["profile_vars"] = build_profile(
                {
                    "age": age,
                    "sex": sex,
                    "height": height,
                    "weight": weight,
                    "activity": activity,
                    "goal": goal,
                }
            )
            st.success("Profile saved for this session.")

    # Chat handler
    def handle_message(user_msg: str):
        if not st.session_state.get("quick_used", False):
            st.session_state["quick_used"] = True

        st.session_state["messages"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("_Thinking…_")
            try:
                reply = call_agent(
                    user_msg,
                    st.session_state["profile_vars"],
                    send_profile,
                )
            except Exception as e:
                reply = f"Sorry, the agent could not respond.\n\n{e}"
            placeholder.markdown(reply)

        st.session_state["messages"].append({"role": "assistant", "content": reply})

    # Quick starts
    if not st.session_state.get("quick_used", False):
        st.markdown(
            "<h3 style='color:#ffffff;'>Quick start samples</h3>",
            unsafe_allow_html=True,
        )

        profile = st.session_state["profile_vars"]
        plan_prompt = quick_start_plan_prompt(profile)

        def queue_prompt(text: str):
            st.session_state["queued_input"] = text
            st.session_state["quick_used"] = True
            st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            if st.button(plan_prompt, use_container_width=True):
                queue_prompt(plan_prompt)
        with c2:
            if st.button(
                "Make lunch vegetarian under 8 dollars and keep totals within ten percent.",
                use_container_width=True,
            ):
                queue_prompt(
                    "Make lunch vegetarian under 8 dollars and keep totals within ten percent."
                )

        c3, c4 = st.columns(2)
        with c3:
            if st.button(
                "End of day recap. I ate breakfast as planned, swapped lunch to tofu stir fry, skipped the snack.",
                use_container_width=True,
            ):
                queue_prompt(
                    "End of day recap. I ate breakfast as planned, swapped lunch to tofu stir fry, skipped the snack."
                )
        with c4:
            if st.button(
                "Show my mini grocery list from the plan.",
                use_container_width=True,
            ):
                queue_prompt("Show my mini grocery list from the plan.")

    # Replay history
    for m in st.session_state["messages"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Handle queued quick-start once
    queued = st.session_state.get("queued_input")
    if queued:
        st.session_state["queued_input"] = None
        handle_message(queued)

    # Chat input
    user_msg = st.chat_input("Ask for a plan, swaps, macros, or a grocery list…")
    if user_msg:
        handle_message(user_msg)

# =========================
# Router
# =========================
page = st.session_state.get("page", "home")
if page == "home":
    render_home()
elif page == "description":
    render_description()
else:
    render_chat()
