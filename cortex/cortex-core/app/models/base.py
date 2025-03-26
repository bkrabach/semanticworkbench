from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class BaseModelWithMetadata(BaseModel):
    """
    Base model with metadata field for storing extra information such as
    experimental flags or debug data.
    """

    metadata: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = Field(default_factory=lambda: str(uuid4()), description="Unique request identifier for tracing")
