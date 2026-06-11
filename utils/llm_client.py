"""
utils/llm_client.py
Single wrapper for all Groq LLM calls.
Model: llama3-70b-8192 (free, fast, excellent at SQL)
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
TEMPERATURE = 0.1   # Low temperature = more deterministic SQL output


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found. Please add it to your .env file.\n"
            "Get a free key at: https://console.groq.com"
        )
    return Groq(api_key=api_key)


def chat(
    system_prompt: str,
    user_message: str,
    temperature: float = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
) -> str:
    """
    Send a system + user message to Groq and return the assistant's reply as a string.
    This is the single function all modules use to talk to the LLM.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content.strip()


def chat_with_history(
    system_prompt: str,
    messages: list,
    temperature: float = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
) -> str:
    """
    Send a full conversation history to Groq (for conversational analytics).
    `messages` is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    """
    client = _get_client()

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    response = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content.strip()
