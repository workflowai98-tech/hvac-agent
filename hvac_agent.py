import streamlit as st
import anthropic
import json
import re
import base64
import datetime
import csv
import io

# ─────────────────────────────────────────────
#  DEFAULT CONFIG  (swap this block per client)
# ─────────────────────────────────────────────
DEFAULT_CONFIG = {
    # Company
    "company_name": "Prestige Air",
    "ai_name": "Max",
    "tagline": "HVAC Services — Dallas, TX",
    "phone": "(555) 123-4567",
    "hours": "Mon–Fri: 8am – 6pm",
    "emergency": "24/7 Emergency Service Available",
    "service_area": "Dallas, TX",
    "services": "AC repair, heating, air quality, maintenance, installations",
    "business_description": "We're a family-owned HVAC company serving the Dallas area for over 15 years. We pride ourselves on fast response times and honest pricing.",
    "google_review_link": "https://g.page/r/your-link-here",
    # Chat
    "welcome_message": "👋 Hi! I'm Max, your AI assistant for Prestige Air. I can help you book appointments, get estimates, or answer any HVAC questions. What can I help you with today?",
    "quick_replies": "My AC isn't cooling,I need to book a tune-up,Get a price estimate,Talk to a person",
    # Branding
    "primary_color": "#1a73e8",
    "bubble_color": "#e8f0fe",
    "font": "Inter",
    "dark_mode": False,
    "logo_b64": "",
    "avatar_b64": "",
    # Social
    "instagram": "",
    "facebook": "",
    "linkedin": "",
    # Notifications
    "notification_email": "",
    "ga_tracking_id": "",
    # Emergency
    "emergency_mode": False,
    "emergency_message": "We are currently experiencing high call volumes. For urgent HVAC issues please call us directly.",
    # FAQ
    "faqs": [
        {"q": "How much does an AC tune-up cost?", "a": "Our standard tune-up is $89 and includes a full system inspection, coil cleaning, and refrigerant check."},
        {"q": "Do you offer financing?", "a": "Yes! We offer 0% financing for 12 months on qualifying installations."},
        {"q": "What areas do you serve?", "a": "We serve all of Dallas and surrounding areas including Plano, Frisco, McKinney, and Allen."},
    ],
    # Pricing
    "pricing": [
        {"service": "AC Tune-Up", "price": "$89"},
        {"service": "Heating Inspection", "price": "$79"},
        {"service": "AC Repair (Diagnostic)", "price": "$69"},
        {"service": "Full System Replacement", "price": "From $3,200"},
        {"service": "Air Quality Assessment", "price": "$49"},
    ],
    # Multiple service areas
    "service_areas": "Dallas, Plano, Frisco, McKinney, Allen, Richardson",
}

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Max AI Assistant",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  SESSION STATE INIT
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "config": DEFAULT_CONFIG.copy(),
        "messages": [],
        "leads": [],
        "bookings": [],
        "review_requests": [],
        "admin_logged_in": False,
        "chat_histories": [],
        "current_session_start": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "quick_reply_used": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
cfg = st.session_state.config

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def require_login():
    if st.session_state.admin_logged_in:
        return True
    st.warning("🔒 This section is for contractors only.")
    pwd = st.text_input("Enter admin password:", type="password", key="login_input")
    if st.button("Login", key="login_btn"):
        admin_pw = st.secrets.get("ADMIN_PASSWORD", "max2024")
        if pwd == admin_pw:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False

def encode_file(uploaded):
    if uploaded is None:
        return ""
    return base64.b64encode(uploaded.read()).decode()

def img_tag(b64, alt="", style=""):
    if not b64:
        return ""
    return f'<img src="data:image/png;base64,{b64}" alt="{alt}" style="{style}"/>'

def apply_css():
    font = cfg.get("font", "Inter")
    primary = cfg.get("primary_color", "#1a73e8")
    bubble = cfg.get("bubble_color", "#e8f0fe")
    dark = cfg.get("dark_mode", False)

    font_map = {
        "Inter": "Inter",
        "Roboto": "Roboto",
        "Poppins": "Poppins",
        "Montserrat": "Montserrat",
        "Open Sans": "Open+Sans",
    }
    font_slug = font_map.get(font, "Inter")

    bg = "#1e1e2e" if dark else "#ffffff"
    text_color = "#e0e0e0" if dark else "#1a1a2e"
    sidebar_bg = "#16213e" if dark else "#f8f9fa"

    st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family={font_slug}:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ font-family: '{font}', sans-serif !important; }}
        .stApp {{ background-color: {bg}; color: {text_color}; }}
        section[data-testid="stSidebar"] {{ background-color: {sidebar_bg}; }}
        .chat-bubble-user {{
            background-color: {primary};
            color: white;
            padding: 10px 14px;
            border-radius: 18px 18px 4px 18px;
            margin: 6px 0;
            max-width: 80%;
            margin-left: auto;
            word-wrap: break-word;
        }}
        .chat-bubble-ai {{
            background-color: {bubble};
            color: #1a1a2e;
            padding: 10px 14px;
            border-radius: 18px 18px 18px 4px;
            margin: 6px 0;
            max-width: 80%;
            word-wrap: break-word;
        }}
        .lead-card {{
            border: 1px solid {primary}33;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
        }}
        .stat-box {{
            background: {primary}11;
            border: 1px solid {primary}33;
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }}
        .emergency-banner {{
            background: #e53935;
            color: white;
            padding: 10px 16px;
            border-radius: 8px;
            margin-bottom: 12px;
            font-weight: 600;
        }}
        .price-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid {primary}22;
        }}
        div[data-testid="stButton"] button {{
            border-radius: 8px;
        }}
    </style>
    """, unsafe_allow_html=True)

    ga_id = cfg.get("ga_tracking_id", "").strip()
    if ga_id:
        st.markdown(f"""
        <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){{dataLayer.push(arguments);}}
          gtag('js', new Date());
          gtag('config', '{ga_id}');
        </script>
        """, unsafe_allow_html=True)

apply_css()

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    logo_b64 = cfg.get("logo_b64", "")
    if logo_b64:
        st.markdown(img_tag(logo_b64, "Logo", "width:160px;margin-bottom:8px;border-radius:8px;"), unsafe_allow_html=True)

    st.markdown(f"## {cfg['company_name']}")
    st.markdown(f"*{cfg['tagline']}*")

    if cfg.get("emergency_mode"):
        st.markdown('<div class="emergency-banner">🚨 EMERGENCY MODE ACTIVE</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"📞 **{cfg['phone']}**")
    st.markdown(f"🕐 {cfg['hours']}")
    st.markdown(f"🌍 {cfg.get('service_areas', cfg['service_area'])}")
    st.markdown(f"⚡ {cfg['emergency']}")

    social_html = ""
    if cfg.get("instagram"):
        social_html += f'<a href="{cfg["instagram"]}" target="_blank">📸 Instagram</a>&nbsp;&nbsp;'
    if cfg.get("facebook"):
        social_html += f'<a href="{cfg["facebook"]}" target="_blank">👤 Facebook</a>&nbsp;&nbsp;'
    if cfg.get("linkedin"):
        social_html += f'<a href="{cfg["linkedin"]}" target="_blank">💼 LinkedIn</a>'
    if social_html:
        st.markdown("---")
        st.markdown(social_html, unsafe_allow_html=True)

    st.markdown("---")
    if st.session_state.admin_logged_in:
        if st.button("🔓 Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()
    else:
        st.caption("Admin: use password to access Dashboard, Reviews & Bookings tabs.")

# ─────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────
tab_chat, tab_dash, tab_reviews, tab_bookings, tab_pricing, tab_settings = st.tabs([
    "💬 Chat", "📊 Dashboard", "⭐ Reviews", "📅 Bookings", "💰 Pricing", "⚙️ Settings"
])

# ══════════════════════════════════════════════
#  TAB 1 — CHAT
# ══════════════════════════════════════════════
with tab_chat:
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        avatar_b64 = cfg.get("avatar_b64", "")
        if avatar_b64:
            st.markdown(
                '<div style="display:flex;align-items:center;gap:12px;">'
                + img_tag(avatar_b64, "AI Avatar", "width:48px;height:48px;border-radius:50%;object-fit:cover;")
                + f'<div><h3 style="margin:0">{cfg["ai_name"]} — {cfg["company_name"]}</h3></div></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"### 🤖 {cfg['ai_name']} — {cfg['company_name']}")
    with col_h2:
        if st.button("🔄 New Chat"):
            if st.session_state.messages:
                st.session_state.chat_histories.append({
                    "ts": st.session_state.current_session_start,
                    "messages": st.session_state.messages.copy(),
                })
            st.session_state.messages = []
            st.session_state.quick_reply_used = False
            st.session_state.current_session_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            st.rerun()

    if cfg.get("emergency_mode"):
        st.markdown(f'<div class="emergency-banner">{cfg.get("emergency_message", "")}</div>', unsafe_allow_html=True)

    if not st.session_state.messages:
        welcome = cfg.get("welcome_message", f"Hi! I'm {cfg['ai_name']}. How can I help?")
        st.markdown(f'<div class="chat-bubble-ai">🤖 {welcome}</div>', unsafe_allow_html=True)

        if not st.session_state.quick_reply_used:
            qr_raw = cfg.get("quick_replies", "")
            qr_list = [q.strip() for q in qr_raw.split(",") if q.strip()]
            if qr_list:
                st.markdown("**Quick questions:**")
                cols = st.columns(min(len(qr_list), 4))
                for i, qr in enumerate(qr_list):
                    with cols[i % 4]:
                        if st.button(qr, key=f"qr_{i}"):
                            st.session_state.messages.append({"role": "user", "content": qr})
                            st.session_state.quick_reply_used = True
                            st.rerun()

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-bubble-user">👤 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bubble-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

    # Build system prompt
    faq_text = "\n".join([f"Q: {f['q']}\nA: {f['a']}" for f in cfg.get("faqs", [])])
    pricing_text = "\n".join([f"- {p['service']}: {p['price']}" for p in cfg.get("pricing", [])])
    biz_desc = cfg.get("business_description", "")

    system_prompt = f"""You are {cfg['ai_name']}, the AI assistant for {cfg['company_name']}.
{biz_desc}

Company details:
- Phone: {cfg['phone']}
- Hours: {cfg['hours']}
- Emergency: {cfg['emergency']}
- Service areas: {cfg.get('service_areas', cfg['service_area'])}
- Services: {cfg['services']}
- Google Reviews: {cfg['google_review_link']}

Pricing:
{pricing_text}

Frequently Asked Questions:
{faq_text}

{'EMERGENCY MODE IS ACTIVE: ' + cfg.get('emergency_message', '') if cfg.get('emergency_mode') else ''}

Your job:
1. Answer questions helpfully and professionally.
2. When a customer gives you their name AND phone number (to request a callback or book), append EXACTLY this tag at the END of your reply:
   [LEAD: {{"name": "...", "phone": "...", "issue": "..."}}]
3. When a customer wants to BOOK an appointment and gives name + phone + preferred date/time, append EXACTLY this tag at the END:
   [BOOKING: {{"name": "...", "phone": "...", "date": "...", "time": "...", "service": "..."}}]
4. Keep replies friendly, concise, and helpful. Never make up prices not listed above.
5. If asked to speak to a person, provide the phone number.
"""

    user_input = st.chat_input(f"Ask {cfg['ai_name']} anything…")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.quick_reply_used = True

        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        api_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

        with st.spinner(f"{cfg['ai_name']} is typing…"):
            full_response = ""
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=1024,
                system=system_prompt,
                messages=api_msgs,
            ) as stream:
                for text in stream.text_stream:
                    full_response += text

        lead_match = re.search(r'\[LEAD:\s*(\{.*?\})\]', full_response, re.DOTALL)
        booking_match = re.search(r'\[BOOKING:\s*(\{.*?\})\]', full_response, re.DOTALL)

        if lead_match:
            try:
                lead_data = json.loads(lead_match.group(1))
                lead_data["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                lead_data["status"] = "New"
                lead_data["notes"] = ""
                lead_data["follow_up"] = ""
                st.session_state.leads.append(lead_data)
            except Exception:
                pass

        if booking_match:
            try:
                bk_data = json.loads(booking_match.group(1))
                bk_data["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                bk_data["status"] = "Pending"
                st.session_state.bookings.append(bk_data)
            except Exception:
                pass

        clean = re.sub(r'\[LEAD:\s*\{.*?\}\]', '', full_response, flags=re.DOTALL)
        clean = re.sub(r'\[BOOKING:\s*\{.*?\}\]', '', clean, flags=re.DOTALL).strip()

        st.session_state.messages.append({"role": "assistant", "content": clean})
        st.rerun()

    if st.session_state.messages:
        transcript_lines = []
        for m in st.session_state.messages:
            speaker = "You" if m["role"] == "user" else cfg["ai_name"]
            transcript_lines.append(f"{speaker}: {m['content']}")
        transcript_text = "\n\n".join(transcript_lines)
        st.download_button(
            "⬇️ Download Chat Transcript",
            data=transcript_text,
            file_name=f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
        )

# ══════════════════════════════════════════════
#  TAB 2 — DASHBOARD
# ══════════════════════════════════════════════
with tab_dash:
    if not require_login():
        st.stop()

    st.markdown("## 📊 Lead Dashboard")

    leads = st.session_state.leads
    total = len(leads)
    new_leads = sum(1 for l in leads if l.get("status") == "New")
    contacted = sum(1 for l in leads if l.get("status") == "Contacted")
    booked = sum(1 for l in leads if l.get("status") == "Booked")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-box"><h2>{total}</h2><p>Total Leads</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><h2>{new_leads}</h2><p>New</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><h2>{contacted}</h2><p>Contacted</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-box"><h2>{booked}</h2><p>Booked</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    status_filter = st.selectbox("Filter by status:", ["All", "New", "Contacted", "Booked", "Closed"])
    filtered = leads if status_filter == "All" else [l for l in leads if l.get("status") == status_filter]

    if not filtered:
        st.info("No leads yet. Start chatting to capture leads!")
    else:
        for i, lead in enumerate(reversed(filtered)):
            real_i = leads.index(lead)
            today = datetime.date.today()
            follow_up = lead.get("follow_up", "")
            is_overdue = False
            if follow_up:
                try:
                    fu_date = datetime.date.fromisoformat(follow_up)
                    is_overdue = fu_date < today
                except Exception:
                    pass

            label = f"{'🔴 ' if is_overdue else ''}👤 {lead.get('name','Unknown')} — {lead.get('phone','No phone')} | {lead.get('status','New')} | {lead.get('timestamp','')}"
            with st.expander(label):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Issue:** {lead.get('issue', 'Not specified')}")
                    new_status = st.selectbox(
                        "Status",
                        ["New", "Contacted", "Booked", "Closed"],
                        index=["New", "Contacted", "Booked", "Closed"].index(lead.get("status", "New")),
                        key=f"status_{real_i}"
                    )
                    if new_status != lead.get("status"):
                        st.session_state.leads[real_i]["status"] = new_status
                        st.rerun()
                with col_b:
                    default_date = datetime.date.today()
                    if follow_up:
                        try:
                            default_date = datetime.date.fromisoformat(follow_up)
                        except Exception:
                            pass
                    new_follow = st.date_input("Follow-up date", value=default_date, key=f"fu_{real_i}")
                    st.session_state.leads[real_i]["follow_up"] = str(new_follow)
                    if is_overdue:
                        st.warning("⚠️ Follow-up is overdue!")

                new_note = st.text_area(
                    "Notes",
                    value=lead.get("notes", ""),
                    key=f"note_{real_i}",
                    placeholder="Add notes about this lead…"
                )
                st.session_state.leads[real_i]["notes"] = new_note

    if leads:
        st.markdown("---")
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["name","phone","issue","status","timestamp","follow_up","notes"])
        writer.writeheader()
        writer.writerows(leads)
        st.download_button("⬇️ Export Leads as CSV", data=output.getvalue(), file_name="leads.csv", mime="text/csv")

    st.markdown("---")
    st.markdown("### 💬 Past Chat Sessions")
    histories = st.session_state.chat_histories
    if not histories:
        st.info("No completed chat sessions yet.")
    else:
        for h in reversed(histories):
            with st.expander(f"Session: {h['ts']} ({len(h['messages'])} messages)"):
                for m in h["messages"]:
                    speaker = "👤 You" if m["role"] == "user" else f"🤖 {cfg['ai_name']}"
                    st.markdown(f"**{speaker}:** {m['content']}")

# ══════════════════════════════════════════════
#  TAB 3 — REVIEWS
# ══════════════════════════════════════════════
with tab_reviews:
    if not require_login():
        st.stop()

    st.markdown("## ⭐ Review Requests")
    st.info("📱 Twilio SMS integration coming in Phase 2. Use this preview to see what messages will go out.")

    with st.form("review_form"):
        r_name = st.text_input("Customer Name")
        r_phone = st.text_input("Customer Phone")
        submitted = st.form_submit_button("Send Review Request")
        if submitted and r_name and r_phone:
            msg = f"Hi {r_name}, thanks for choosing {cfg['company_name']}! We'd love your feedback — can you leave us a quick Google review? {cfg['google_review_link']}"
            st.session_state.review_requests.append({
                "name": r_name,
                "phone": r_phone,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "message": msg,
            })
            st.success("✅ Review request logged!")
            st.markdown(f"**Preview SMS:**\n\n> {msg}")

    st.markdown("---")
    st.markdown(f"### Sent Requests ({len(st.session_state.review_requests)})")
    for req in reversed(st.session_state.review_requests):
        with st.expander(f"📨 {req['name']} — {req['phone']} | {req['timestamp']}"):
            st.markdown(f"**Message:** {req['message']}")

# ══════════════════════════════════════════════
#  TAB 4 — BOOKINGS
# ══════════════════════════════════════════════
with tab_bookings:
    if not require_login():
        st.stop()

    st.markdown("## 📅 Appointments")
    st.info("📅 Google Calendar integration coming in Phase 3.")

    bookings = st.session_state.bookings
    if not bookings:
        st.info("No bookings yet. Customers can book through the chat.")
    else:
        for i, bk in enumerate(reversed(bookings)):
            real_i = len(bookings) - 1 - i
            with st.expander(f"📅 {bk.get('name')} — {bk.get('date')} {bk.get('time')} | {bk.get('status','Pending')}"):
                st.markdown(f"**Phone:** {bk.get('phone', 'N/A')}")
                st.markdown(f"**Service:** {bk.get('service', 'N/A')}")
                st.markdown(f"**Booked at:** {bk.get('timestamp','')}")
                new_bk_status = st.selectbox(
                    "Status",
                    ["Pending", "Confirmed", "Completed", "Cancelled"],
                    index=["Pending","Confirmed","Completed","Cancelled"].index(bk.get("status","Pending")),
                    key=f"bk_status_{real_i}"
                )
                if new_bk_status != bk.get("status"):
                    st.session_state.bookings[real_i]["status"] = new_bk_status
                    st.rerun()

    st.markdown("---")
    st.markdown("### ➕ Add Manual Booking")
    with st.form("manual_booking"):
        mb_name = st.text_input("Customer Name")
        mb_phone = st.text_input("Phone")
        mb_service = st.text_input("Service")
        mb_date = st.date_input("Date", value=datetime.date.today())
        mb_time = st.time_input("Time")
        if st.form_submit_button("Add Booking"):
            st.session_state.bookings.append({
                "name": mb_name,
                "phone": mb_phone,
                "service": mb_service,
                "date": str(mb_date),
                "time": str(mb_time),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "Confirmed",
            })
            st.success("✅ Booking added!")
            st.rerun()

# ══════════════════════════════════════════════
#  TAB 5 — PRICING (PUBLIC)
# ══════════════════════════════════════════════
with tab_pricing:
    st.markdown(f"## 💰 {cfg['company_name']} — Service Pricing")
    st.markdown(f"*Serving {cfg.get('service_areas', cfg['service_area'])}*")
    st.markdown("---")

    pricing_list = cfg.get("pricing", [])
    if not pricing_list:
        st.info("No pricing added yet. Go to Settings → Pricing to add your services.")
    else:
        for item in pricing_list:
            st.markdown(
                f'<div class="price-row"><span>{item["service"]}</span><strong>{item["price"]}</strong></div>',
                unsafe_allow_html=True
            )

    st.markdown("---")
    st.markdown(f"📞 Call us for a free quote: **{cfg['phone']}**")
    st.markdown(f"🕐 Hours: {cfg['hours']}")

    faqs = cfg.get("faqs", [])
    if faqs:
        st.markdown("---")
        st.markdown("### ❓ Common Questions")
        for faq in faqs:
            with st.expander(faq["q"]):
                st.markdown(faq["a"])

# ══════════════════════════════════════════════
#  TAB 6 — SETTINGS
# ══════════════════════════════════════════════
with tab_settings:
    if not require_login():
        st.stop()

    st.markdown("## ⚙️ Settings")

    s1, s2, s3, s4, s5, s6, s7, s8 = st.tabs([
        "🏢 Company", "🎨 Branding", "💬 Chat", "❓ FAQ", "💰 Pricing", "📲 Social", "🔔 Notifications", "🛠️ Tools"
    ])

    # ── Company ──
    with s1:
        st.markdown("### 🏢 Company Info")
        with st.form("company_form"):
            c_name = st.text_input("Company Name", value=cfg["company_name"])
            c_ai = st.text_input("AI Name", value=cfg["ai_name"])
            c_tag = st.text_input("Tagline", value=cfg["tagline"])
            c_phone = st.text_input("Phone Number", value=cfg["phone"])
            c_hours = st.text_input("Business Hours", value=cfg["hours"])
            c_emerg = st.text_input("Emergency Hours", value=cfg["emergency"])
            c_area = st.text_input("Primary Service Area", value=cfg["service_area"])
            c_areas = st.text_area("All Service Areas (comma separated)", value=cfg.get("service_areas", ""))
            c_services = st.text_area("Services Offered", value=cfg["services"])
            c_desc = st.text_area("Business Description (shown to AI)", value=cfg.get("business_description", ""), height=100)
            c_review = st.text_input("Google Review Link", value=cfg["google_review_link"])
            if st.form_submit_button("💾 Save Company Info"):
                st.session_state.config.update({
                    "company_name": c_name, "ai_name": c_ai, "tagline": c_tag,
                    "phone": c_phone, "hours": c_hours, "emergency": c_emerg,
                    "service_area": c_area, "service_areas": c_areas,
                    "services": c_services, "business_description": c_desc,
                    "google_review_link": c_review,
                })
                cfg = st.session_state.config
                st.success("✅ Company info saved!")
                st.rerun()

        st.markdown("---")
        st.markdown("### 🚨 Emergency Mode")
        em_on = st.toggle("Enable Emergency Mode", value=cfg.get("emergency_mode", False))
        em_msg = st.text_area("Emergency Message", value=cfg.get("emergency_message", ""), height=80)
        if st.button("Save Emergency Settings"):
            st.session_state.config["emergency_mode"] = em_on
            st.session_state.config["emergency_message"] = em_msg
            st.success("✅ Emergency settings saved!")
            st.rerun()

    # ── Branding ──
    with s2:
        st.markdown("### 🎨 Branding & Appearance")

        st.markdown("**Upload Logo**")
        logo_file = st.file_uploader("Logo image (PNG/JPG)", type=["png","jpg","jpeg"], key="logo_upload")
        if logo_file:
            encoded = encode_file(logo_file)
            st.session_state.config["logo_b64"] = encoded
            st.success("✅ Logo uploaded!")
            st.markdown(img_tag(encoded, "Logo preview", "width:120px;border-radius:8px;"), unsafe_allow_html=True)
        elif cfg.get("logo_b64"):
            st.markdown("**Current logo:**")
            st.markdown(img_tag(cfg["logo_b64"], "Logo", "width:120px;border-radius:8px;"), unsafe_allow_html=True)
            if st.button("❌ Remove Logo"):
                st.session_state.config["logo_b64"] = ""
                st.rerun()

        st.markdown("**Upload AI Avatar**")
        avatar_file = st.file_uploader("Avatar image (PNG/JPG, square recommended)", type=["png","jpg","jpeg"], key="avatar_upload")
        if avatar_file:
            encoded = encode_file(avatar_file)
            st.session_state.config["avatar_b64"] = encoded
            st.success("✅ Avatar uploaded!")
            st.markdown(img_tag(encoded, "Avatar preview", "width:60px;height:60px;border-radius:50%;object-fit:cover;"), unsafe_allow_html=True)
        elif cfg.get("avatar_b64"):
            st.markdown("**Current avatar:**")
            st.markdown(img_tag(cfg["avatar_b64"], "Avatar", "width:60px;height:60px;border-radius:50%;object-fit:cover;"), unsafe_allow_html=True)
            if st.button("❌ Remove Avatar"):
                st.session_state.config["avatar_b64"] = ""
                st.rerun()

        with st.form("branding_form"):
            b_primary = st.color_picker("Primary Color (buttons, user bubbles)", value=cfg.get("primary_color", "#1a73e8"))
            b_bubble = st.color_picker("AI Chat Bubble Color", value=cfg.get("bubble_color", "#e8f0fe"))
            b_font = st.selectbox(
                "Font",
                ["Inter", "Roboto", "Poppins", "Montserrat", "Open Sans"],
                index=["Inter", "Roboto", "Poppins", "Montserrat", "Open Sans"].index(cfg.get("font", "Inter"))
            )
            b_dark = st.toggle("Dark Mode", value=cfg.get("dark_mode", False))
            if st.form_submit_button("💾 Save Branding"):
                st.session_state.config.update({
                    "primary_color": b_primary,
                    "bubble_color": b_bubble,
                    "font": b_font,
                    "dark_mode": b_dark,
                })
                cfg = st.session_state.config
                st.success("✅ Branding saved! Refresh to see full effect.")
                st.rerun()

    # ── Chat ──
    with s3:
        st.markdown("### 💬 Chat Settings")
        with st.form("chat_form"):
            ch_welcome = st.text_area("Welcome Message", value=cfg.get("welcome_message", ""), height=80)
            ch_quick = st.text_input("Quick Reply Buttons (comma separated)", value=cfg.get("quick_replies", ""))
            if st.form_submit_button("💾 Save Chat Settings"):
                st.session_state.config["welcome_message"] = ch_welcome
                st.session_state.config["quick_replies"] = ch_quick
                st.session_state.messages = []
                st.session_state.quick_reply_used = False
                cfg = st.session_state.config
                st.success("✅ Chat settings saved! Chat has been reset.")
                st.rerun()

    # ── FAQ ──
    with s4:
        st.markdown("### ❓ FAQ Builder")
        st.markdown("These Q&As are fed directly to the AI so it answers accurately.")

        faqs = cfg.get("faqs", [])
        updated_faqs = list(faqs)

        for i, faq in enumerate(faqs):
            label = f"FAQ #{i+1}: {faq['q'][:50]}…" if len(faq['q']) > 50 else f"FAQ #{i+1}: {faq['q']}"
            with st.expander(label):
                new_q = st.text_input("Question", value=faq["q"], key=f"faq_q_{i}")
                new_a = st.text_area("Answer", value=faq["a"], key=f"faq_a_{i}", height=80)
                updated_faqs[i] = {"q": new_q, "a": new_a}
                if st.button("🗑️ Delete this FAQ", key=f"del_faq_{i}"):
                    st.session_state.config["faqs"] = [f for j, f in enumerate(updated_faqs) if j != i]
                    st.rerun()

        st.markdown("---")
        st.markdown("**Add New FAQ:**")
        with st.form("add_faq_form"):
            new_q_input = st.text_input("Question")
            new_a_input = st.text_area("Answer", height=80)
            if st.form_submit_button("➕ Add FAQ"):
                st.session_state.config["faqs"] = updated_faqs + [{"q": new_q_input, "a": new_a_input}]
                st.success("✅ FAQ added!")
                st.rerun()

        if st.button("💾 Save FAQ Changes"):
            st.session_state.config["faqs"] = updated_faqs
            st.success("✅ FAQs saved!")
            st.rerun()

    # ── Pricing ──
    with s5:
        st.markdown("### 💰 Pricing Builder")
        st.markdown("Shown on the public Pricing tab and used by the AI when quoting.")

        pricing = cfg.get("pricing", [])
        updated_pricing = list(pricing)

        for i, item in enumerate(pricing):
            col_a, col_b, col_c = st.columns([3, 2, 1])
            with col_a:
                new_svc = st.text_input("Service", value=item["service"], key=f"p_svc_{i}")
            with col_b:
                new_price = st.text_input("Price", value=item["price"], key=f"p_price_{i}")
            with col_c:
                if st.button("🗑️", key=f"del_p_{i}"):
                    st.session_state.config["pricing"] = [p for j, p in enumerate(pricing) if j != i]
                    st.rerun()
            updated_pricing[i] = {"service": new_svc, "price": new_price}

        st.markdown("---")
        with st.form("add_pricing_form"):
            p_svc = st.text_input("New Service Name")
            p_price = st.text_input("Price (e.g. $89 or From $500)")
            if st.form_submit_button("➕ Add Service"):
                st.session_state.config["pricing"] = updated_pricing + [{"service": p_svc, "price": p_price}]
                st.success("✅ Service added!")
                st.rerun()

        if st.button("💾 Save Pricing"):
            st.session_state.config["pricing"] = updated_pricing
            st.success("✅ Pricing saved!")
            st.rerun()

    # ── Social ──
    with s6:
        st.markdown("### 📲 Social Media Links")
        with st.form("social_form"):
            soc_ig = st.text_input("Instagram URL", value=cfg.get("instagram", ""), placeholder="https://instagram.com/yourpage")
            soc_fb = st.text_input("Facebook URL", value=cfg.get("facebook", ""), placeholder="https://facebook.com/yourpage")
            soc_li = st.text_input("LinkedIn URL", value=cfg.get("linkedin", ""), placeholder="https://linkedin.com/in/yourprofile")
            if st.form_submit_button("💾 Save Social Links"):
                st.session_state.config.update({"instagram": soc_ig, "facebook": soc_fb, "linkedin": soc_li})
                cfg = st.session_state.config
                st.success("✅ Social links saved!")
                st.rerun()

    # ── Notifications ──
    with s7:
        st.markdown("### 🔔 Notifications & Tracking")
        with st.form("notif_form"):
            n_email = st.text_input(
                "Notification Email (for lead alerts — Phase 2)",
                value=cfg.get("notification_email", ""),
                placeholder="you@yourbusiness.com"
            )
            n_ga = st.text_input(
                "Google Analytics Tracking ID",
                value=cfg.get("ga_tracking_id", ""),
                placeholder="G-XXXXXXXXXX"
            )
            if st.form_submit_button("💾 Save Notification Settings"):
                st.session_state.config["notification_email"] = n_email
                st.session_state.config["ga_tracking_id"] = n_ga
                cfg = st.session_state.config
                st.success("✅ Notification settings saved!")
                st.rerun()

        if cfg.get("ga_tracking_id"):
            st.success(f"✅ Google Analytics active: `{cfg['ga_tracking_id']}`")

    # ── Tools ──
    with s8:
        st.markdown("### 🛠️ Developer Tools")

        st.markdown("#### 🔗 Embed Widget Code")
        st.markdown("Copy this snippet to embed the chat widget on any website:")
        embed_code = f"""<!-- Max AI Chat Widget — {cfg['company_name']} -->
<iframe
  src="https://max-hvac-assistant.streamlit.app/?embedded=true"
  width="400"
  height="600"
  frameborder="0"
  style="border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,0.15);position:fixed;bottom:24px;right:24px;"
  title="{cfg['ai_name']} — {cfg['company_name']}"
></iframe>"""
        st.code(embed_code, language="html")
        st.download_button(
            "⬇️ Download Embed Code",
            data=embed_code,
            file_name="max_embed.html",
            mime="text/html"
        )

        st.markdown("---")
        st.markdown("#### 📤 Export Config")
        config_export = json.dumps(
            {k: v for k, v in st.session_state.config.items() if k not in ("logo_b64", "avatar_b64")},
            indent=2
        )
        st.download_button("⬇️ Export Config (JSON)", data=config_export, file_name="max_config.json", mime="application/json")

        st.markdown("---")
        st.markdown("#### ⚠️ Reset Data")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            if st.button("🗑️ Clear All Leads"):
                st.session_state.leads = []
                st.success("Leads cleared.")
        with col_r2:
            if st.button("🗑️ Clear All Bookings"):
                st.session_state.bookings = []
                st.success("Bookings cleared.")
        with col_r3:
            if st.button("🗑️ Clear Chat History"):
                st.session_state.messages = []
                st.session_state.chat_histories = []
                st.session_state.quick_reply_used = False
                st.success("Chat cleared.")

        st.markdown("---")
        st.markdown("#### 🔄 Reset to Default Config")
        if st.button("⚠️ Reset ALL Settings to Default"):
            st.session_state.config = DEFAULT_CONFIG.copy()
            st.success("✅ Config reset to default!")
            st.rerun()
