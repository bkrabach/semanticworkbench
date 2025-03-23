# LLM Adapter Cleanup Plan

This document outlines the steps to improve the LLM Adapter component by refactoring it to use the Pydantic AI abstraction layer consistently across all supported providers (OpenAI, Azure OpenAI, and Anthropic).

## Current Issues

1. **Inconsistent Provider Handling**: The adapter handles different providers in slightly different ways, with complex conditional code.

2. **Direct API Dependencies**: Parts of the code directly use provider-specific APIs instead of using the Pydantic AI abstraction.

3. **Type Casting Complexity**: Different provider APIs require different approaches to type casting and parameter handling.

4. **Configuration Complexity**: Provider configuration is spread across multiple locations.

## Implementation Plan

### 1. Refactor LLMAdapter Class

```python
class LLMAdapter:
    """Adapter for interacting with LLMs through Pydantic AI."""

    def __init__(self) -> None:
        """Initialize the LLM adapter based on environment variables."""
        # Provider configuration
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

        # Validate provider is supported
        supported_providers = ["openai", "azure_openai", "anthropic"]
        if not self.use_mock and self.provider not in supported_providers:
            logger.warning(f"Unsupported provider: {self.provider}, defaulting to openai")
            self.provider = "openai"

        # Common parameters
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1024"))

        # Set up provider-specific model names
        self.model_name = self._get_model_name()
        
        # Set up configuration for Pydantic AI
        self.config = {
            "provider": self.provider,
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # Initialize the Pydantic AI agent if not using mock
        if not self.use_mock:
            try:
                self.agent = self._create_pydantic_ai_agent()
                logger.info(f"LLM Adapter initialized with provider: {self.provider}, model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM provider: {str(e)}. Falling back to mock LLM.")
                self.use_mock = True

        if self.use_mock:
            logger.info("Using Mock LLM for responses")
            
    def _get_model_name(self) -> str:
        """Get the appropriate model name based on provider."""
        if self.provider == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        elif self.provider == "azure_openai":
            return os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
        elif self.provider == "anthropic":
            return os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        else:
            # Should not reach here due to validation above
            return "gpt-3.5-turbo"
            
    def _create_pydantic_ai_agent(self) -> CortexLLMAgent:
        """Create the appropriate Pydantic AI agent."""
        # Validate required environment variables are set
        self._validate_provider_config()
        
        # Create and return the agent
        return CortexLLMAgent(self.config)
        
    def _validate_provider_config(self) -> None:
        """Validate that required provider configuration is available."""
        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
        elif self.provider == "azure_openai":
            api_key = os.getenv("AZURE_OPENAI_KEY")
            base_url = os.getenv("AZURE_OPENAI_BASE_URL")
            if not api_key or not base_url:
                raise ValueError("AZURE_OPENAI_KEY and AZURE_OPENAI_BASE_URL environment variables are required")
        elif self.provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")
```

### 2. Simplify the CortexLLMAgent Class

```python
class CortexLLMAgent:
    """Agent implementation using Pydantic AI for LLM interactions."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the Pydantic AI agent with configuration."""
        self.config = config
        self.provider = config.get("provider", "openai").lower()
        self.model_name = config.get("model")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 1024)

        # Create the model through Pydantic AI
        self.model = self._create_pydantic_model()

    def _create_pydantic_model(self) -> PydAIBaseModel:
        """Create the appropriate Pydantic AI model based on provider."""
        # Import pydantic_ai here (or wherever appropriate)
        import pydantic_ai as pai
        
        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_API_BASE")
            
            # Use Pydantic AI's OpenAI model implementation
            return pai.OpenAIModel(
                api_key=api_key,
                model=self.model_name,
                base_url=base_url
            )
            
        elif self.provider == "azure_openai":
            api_key = os.getenv("AZURE_OPENAI_KEY")
            base_url = os.getenv("AZURE_OPENAI_BASE_URL")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
            
            # Use Pydantic AI's Azure OpenAI implementation
            return pai.AzureOpenAIModel(
                api_key=api_key,
                deployment_name=self.model_name,
                api_version=api_version,
                endpoint=base_url
            )
            
        elif self.provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            
            # Use Pydantic AI's Anthropic model implementation
            return pai.AnthropicModel(
                api_key=api_key,
                model=self.model_name
            )
            
        else:
            # This should not happen due to validation in LLMAdapter
            raise ValueError(f"Unsupported provider: {self.provider}")
```

### 3. Refactor the run Method to Use Pydantic AI Consistently

```python
async def run(self, input_data: LLMInput) -> LLMOutput:
    """
    Execute the agent with the given input using Pydantic AI.

    Args:
        input_data: The structured input for the LLM

    Returns:
        The structured output from the LLM

    Raises:
        LLMException: If there's an error interacting with the LLM
    """
    try:
        # Use Pydantic AI's abstraction for structured inputs
        pai_input = self._convert_to_pydantic_ai_input(input_data)
        
        # Call Pydantic AI's run method
        pai_output = await self.model.run(pai_input)
        
        # Convert the output back to our format
        return self._convert_from_pydantic_ai_output(pai_output)
    except Exception as e:
        raise LLMException(f"Error from LLM provider: {str(e)}")
        
def _convert_to_pydantic_ai_input(self, input_data: LLMInput) -> Any:
    """Convert our input format to Pydantic AI's input format."""
    # This would be implemented based on Pydantic AI's requirements
    # For now, it's a placeholder
    return input_data
    
def _convert_from_pydantic_ai_output(self, pai_output: Any) -> LLMOutput:
    """Convert Pydantic AI's output format to our output format."""
    # This would be implemented based on Pydantic AI's output format
    # For now, it's a placeholder
    
    # Example implementation
    if hasattr(pai_output, "tool_calls") and pai_output.tool_calls:
        # Convert tool calls
        tool_calls = []
        for tc in pai_output.tool_calls:
            tool_calls.append(ToolCall(
                id=tc.id,
                name=tc.name,
                arguments=tc.arguments
            ))
        return LLMOutput(response=AssistantMessage(content=""), tool_calls=tool_calls)
    else:
        # Convert content response
        return LLMOutput(
            response=AssistantMessage(content=pai_output.content),
            tool_calls=None
        )
```

### 4. Simplify the generate Method

```python
async def generate(self, messages: List[ChatMessage]) -> Optional[Dict[str, Any]]:
    """
    Call the configured LLM provider with the given conversation messages.

    Args:
        messages: List of message dictionaries with "role" and "content" keys

    Returns:
        Dict with either {"content": "..."} for a final answer,
        or {"tool": "...", "input": {...}} for a tool request.
        Returns None if the call fails.
    """
    # Check if we should use the mock LLM (for testing only)
    if self.use_mock:
        logger.info("Using mock LLM for response generation")
        # Import here to avoid circular dependency
        from tests.mocks.mock_llm import generate_mock_response
        return await generate_mock_response(messages)

    try:
        # Convert messages to LLMInput format
        input_data = self._prepare_input(messages)
        
        # Run the agent
        logger.info(f"Calling LLM provider: {self.provider}, model: {self.model_name}")
        output = await self.agent.run(input_data)

        # Format the output for response_handler
        if output.tool_calls:
            # Return the first tool call
            tool_call = output.tool_calls[0]
            logger.info(f"LLM requested tool: {tool_call.name}")
            return {"tool": tool_call.name, "input": tool_call.arguments}
        else:
            # Return the content
            logger.info("LLM returned content response")
            return {"content": output.response.content}

    except Exception as e:
        logger.error(f"LLM API call failed: {type(e).__name__} - {str(e)}")
        return None
        
def _prepare_input(self, messages: List[ChatMessage]) -> LLMInput:
    """Prepare input for the LLM in the appropriate format."""
    # Extract system message if present
    system_message = None
    chat_history: List[ChatMessage] = []
    user_message = None

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            system_message = SystemMessage(content=content)
        elif role == "user":
            # Keep track of the last user message
            user_message = UserMessage(content=content)
        else:
            # Add to history
            chat_history.append(msg)

    # If no user message was found, use the last message
    if not user_message and messages:
        last_msg = messages[-1]
        user_message = UserMessage(content=last_msg.get("content", ""))

    # Make sure we have a user message
    if not user_message:
        user_message = UserMessage(content="")

    # Create and return input
    return LLMInput(
        user_message=user_message,
        system_message=system_message,
        history=cast(List[PydanticChatMessage], chat_history),
    )
```

## Required Changes

1. Implement Pydantic AI integration consistently across all providers
2. Clean up provider configuration management
3. Add validation for required environment variables
4. Move provider-specific logic into factory methods
5. Simplify the interface with Pydantic AI

## Testing Updates

1. Update tests to work with the refactored implementation
2. Add tests for configuration validation
3. Mock Pydantic AI interactions where appropriate
4. Ensure compatibility with all supported providers

## Note on Pydantic AI Documentation

Additional documentation on Pydantic AI would be helpful to complete this implementation, particularly:

1. How to create models for different providers
2. Input/output formats
3. Tool calling support
4. Type definitions and interfaces

With this documentation, the implementation can be further refined to leverage Pydantic AI fully.