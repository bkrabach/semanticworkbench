"""
Module for handling model selection and preferences.

This module centralizes the logic for selecting models based on user preferences,
system requirements, and available options. It's designed to support dynamic model
switching and preference configuration.
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Literal, Optional, Union

from openai_client import OpenAIRequestConfig

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Types of models that can be used by the system."""

    GENERATIVE = auto()
    REASONING = auto()
    SPECIALIZED = auto()  # For more specialized models like image generation, etc.


@dataclass
class ModelOption:
    """
    Represents a model that can be selected and its capabilities.
    """

    name: str
    display_name: str
    description: str
    type: ModelType
    max_tokens: int
    default_temperature: float = 0.7
    service_type: Literal["azure", "openai"] = "azure"
    is_default: bool = False


class ModelSelector:
    """
    Handles selection of appropriate models based on task requirements and user preferences.
    """

    def __init__(self):
        self._available_models: Dict[str, ModelOption] = {}
        self._default_models: Dict[ModelType, str] = {}  # Maps model type to default model name

    def register_model(self, model: ModelOption) -> None:
        """
        Register a model as available for selection.

        Args:
            model: The model option to register
        """
        self._available_models[model.name] = model

        # If this is marked as default for its type, update the default model map
        if model.is_default:
            self._default_models[model.type] = model.name
            logger.info(f"Set default {model.type.name} model to {model.name}")

    def register_models(self, models: List[ModelOption]) -> None:
        """
        Register multiple models at once.

        Args:
            models: List of model options to register
        """
        for model in models:
            self.register_model(model)

    def get_default_model(self, model_type: ModelType) -> Optional[ModelOption]:
        """
        Get the default model for a specific type.

        Args:
            model_type: The type of model to get the default for

        Returns:
            The default model option, or None if no default is set
        """
        if model_type not in self._default_models:
            return None

        model_name = self._default_models[model_type]
        return self._available_models.get(model_name)

    def get_model_option(self, model_name: str) -> Optional[ModelOption]:
        """
        Get a model option by name.

        Args:
            model_name: The name of the model to retrieve

        Returns:
            The model option, or None if not found
        """
        return self._available_models.get(model_name)

    def get_all_models(self) -> List[ModelOption]:
        """
        Get all registered models.

        Returns:
            List of all registered model options
        """
        return list(self._available_models.values())

    def get_models_by_type(self, model_type: ModelType) -> List[ModelOption]:
        """
        Get all models of a specific type.

        Args:
            model_type: The type of models to retrieve

        Returns:
            List of model options matching the type
        """
        return [model for model in self._available_models.values() if model.type == model_type]

    def update_request_config_for_model(
        self, model_name: str, original_config: OpenAIRequestConfig
    ) -> OpenAIRequestConfig:
        """
        Update a request configuration for a specific model.

        Args:
            model_name: The name of the model to configure for
            original_config: The original request configuration

        Returns:
            Updated request configuration
        """
        model_option = self.get_model_option(model_name)
        if not model_option:
            logger.warning(f"Model {model_name} not found, using original config")
            return original_config

        # Create new config with model-specific settings
        updated_config = OpenAIRequestConfig(
            model=model_name,
            response_tokens=min(original_config.response_tokens, model_option.max_tokens),
            max_tokens=model_option.max_tokens,
            is_reasoning_model=model_option.type == ModelType.REASONING,
            # Preserve other fields from original config
            reasoning_effort=getattr(original_config, "reasoning_effort", "medium"),
            enable_markdown_in_reasoning_response=getattr(
                original_config, "enable_markdown_in_reasoning_response", True
            ),
            reasoning_token_allocation=getattr(original_config, "reasoning_token_allocation", 25000),
        )

        # Note: OpenAIRequestConfig doesn't have a temperature parameter in its constructor
        # Temperature would need to be set through another mechanism if needed

        return updated_config

    def select_model_for_task(
        self, task_type: Union[str, ModelType], preferred_model: Optional[str] = None
    ) -> Optional[ModelOption]:
        """
        Select the most appropriate model for a given task.

        Args:
            task_type: Type of task or model type needed
            preferred_model: User's preferred model name (if any)

        Returns:
            The selected model option, or None if no suitable model found
        """
        # Convert string task type to ModelType if needed
        if isinstance(task_type, str):
            try:
                model_type = ModelType[task_type.upper()]
            except KeyError:
                logger.warning(f"Unknown task type: {task_type}")
                return None
        else:
            model_type = task_type

        # If user has a preference and it's available, use it
        if preferred_model and preferred_model in self._available_models:
            return self._available_models[preferred_model]

        # Otherwise use the default model for this type
        return self.get_default_model(model_type)


# Initialize default model options
def initialize_default_models() -> ModelSelector:
    """
    Initialize the model selector with default model options.

    Returns:
        Configured ModelSelector instance
    """
    selector = ModelSelector()

    # Register default models
    selector.register_models([
        ModelOption(
            name="gpt-4o",
            display_name="GPT-4o",
            description="General purpose AI model with strong reasoning, coding, and multimodal capabilities",
            type=ModelType.GENERATIVE,
            max_tokens=128000,
            default_temperature=0.7,
            is_default=True,
        ),
        ModelOption(
            name="o3-mini",
            display_name="o3-mini",
            description="Reasoning model optimized for complex problem solving and step-by-step thinking",
            type=ModelType.REASONING,
            max_tokens=200000,
            default_temperature=0.6,
            is_default=True,
        ),
        ModelOption(
            name="o3-preview",
            display_name="o3-preview",
            description="Advanced reasoning capabilities with higher token capacity",
            type=ModelType.REASONING,
            max_tokens=250000,
            default_temperature=0.5,
        ),
    ])

    return selector
