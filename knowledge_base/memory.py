from typing import Dict, List


class ConversationMemory:
    def __init__(self, max_turns: int = 5) -> None:
        self.max_turns = max_turns
        self.messages: List[Dict[str, str]] = []

    def add_user_message(self, text: str) -> None:
        self._add_message("user", text)

    def add_assistant_message(self, text: str) -> None:
        self._add_message("assistant", text)

    def get_history(self) -> List[Dict[str, str]]:
        return list(self.messages)

    def format_history(self) -> str:
        lines = []
        for message in self.messages:
            role = "User" if message["role"] == "user" else "Assistant"
            lines.append(f"{role}: {message['content']}")
        return "\n".join(lines)

    def clear(self) -> None:
        self.messages = []

    def _add_message(self, role: str, text: str) -> None:
        self.messages.append({"role": role, "content": text})
        max_messages = self.max_turns * 2
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]
