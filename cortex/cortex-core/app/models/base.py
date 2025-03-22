from typing import Any, Dict

from pydantic import BaseModel, Field


class BaseModelWithMetadata(BaseModel):
    """
    Base model with metadata field for storing extra information such as
    experimental flags or debug data.
    """

    metadata: Dict[str, Any] = Field(default_factory=dict)
