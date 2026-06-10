"""
Module 8: Conversational Analytics
Maintains conversation history so users can ask follow-up questions
with context ("Only from Delhi", "Compare with last month", etc.)
This is what turns DataPilot from a query generator into a true copilot.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from utils.llm_client import chat_with_history
from core.ingestion import schema_to_prompt_str


@dataclass
class Turn:
    """One exchange in the conversation."""
    question: str
    sql: str
    explanation: str
    insight: str


@dataclass
class ConversationManager:
    """
    Stores the full conversation history for one session.
    Exposes methods to:
      - Add turns
      - Build an LLM-ready message history
      - Generate a context summary for SQL generation
    """
    schema: Dict[str, Any]
    history: List[Turn] = field(default_factory=list)

    def add_turn(self, question: str, sql: str, explanation: str, insight: str):
        """Record a completed Q&A turn."""
        self.history.append(Turn(question, sql, explanation, insight))

    def get_context_for_sql(self) -> str:
        """
        Return a compact context string summarising recent turns.
        This is injected into the SQL generation prompt so the LLM
        understands follow-up references like 'only from Delhi'.
        """
        if not self.history:
            return ""

        recent = self.history[-3:]   # Only last 3 turns to keep prompt short
        lines = ["Recent conversation:"]
        for i, turn in enumerate(recent, 1):
            lines.append(f"  Q{i}: {turn.question}")
            lines.append(f"  SQL{i}: {turn.sql}")
        return "\n".join(lines)

    def build_llm_messages(self) -> List[dict]:
        """
        Build an OpenAI-style messages list from history.
        Used by chat_with_history() for follow-up analysis.
        """
        messages = []
        for turn in self.history:
            messages.append({"role": "user", "content": turn.question})
            messages.append({"role": "assistant", "content": turn.insight})
        return messages

    def answer_followup(self, question: str) -> str:
        """
        Answer a follow-up conversational question that doesn't require
        a new SQL query (e.g., "Why is Mumbai performing better?").
        """
        schema_str = schema_to_prompt_str(self.schema)
        system = (
            f"You are a data analyst. The user is exploring a dataset with this schema:\n"
            f"{schema_str}\n\n"
            f"Answer their follow-up question based on the conversation so far. "
            f"Be concise and insightful. Keep response under 100 words."
        )

        messages = self.build_llm_messages()
        messages.append({"role": "user", "content": question})

        return chat_with_history(
            system_prompt=system,
            messages=messages,
            temperature=0.4,
            max_tokens=200,
        )

    def clear(self):
        """Reset conversation history (new dataset uploaded)."""
        self.history = []

    @property
    def turn_count(self) -> int:
        return len(self.history)

    @property
    def last_sql(self) -> Optional[str]:
        if self.history:
            return self.history[-1].sql
        return None
