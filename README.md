# Project DEMO link:
https://vduong421-health-agent-final-app-cthqyz.streamlit.app/

# SJSU Spartan Health Agent

A minimal, production-style demo for embedding an **IBM watsonx.ai Agent** into a modern web app.

This project is designed to be both **portfolio-ready** and **product-ready**:

- Clean separation between a branded landing experience and an agent chat interface  
- Straightforward, reusable integration pattern with **IBM watsonx.ai**

## Overview

**SJSU Spartan Health Agent** is an AI-powered wellness coach built with **Streamlit** and **IBM watsonx.ai**.  
It helps students (and anyone) generate personalized guidance based on:

- Age  
- Height & weight  
- Activity level  
- Goal (lose / maintain / gain)

## Core Capabilities

The agent can generate:

- Personalized daily meal plans  
- Calorie and macro targets  
- Mini grocery lists  
- Quick food swaps and suggestions


---

## What This Project Demonstrates

- **Realistic UX flow**
  - `Home` page with hero text, CTA buttons, and background media.
  - `About this Project` page that explains the architecture and business use case.
  - `Chat with AI Agent` page: full chat interface wired to an IBM watsonx.ai Agent.

- **Agent integration pattern**
  - Uses `IBM_CLOUD_API_KEY` and `WATSONX_AGENT_URL` from `.env`.
  - Sends user messages plus optional profile variables to the backend Agent.
  - Tries multiple payload formats (`candidate_payloads`) for compatibility with
    different watsonx.ai / Agent deployments.
  - Central `extract_text` function to normalize diverse response JSON shapes.

- **Personalization**
  - Sidebar form for **age, sex, height, weight, activity level, goal**.
  - Optionally sends this as `variables.profile` so the Agent can tailor responses.

- **UI / Frontend**
  - Built with **Streamlit** for a lightweight Python-first UI.
  - Fullscreen **video or image backgrounds** driven by local assets:
    - `./stock/base` → background for Home + About.
    - `./stock` → background for Chat page.
  - Behavior:
    - Prefer a short `mp4` (≤ 6 MB) as looping background.
    - Fallback to png/jpg/jpeg.
    - Fallback gradient if no media is present.
  - Custom sidebar background color to visually separate profile settings.

- **Code structure**
  - Single-file app for easy review (`app.py`).
  - Clear separation:
    - Background helpers
    - IAM token + agent call utilities
    - UI renderers: `render_home`, `render_description`, `render_chat`
    - Simple router using `st.session_state["page"]`.

---

## Tech Stack

- Python 3.10+
- Streamlit
- requests
- python-dotenv
- IBM watsonx.ai / Agent endpoint

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/vduong/Health-Agent-Final.git
cd Health-Agent-Final
```

### 2. Create & activate a virtual environment (recommended)

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Minimal `requirements.txt`:

```txt
streamlit
requests
python-dotenv
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
IBM_CLOUD_API_KEY=your-ibm-api-key
WATSONX_AGENT_URL=https://your-watsonx-agent-endpoint/ai_service?version=2021-05-01
```

> Keep this file private. Do **not** commit it.

### 5. Add background media (optional but recommended)

Project layout:

```text
project_root/
  app.py
  stock/
    base/
      a.mp4              # or background.png / .jpg for Home + About
    chat_bg.mp4          # or image(s) for Chat page (optional)
```

Rules:

- The app:
  - Looks for `*.mp4` in the folder.
  - Uses the **first mp4 ≤ 6 MB** as a looping fullscreen background.
  - Else uses the first png/jpg/jpeg.
  - Else falls back to a dark gradient.

### 6. Run the app

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Architecture Overview

1. **Routing**
   - `st.session_state["page"]` stores which view to show.
   - `go("home" | "description" | "chat")` updates it and triggers `st.rerun()`.

2. **Background handling**
   - `set_base_background_from_stock()`:
     - Uses `/stock/base` for Home + About.
   - `set_background_from_stock()`:
     - Uses `/stock` for Chat.
   - `_apply_stock_background()`:
     - Picks media and injects HTML/CSS that renders a fullscreen video/image behind Streamlit.

3. **Chat pipeline**
   - User input → `handle_message()`.
   - `handle_message()`:
     - Appends to `st.session_state.messages`.
     - Calls `call_agent()` for a response.
   - `call_agent()`:
     - Requests IAM token via `get_iam_token()`.
     - Iterates through `candidate_payloads(...)` until the Agent returns successfully.
     - Uses `extract_text()` to convert different response formats into plain text.

4. **Profile variables**
   - Sidebar → `build_profile()` → `st.session_state["profile_vars"]`.
   - When enabled, profile is sent as `variables.profile` to the Agent.

---

## Using This as a Portfolio Piece

When presenting this project:

- Explain that this is a **reusable AI integration template**:
  - Any company can plug in their own IBM watsonx.ai Agent endpoint.
  - Frontend stays the same; branding and content are easily customizable.
- Highlight:
  - Secure secret management via `.env`.
  - Clean separation of concerns (UI vs API vs layout).
  - Support for personalization and future domain-specific tools.
- Suggest extensions:
  - Connect to internal APIs (appointments, recommendations, FAQs).
  - Role-based experiences for patients, students, or customers.

---

## License

MIT License  
Copyright (c) 2025 Van Duong
