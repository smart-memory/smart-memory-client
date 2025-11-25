from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

@dataclass
class MemoryItem:
    """
    Client-side representation of a MemoryItem.
    Decoupled from the core smart-memory package.
    """
    item_id: str
    content: str
    memory_type: str = "semantic"
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    embedding: Optional[List[float]] = None
