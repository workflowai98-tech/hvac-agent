import streamlit as st
import anthropic

client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
SYSTEM_PROMPT = """You are Max, a friendly AI assistant for Prestige Air, a professional HVAC company serving the Dallas area.

Your job is to:
- Help customers troubleshoot common heating and cooling issues
- Answer questions about HVAC maintenance, air quality, and repairs
- Collect the customer's name and phone number when they need a technician
- Direct urgent issues to call the office directly at (555) 123-4567

Always be friendly, clear, and avoid heavy technical jargon. Never diagnose a problem with 100% certainty — always recommend a service call for anything serious. You represent this company professionally."""

st.title("Max — HVAC AI Assistant")
st.caption("Prestige Air | Dallas, TX")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask me anything about your HVAC system..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=st.session_state.messages
        )
        reply = response.content[0].text
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})