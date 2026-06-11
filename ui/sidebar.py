"""
ui/sidebar.py
Streamlit sidebar — supports both single-table and multi-table (Feature 3) modes.
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any

from core.ingestion import load_file, detect_schema
from core.database import create_database
from core.health_analyzer import analyze_health
from core.conversation import ConversationManager
from core.multi_table import get_combined_schema_for_display, detect_join_keys
from utils.schema_utils import format_schema_badge, schema_to_display_table


def render_sidebar():
    """
    Render the full sidebar.
    Populates st.session_state with all session data.
    Supports single-table and multi-table modes.
    """
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/48/database.png", width=40)
        st.title("DataPilot AI")
        st.caption("Your intelligent database copilot")
        st.divider()

        # ── Mode selector ─────────────────────────────────────────────────────
        st.subheader("📂 Upload Dataset")
        mode = st.radio(
            "Mode",
            ["Single Table", "Multi-Table (JOIN)"],
            horizontal=True,
            help="Multi-Table lets you upload 2 files and ask JOIN questions across them.",
        )
        st.session_state["multi_table_mode"] = (mode == "Multi-Table (JOIN)")

        # ── File upload ───────────────────────────────────────────────────────
        if not st.session_state.get("multi_table_mode"):
            _render_single_upload()
        else:
            _render_multi_upload()

        # ── Session info ──────────────────────────────────────────────────────
        _render_session_info()

        # ── Sample questions ──────────────────────────────────────────────────
        _render_sample_questions()

        st.divider()
        st.caption("Powered by Groq · LLaMA 3.3 70B · SQLite")


# ── Single table upload ───────────────────────────────────────────────────────

def _render_single_upload():
    uploaded = st.file_uploader(
        "CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        key="single_upload",
        help="Upload your dataset to start asking questions.",
    )
    if uploaded:
        _handle_single_upload(uploaded)


def _handle_single_upload(uploaded_file):
    if st.session_state.get("uploaded_filename") == uploaded_file.name:
        return

    with st.spinner("Analyzing dataset..."):
        try:
            df, table_name = load_file(uploaded_file)
            schema = detect_schema(df, table_name)
            db_path, session_id = create_database(df, table_name)
            health_report = analyze_health(df)

            st.session_state["df"]               = df
            st.session_state["table_name"]       = table_name
            st.session_state["schema"]           = schema
            st.session_state["schemas"]          = {table_name: schema}
            st.session_state["db_path"]          = db_path
            st.session_state["session_id"]       = session_id
            st.session_state["health_report"]    = health_report
            st.session_state["conversation"]     = ConversationManager(schema=schema)
            st.session_state["uploaded_filename"] = uploaded_file.name
            st.session_state["chat_history"]     = []
            st.session_state["health_shown"]     = False

            st.success(f"✅ Loaded **{table_name}** — {len(df):,} rows, {len(df.columns)} cols")

            for w in df.attrs.get("warnings", []):
                st.warning(f"⚠️ {w}")

        except Exception as e:
            st.error(f"Upload failed: {e}")


# ── Multi-table upload ────────────────────────────────────────────────────────

def _render_multi_upload():
    st.caption("Upload 2 files to enable JOIN queries across them.")

    col1, col2 = st.columns(2)
    with col1:
        file_a = st.file_uploader("Table 1", type=["csv", "xlsx", "xls"], key="multi_upload_a")
    with col2:
        file_b = st.file_uploader("Table 2", type=["csv", "xlsx", "xls"], key="multi_upload_b")

    if file_a and file_b:
        key = f"{file_a.name}+{file_b.name}"
        if st.session_state.get("multi_upload_key") != key:
            _handle_multi_upload(file_a, file_b, key)


def _handle_multi_upload(file_a, file_b, key: str):
    with st.spinner("Loading and analyzing both tables..."):
        try:
            df_a, name_a = load_file(file_a)
            df_b, name_b = load_file(file_b)

            # Prevent name collision
            if name_a == name_b:
                name_b = name_b + "_2"

            schema_a = detect_schema(df_a, name_a)
            schema_b = detect_schema(df_b, name_b)

            # Load both into the SAME SQLite database
            db_path, session_id = create_database(df_a, name_a)
            # Add second table to same DB
            from core.database import get_session_db_path
            import sqlite3
            conn = sqlite3.connect(db_path)
            df_b.to_sql(name_b, conn, if_exists="replace", index=False)
            conn.commit()
            conn.close()

            schemas = {name_a: schema_a, name_b: schema_b}
            combined_schema = get_combined_schema_for_display([schema_a, schema_b])

            # Detect join keys and surface them
            join_keys = detect_join_keys(schema_a, schema_b)

            st.session_state["schemas"]          = schemas
            st.session_state["schema"]           = combined_schema
            st.session_state["db_path"]          = db_path
            st.session_state["session_id"]       = session_id
            st.session_state["health_report"]    = analyze_health(df_a)
            st.session_state["conversation"]     = ConversationManager(schema=combined_schema)
            st.session_state["chat_history"]     = []
            st.session_state["health_shown"]     = False
            st.session_state["join_keys"]        = join_keys
            st.session_state["multi_upload_key"] = key

            st.success(f"✅ Loaded **{name_a}** ({len(df_a):,} rows) + **{name_b}** ({len(df_b):,} rows)")

            # Show detected join keys
            if join_keys:
                best = join_keys[0]
                st.info(
                    f"🔗 Auto-detected join key: "
                    f"`{name_a}.{best[0]}` ↔ `{name_b}.{best[1]}` "
                    f"({best[2]:.0%} confidence)"
                )
            else:
                st.warning("⚠️ No obvious join key detected — you can still ask questions and the LLM will figure it out.")

        except Exception as e:
            st.error(f"Upload failed: {e}")


# ── Session info panel ────────────────────────────────────────────────────────

def _render_session_info():
    schema = st.session_state.get("schema")
    if not schema:
        return

    st.divider()
    st.subheader("📋 Dataset Info")

    is_multi = schema.get("is_multi_table", False)

    if is_multi:
        # Multi-table display
        table_names = schema.get("table_names", [])
        st.markdown(f"**Tables:** {' + '.join(f'`{t}`' for t in table_names)}")
        st.markdown(f"**Combined rows:** {schema['row_count']:,} · **Columns:** {schema['col_count']}")

        # Show join keys
        join_keys = st.session_state.get("join_keys", [])
        if join_keys:
            with st.expander("🔗 Detected Join Keys", expanded=False):
                for col_a, col_b, score in join_keys[:5]:
                    st.markdown(
                        f"- `{table_names[0]}.{col_a}` ↔ `{table_names[1]}.{col_b}` "
                        f"— {score:.0%} confidence"
                    )
    else:
        st.markdown(format_schema_badge(schema))
        with st.expander("View Schema", expanded=False):
            rows = schema_to_display_table(schema)
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Health score
    report = st.session_state.get("health_report")
    if report:
        color = _grade_color(report.grade)
        st.markdown(
            f"**Data Health:** "
            f"<span style='color:{color}; font-size:1.1rem; font-weight:700'>"
            f"{report.score}/100 ({report.grade})</span>",
            unsafe_allow_html=True,
        )

    # Conversation counter
    conv = st.session_state.get("conversation")
    if conv and conv.turn_count > 0:
        st.caption(f"💬 {conv.turn_count} question(s) asked this session")

    st.divider()
    if st.button("🗑️ Clear & Upload New File", use_container_width=True):
        _clear_session()
        st.rerun()


# ── Sample questions ──────────────────────────────────────────────────────────

def _render_sample_questions():
    st.divider()
    st.subheader("💡 Sample Questions")

    is_multi = st.session_state.get("multi_table_mode", False)

    if is_multi:
        sample_qs = [
            "Show all records joined across both tables",
            "Which records appear in both tables?",
            "Count total records from both tables combined",
            "Show top 10 by joining both tables on the key",
            "Find records in table 1 not in table 2",
        ]
    else:
        sample_qs = [
            "Show top 10 records by the first numeric column",
            "What is the total count grouped by each category?",
            "What are the minimum, maximum, and average values?",
            "Show the distribution of values in the first text column",
            "Which rows have missing values?",
        ]

    for q in sample_qs:
        if st.button(q, use_container_width=True, key=f"sq_{q[:25]}"):
            st.session_state["prefill_question"] = q
            st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clear_session():
    keys = [
        "df", "table_name", "schema", "schemas", "db_path", "session_id",
        "health_report", "conversation", "uploaded_filename", "chat_history",
        "prefill_question", "health_shown", "join_keys", "multi_upload_key",
        "multi_table_mode",
    ]
    for k in keys:
        st.session_state.pop(k, None)


def _grade_color(grade: str) -> str:
    return {
        "A": "#10B981", "B": "#6366F1",
        "C": "#F59E0B", "D": "#EF4444", "F": "#DC2626",
    }.get(grade, "#64748B")
