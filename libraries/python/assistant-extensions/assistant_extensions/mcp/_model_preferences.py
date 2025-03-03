from typing import List, Optional

from pydantic import BaseModel, Field


class ModelHint(BaseModel):
    """
    A hint for model selection, specifying a preferred model name or family.
    """

    name: Optional[str] = None


class ModelPreferences(BaseModel):
    """
    Model preferences used to guide model selection.

    Attributes:
        hints: List of model name hints to try
        costPriority: Priority for minimizing cost (0-1). None is treated as 0.
        speedPriority: Priority for low latency (0-1). None is treated as 0.
        intelligencePriority: Priority for capabilities (0-1). None is treated as 0.

    Note:
        When comparing priorities, None values are treated as 0. This allows
        setting just one priority (e.g., intelligencePriority=1) to prioritize
        that aspect without having to explicitly set the others to 0.
    """

    hints: Optional[List[ModelHint]] = None
    costPriority: Optional[float] = Field(None, ge=0, le=1)
    speedPriority: Optional[float] = Field(None, ge=0, le=1)
    intelligencePriority: Optional[float] = Field(None, ge=0, le=1)
