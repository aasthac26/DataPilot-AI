
import streamlit as st

st.set_page_config(
    page_title="DataPilot AI",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Clean font and subtle bg */
    html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
    .stChatMessage { border-radius: 12px; }
    .stButton > button {
        border-radius: 8px;
        font-size: 0.82rem;
        text-align: left;
    }
    /* Hide Streamlit default header */
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

from core.nl_to_sql import generate_sql
from core.validator import validate_query
from core.database import execute_query
from core.explainer import explain_sql
from core.visualizer import render_chart
from core.insights import generate_insights
from core.conversation import ConversationManager

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


# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar()

# ── Main content area ─────────────────────────────────────────────────────────
st.markdown("## 🗄️ DataPilot AI")
st.caption("Ask questions about your data in plain English")

# Show health report if dataset just loaded (only once per upload)
if (
    st.session_state.get("health_report")
    and not st.session_state.get("health_shown")
):
    render_health_report(st.session_state["health_report"])
    st.session_state["health_shown"] = True
    # Reset on new file
    if st.session_state.get("chat_history") == []:
        st.session_state["health_shown"] = False

st.divider()

# ── No dataset yet → welcome screen ──────────────────────────────────────────
if not st.session_state.get("schema"):
    render_welcome_screen()
    st.stop()

# ── Render existing chat history ──────────────────────────────────────────────
render_chat_history()

# ── Handle new question ───────────────────────────────────────────────────────
question = get_user_input()

if question:
    # Show user's message immediately
    push_user_message(question)
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(question)

    # Pull session state
    schema = st.session_state["schema"]
    db_path = st.session_state["db_path"]
    conversation: ConversationManager = st.session_state["conversation"]

    # ── Pipeline ──────────────────────────────────────────────────────────────
    with st.chat_message("assistant", avatar="🤖"):
        status = st.status("🤔 Thinking...", expanded=True)

        try:
            # Step 1: Generate SQL
            status.update(label="⚙️ Generating SQL query...")
            context = conversation.get_context_for_sql()
            sql = generate_sql(question, schema, conversation_context=context)

            # Step 2: Validate SQL
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

            # Step 3: Execute query
            status.update(label="🗄️ Executing query...")
            result_df = execute_query(db_path, validation.cleaned_sql)

            if result_df.empty:
                status.update(label="✅ Done — no rows matched", state="complete")
                msg = "The query ran successfully but returned no results. Try a different filter or question."
                render_error(msg)
                push_assistant_message(msg)
                st.stop()

            # Step 4: Explain the SQL
            status.update(label="📖 Explaining query...")
            explanation = explain_sql(validation.cleaned_sql, schema)

            # Step 5: Generate chart
            status.update(label="📊 Building chart...")
            figure = render_chart(result_df, title=question)

            # Step 6: Generate AI insights
            status.update(label="💡 Generating insights...")
            insight = generate_insights(result_df, question, schema)

            status.update(label="✅ Done!", state="complete", expanded=False)

            # ── Render result inline ──────────────────────────────────────────
            # Capture current values for the closure
            _sql = validation.cleaned_sql
            _explanation = explanation
            _insight = insight
            _figure = figure
            _df = result_df

            render_result(_df, _sql, _explanation, _insight, _figure)

            # Save a renderable widget for history replay
            def _make_widget(sql, explanation, insight, figure, df):
                def widget():
                    render_result(df, sql, explanation, insight, figure)
                return widget

            push_assistant_result(
                _make_widget(_sql, _explanation, _insight, _figure, _df)
            )

            # Step 7: Update conversation memory
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
