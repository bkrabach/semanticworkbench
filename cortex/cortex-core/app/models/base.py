from pydantic import BaseModel, Field
from typing import Dict, Any

class BaseModelWithMetadata(BaseModel):
    """
    Base model with metadata field for storing extra information such as
    experimental flags or debug data.
    """
    metadata: Dict[str, Any] = Field(default_factory=dict)