"""
Module for handling model preferences based on search context analysis.

This module provides functionality to analyze user context and determine the appropriate
model preferences for image selection based on detected intents in the search query.
"""

import re
from typing import List

from mcp.types import ModelHint, ModelPreferences


def detect_intent(context: str) -> dict[str, float]:
    """
    Analyze the context to detect various intents and their confidence scores.

    Args:
        context: The search context string

    Returns:
        Dictionary of intent types and their confidence scores (0.0-1.0)
    """
    # Initialize with default scores
    intents = {
        "humor": 0.0,
        "creativity": 0.0,
        "reasoning": 0.0,
        "complexity": 0.0,
    }

    # Check for humor indicators
    humor_patterns = [r"\b(funny|hilarious|laugh|joke|humor|comedy|amusing)\b", r"\b(lol|haha|rofl)\b", r"😂|🤣|😆|😄"]
    for pattern in humor_patterns:
        if re.search(pattern, context, re.IGNORECASE):
            intents["humor"] += 0.3

    # Check for creativity indicators
    creativity_patterns = [
        r"\b(creative|artistic|imaginative|novel|unique|original)\b",
        r"\b(abstract|dream|fantasy|surreal)\b",
    ]
    for pattern in creativity_patterns:
        if re.search(pattern, context, re.IGNORECASE):
            intents["creativity"] += 0.3

    # Check for reasoning indicators
    reasoning_patterns = [
        r"\b(why|how|explain|reason|logic|analyze|understand)\b",
        r"\b(because|therefore|thus|hence|consequently)\b",
        r"\b(technical|scientific|detailed)\b",
    ]
    for pattern in reasoning_patterns:
        if re.search(pattern, context, re.IGNORECASE):
            intents["reasoning"] += 0.3

    # Check for complexity indicators
    complexity_indicators = [
        len(context) > 100,  # Long query
        len(context.split()) > 15,  # Many words
        "," in context,  # Contains commas (likely more complex expression)
        ";" in context,  # Contains semicolons (likely more complex expression)
    ]
    intents["complexity"] = sum(1 for indicator in complexity_indicators if indicator) * 0.2

    # Cap all scores at 1.0
    for intent in intents:
        intents[intent] = min(intents[intent], 1.0)

    return intents


def get_model_preferences(context: str) -> ModelPreferences:
    """
    Determine model preferences based on context analysis.

    Args:
        context: The search context string

    Returns:
        ModelPreferences object with appropriate settings
    """
    intents = detect_intent(context)

    # Initialize list for model hints
    hints: List[ModelHint] = []

    # Add appropriate hints based on detected intents
    if intents["humor"] > 0.6:
        hints.append(ModelHint(name="humor"))

    if intents["creativity"] > 0.6:
        hints.append(ModelHint(name="creative"))

    if intents["reasoning"] > 0.6:
        hints.append(ModelHint(name="reasoning"))

    # Balance priorities based on complexity
    complexity_score = intents["complexity"]

    # For complex queries, prioritize intelligence over speed
    if complexity_score > 0.5:
        return ModelPreferences(
            hints=hints,
            intelligencePriority=0.8,
            speedPriority=0.2,
            costPriority=0.0,  # Keep cost priority at 0
        )
    # For simple queries, prioritize speed
    else:
        return ModelPreferences(
            hints=hints,
            intelligencePriority=0.4,
            speedPriority=0.6,
            costPriority=0.0,  # Keep cost priority at 0
        )
