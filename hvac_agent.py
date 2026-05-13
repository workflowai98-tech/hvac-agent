import streamlit as st
import anthropic
import json
import re
import csv
import io
from datetime import datetime, timedelta

# ============================================================
# WHITE-LABEL CONFIG — change this block per contractor client
# ============================================================
CONFIG = {
    "company_name": "Prestige Air",
    "ai_name": "Max",
    "tagline": "HVAC Services — Dallas, TX",
    "phone": "(555) 123-4567",
    "hours": "Mon–Fri: 8am – 6pm",
    "emergency": "24/7",
    "service_area": "Dallas, TX",
    "services": ["AC repair", "heating", "air quality", "maintenance", "installations"],
    "google_review_link": "https://g.page/r/your-google-review-link",
    "primary_color": "#1a73e8",
}

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title=f"{CONFIG['ai_name']} — {CONFIG['company_name']}",
    page_icon="❄️",
    layout="wide"
)

# ============================================================
# ANTHROPIC CLIENT
# ============================================================
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# ============================================================
# SYSTEM PROMPT (driven by config)
# ============================================================
def build_system_prompt():
    services = ", ".join(CONFIG["services"])
    return f"""You are {CONFIG['ai_name']}, a friendly AI assistant for {CONFIG['company_name']}, a professional contractor serving the {CONFIG['service_area']} area.

Your job is to:
- Help customers troubleshoot common issues related to: {services}
- Answer questions about maintenance, repairs, and air quality
- Collect the customer's name and phone number when they need a technician
- Direct urgent issues to call the office directly at {CONFIG['phone']}
- Help customers book appointments by collecting: preferred date, preferred time (morning/afternoon/evening), and a brief description of the issue

LEAD CAPTURE RULE:
The moment a customer provides both their full name AND a phone number, append this tag on its own line at the very end of your response:
[LEAD: {{"name": "Their Full Name", "phone": "Their Phone Number", "issue": "brief issue description"}}]
Only append this once. Never show it in your visible message.

BOOKING RULE:
When a customer wants to book an appointment and provides their preferred date, time, and issue description, append this tag at the very end:
[BOOKING: {{"name": "Customer Name", "phone": "Their Phone", "date": "preferred date", "time": "morning/afternoon/evening", "issue": "brief description"}}]
Only append this once. Never show it in your visible message.

Always be friendly, clear, and avoid heavy technical jargon. Never diagnose a problem with 100% certainty — always recommend a service call for anything serious. You represent {CONFIG['company_name']} professionally."""

# ============================================================
# SESSION STATE
# ============================================================
for key, default in {
    "messages": [],
    "leads": [],
    "lead_keys": set(),
    "bookings": [],
    "booking_keys": set(),
    "review_requests": [],
    "active_tab": "💬 Chat",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# HELPERS
# ============================================================
def extract_tag(text, tag_name):
    match = re.search(rf'\[{tag_name}:\s*(\{{.*?\}})\]', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            clean = re.sub(rf'\s*\[{tag_name}:\s*\{{.*?\}}\]', '', text, flags=re.DOTALL).strip()
            return data, clean
        except json.JSONDecodeError:
            pass
    return None, text

def time_now():
    return datetime.now().strftime("%b %d, %I:%M %p")

def leads_this_week():
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    count = 0
    for lead in st.session_state.leads:
        try:
            t = datetime.strptime(lead.get("time", ""), "%b %d, %I:%M %p").replace(year=now.year)
            if t >= week_ago:
                count += 1
        except:
            count += 1
    return count

def status_color(status):
    return {
        "New": "🔴",
        "Contacted": "🟡",
        "Booked": "🟢",
        "Closed": "⚫",
    }.get(status, "🔴")

# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
with st.sidebar:
    st.markdown(f"## ❄️ {CONFIG['company_name']}")
    st.markdown(f"**{CONFIG['tagline']}**")
    st.markdown("---")
    st.markdown(f"📞 **{CONFIG['phone']}**")
    st.markdown(f"🕐 {CONFIG['hours']}")
    st.markdown(f"🚨 Emergency: {CONFIG['emergency']}")
    st.markdown("---")

    tabs = ["💬 Chat", "📊 Dashboard", "⭐ Reviews", "📅 Bookings"]
    for tab in tabs:
        if st.button(tab, use_container_width=True,
                     type="primary" if st.session_state.active_tab == tab else "secondary"):
            st.session_state.active_tab = tab
            st.rerun()

    st.markdown("---")
    total_leads = len(st.session_state.leads)
    total_bookings = len(st.session_state.bookings)
    week_leads = leads_this_week()
    st.markdown(f"**Leads this week:** {week_leads}")
    st.markdown(f"**Total leads:** {total_leads}")
    st.markdown(f"**Bookings:** {total_bookings}")

# ============================================================
# TAB: CHAT
# ============================================================
if st.session_state.active_tab == "💬 Chat":
    st.title(f"{CONFIG['ai_name']} — AI Assistant")
    st.caption(f"{CONFIG['company_name']} | {CONFIG['service_area']} · Powered by AI")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(f"Ask {CONFIG['ai_name']} anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_reply = ""

            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=1024,
                system=build_system_prompt(),
                messages=st.session_state.messages
            ) as stream:
                for chunk in stream.text_stream:
                    full_reply += chunk
                    display = re.sub(r'\s*\[(LEAD|BOOKING):.*', '', full_reply, flags=re.DOTALL).strip()
                    placeholder.markdown(display + "▌")

            # Extract lead
            lead_data, full_reply = extract_tag(full_reply, "LEAD")
            # Extract booking
            booking_data, clean_reply = extract_tag(full_reply, "BOOKING")
            placeholder.markdown(clean_reply)

            # Store lead
            if lead_data:
                key = f"{lead_data.get('name','').lower()}_{lead_data.get('phone','')}"
                if key not in st.session_state.lead_keys:
                    lead_data["time"] = time_now()
                    lead_data["status"] = "New"
                    st.session_state.leads.append(lead_data)
                    st.session_state.lead_keys.add(key)
                    st.success(f"✅ Lead captured: {lead_data['name']} — {lead_data['phone']}")

            # Store booking
            if booking_data:
                key = f"{booking_data.get('name','').lower()}_{booking_data.get('date','')}"
                if key not in st.session_state.booking_keys:
                    booking_data["time"] = time_now()
                    booking_data["status"] = "Pending"
                    st.session_state.bookings.append(booking_data)
                    st.session_state.booking_keys.add(key)
                    st.success(f"📅 Booking requested: {booking_data.get('name')} — {booking_data.get('date')} {booking_data.get('time')}")

            st.session_state.messages.append({"role": "assistant", "content": clean_reply})

            if lead_data or booking_data:
                st.rerun()

# ============================================================
# TAB: DASHBOARD
# ============================================================
elif st.session_state.active_tab == "📊 Dashboard":
    st.title("📊 Lead Dashboard")
    st.caption(f"{CONFIG['company_name']} · All captured leads")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Leads", len(st.session_state.leads))
    col2.metric("This Week", leads_this_week())
    col3.metric("Bookings", len(st.session_state.bookings))

    st.markdown("---")

    if not st.session_state.leads:
        st.info("No leads yet. They'll appear here as Max captures them in chat.")
    else:
        st.markdown("### All Leads")
        for i, lead in enumerate(reversed(st.session_state.leads)):
            idx = len(st.session_state.leads) - 1 - i
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                col1.markdown(f"**{lead.get('name', '—')}**  \n📱 {lead.get('phone', '—')}")
                col2.markdown(f"🔧 {lead.get('issue', '—')[:40]}")
                col3.markdown(f"🕐 {lead.get('time', '—')}")
                status = lead.get("status", "New")
                new_status = col4.selectbox(
                    "Status",
                    ["New", "Contacted", "Booked", "Closed"],
                    index=["New", "Contacted", "Booked", "Closed"].index(status),
                    key=f"lead_status_{idx}",
                    label_visibility="collapsed"
                )
                if new_status != status:
                    st.session_state.leads[idx]["status"] = new_status
                    st.rerun()
            st.markdown("---")

        # CSV export
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["name", "phone", "issue", "time", "status"])
        writer.writeheader()
        writer.writerows(st.session_state.leads)
        st.download_button(
            "⬇️ Export Leads CSV",
            data=output.getvalue(),
            file_name=f"{CONFIG['company_name'].replace(' ', '_')}_leads_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# ============================================================
# TAB: REVIEWS
# ============================================================
elif st.session_state.active_tab == "⭐ Reviews":
    st.title("⭐ Review Requests")
    st.caption("Send post-job review requests via SMS")

    st.info("📱 **How this works:** Enter a customer's name and phone number after completing a job. Max generates the text message. In the full version (Phase 2), this sends automatically via Twilio.")

    with st.form("review_form"):
        col1, col2 = st.columns(2)
        customer_name = col1.text_input("Customer Name")
        customer_phone = col2.text_input("Customer Phone")
        submitted = st.form_submit_button("Generate Review Request", use_container_width=True)

    if submitted and customer_name and customer_phone:
        message = f"Hi {customer_name}! 👋 Thanks for choosing {CONFIG['company_name']}. We hope everything is working great! Would you mind leaving us a quick Google review? It really helps our small business: {CONFIG['google_review_link']} — The {CONFIG['company_name']} Team"

        st.markdown("### 📱 Preview SMS Message")
        st.code(message, language=None)

        request = {
            "name": customer_name,
            "phone": customer_phone,
            "message": message,
            "time": time_now(),
            "status": "Preview (not sent)"
        }
        st.session_state.review_requests.append(request)
        st.success(f"✅ Message ready for {customer_name} at {customer_phone}. (Twilio auto-send coming in Phase 2)")

    if st.session_state.review_requests:
        st.markdown("---")
        st.markdown("### Sent Requests")
        for req in reversed(st.session_state.review_requests):
            st.markdown(f"**{req['name']}** · {req['phone']} · {req['time']} · `{req['status']}`")

# ============================================================
# TAB: BOOKINGS
# ============================================================
elif st.session_state.active_tab == "📅 Bookings":
    st.title("📅 Appointment Bookings")
    st.caption("Appointments booked through Max chat or manually entered here")

    st.info("📅 **How this works:** Max collects booking requests in chat. In Phase 3, this syncs directly with Google Calendar and sends confirmation texts.")

    with st.form("manual_booking"):
        st.markdown("#### Add Manual Booking")
        col1, col2 = st.columns(2)
        b_name = col1.text_input("Customer Name")
        b_phone = col2.text_input("Phone Number")
        col3, col4 = st.columns(2)
        b_date = col3.date_input("Preferred Date")
        b_time = col4.selectbox("Preferred Time", ["Morning (8am–12pm)", "Afternoon (12pm–5pm)", "Evening (5pm–8pm)"])
        b_issue = st.text_input("Issue Description")
        add_booking = st.form_submit_button("Add Booking", use_container_width=True)

    if add_booking and b_name and b_phone:
        booking = {
            "name": b_name,
            "phone": b_phone,
            "date": str(b_date),
            "time": b_time,
            "issue": b_issue,
            "time_logged": time_now(),
            "status": "Pending"
        }
        st.session_state.bookings.append(booking)
        st.success(f"✅ Booking added for {b_name} on {b_date} — {b_time}")
        st.rerun()

    st.markdown("---")

    if not st.session_state.bookings:
        st.info("No bookings yet. They'll appear here when Max captures them in chat or when you add them manually.")
    else:
        st.markdown("### All Bookings")
        for i, booking in enumerate(reversed(st.session_state.bookings)):
            idx = len(st.session_state.bookings) - 1 - i
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                col1.markdown(f"**{booking.get('name')}**  \n📱 {booking.get('phone')}")
                col2.markdown(f"📅 {booking.get('date')}  \n🕐 {booking.get('time')}")
                col3.markdown(f"🔧 {booking.get('issue', '—')[:40]}")
                status = booking.get("status", "Pending")
                new_status = col4.selectbox(
                    "Status",
                    ["Pending", "Confirmed", "Completed", "Cancelled"],
                    index=["Pending", "Confirmed", "Completed", "Cancelled"].index(status),
                    key=f"booking_status_{idx}",
                    label_visibility="collapsed"
                )
                if new_status != status:
                    st.session_state.bookings[idx]["status"] = new_status
                    st.rerun()
            st.markdown("---")

        # CSV export
        output = io.StringIO()
        fields = ["name", "phone", "date", "time", "issue", "time_logged", "status"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(st.session_state.bookings)
        st.download_button(
            "⬇️ Export Bookings CSV",
            data=output.getvalue(),
            file_name=f"{CONFIG['company_name'].replace(' ', '_')}_bookings_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
