import dataclasses
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ConversationContextModel:
    """
    Client-side representation of conversation context.
    Used to enable conversation-aware extraction with entity tracking,
    coreference resolution, and speaker relations.
    """

    conversation_id: Optional[str] = None
    participant_id: Optional[str] = (
        None  # Who is participating (see contracts/conversation.json)
    )
    topics: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    turn_history: List[Dict[str, Any]] = field(default_factory=list)
    sentiment: Optional[str] = None
    active_threads: List[str] = field(default_factory=list)
    extra: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationContextModel":
        """Build from a plain dict, ignoring unknown keys."""
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})
