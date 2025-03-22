# Using the Response Handler

This guide demonstrates how to use the Response Handler system in your Cortex Core application.

## Basic Usage

The ResponseHandler is typically used through the API endpoints. When a user sends a message, it's processed by the `receive_input` endpoint, which dispatches it to the ResponseHandler for processing.

```python
# Example API client code
import requests

# Send a message
response = requests.post(
    "http://localhost:8000/api/v1/input",
    json={
        "content": "What's the current time?",
        "conversation_id": "conversation123"
    },
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

# Start streaming the response
stream = requests.get(
    "http://localhost:8000/api/v1/output/stream?conversation_id=conversation123",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    stream=True
)

# Process the stream
for line in stream.iter_lines():
    if line:
        # Filter out keep-alive new lines
        if line.startswith(b'data: '):
            # Parse the SSE data
            data = json.loads(line[6:].decode('utf-8'))
            
            # Process based on event type
            if data.get('type') == 'response_chunk':
                print(data.get('data'), end='', flush=True)
            elif data.get('type') == 'response_complete':
                print("\nResponse complete!")
                break
```

## Creating Custom Tools

To create a custom tool for the ResponseHandler:

1. Define a function with the tool's implementation
2. Register it with the `@register_tool` decorator
3. Ensure it's imported at application startup

```python
# my_tools.py
from app.core.response_handler import register_tool
import httpx

@register_tool("weather_lookup")
async def weather_lookup(location: str) -> dict:
    """Look up weather information for a location."""
    # Example implementation using a weather API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.weatherapi.com/v1/current.json",
            params={
                "key": "YOUR_API_KEY",
                "q": location,
                "aqi": "no"
            }
        )
        data = response.json()
        
        # Extract relevant information
        return {
            "location": data["location"]["name"],
            "country": data["location"]["country"],
            "temperature_c": data["current"]["temp_c"],
            "temperature_f": data["current"]["temp_f"],
            "condition": data["current"]["condition"]["text"],
            "humidity": data["current"]["humidity"],
            "wind_kph": data["current"]["wind_kph"]
        }

# Import in main.py or another startup file
# import my_tools
```

## LLM Configuration

Configure the LLM adapter through environment variables:

```bash
# .env file
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1024
```

Or for Azure OpenAI:

```bash
LLM_PROVIDER=azure_openai
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_BASE_URL=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2023-05-15
```

For testing purposes, you can use the mock LLM:

```bash
USE_MOCK_LLM=true
```

## System Prompt Customization

To customize the system prompt used by the ResponseHandler:

```bash
# .env file
SYSTEM_PROMPT="You are a helpful assistant with access to various tools. When the user asks a question that requires current information or specific data lookups, use the appropriate tool to find the answer. Otherwise, provide a direct response based on your existing knowledge."
```

## Direct Usage in Code

While the ResponseHandler is typically accessed through API endpoints, you can also use it directly in your code:

```python
from app.core.response_handler import response_handler

async def process_message(user_id, conversation_id, message_content):
    """Process a message directly with the ResponseHandler."""
    await response_handler.handle_message(
        user_id=user_id,
        conversation_id=conversation_id,
        message_content=message_content,
        metadata={"source": "direct"}  # Optional metadata
    )
    
    # To get the response, you'd typically listen to the output queue:
    from app.core.response_handler import get_output_queue
    
    queue = get_output_queue(conversation_id)
    
    # Process messages from the queue
    while True:
        event_data = await queue.get()
        # Process the event data
        # Break when you receive a final message or timeout
```

## Best Practices

1. **Tool Design**: Keep tools focused on specific tasks with clear inputs and outputs.
2. **Error Handling**: Implement robust error handling in your tools to avoid cascade failures.
3. **Context Management**: Provide relevant context to the LLM for better responses.
4. **Prompt Engineering**: Carefully design system prompts for optimal LLM behavior.
5. **Testing**: Use `USE_MOCK_LLM=true` for testing without LLM API calls.
6. **Security**: Be mindful of what capabilities you expose through tools.
7. **Performance**: Consider caching for expensive operations in frequently used tools.

## Debugging

If you encounter issues with the ResponseHandler:

1. Check the application logs for detailed error messages
2. Verify that your LLM provider is properly configured
3. Test your tools independently to ensure they work as expected
4. Use the mock LLM (`USE_MOCK_LLM=true`) to isolate issues
5. Check that your conversation_id is consistent between requests

## Advanced: Customizing ResponseHandler Behavior

For advanced customization, you can create a custom ResponseHandler by extending the base class:

```python
from app.core.response_handler import ResponseHandler

class CustomResponseHandler(ResponseHandler):
    """Custom response handler with application-specific behavior."""
    
    def __init__(self):
        super().__init__()
        # Custom initialization
        
    async def _execute_tool(self, tool_name, tool_args, user_id):
        """Override tool execution to add custom behavior."""
        # Add pre-processing logic
        result = await super()._execute_tool(tool_name, tool_args, user_id)
        # Add post-processing logic
        return result
    
    async def handle_message(self, user_id, conversation_id, message_content, metadata=None):
        """Override message handling to add custom behavior."""
        # Custom pre-processing
        await super().handle_message(user_id, conversation_id, message_content, metadata)
        # Custom post-processing
```