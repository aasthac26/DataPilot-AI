"""
app.py — DataPilot AI
Main Streamlit application entry point.
Wires all modules + 3 novel features together:
  Feature 1: Smart Follow-up Question Suggester
  Feature 2: Auto Chart Narrator
  Feature 3: Multi-table JOIN support

Run with:
    streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="DataPilot AI",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
    .stChatMessage { border-radius: 12px; }
    .stButton > button {
        border-radius: 8px;
        font-size: 0.82rem;
        text-align: left;
    }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Core imports ──────────────────────────────────────────────────────────────
from core.nl_to_sql import generate_sql
from core.validator import validate_query
from core.database import execute_query
from core.explainer import explain_sql
from core.visualizer import render_chart
from core.insights import generate_insights
from core.conversation import ConversationManager
from core.database import cleanup_old_sessions
cleanup_old_sessions()

# ── Novel feature imports ─────────────────────────────────────────────────────
from core.followup import generate_followup_questions          # Feature 1
from core.chart_narrator import narrate_chart_from_df          # Feature 2
from core.multi_table import (                                  # Feature 3
    generate_multi_table_sql,
    get_active_schemas,
    is_multi_table_mode,
)

# ── UI imports ────────────────────────────────────────────────────────────────
from ui.sidebar import render_sidebar
from ui.chat_interface import (
    render_chat_history,
    get_user_input,
    push_user_message,
    push_assistant_result,
    push_assistant_message,
    render_welcome_screen,
)
from ui.result_display import render_result, render_error
from ui.health_report import render_health_report
from utils.chart_utils import detect_chart_type

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🗄️ DataPilot AI")

# Show mode badge
if st.session_state.get("multi_table_mode"):
    st.caption("Multi-table mode — ask JOIN questions across your datasets")
else:
    st.caption("Ask questions about your data in plain English")

# ── Health report (shown once after upload) ───────────────────────────────────
if (
    st.session_state.get("health_report")
    and not st.session_state.get("health_shown")
):
    render_health_report(st.session_state["health_report"])
    st.session_state["health_shown"] = True

st.divider()

# ── Welcome screen ────────────────────────────────────────────────────────────
if not st.session_state.get("schema"):
    render_welcome_screen()
    st.stop()

# ── Chat history ──────────────────────────────────────────────────────────────
render_chat_history()

# ── Handle new question ───────────────────────────────────────────────────────
question = get_user_input()

if question:
    push_user_message(question)
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(question)

    schema     = st.session_state["schema"]
    db_path    = st.session_state["db_path"]
    conversation: ConversationManager = st.session_state["conversation"]
    multi_mode = is_multi_table_mode(st.session_state)
    join_keys    = st.session_state.get("join_keys", None)

    with st.chat_message("assistant", avatar="🤖"):
        status = st.status("🤔 Thinking...", expanded=True)

        try:
            # ── Step 1: Generate SQL ──────────────────────────────────────────
            status.update(label="⚙️ Generating SQL query...")
            context = conversation.get_context_for_sql()

            if multi_mode:
                # Feature 3: use multi-table SQL generator
                schemas_list = get_active_schemas(st.session_state)
                sql = generate_multi_table_sql(
                    question,
                    schemas_list,
                    conversation_context=context,
                )
            else:
                sql = generate_sql(question, schema, conversation_context=context, join_keys=join_keys)

            # ── Step 2: Validate ──────────────────────────────────────────────
            status.update(label="🔒 Validating query safety...")
            validation = validate_query(sql)

            if not validation.is_safe:
                status.update(label="❌ Query blocked", state="error")
                error_msg = "Query blocked for safety:\n" + "\n".join(
                    f"• {i}" for i in validation.issues
                )
                render_error(error_msg)
                push_assistant_message(f"⚠️ {error_msg}")
                st.stop()

            # ── Step 3: Execute ───────────────────────────────────────────────
            status.update(label="🗄️ Executing query...")
            result_df = execute_query(db_path, validation.cleaned_sql)

            if result_df.empty:
                status.update(label="✅ Done — no rows matched", state="complete")
                msg = "The query ran successfully but returned no results. Try rephrasing or a different filter."
                render_error(msg)
                push_assistant_message(msg)
                st.stop()

            # ── Step 4: Explain SQL ───────────────────────────────────────────
            status.update(label="📖 Explaining query...")
            explanation = explain_sql(validation.cleaned_sql, schema)

            # ── Step 5: Chart ─────────────────────────────────────────────────
            status.update(label="📊 Building chart...")
            figure = render_chart(result_df, title=question)

            # ── Step 6: Chart Narration (Feature 2) ───────────────────────────
            status.update(label="🎙️ Narrating chart...")
            narration = narrate_chart_from_df(result_df, question)

            # ── Step 7: AI Insights ───────────────────────────────────────────
            status.update(label="💡 Generating insights...")
            insight = generate_insights(result_df, question, schema)

            # ── Step 8: Follow-up Questions (Feature 1) ───────────────────────
            status.update(label="🔮 Suggesting follow-up questions...")
            followup_questions = generate_followup_questions(
                question, result_df, schema
            )

            status.update(label="✅ Done!", state="complete", expanded=False)

            # ── Capture for closures ──────────────────────────────────────────
            _sql         = validation.cleaned_sql
            _explanation = explanation
            _insight     = insight
            _figure      = figure
            _narration   = narration
            _followups   = followup_questions
            _df          = result_df

            # ── Render ────────────────────────────────────────────────────────
            render_result(
                _df, _sql, _explanation, _insight, _figure,
                narration=_narration,
                followup_questions=_followups,
            )

            # ── Save to history ───────────────────────────────────────────────
            def _make_widget(sql, explanation, insight, figure, df, narration, followups):
                def widget():
                    render_result(
                        df, sql, explanation, insight, figure,
                        narration=narration,
                        followup_questions=followups,
                    )
                return widget

            push_assistant_result(
                _make_widget(_sql, _explanation, _insight, _figure, _df, _narration, _followups)
            )

            # ── Update conversation memory ────────────────────────────────────
            conversation.add_turn(
                question=question,
                sql=_sql,
                explanation=explanation,
                insight=insight,
            )

        except Exception as e:
            status.update(label="❌ Something went wrong", state="error")
            render_error(str(e))
            push_assistant_message(f"❌ Error: {e}")
