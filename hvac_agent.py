import streamlit as st
import anthropic
import json
import re
import csv
import io
from datetime import datetime

# --- Page config ---
st.set_page_config(
    page_title="Max — Prestige Air",
    page_icon="❄️",
    layout="wide"
)

# --- Anthropic client ---
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# --- System prompt ---
SYSTEM_PROMPT = """You are Max, a friendly AI assistant for Prestige Air, a professional HVAC company serving the Dallas area.

Your job is to:
- Help customers troubleshoot common heating and cooling issues
- Answer questions about HVAC maintenance, air quality, and repairs
- Collect the customer's name and phone number when they need a technician
- Direct urgent issues to call the office directly at (555) 123-4567

LEAD CAPTURE RULE:
The moment a customer has provided both their full name AND a phone number (across any point in the conversation), append this exact tag on its own line at the very end of your response — after your normal message text:
[LEAD: {"name": "Their Full Name", "phone": "Their Phone Number"}]

Only append this tag once — the first time you have both pieces of information. Never repeat it. Never include it in your visible message text.

Always be friendly, clear, and avoid heavy technical jargon. Never diagnose a problem with 100% certainty — always recommend a service call for anything serious. You represent this company professionally."""


# --- Helper: extract and strip lead tag ---
def extract_lead(text):
    match = re.search(r'\[LEAD:\s*(\{.*?\})\]', text, re.DOTALL)
    if match:
        try:
            lead_data = json.loads(match.group(1))
            clean_text = re.sub(r'\s*\[LEAD:\s*\{.*?\}\]', '', text, flags=re.DOTALL).strip()
            return lead_data, clean_text
        except json.JSONDecodeError:
            pass
    return None, text


# --- Session state init ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "leads" not in st.session_state:
    st.session_state.leads = []
if "lead_keys" not in st.session_state:
    st.session_state.lead_keys = set()


# --- Sidebar ---
with st.sidebar:
    st.markdown("## ❄️ Prestige Air")
    st.markdown("**HVAC Services — Dallas, TX**")
    st.markdown("---")
    st.markdown("📞 **(555) 123-4567**")
    st.markdown("🕐 Mon–Fri: 8am – 6pm")
    st.markdown("🚨 Emergency: 24/7")
    st.markdown("---")

    lead_count = len(st.session_state.leads)
    st.markdown(f"### 🎯 Captured Leads ({lead_count})")

    if st.session_state.leads:
        for lead in reversed(st.session_state.leads):
            with st.container():
                st.markdown(f"**{lead['name']}**")
                st.markdown(f"📱 {lead['phone']}")
                st.caption(lead.get("time", ""))
            st.markdown("---")

        # CSV export
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["name", "phone", "time"])
        writer.writeheader()
        writer.writerows(st.session_state.leads)
        st.download_button(
            label="⬇️ Download Leads CSV",
            data=output.getvalue(),
            file_name=f"prestige_air_leads_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.caption("No leads yet. Max will capture name + phone automatically.")


# --- Main chat UI ---
st.title("Max — HVAC AI Assistant")
st.caption("Prestige Air | Dallas, TX · Powered by AI")

# Render chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about your HVAC system..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream assistant response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_reply = ""

        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=st.session_state.messages
        ) as stream:
            for chunk in stream.text_stream:
                full_reply += chunk
                # Strip lead tag from live display so it never shows to user
                display = re.sub(r'\s*\[LEAD:.*', '', full_reply, flags=re.DOTALL).strip()
                placeholder.markdown(display + "▌")

        # Final: extract lead, clean reply, render without cursor
        lead_data, clean_reply = extract_lead(full_reply)
        placeholder.markdown(clean_reply)

        # Store lead if captured and not a duplicate
        if lead_data:
            lead_key = f"{lead_data.get('name', '').lower().strip()}_{lead_data.get('phone', '').strip()}"
            if lead_key not in st.session_state.lead_keys:
                lead_data["time"] = datetime.now().strftime("%b %d, %I:%M %p")
                st.session_state.leads.append(lead_data)
                st.session_state.lead_keys.add(lead_key)
                st.success(f"✅ Lead captured: {lead_data['name']} — {lead_data['phone']}")
                st.rerun()

    # Save clean reply to history (no lead tag)
    st.session_state.messages.append({"role": "assistant", "content": clean_reply})
