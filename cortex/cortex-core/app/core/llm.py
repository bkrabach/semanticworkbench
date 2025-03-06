import logging
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable
import asyncio
import json
from datetime import datetime
import uuid
from enum import Enum
import os
import traceback
import tiktoken

# LiteLLM will be used to interact with the LLM APIs
import litellm
from litellm import completion, acompletion

from app.core.config import get_settings
from app.core.router import message_router

# Setup logging
logger = logging.getLogger(__name__)
settings = get_settings()

class ModelType(str, Enum):
    """Model types for different use cases."""
    CORE = "core"  # Main model for reasoning
    FAST = "fast"  # Faster, smaller model for simple tasks
    BACKUP = "backup"  # Backup model if primary is unavailable

class LLMClient:
    """
    Client for LLM interactions using LiteLLM.
    
    This class is responsible for:
    - Interacting with various LLM providers through LiteLLM
    - Formatting messages for the LLM
    - Parsing responses from the LLM
    - Handling tool usage in LLM interactions
    - Managing fallbacks for API failures
    """
    
    def __init__(self):
        """Initialize the LLM Client."""
        # Configure LiteLLM
        self._configure_litellm()
        
        # Cache for token counters
        self.token_counters = {}
        
        # Cost tracking
        self.total_cost = 0.0
        self.total_tokens = 0
        
        # Model configurations
        self.models = {
            ModelType.CORE: settings.llm_core_model if hasattr(settings, 'llm_core_model') else "gpt-4o",
            ModelType.FAST: settings.llm_fast_model if hasattr(settings, 'llm_fast_model') else "gpt-3.5-turbo",
            ModelType.BACKUP: settings.llm_backup_model if hasattr(settings, 'llm_backup_model') else "claude-3-haiku-20240307"
        }
        
        # Generic fallback model
        self.fallback_model = "gpt-3.5-turbo"
        
        # Model parameters
        self.model_params = {
            # Default parameters for all models
            "default": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 1000
            },
            # Model-specific parameters
            "gpt-4o": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2000
            },
            "gpt-3.5-turbo": {
                "temperature": 0.8,
                "top_p": 0.9,
                "max_tokens": 1000
            },
            "claude-3-haiku-20240307": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 1000
            }
        }
        
        # Tool specifications for different models
        self.tool_specs = {}
        
        # Register with router for events
        message_router.register_component("llm_client", self)
        
        logger.info("LLMClient initialized")
    
    def _configure_litellm(self) -> None:
        """Configure LiteLLM with API keys and settings."""
        try:
            # Set API keys from environment or settings
            litellm.openai_api_key = settings.openai_api_key if hasattr(settings, 'openai_api_key') else os.environ.get("OPENAI_API_KEY")
            litellm.anthropic_api_key = settings.anthropic_api_key if hasattr(settings, 'anthropic_api_key') else os.environ.get("ANTHROPIC_API_KEY")
            
            # Configure global settings
            litellm.drop_params = True  # Drop invalid params instead of raising errors
            litellm.set_verbose = settings.llm_verbose if hasattr(settings, 'llm_verbose') else False
            
            # Configure custom fallbacks (in a production system)
            # litellm.failure_handler = self._handle_litellm_failure
            
            # Log configuration status
            if litellm.openai_api_key:
                logger.info("OpenAI API key configured")
            else:
                logger.warning("OpenAI API key not configured")
            
            if litellm.anthropic_api_key:
                logger.info("Anthropic API key configured")
            else:
                logger.warning("Anthropic API key not configured")
            
        except Exception as e:
            logger.error(f"Error configuring LiteLLM: {str(e)}")
            logger.error(traceback.format_exc())
    
    def get_token_counter(self, model: str):
        """
        Get a token counter for the specified model.
        
        Args:
            model: Model name
            
        Returns:
            Token counting function
        """
        # Check if we already have a counter for this model
        if model in self.token_counters:
            return self.token_counters[model]
        
        try:
            # Get the appropriate encoding for the model
            if "gpt-4" in model:
                encoding = tiktoken.encoding_for_model("gpt-4")
            elif "gpt-3.5" in model:
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            else:
                # Default encoding
                encoding = tiktoken.get_encoding("cl100k_base")
            
            # Create counter function
            def count_tokens(text: str) -> int:
                if not text:
                    return 0
                
                return len(encoding.encode(text))
            
            # Cache and return
            self.token_counters[model] = count_tokens
            return count_tokens
            
        except Exception as e:
            logger.error(f"Error creating token counter for {model}: {str(e)}")
            
            # Fallback to a simple counter
            def simple_counter(text: str) -> int:
                if not text:
                    return 0
                
                # Rough approximation: 4 chars ~= 1 token
                return len(text) // 4
            
            # Cache and return
            self.token_counters[model] = simple_counter
            return simple_counter
    
    def _estimate_tokens(
        self,
        messages: List[Dict[str, str]],
        model: str
    ) -> int:
        """
        Estimate token count for a list of messages.
        
        Args:
            messages: List of messages
            model: Model name
            
        Returns:
            Estimated token count
        """
        counter = self.get_token_counter(model)
        
        # Base overhead for each request
        num_tokens = 3  # every reply is primed with <|start|>assistant<|message|>
        
        for message in messages:
            # Every message has a role and content
            # Add 4 tokens for overhead per message
            num_tokens += 4
            
            # Count tokens in content
            if "content" in message and message["content"]:
                num_tokens += counter(message["content"])
            
            # Count tokens in function calls/results if present
            if "function_call" in message:
                num_tokens += counter(json.dumps(message["function_call"]))
            
            if "tool_calls" in message:
                num_tokens += counter(json.dumps(message["tool_calls"]))
            
            if "tool_call_id" in message:
                num_tokens += counter(message["tool_call_id"])
        
        return num_tokens
    
    def _get_model_params(
        self,
        model: str,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get parameters for the specified model.
        
        Args:
            model: Model name
            custom_params: Optional custom parameters
            
        Returns:
            Model parameters
        """
        # Start with default parameters
        params = self.model_params["default"].copy()
        
        # Add model-specific parameters
        if model in self.model_params:
            params.update(self.model_params[model])
        
        # Add custom parameters
        if custom_params:
            params.update(custom_params)
        
        return params
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model_type: ModelType = ModelType.CORE,
        tools: Optional[List[Dict[str, Any]]] = None,
        custom_params: Optional[Dict[str, Any]] = None,
        retry_count: int = 2,
        timeout: int = 30,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a completion from the LLM.
        
        Args:
            messages: List of messages
            model_type: Type of model to use
            tools: Optional tools to provide to the model
            custom_params: Optional custom parameters
            retry_count: Number of retries on failure
            timeout: Timeout in seconds
            response_format: Optional response format specification
            
        Returns:
            LLM response
        """
        # Get model
        model = self.models[model_type]
        
        # Get model parameters
        params = self._get_model_params(model, custom_params)
        
        # Add tools if provided
        if tools:
            params["tools"] = tools
        
        # Add response format if provided
        if response_format:
            params["response_format"] = response_format
        
        # Estimate tokens
        estimated_tokens = self._estimate_tokens(messages, model)
        logger.debug(f"Estimated tokens for request: {estimated_tokens}")
        
        # Track retries
        retries = 0
        
        while retries <= retry_count:
            try:
                # Log attempt
                if retries > 0:
                    logger.info(f"Retry {retries}/{retry_count} for model {model}")
                
                # Make request
                start_time = datetime.utcnow()
                
                # Async completion with timeout
                response = await asyncio.wait_for(
                    acompletion(
                        model=model,
                        messages=messages,
                        **params
                    ),
                    timeout=timeout
                )
                
                # Calculate duration
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # Log success
                logger.info(f"LLM completion completed in {duration:.2f}s, model={model}")
                
                # Track usage and cost
                if "usage" in response:
                    usage = response["usage"]
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                    
                    # Update token count
                    self.total_tokens += total_tokens
                    
                    # Calculate cost (approximate)
                    cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
                    self.total_cost += cost
                    
                    logger.debug(f"Tokens: {prompt_tokens} prompt, {completion_tokens} completion, cost: ${cost:.6f}")
                
                return response
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout calling {model} after {timeout}s")
                retries += 1
                
                # If we've exhausted retries with the current model, try fallback
                if retries > retry_count:
                    if model != self.fallback_model:
                        logger.warning(f"Falling back to {self.fallback_model} after timeout")
                        model = self.fallback_model
                        retries = 0  # Reset retries for the fallback model
                    else:
                        # We're already on the fallback model and still timing out
                        raise TimeoutError(f"LLM request timed out after {retry_count} retries")
                
            except Exception as e:
                logger.error(f"Error calling LLM: {str(e)}")
                retries += 1
                
                # If we've exhausted retries with the current model, try fallback
                if retries > retry_count:
                    if model != self.fallback_model:
                        logger.warning(f"Falling back to {self.fallback_model} after error: {str(e)}")
                        model = self.fallback_model
                        retries = 0  # Reset retries for the fallback model
                    else:
                        # We're already on the fallback model and still getting errors
                        raise RuntimeError(f"LLM request failed after {retry_count} retries: {str(e)}")
    
    def _calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        Calculate the approximate cost of an LLM request.
        
        Args:
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            Estimated cost in USD
        """
        # Default rates
        prompt_rate = 0.0
        completion_rate = 0.0
        
        # Set rates based on model
        if model == "gpt-4o":
            prompt_rate = 0.01 / 1000
            completion_rate = 0.03 / 1000
        elif model == "gpt-3.5-turbo":
            prompt_rate = 0.0015 / 1000
            completion_rate = 0.002 / 1000
        elif "claude-3-haiku" in model:
            prompt_rate = 0.00025 / 1000
            completion_rate = 0.00125 / 1000
        elif "claude-3-sonnet" in model:
            prompt_rate = 0.003 / 1000
            completion_rate = 0.015 / 1000
        
        # Calculate cost
        cost = (prompt_tokens * prompt_rate) + (completion_tokens * completion_rate)
        
        return cost
    
    def format_system_message(
        self,
        content: str
    ) -> Dict[str, str]:
        """
        Format a system message.
        
        Args:
            content: Message content
            
        Returns:
            Formatted message
        """
        return {
            "role": "system",
            "content": content
        }
    
    def format_user_message(
        self,
        content: str
    ) -> Dict[str, str]:
        """
        Format a user message.
        
        Args:
            content: Message content
            
        Returns:
            Formatted message
        """
        return {
            "role": "user",
            "content": content
        }
    
    def format_assistant_message(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Format an assistant message.
        
        Args:
            content: Message content
            tool_calls: Optional tool calls
            
        Returns:
            Formatted message
        """
        message = {
            "role": "assistant",
            "content": content
        }
        
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        return message
    
    def format_tool_result_message(
        self,
        tool_call_id: str,
        content: str
    ) -> Dict[str, str]:
        """
        Format a tool result message.
        
        Args:
            tool_call_id: Tool call ID
            content: Result content
            
        Returns:
            Formatted message
        """
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content
        }
    
    def format_mcp_tools(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format MCP tools for LLM tools API.
        
        Args:
            tools: List of MCP tools
            
        Returns:
            Formatted tools
        """
        formatted_tools = []
        
        for tool in tools:
            # Create tool spec
            tool_spec = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            # Add parameters
            for param in tool["parameters"]:
                param_name = param["name"]
                param_type = param["type"]
                
                # Map parameter type
                if param_type == "string":
                    param_spec = {"type": "string"}
                elif param_type == "integer":
                    param_spec = {"type": "integer"}
                elif param_type == "number":
                    param_spec = {"type": "number"}
                elif param_type == "boolean":
                    param_spec = {"type": "boolean"}
                elif param_type == "array":
                    param_spec = {"type": "array", "items": {"type": "string"}}
                elif param_type == "object":
                    param_spec = {"type": "object"}
                else:
                    # Default to string
                    param_spec = {"type": "string"}
                
                # Add description
                if param["description"]:
                    param_spec["description"] = param["description"]
                
                # Add default value if available
                if param.get("default") is not None:
                    param_spec["default"] = param["default"]
                
                # Add to properties
                tool_spec["function"]["parameters"]["properties"][param_name] = param_spec
                
                # Add to required list if required
                if param["required"]:
                    tool_spec["function"]["parameters"]["required"].append(param_name)
            
            # Add to formatted tools
            formatted_tools.append(tool_spec)
        
        return formatted_tools
    
    def parse_tool_calls(
        self,
        response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Parse tool calls from an LLM response.
        
        Args:
            response: LLM response
            
        Returns:
            List of tool calls
        """
        # Check if response contains choices
        if "choices" not in response or not response["choices"]:
            return []
        
        # Get first choice
        choice = response["choices"][0]
        
        # Get message
        if "message" not in choice:
            return []
        
        message = choice["message"]
        
        # Check for tool calls
        if "tool_calls" not in message or not message["tool_calls"]:
            return []
        
        # Extract tool calls
        tool_calls = []
        
        for tool_call in message["tool_calls"]:
            # Check if it's a function call
            if tool_call["type"] != "function":
                continue
            
            # Get function call
            function = tool_call["function"]
            
            # Parse arguments
            args = {}
            
            if "arguments" in function:
                try:
                    args = json.loads(function["arguments"])
                except Exception as e:
                    logger.error(f"Error parsing tool arguments: {str(e)}")
                    continue
            
            # Create tool call
            tool_calls.append({
                "id": tool_call["id"],
                "tool": function["name"],
                "args": args
            })
        
        return tool_calls
    
    async def initialize(self) -> None:
        """
        Initialize the LLM Client.
        
        This method is called during application startup.
        """
        try:
            # Re-configure LiteLLM to ensure we have the latest settings
            self._configure_litellm()
            
            # Reset usage stats
            self.total_cost = 0.0
            self.total_tokens = 0
            
            # Subscribe to relevant events if needed
            await message_router.subscribe_to_event(
                "llm_client",
                "application_startup",
                self.on_application_startup
            )
            
            logger.info("LLMClient successfully initialized")
        except Exception as e:
            logger.error(f"Error initializing LLMClient: {str(e)}")
            raise
            
    async def on_application_startup(self, data: Dict[str, Any]) -> None:
        """
        Handle application startup event.
        
        Args:
            data: Event data
        """
        logger.info("LLMClient received application startup event")
        # Additional initialization can happen here if needed
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        # Nothing to clean up for now
        logger.info("LLMClient cleaned up")

# Create a global instance for use throughout the application
llm_client = LLMClient()