"""Vela-Law Preferences Dashboard — Streamlit single-file app.

Run locally:
    pip install streamlit
    streamlit run dashboard/app.py

Attorneys use this to view and edit their scheduling preferences
without emailing commands to Vela.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core.config import settings
from core.models import AttorneyPreferences, Tone
from core.table_storage import VelaTableStorage

# ── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Vela-Law Preferences",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ──────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main .block-container { max-width: 900px; padding-top: 2rem; }
    .stMetric { background: #f8f9fb; border-radius: 8px; padding: 12px; }
    h1 { color: #1a3a5c; }
    h2, h3 { color: #2c5282; }
</style>
""", unsafe_allow_html=True)

# ── Storage ──────────────────────────────────────────────────────────────────


@st.cache_resource
def get_storage() -> VelaTableStorage:
    return VelaTableStorage(settings.azure_storage_connection_string)


# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("Vela-Law")
st.sidebar.caption("Attorney Preferences Dashboard")

storage = get_storage()
attorneys = storage.list_attorneys()

if not attorneys:
    st.sidebar.warning("No attorneys found. Run `python data/seed_preferences.py` first.")
    st.stop()

selected_email = st.sidebar.selectbox(
    "Select attorney",
    attorneys,
    format_func=lambda e: f"{storage.get_preferences(e).display_name or e}",
)

st.sidebar.divider()
st.sidebar.caption(f"Connected to Table Storage")
st.sidebar.caption(f"Last refreshed: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")

if st.sidebar.button("Refresh"):
    st.cache_resource.clear()
    st.rerun()

# ── Main Content ─────────────────────────────────────────────────────────────

prefs = storage.get_preferences(selected_email)

st.title(f"Preferences — {prefs.display_name or selected_email}")
st.caption(f"`{selected_email}`")

# ── Tabs ─────────────────────────────────────────────────────────────────────

tab_schedule, tab_meetings, tab_tone, tab_escalation, tab_audit = st.tabs(
    ["Schedule", "Meetings", "Tone & Signature", "Escalation", "Audit Log"]
)

# ── Tab: Schedule ────────────────────────────────────────────────────────────

with tab_schedule:
    st.subheader("Working Hours & Availability")

    col1, col2, col3 = st.columns(3)
    with col1:
        working_start = st.text_input("Start time", value=prefs.working_hours_start)
    with col2:
        working_end = st.text_input("End time", value=prefs.working_hours_end)
    with col3:
        tz = st.text_input("Timezone", value=prefs.timezone)

    st.divider()
    st.subheader("Buffer Times")

    col1, col2 = st.columns(2)
    with col1:
        buf_before = st.number_input(
            "Buffer before meetings (min)", value=prefs.buffer_before_minutes, min_value=0, max_value=60
        )
    with col2:
        buf_after = st.number_input(
            "Buffer after meetings (min)", value=prefs.buffer_after_minutes, min_value=0, max_value=60
        )

    st.divider()
    st.subheader("Blackout Dates")
    blackout_str = st.text_area(
        "One date per line (YYYY-MM-DD)",
        value="\n".join(prefs.blackout_dates),
        height=100,
    )
    blackout_dates = [d.strip() for d in blackout_str.split("\n") if d.strip()]

    st.subheader("Blocked Recurring Times")
    blocked_str = st.text_area(
        "Format: 'MWF 12:00-13:00' — one per line",
        value="\n".join(prefs.blocked_times),
        height=80,
    )
    blocked_times = [t.strip() for t in blocked_str.split("\n") if t.strip()]

# ── Tab: Meetings ────────────────────────────────────────────────────────────

with tab_meetings:
    st.subheader("Meeting Preferences")

    col1, col2 = st.columns(2)
    with col1:
        dur_internal = st.number_input(
            "Internal meeting default (min)", value=prefs.preferred_duration_internal, min_value=15, step=15
        )
    with col2:
        dur_client = st.number_input(
            "Client meeting default (min)", value=prefs.preferred_duration_client, min_value=15, step=15
        )

    platform = st.text_input("Default virtual platform", value=prefs.default_virtual_platform)

    st.subheader("Favorite Locations")
    locations_str = st.text_area(
        "One per line",
        value="\n".join(prefs.favorite_locations),
        height=80,
    )
    favorite_locations = [loc.strip() for loc in locations_str.split("\n") if loc.strip()]

# ── Tab: Tone & Signature ───────────────────────────────────────────────────

with tab_tone:
    st.subheader("Communication Style")

    tone_options = ["formal", "friendly", "concise"]
    current_idx = tone_options.index(prefs.response_tone.value) if prefs.response_tone.value in tone_options else 0
    tone = st.radio("Response tone", tone_options, index=current_idx, horizontal=True)

    st.divider()
    st.subheader("Email Signature")
    signature = st.text_area("Custom signature", value=prefs.custom_signature, height=120)

    st.info(
        "**Tone preview:**\n\n"
        + {
            "formal": '"Dear Ms. Chen, Thank you for reaching out. I have reviewed the calendar and would like to propose..."',
            "friendly": '"Hi Sarah! I checked the schedule and have a few great options for you..."',
            "concise": '"Available: (1) Tue 10 AM, (2) Wed 2 PM, (3) Thu 10:30 AM. Confirm?"',
        }.get(tone, "")
    )

# ── Tab: Escalation ─────────────────────────────────────────────────────────

with tab_escalation:
    st.subheader("Auto-Approve & Escalation")

    threshold = st.slider(
        "Auto-approve confidence threshold (%)",
        min_value=0,
        max_value=100,
        value=prefs.auto_approve_threshold,
        help="Vela will send replies automatically when confidence is above this threshold.",
    )

    escalation_email = st.text_input(
        "Escalation email override (leave blank to use your primary email)",
        value=prefs.escalation_email,
    )

    st.divider()
    st.subheader("Escalation Keywords")
    st.caption("Vela escalates when any of these terms appear in the email body.")
    keywords_str = st.text_area(
        "One keyword per line",
        value="\n".join(prefs.escalation_keywords),
        height=120,
    )
    escalation_keywords = [kw.strip() for kw in keywords_str.split("\n") if kw.strip()]

# ── Tab: Audit Log ───────────────────────────────────────────────────────────

with tab_audit:
    st.subheader("Recent Activity")
    try:
        audit_entries = storage.get_audit_trail(selected_email, limit=20)
        if audit_entries:
            for entry in audit_entries:
                with st.expander(
                    f"{entry.get('action', 'unknown')} — {entry.get('timestamp', '')}"
                ):
                    st.json(entry)
        else:
            st.info("No audit log entries yet for this attorney.")
    except Exception as e:
        st.error(f"Could not load audit log: {e}")

# ── Save Button ──────────────────────────────────────────────────────────────

st.divider()

if st.button("Save Preferences", type="primary", use_container_width=True):
    updated = AttorneyPreferences(
        attorney_email=selected_email,
        display_name=prefs.display_name,
        working_hours_start=working_start,
        working_hours_end=working_end,
        timezone=tz,
        buffer_before_minutes=buf_before,
        buffer_after_minutes=buf_after,
        preferred_duration_internal=dur_internal,
        preferred_duration_client=dur_client,
        priority_order=prefs.priority_order,
        response_tone=Tone(tone),
        auto_approve_threshold=threshold,
        blackout_dates=blackout_dates,
        blocked_times=blocked_times,
        favorite_locations=favorite_locations,
        default_virtual_platform=platform,
        escalation_email=escalation_email,
        escalation_keywords=escalation_keywords,
        custom_signature=signature,
        court_block_calendars=prefs.court_block_calendars,
    )
    storage.upsert_preferences(updated)
    st.success("Preferences saved successfully.")
    st.balloons()
