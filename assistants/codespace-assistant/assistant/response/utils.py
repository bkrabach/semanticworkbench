import logging
from typing import Any, Dict, List

from assistant_extensions.mcp import MCPSession, MCPToolsConfigModel
from openai.types.chat import ChatCompletion, ChatCompletionToolParam, ParsedChatCompletion
from openai_client import (
    AzureOpenAIServiceConfig,
    OpenAIRequestConfig,
    OpenAIServiceConfig,
)

from ..config import AssistantConfigModel

logger = logging.getLogger(__name__)


def get_formatted_token_count(count: int) -> str:
    """Format token count for display."""
    if count < 1000:
        return str(count)
    return f"{count / 1000:.1f}k"


def get_openai_tools_from_mcp_sessions(
    mcp_sessions: List[MCPSession], tools_config: MCPToolsConfigModel
) -> List[ChatCompletionToolParam]:
    """Convert MCP tools to the format expected by OpenAI."""
    from typing import Any, cast

    tools: List[ChatCompletionToolParam] = []

    # Only add function calling tool if enabled
    # Use getattr to avoid Pylance errors for potential missing attributes
    enable_function_calling = getattr(tools_config, "enable_function_calling", False)
    if enable_function_calling:
        for session in mcp_sessions:
            server_enabled = True
            server_enabled_flags = getattr(tools_config, "server_enabled_flags", {})
            if server_enabled_flags:
                server_name = getattr(session, "server_name", "")
                server_enabled = server_enabled_flags.get(server_name, True)

            # Safe checks for functions
            has_functions_method = getattr(session, "has_functions", None)
            if server_enabled and has_functions_method and has_functions_method():
                get_functions_method = getattr(session, "get_openai_functions", None)
                if get_functions_method:
                    # Cast to Any to avoid type checking issues with dynamic methods
                    session_any = cast(Any, session)
                    for function in session_any.get_openai_functions():
                        tools.append({"type": "function", "function": function})

    return tools


async def get_completion(
    client,
    request_config: OpenAIRequestConfig,
    messages: List[Dict[str, Any]],
    tools: List[ChatCompletionToolParam],
) -> ParsedChatCompletion | ChatCompletion:
    """Get a completion from the OpenAI API."""
    # If tools are present and function calling is enabled, include them in the request
    kwargs = {
        "model": request_config.model,
        "messages": messages,
        "max_tokens": request_config.response_tokens,
        "stream": False,
    }

    # Add optional parameters if they exist on the request_config - use getattr for safe access
    temperature = getattr(request_config, "temperature", None)
    if temperature is not None:
        kwargs["temperature"] = temperature

    top_p = getattr(request_config, "top_p", None)
    if top_p is not None:
        kwargs["top_p"] = top_p

    n = getattr(request_config, "n", None)
    if n is not None:
        kwargs["n"] = n

    if tools and len(tools) > 0:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    # Depending on client implementation, this might be create_chat_completion or chat.completions.create
    if hasattr(client, "create_chat_completion"):
        return await client.create_chat_completion(**kwargs)
    else:
        # Newer OpenAI client has chat.completions.create pattern
        return await client.chat.completions.create(**kwargs)


def get_ai_client_configs(
    config: AssistantConfigModel, request_type: str
) -> tuple[OpenAIRequestConfig, AzureOpenAIServiceConfig | OpenAIServiceConfig]:
    """
    Get the AI client configuration based on the request type.

    Args:
        config: The assistant configuration
        request_type: The type of request (e.g., "reasoning", "generative")

    Returns:
        A tuple of (request_config, service_config)
    """
    if request_type == "reasoning":
        # Use reasoning model configuration
        return (
            config.reasoning_ai_client_config.request_config,
            config.reasoning_ai_client_config.service_config,
        )
    else:
        # Default to generative model configuration
        return (
            config.generative_ai_client_config.request_config,
            config.generative_ai_client_config.service_config,
        )
