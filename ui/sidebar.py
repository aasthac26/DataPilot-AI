"""
ui/sidebar.py
Streamlit sidebar: file upload, session info, schema display, sample questions.
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any

from core.ingestion import load_file, detect_schema
from core.database import create_database
from core.health_analyzer import analyze_health
from core.conversation import ConversationManager
from utils.schema_utils import format_schema_badge, schema_to_display_table


def render_sidebar():
    """
    Render the full left sidebar.
    Manages file upload and populates st.session_state with:
      - df, table_name, schema, db_path, session_id
      - health_report, conversation
    """
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/48/database.png", width=40)
        st.title("DataPilot AI")
        st.caption("Your intelligent database copilot")
        st.divider()

        # ── File Upload ───────────────────────────────────────────────────────
        st.subheader("📂 Upload Dataset")
        uploaded = st.file_uploader(
            "CSV or Excel file",
            type=["csv", "xlsx", "xls"],
            help="Upload your dataset to start asking questions.",
        )

        if uploaded:
            _handle_upload(uploaded)

        # ── Session Info ──────────────────────────────────────────────────────
        if st.session_state.get("schema"):
            schema = st.session_state["schema"]
            st.divider()
            st.subheader("Dataset Info")
            st.markdown(format_schema_badge(schema))

            with st.expander("View Schema", expanded=False):
                rows = schema_to_display_table(schema)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Health Score badge
            report = st.session_state.get("health_report")
            if report:
                color = _grade_color(report.grade)
                st.markdown(
                    f"**Data Health:** "
                    f"<span style='color:{color}; font-size:1.1rem; font-weight:700'>"
                    f"{report.score}/100 ({report.grade})</span>",
                    unsafe_allow_html=True,
                )

            # Conversation turn counter
            conv: ConversationManager = st.session_state.get("conversation")
            if conv and conv.turn_count > 0:
                st.caption(f"💬 {conv.turn_count} question(s) asked this session")

            # Clear / reset
            st.divider()
            if st.button("Clear & Upload New File", use_container_width=True):
                _clear_session()
                st.rerun()

        # ── Sample Questions ──────────────────────────────────────────────────
        st.divider()
        st.subheader("💡 Sample Questions")
        sample_qs = [
            "Show top 10 records by the first numeric column",
            "What is the total count grouped by each category?",
            "Show me rows where any value is missing",
            "What are the minimum, maximum, and average values?",
            "Show the distribution of values in the first text column",
        ]
        for q in sample_qs:
            if st.button(q, use_container_width=True, key=f"sq_{q[:20]}"):
                st.session_state["prefill_question"] = q
                st.rerun()

        st.divider()
        st.caption("Powered by Groq · LLaMA 3 70B · SQLite")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _handle_upload(uploaded_file):
    """Process an uploaded file and populate session state."""
    # Avoid reprocessing if same file
    if st.session_state.get("uploaded_filename") == uploaded_file.name:
        return

    with st.spinner("Analyzing dataset..."):
        try:
            df, table_name = load_file(uploaded_file)
            schema = detect_schema(df, table_name)
            db_path, session_id = create_database(df, table_name)
            health_report = analyze_health(df)
            conversation = ConversationManager(schema=schema)

            # Store everything in session state
            st.session_state["df"] = df
            st.session_state["table_name"] = table_name
            st.session_state["schema"] = schema
            st.session_state["db_path"] = db_path
            st.session_state["session_id"] = session_id
            st.session_state["health_report"] = health_report
            st.session_state["conversation"] = conversation
            st.session_state["uploaded_filename"] = uploaded_file.name
            st.session_state["chat_history"] = []    # Reset chat on new upload

            st.success(f"Loaded **{table_name}** — {len(df):,} rows, {len(df.columns)} columns")

        except Exception as e:
            st.error(f"Upload failed: {e}")


def _clear_session():
    """Wipe all DataPilot session state keys."""
    keys = [
        "df", "table_name", "schema", "db_path", "session_id",
        "health_report", "conversation", "uploaded_filename",
        "chat_history", "prefill_question",
    ]
    for k in keys:
        st.session_state.pop(k, None)


def _grade_color(grade: str) -> str:
    return {
        "A": "#10B981",
        "B": "#6366F1",
        "C": "#F59E0B",
        "D": "#EF4444",
        "F": "#DC2626",
    }.get(grade, "#64748B")
