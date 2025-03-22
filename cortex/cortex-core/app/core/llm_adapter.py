"""
LLM Adapter module.

This module provides a simple, direct interface to call different LLM providers
(OpenAI, Azure OpenAI, Anthropic) with unified message formatting and 
environment-based configuration.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional

# Import provider SDKs conditionally
try:
    import openai  # type: ignore
except ImportError:
    openai = None

try:
    import anthropic  # type: ignore
except ImportError:
    anthropic = None

# Import mock LLM for fallback
from .mock_llm import mock_llm

logger = logging.getLogger(__name__)


class LLMAdapter:
    """Adapter for interacting with various LLM providers."""

    def __init__(self):
        """Initialize the LLM adapter based on environment variables."""
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
        
        if self.provider not in ("openai", "azure_openai", "anthropic"):
            logger.warning(f"Unsupported LLM_PROVIDER: {self.provider}, falling back to mock")
            self.use_mock = True
        
        # Common parameters
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1024"))
        
        if not self.use_mock:
            try:
                # Provider-specific setup
                if self.provider == "openai":
                    if not openai:
                        raise ImportError("OpenAI SDK not installed but 'openai' provider selected")
                    
                    self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                    openai.api_key = os.getenv("OPENAI_API_KEY")
                    if not openai.api_key:
                        raise ValueError("OPENAI_API_KEY environment variable not set")
                        
                    base_url = os.getenv("OPENAI_API_BASE")
                    if base_url:
                        openai.api_base = base_url
                        
                elif self.provider == "azure_openai":
                    if not openai:
                        raise ImportError("OpenAI SDK not installed but 'azure_openai' provider selected")
                        
                    self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT")
                    openai.api_type = "azure"
                    openai.api_key = os.getenv("AZURE_OPENAI_KEY")
                    openai.api_base = os.getenv("AZURE_OPENAI_BASE_URL")
                    openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
                    
                    if not self.model or not openai.api_key or not openai.api_base:
                        raise ValueError("Azure OpenAI configuration is incomplete")
                        
                elif self.provider == "anthropic":
                    if not anthropic:
                        raise ImportError("Anthropic SDK not installed but 'anthropic' provider selected")
                        
                    self.model = os.getenv("ANTHROPIC_MODEL", "claude-2")
                    self.api_key = os.getenv("ANTHROPIC_API_KEY")
                    
                    if not self.api_key:
                        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
                        
                    self.client = anthropic.Anthropic(api_key=self.api_key)
                
                logger.info(f"LLM Adapter initialized with provider: {self.provider}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM provider: {str(e)}. Falling back to mock LLM.")
                self.use_mock = True
        
        if self.use_mock:
            logger.info("Using Mock LLM for responses")

    async def generate(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """
        Call the configured LLM provider with the given conversation messages.
        
        Args:
            messages: List of message dictionaries with "role" and "content" keys
            
        Returns:
            Dict with either {"content": "..."} for a final answer,
            or {"tool": "...", "input": {...}} for a tool request.
            Returns None if the call fails.
        """
        # Check if we should use the mock LLM
        if self.use_mock:
            # Random chance of a tool call to simulate realistic responses
            # Check last 3 messages to see if we've already made a tool call
            recent_tool_call = False
            for i in range(min(3, len(messages))):
                idx = len(messages) - 1 - i
                if idx >= 0 and "Tool '" in messages[idx].get("content", ""):
                    recent_tool_call = True
                    break
                    
            # Don't use tool if we've already made a recent tool call to avoid loops
            return await mock_llm.generate_mock_response(messages, with_tool=not recent_tool_call)
        
        # Use the real provider if available
        if self.provider in ("openai", "azure_openai"):
            return await self._generate_openai(messages)
        elif self.provider == "anthropic":
            return await self._generate_anthropic(messages)
        else:
            logger.error(f"Unsupported provider: {self.provider}")
            return None

    async def _generate_openai(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Generate a response using OpenAI's API (works for both OpenAI and Azure)."""
        try:
            if self.provider == "openai":
                response = await openai.ChatCompletion.acreate(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
            else:  # azure_openai
                response = await openai.ChatCompletion.acreate(
                    engine=self.model,  # deployment name for Azure
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )

            # Parse the response
            choice = response["choices"][0]["message"]
            content = choice.get("content", "")
            function_call = choice.get("function_call")

            if function_call:
                # OpenAI function calling scenario
                tool_name = function_call.get("name")
                args_str = function_call.get("arguments", "{}")
                try:
                    tool_args = json.loads(args_str)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse function arguments: {args_str}")
                    tool_args = {"raw_args": args_str}
                return {"tool": tool_name, "input": tool_args}
            else:
                # Try to parse content as potential JSON tool request
                content = content.strip()
                if content.startswith('{') and content.endswith('}'):
                    try:
                        data = json.loads(content)
                        if "tool" in data:
                            return {
                                "tool": data["tool"],
                                "input": data.get("input", {})
                            }
                    except json.JSONDecodeError:
                        pass  # Not valid JSON, treat as regular content
                
                # Normal content answer
                return {"content": content}
                
        except Exception as e:
            logger.error(f"OpenAI API call failed: {type(e).__name__} - {str(e)}")
            return None

    async def _generate_anthropic(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Generate a response using Anthropic's API."""
        try:
            # Check if the newer messages API is available
            if hasattr(self.client, "messages") and callable(getattr(self.client.messages, "create", None)):
                # Use the messages API (Claude 3)
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=messages
                )
                completion_text = response.content[0].text
            else:
                # Fall back to the older completions API
                prompt = self._anthropic_prompt_from_messages(messages)
                response = await self.client.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    prompt=prompt,
                    stop_sequences=[anthropic.HUMAN_PROMPT]
                )
                completion_text = response.completion

            # Try to parse as JSON for a tool request
            stripped = completion_text.strip()
            if stripped.startswith('{'):
                try:
                    tool_req = json.loads(stripped)
                    if "tool" in tool_req:
                        return {
                            "tool": tool_req["tool"], 
                            "input": tool_req.get("input", {})
                        }
                except json.JSONDecodeError:
                    pass  # Not valid JSON, treat as regular content
                    
            # Otherwise, return as final content
            return {"content": completion_text}
            
        except Exception as e:
            logger.error(f"Anthropic API call failed: {type(e).__name__} - {str(e)}")
            return None

    def _anthropic_prompt_from_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert a list of role-based messages to Anthropic's expected format.
        
        Args:
            messages: List of message dictionaries with "role" and "content" keys
            
        Returns:
            A single prompt string in Anthropic's format
        """
        prompt_parts = []
        
        # Handle system message separately
        system_content = None
        for i, msg in enumerate(messages):
            if msg["role"] == "system":
                system_content = msg["content"]
                continue
                
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                prompt_parts.append(f"{anthropic.HUMAN_PROMPT} {content}")
            elif role == "assistant":
                prompt_parts.append(f"{anthropic.AI_PROMPT} {content}")
                
        # Add final assistant prompt to generate the next response
        prompt_parts.append(anthropic.AI_PROMPT)
        
        # Combine everything
        prompt = "\n\n".join(prompt_parts)
        
        # If there was a system message, prepend it with special handling
        if system_content:
            prompt = f"{anthropic.HUMAN_PROMPT} <system>\n{system_content}\n</system>\n\n{prompt}"
            
        return prompt


# Create a global instance
llm_adapter = LLMAdapter()