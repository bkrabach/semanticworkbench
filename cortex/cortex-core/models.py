from dataclasses import dataclass, field
import time
import uuid


@dataclass
class ConversationMessage:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "assistant"  # or "user"
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    streaming: bool = True  # True for streaming updates, False for final message
    metadata: dict = field(default_factory=dict)
