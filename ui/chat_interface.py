"""
ui/chat_interface.py
The main chat interface: renders message history and handles user input.
"""

import streamlit as st
from typing import Optional


def render_chat_history():
    """
    Render all messages from st.session_state['chat_history'].
    Each entry is a dict with:
      role:     "user" | "assistant"
      content:  str  (for user messages)
      widget:   callable (for assistant messages — renders result block)
    """
    history = st.session_state.get("chat_history", [])

    for msg in history:
        role = msg["role"]
        avatar = "🧑‍💼" if role == "user" else "🤖"

        with st.chat_message(role, avatar=avatar):
            if role == "user":
                st.markdown(msg["content"])
            else:
                # Assistant messages store a render function
                if "widget" in msg and callable(msg["widget"]):
                    msg["widget"]()
                elif "content" in msg:
                    st.markdown(msg["content"])


def get_user_input() -> Optional[str]:
    """
    Render the chat input box.
    Returns the user's typed question, or None.
    Also checks for a pre-filled question from the sidebar sample buttons.
    """
    # Check for sidebar sample question injection
    prefill = st.session_state.pop("prefill_question", None)

    question = st.chat_input(
        placeholder="Ask anything about your data... e.g. 'Show top 10 customers by revenue'",
    )

    return question or prefill


def push_user_message(question: str):
    """Add the user's question to chat history."""
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    st.session_state["chat_history"].append({"role": "user", "content": question})


def push_assistant_result(widget_fn):
    """Add an assistant result (as a renderable widget function) to chat history."""
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    st.session_state["chat_history"].append({"role": "assistant", "widget": widget_fn})


def push_assistant_message(text: str):
    """Add a plain text assistant message to chat history."""
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    st.session_state["chat_history"].append({"role": "assistant", "content": text})


def render_welcome_screen():
    """Show the welcome state when no dataset is uploaded."""
    st.markdown(
        """
        <div style='text-align:center; padding:60px 20px;'>
            <div style='font-size:4rem;'>🗄️</div>
            <h2 style='color:#1E293B; font-weight:700;'>Welcome to DataPilot AI</h2>
            <p style='color:#64748B; font-size:1.05rem; max-width:480px; margin:0 auto;'>
                Upload a CSV or Excel file from the sidebar to start<br>
                asking questions about your data in plain English.
            </p>
            <br>
            <div style='display:flex; gap:12px; justify-content:center; flex-wrap:wrap;'>
                <span style='background:#EEF2FF; color:#6366F1; padding:6px 14px; border-radius:20px; font-size:0.85rem;'>📊 Auto-generates charts</span>
                <span style='background:#F0FDF4; color:#10B981; padding:6px 14px; border-radius:20px; font-size:0.85rem;'>🤖 AI-powered insights</span>
                <span style='background:#FFF7ED; color:#F59E0B; padding:6px 14px; border-radius:20px; font-size:0.85rem;'>🔒 Safe query validation</span>
                <span style='background:#FDF4FF; color:#A855F7; padding:6px 14px; border-radius:20px; font-size:0.85rem;'>💬 Conversational context</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
