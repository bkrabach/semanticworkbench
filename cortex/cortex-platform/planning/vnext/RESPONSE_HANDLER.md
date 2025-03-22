# Design and Implementation Plan: ResponseHandler and LLM Adapter

This document describes a clear, self-contained design for the **ResponseHandler** and **LLM Adapter** components of Cortex Core. These components orchestrate the generation of responses using Large Language Models (LLMs) and tool integrations. The design prioritizes simplicity, directness, and minimal abstraction, while supporting multi-step tool use and streaming outputs via Server-Sent Events (SSE).

## Overview

**ResponseHandler** is responsible for processing incoming user messages, calling external LLM APIs to generate responses, handling any requested tool invocations in a loop, and delivering the final answer to clients through SSE. **LLM Adapter** provides a minimal interface to call different LLM providers (OpenAI, Azure OpenAI, Anthropic) with unified message formatting and straightforward environment-based configuration.

Key features of this design include:

- **Multi-step Tool Call Resolution**: The system can handle an LLM requesting one or more tool executions before producing a final answer. The ResponseHandler will iteratively call the LLM, execute tools, and continue the dialogue until completion.
- **Minimal Integration with LLM APIs**: The LLM Adapter directly calls provider APIs (OpenAI, Azure OpenAI, or Anthropic) using simple message lists and basic SDK/HTTP calls, without extra abstraction layers.
- **Direct Message Formatting**: LLM prompts are constructed as a list of role-based messages (with optional system instructions) in the format each provider expects, keeping the structure simple and consistent.
- **Basic Tool Execution Interface**: Tools are invoked via direct Python function calls or simple async service calls (e.g., using the Memory or Cognition service clients) with no complex wrappers.
- **Incremental Streaming Output**: Final responses are streamed to the client in real-time over SSE, sending plain text chunks as they become available, with minimal formatting (just the SSE `data:` prefix and newlines).
- **Straightforward Error Handling**: Errors in LLM calls or tool execution are caught and logged, and cause an immediate, clearly visible error message to be sent to the client (instead of silent failures or obscure behaviors).
- **Environment-Based Configuration**: All external settings (API keys, model names, etc.) are taken from environment variables. The code directly reads these variables to configure the LLM Adapter and related components, avoiding complex config files or layered config objects.
- **Minimal File and Code Structure**: The core logic resides primarily in two modules (e.g. `response_handler.py` and `llm_adapter.py`). The implementation avoids unnecessary indirection or legacy compatibility code, focusing on the current requirements only.

Below, we detail the design of each component, the flow of handling a user message with possible tool usage, integration specifics for each LLM provider, and how the event loop and streaming output tie everything together.

## ResponseHandler Design

### Responsibilities and Workflow

The **ResponseHandler** orchestrates the end-to-end processing of a user’s message. Its responsibilities include:

- Receiving a new user message event (with user ID, conversation ID, and message content).
- Storing the user message and retrieving relevant conversation context (via the Memory and Cognition services).
- Preparing the prompt messages for the LLM (including system instructions, context, and the user query).
- Invoking the LLM (through the LLM Adapter) to generate a response.
- Detecting if the LLM’s response requests a tool/action instead of a final answer.
- If a tool is requested, executing the tool and inserting the result into the conversation context, then calling the LLM again. This loop repeats for multi-step tool usage.
- Once a final answer (no tool call) is obtained from the LLM, streaming that answer back to the client via SSE.
- Handling any errors by logging and sending an error message to the client.

The logic is kept linear and clear: input → [store] → [get context] → LLM generate → possibly tool → LLM generate → ... → output. There are no extraneous abstraction layers around these steps.

### Multi-Step Tool Call Resolution

The ResponseHandler supports iterative tool use by the AI. The conversation with the LLM may involve multiple turns where the assistant first asks to use a tool, receives the tool result, and then provides the final answer. We implement this with a simple loop. On each iteration, we call the LLM and check if the output indicates a tool should be used. Pseudocode for this loop in `ResponseHandler.handle_message` could look like:

```python
class ResponseHandler:
    def __init__(self, memory_client, cognition_client, llm_adapter):
        self.memory = memory_client
        self.cognition = cognition_client
        self.llm = llm_adapter

    async def handle_message(self, user_id: str, conversation_id: str, message: str):
        """Process a user message and produce a response (possibly with tool calls)."""
        # 1. Store the user input in memory service (no caching or preprocessing)
        await self.memory.store_input(user_id, {"role": "user", "content": message})
        # 2. Retrieve conversation history or context (e.g., last N messages)
        history = await self.memory.get_history(user_id)
        # Optionally, enrich context via cognition service (not processing here for simplicity)
        # context = await self.cognition.get_context(user_id)

        # 3. Prepare initial messages list for LLM (include history and new user message)
        messages = []
        system_instruction = os.getenv("SYSTEM_PROMPT")  # optional system-level prompt from env
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        # Append conversation history (alternating user/assistant messages from memory)
        for entry in history:
            # Assuming history entries are stored as {"role": ..., "content": ...}
            messages.append({"role": entry["role"], "content": entry["content"]})
        # (If the new user message isn't already in history, ensure it's included as the last user message)
        if not history or history[-1]["content"] != message:
            messages.append({"role": "user", "content": message})

        # 4. Iteratively call LLM and handle tool requests
        final_answer = None
        while True:
            # Call the LLM to generate a response (non-streaming for intermediate steps)
            result = await self.llm.generate(messages)
            if result is None:
                # LLM returned nothing or error; handle error by breaking loop
                final_answer = "ERROR: LLM call failed."
                break
            # If the LLM indicates a tool call
            if result.get("tool"):
                tool_name = result["tool"]
                tool_args = result.get("input", {})
                try:
                    # Execute the requested tool (either a local function or service call)
                    tool_result = await self._execute_tool(tool_name, tool_args, user_id)
                except Exception as e:
                    # Tool execution failed
                    final_answer = f"ERROR: tool '{tool_name}' failed: {e}"
                    break
                # Insert the tool result into the conversation history for the next LLM call.
                # For example, we treat it as an assistant's observation/answer to the tool usage.
                messages.append({"role": "assistant", "content": str(tool_result)})
                continue  # Loop back to LLM with updated context
            else:
                # LLM returned a final answer (no tool call requested)
                final_answer = result.get("content", "")
                # Optionally store the assistant's answer in memory for future history
                if final_answer:
                    await self.memory.store_input(user_id, {"role": "assistant", "content": final_answer})
                break

        # 5. Stream the final answer via SSE
        await self._stream_response(conversation_id, final_answer)
```

In this loop:

- We first **store the user input** (`store_input` tool on the Memory service) and **retrieve history** (`get_history` resource). This provides context for the conversation. No caching or complex preprocessing is done on history — we fetch it fresh for each message to keep things simple.
- We build the `messages` list to send to the LLM. If a system instruction is provided (via an environment variable `SYSTEM_PROMPT` or similar), it’s included as a system role message. Then we append the conversation history (each entry already labeled with a role, e.g., `"user"` or `"assistant"`). Finally, we ensure the latest user message is in the list (the memory history might already include it, but we guard against duplication).
- We enter a loop to handle potential tool calls:
  1. **Call the LLM** via the LLM Adapter’s `generate` method with the current messages. At this stage, we request a single message completion (we do not stream token-by-token yet, since the response might not be final).
  2. **Examine the result**: We expect `result` to be a dictionary containing either a `"content"` for a final answer, or a `"tool"` field indicating a tool request.
     - If `result` indicates a tool (e.g., `{"tool": "weather", "input": {"location": "Seattle"}}`), we extract the tool name and arguments. The ResponseHandler then **executes the tool**. Tool execution is done in the simplest way possible:
       - If the tool corresponds to an MCP service call (like Memory or Cognition), we directly call the appropriate client method (for example, `await self.cognition.get_context(user_id)` if tool is `"get_context"`).
       - If the tool is implemented as a local Python function (for domain logic), we call that function directly (possibly using `await` if it's async).
       - The result of the tool call (e.g., some data or text) is captured as `tool_result`. We then append a new message to the `messages` list representing the **assistant’s observation** or result from the tool. For simplicity, we treat this as an assistant message containing the raw tool result (converted to string if needed). This way, the next LLM call has access to the outcome of the tool use.
       - We then `continue` the loop to call the LLM again, now with the updated context (which includes the tool result).
     - If `result` does **not** indicate a tool (meaning it contains a `"content"` field with the answer), then we have our **final answer**. We break out of the loop.
  3. If at any point an error occurs (the LLM call fails or a tool execution raises an exception), we break out with an error message assigned to `final_answer`. All exceptions are caught and turned into a clear error string (e.g., `"ERROR: tool 'X' failed: <details>"`) so the client can see something went wrong. We also log the error for debugging, but we do not hide it behind silent retries or complex fallback logic.
- After the loop, we have either a final answer from the LLM or an error message. We optionally store the assistant’s final answer in memory (by calling `store_input` again with role `"assistant"` and the content) so that it becomes part of the conversation history. This keeps the history complete for future queries.
- Finally, we call `_stream_response` to deliver the `final_answer` to the client via SSE.

This multi-step process ensures that if the LLM requires multiple tools, each will be executed in turn, and the model gets to see the result of each tool call before deciding how to proceed. The loop terminates only when a final answer is produced or an error occurs. The logic avoids any complex state machines or recursive calls – it’s a simple `while True` loop managing the conversation state.

**Tool Request Format:** The ResponseHandler needs a reliable way to recognize when the LLM is asking for a tool. To keep things simple and provider-agnostic, we use a **convention** in the LLM’s response content. We instruct the LLM (via the system prompt or fine-tuned behavior) to respond with a structured JSON or marker when it wants to use a tool. For example, the assistant might output:

```json
{ "tool": "lookup_weather", "input": { "city": "Paris" } }
```

as its message content to request using a `lookup_weather` tool. The ResponseHandler checks if the LLM output can be parsed as JSON with a `"tool"` key (or otherwise matches a pattern indicating a tool call). If so, it treats it as a tool invocation request. This approach is straightforward to implement (a simple `if "tool" in result` check after parsing the LLM output). It does require the LLM to follow the format, which we enforce by including guidelines in the system message (for OpenAI and Anthropic) or by using function-call features where available (OpenAI’s API can handle function calls natively, but we default to our own check to keep logic uniform across providers).

### SSE Streaming of Final Output

After obtaining the final answer, the ResponseHandler streams it to clients via Server-Sent Events. The SSE integration is implemented with minimal formatting and direct output of text:

- The `/output/stream` FastAPI endpoint (already part of Cortex Core) uses a `StreamingResponse` that subscribes to the output of the ResponseHandler. Typically, we maintain an asyncio queue or event bus channel for each conversation/user to which ResponseHandler will publish the response text.
- `_stream_response(conversation_id, final_answer)` in ResponseHandler will take the final answer text and break it into chunks (for example, by sentence or a fixed number of characters) and push those chunks to the output stream asynchronously. Each chunk is sent as an SSE `data` event. For example, if using an asyncio Queue, `_stream_response` can `await queue.put(chunk)` for each piece, and the SSE endpoint will read from the queue and yield it.
- We keep SSE formatting minimal: each message is prefixed by `data: ` and followed by two newline characters, per SSE protocol. We do not wrap the data in JSON or add event names (unless needed). The client will receive the stream as plaintext segments which can be concatenated to form the full response.
- Importantly, we **stream incrementally**: as soon as we have the first part of the final answer, we send it out, without waiting to form the entire message. In our implementation, since we typically will have the full `final_answer` string by the time we stream (because we gathered it from the LLM), we simulate streaming by slicing it. For example:

```python
async def _stream_response(self, conversation_id: str, final_text: str):
    """Stream the final response text to the client's SSE connection."""
    if final_text is None:
        final_text = ""
    # In a real implementation, get the output queue for this conversation
    output_queue = get_output_queue(conversation_id)
    # Stream the text in chunks to the queue
    chunk_size = 50  # characters per chunk, for example
    for i in range(0, len(final_text), chunk_size):
        chunk = final_text[i:i+chunk_size]
        data_line = f"data: {chunk}\n\n"
        await output_queue.put(data_line)
    # Indicate completion (optional: some clients may use a special end-of-stream marker)
    await output_queue.put("data: [DONE]\n\n")
```

And in the FastAPI output endpoint, we might have something like:

```python
from fastapi import Response
from fastapi.responses import StreamingResponse

@app.get("/output/stream")
async def output_stream(user: User = Depends(get_current_user)):
    user_id = user.id
    # Assume we have an output_queue per user (or conversation) created when the conversation started
    queue = get_output_queue_for_user(user_id)
    async def event_generator():
        while True:
            data = await queue.get()  # wait for next chunk to send
            yield data
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

In this scheme, when `ResponseHandler.handle_message` completes and calls `_stream_response`, it pushes the final answer chunks into the queue, which the `event_generator` in the SSE endpoint is listening on. The client starts receiving those chunks immediately. The design avoids any complex formatting or encoding; it’s literally streaming the text with SSE protocol markers.

**Note:** If using the OpenAI API’s streaming capability directly, we could stream tokens from the model in real-time. However, to keep integration simple and consistent across providers, we choose to retrieve the complete answer then stream it ourselves. This approach is easier to implement and debug, and it ensures we have the full answer in case we needed to handle it (for example, to store in memory or check for finality). The trade-off is a slight increase in latency (waiting for the full answer before the first byte is sent), but since we chunk and send immediately after generation, the user still sees an incremental response.

### Error Handling

Throughout the ResponseHandler, errors are handled in a direct and transparent way:

- If the Memory or Cognition service calls fail (e.g., network issue or service down), the exception is caught. We log the error (so developers can see what happened) and we can propagate an error message. For instance, if `get_history` fails, we might proceed with an empty history and include a system note that context couldn't be retrieved (or simply proceed; losing context is not fatal to the flow).
- If the LLM call (`llm.generate`) raises an exception (e.g., due to a timeout or API error), we catch it and set `final_answer = "ERROR: Failed to generate response."`. This ensures the loop breaks and we don’t attempt further tool calls.
- If a tool execution throws an exception (for example, a KeyError in a local function or a service call error), we catch it and embed the error message in `final_answer` (as shown in the pseudocode above). We break out so we can inform the user that the tool failed.
- In `_stream_response`, if for some reason sending to the queue fails (e.g., no active listener), we log it. Typically, the SSE connection might be closed by the client; our design doesn’t attempt complex retries or buffering for a reconnect. We prefer to keep it simple: if the stream is gone, the message is effectively dropped (and error logged). The client can always request again or the system can store the answer for later retrieval if needed.
- We do not attempt hidden retries or fallback to alternate models in this design. All failure modes are meant to be **visible** either in logs or to the end user. For example, if the LLM API key is invalid, the OpenAI SDK will throw an authentication error; our code will catch it and send an `"ERROR: Unauthorized LLM API key"` (or similar) back to the user and log the stack trace. This clarity helps to debug configuration issues early.

By handling errors at each step and ultimately sending a clear error string as the SSE output, we make failure modes obvious. There is no silent hanging or endlessly retried loop – either a valid answer or an error message will always be produced for each input.

### Concurrency and Event Loop Integration

The ResponseHandler is designed to run as part of the Cortex Core’s event loop. Typically, a new user message arrives via the `/input` endpoint, which places the message into an internal event bus or queue. A background task (or the input endpoint itself) will invoke `ResponseHandler.handle_message` asynchronously. We ensure this integration is straightforward:

- When the application starts, we instantiate a single `ResponseHandler` (with the necessary service clients and LLM adapter). This can be done in the startup section of the FastAPI app, or lazily at first use.
- For each incoming message event, we spawn a **task** to handle it. For example, the input endpoint could do:
  ```python
  # inside input endpoint after validating input
  asyncio.create_task(response_handler.handle_message(user.id, conv.id, message))
  return {"status": "processing"}  # immediately acknowledge input
  ```
  This way, the input endpoint is non-blocking and returns quickly, while the actual processing happens in the background.
- The `ResponseHandler.handle_message` runs on the event loop, performing async calls to services and the LLM as needed. Because we `await` each external call, other tasks (like handling other users’ messages) can run concurrently.
- If multiple messages come in for the **same conversation** before the first is finished, our design will start multiple tasks. This could lead to interleaved responses or context confusion. For simplicity, we assume the client or user will mostly wait for an answer before sending another query. If needed, we could add a check to avoid parallel handling of the same conversation (e.g., queue them or drop one), but this is beyond the minimal scope.
- The SSE output streaming for each user/conversation is handled by the `output_stream` endpoint as shown. It will continuously read from that user’s output queue. Our design ensures to `put` the final answer chunks in the queue **in order** and then a `[DONE]` marker. Because `handle_message` is a single task per input, it will place chunks sequentially. If two tasks were somehow streaming at once for one user, their chunks might intermix. Preventing that would require per-conversation locking or sequential processing, which we can consider if needed. In this design, we focus on correctness for one query at a time per conversation.

In summary, ResponseHandler cleanly integrates with the event loop by using `async`/`await` for all I/O operations (service calls, LLM calls, SSE queue operations). It doesn’t block the loop with synchronous waits. The combination of the background task for generation and the streaming response in SSE demonstrates a separation of concerns: generation happens off the request/response cycle, and streaming happens continuously to push results out.

## LLM Adapter Design

The **LLM Adapter** (`llm_adapter.py`) is a simple utility that interfaces with external LLM APIs. Its goal is to hide the differences between OpenAI, Azure OpenAI, and Anthropic Claude, providing a single method to get a model completion. The adapter is intentionally minimal: it does not attempt sophisticated prompt engineering or model-agnostic abstractions beyond what’s necessary to call each API. It primarily does the following:

- Reads configuration from environment variables to determine which provider to use and the necessary credentials/model identifiers.
- Formats the input messages and parameters according to the selected provider’s API.
- Makes an asynchronous API call to the provider (using the official SDK if available, or a direct HTTP call).
- Returns the result in a unified structure: either a final text content or a tool request indication (as described earlier).
- Handles basic errors from the API and timeouts, returning `None` or raising exceptions which ResponseHandler will catch.

### Configuration and Initialization

Configuration is done via environment variables for clarity and simplicity. The following env variables are used:

- `LLM_PROVIDER`: which provider to use. Expected values: `"openai"`, `"azure_openai"`, or `"anthropic"`. (We default to OpenAI if not set.)
- For OpenAI:
  - `OPENAI_API_KEY`: API key for OpenAI.
  - `OPENAI_MODEL`: Model name (e.g., `"gpt-3.5-turbo"` or `"gpt-4"`).
  - Optionally `OPENAI_API_BASE` if using a custom endpoint (for example, OpenAI enterprise or proxy).
- For Azure OpenAI:
  - `AZURE_OPENAI_KEY`: API key for Azure OpenAI service.
  - `AZURE_OPENAI_BASE_URL`: Base URL for the Azure OpenAI endpoint (e.g., `"https://<resource>.openai.azure.com"`).
  - `AZURE_OPENAI_DEPLOYMENT`: Deployment name of the model (set up in Azure) to use.
  - `AZURE_OPENAI_API_VERSION`: API version date, e.g., `"2023-05-15"` (as required by Azure OpenAI).
- For Anthropic:
  - `ANTHROPIC_API_KEY`: API key for Anthropic Claude.
  - `ANTHROPIC_MODEL`: Model name, e.g., `"claude-2"` or `"claude-1.3"`.
  - (Anthropic’s API also allows setting `MAX_TOKENS` or other params, which we can configure with defaults or environment if needed, but keep minimal by using safe defaults.)

The LLM Adapter will read these variables at startup. For example, we might implement it as:

```python
# llm_adapter.py
import os, json
import openai
# anthropic and azure OpenAI (which uses openai lib under the hood)
try:
    import anthropic
except ImportError:
    anthropic = None  # ensure code still runs if anthropic not installed and not needed

class LLMAdapter:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        if self.provider not in ("openai", "azure_openai", "anthropic"):
            raise RuntimeError(f"Unsupported LLM_PROVIDER: {self.provider}")
        # Common parameters
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        # Setup per provider
        if self.provider == "openai":
            self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            openai.api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_API_BASE")
            if base_url:
                openai.api_base = base_url
            # (openai.api_type defaults to "open_ai" for normal OpenAI usage)
        elif self.provider == "azure_openai":
            self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT")  # Azure uses deployment name as model
            openai.api_type = "azure"
            openai.api_key = os.getenv("AZURE_OPENAI_KEY")
            openai.api_base = os.getenv("AZURE_OPENAI_BASE_URL")
            openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
            if not self.model or not openai.api_key or not openai.api_base:
                raise RuntimeError("Azure OpenAI configuration is incomplete.")
        elif self.provider == "anthropic":
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-2")
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic:
                raise RuntimeError("Anthropic SDK not installed.")
            if not self.api_key:
                raise RuntimeError("Anthropic API key not provided.")
            # Initialize the Anthropic client
            self.client = anthropic.Anthropic(api_key=self.api_key)
```

This initialization does a few things in a straightforward manner:

- It determines the provider and normalizes the name (for example, we accept `"azure_openai"` as a value).
- It sets a default temperature (which controls randomness) from env or uses 0.7 as a reasonable default. (We could also expose max tokens or other settings if needed, but we avoid overloading with too many config options—only essentials.)
- For OpenAI:
  - It reads the model and API key, and optionally an API base URL. We directly assign `openai.api_key` and `openai.api_base`. Using the official `openai` Python SDK keeps things simple (no manual HTTP calls needed).
- For Azure OpenAI:
  - It configures the OpenAI SDK to use Azure: `openai.api_type = "azure"` and sets the base URL, key, and version. Azure’s `deployment` acts like the model name. We ensure all required pieces are present; otherwise, we raise an error early.
- For Anthropic:
  - It requires the `anthropic` SDK. We check if it’s installed; if not and Anthropic is requested, we error out (clear failure). If present, we instantiate an `Anthropic` client with the API key. (The Anthropic SDK uses `httpx` under the hood and will manage the requests.)
  - We store the chosen model name.

We avoid any sophisticated logic or polymorphic classes for each provider—just an `if/elif` and straightforward configuration.

### Generating Completions

The core method of LLMAdapter is something like `generate(messages: List[dict]) -> dict`. This method takes a list of message dicts (with `"role"` and `"content"` keys) and returns either a final answer or a tool request. The implementation directly calls the appropriate API based on `self.provider`. For example:

```python
class LLMAdapter:
    # ... (initialization as above)

    async def generate(self, messages: list) -> dict:
        """
        Call the configured LLM API with the given conversation messages.
        Returns a dict with either {"content": "..."} for a final answer,
        or {"tool": "...", "input": {...}} for a tool request.
        """
        if self.provider in ("openai", "azure_openai"):
            # Use OpenAI ChatCompletion (works for both OpenAI and Azure configs)
            try:
                response = await openai.ChatCompletion.acreate(
                    model=(self.model if self.provider == "openai" else None),
                    engine=(self.model if self.provider == "azure_openai" else None),
                    messages=messages,
                    temperature=self.temperature
                    # Note: for OpenAI, use model; for Azure, use engine=deployment name.
                )
            except Exception as e:
                logger.error(f"LLM API call failed: {e}")
                return None  # ResponseHandler will handle error
            # Parse the response
            choice = response["choices"][0]["message"]
            content = choice.get("content")
            function_call = choice.get("function_call")
            if function_call:
                # OpenAI function calling scenario
                tool_name = function_call.get("name")
                # arguments might be a JSON string; try to parse if present
                args_str = function_call.get("arguments", "")
                try:
                    tool_args = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError:
                    tool_args = {"raw_args": args_str}
                return {"tool": tool_name, "input": tool_args}
            else:
                # Normal content answer
                return {"content": content or ""}
        elif self.provider == "anthropic":
            try:
                # The Anthropic SDK supports a similar messages API:
                # We'll use the messages interface if available, otherwise fallback to completion.
                result = await self.client.completions.create(
                    model=self.model,
                    max_tokens=1024,
                    temperature=self.temperature,
                    # Convert our messages list to the single prompt format expected.
                    # Option 1: if the anthropic SDK now accepts 'messages' like OpenAI:
                    # messages=messages
                    # Option 2: manually format prompt from messages:
                    prompt=self._anthropic_prompt_from_messages(messages),
                    stop_sequences=[anthropic.HUMAN_PROMPT]  # stop when next human msg would start
                )
            except Exception as e:
                logger.error(f"Anthropic API call failed: {e}")
                return None
            # Anthropic completions.create returns a dict with 'completion' text
            completion_text = result.get("completion", "")
            # Try to parse as JSON for a tool request
            stripped = completion_text.strip()
            if stripped.startswith('{'):
                try:
                    tool_req = json.loads(stripped)
                    if "tool" in tool_req:
                        return {"tool": tool_req["tool"], "input": tool_req.get("input", {})}
                except json.JSONDecodeError:
                    pass
            # Otherwise, return as final content
            return {"content": completion_text}
```

A few notes on this implementation:

- We use **async** API calls for OpenAI and Anthropic:
  - OpenAI’s SDK provides an `acreate` coroutine for chat completion, which we `await`. We pass `model` or `engine` appropriately depending on OpenAI vs Azure, and the `messages` list directly. We include the temperature. (We could also include a max_tokens from an env var if needed, or rely on model defaults.)
  - Anthropic’s SDK can also be used asynchronously. We show using `completions.create` with a prompt. The Anthropic SDK recently introduced a `messages.create` method that accepts an array of messages with roles (similar to OpenAI). If available, we could use that directly with our `messages` list. If not, we manually convert the messages to the format expected by Claude:
    - Typically, Anthropic expects a single prompt string that alternates `\n\nHuman:` and `\n\nAssistant:` prefixes for conversation turns. We can implement `_anthropic_prompt_from_messages(messages)` to join the list into one string. For example, for each message:
      - If role is `"system"`, we might prepend something like an instruction at the very beginning (Anthropic doesn’t have a native system role; we can treat system content as if it were an initial assistant message stating the rules, or just include it before the first Human prompt without a label).
      - If role is `"user"`, prefix content with `"\n\nHuman: "`.
      - If role is `"assistant"`, prefix with `"\n\nAssistant: "`.
      - Ensure the prompt ends with an `Assistant:` prefix if we want the model to continue as the assistant. However, the Anthropic SDK’s `stop_sequences` usage above with `HUMAN_PROMPT` ensures it stops when it’s about to start a human message, which effectively means it will produce only the assistant continuation.
    - For simplicity, in the code above we used `prompt=self._anthropic_prompt_from_messages(messages)` to handle this formatting (to avoid diving into all details here).
- **Parsing the response**:
  - For OpenAI/Azure: The response is a JSON-like object. We take the first choice (index 0) and get the `"message"` dict. If the model chose to call a function (tool), OpenAI’s API will present `message["function_call"]` with the function name and arguments. We detect that and return our unified `{"tool": ..., "input": ...}` dict. If instead there’s normal content, we return `{"content": ...}`. If content is `None` (which can happen if the assistant only returned a function call and no message), we ensure to return an empty string for content to avoid None issues.
  - For Anthropic: The result is typically a text completion. We strip it and check if it looks like a JSON (starts with `{`). If yes, we attempt to parse it. If parsing succeeds and contains a `"tool"` key, we interpret it as a tool request and return accordingly. Otherwise, we treat the completion as final answer content. (Anthropic models won’t automatically structure outputs for function calls since they don’t have that feature built-in, so this relies on the prompt instruction that the assistant should output a JSON when wanting a tool.)
- We include basic error handling around each API call:
  - If the OpenAI or Anthropic call raises an exception (due to network error, invalid request, etc.), we catch it, log an error, and return `None`. The ResponseHandler will see that as a failure and handle it by sending an error to the user. We do not attempt fancy retries in the LLM Adapter; any retry logic if needed could be handled at a higher level or by relying on the provider’s reliability. Keeping it simple, one attempt per user message is usually enough, and errors are surfaced immediately.
  - We could incorporate a timeout using `asyncio.wait_for` if we want to ensure the LLM doesn’t hang beyond a certain duration. For example, wrapping `openai.ChatCompletion.acreate` in `await asyncio.wait_for(..., timeout=15)`. However, the OpenAI SDK likely has its own request timeout, and we specified no more than 1024 tokens for Anthropic. We can add such a timeout in configuration if needed, but the design’s emphasis is on simplicity, so we may omit it or use a single global default if easily set.

### Message Format and Role Handling

We structure all LLM inputs as a list of message dictionaries. This format is directly compatible with OpenAI’s chat API and with Anthropic’s message interface. By using a unified list of `{"role": ..., "content": ...}`, we avoid hard-coding prompt templates per provider (except for the behind-the-scenes conversion needed for Anthropic’s single-string API). The roles we use are:

- `"system"` – for initial instructions or context we want the model to always have (e.g., guidelines like “You are a helpful assistant” or tools format instructions).
- `"user"` – for user messages/prompts.
- `"assistant"` – for the AI assistant’s own messages (including possibly previous answers or tool outputs we’ve injected).

Azure OpenAI uses the same message schema as OpenAI (just passed under the hood via the openai SDK), so no difference in formatting there.

Anthropic’s newer API (as of Claude v2, etc.) supports the message list directly. If using the message list, the Anthropic client usage would be:

```python
await self.client.messages.create(model=self.model, messages=messages, max_tokens=1024, temperature=self.temperature)
```

which returns an object (maybe similar to OpenAI’s) with a `.content`. In the code above, we demonstrated the completion approach for clarity, but in practice using the messages API would simplify it further and allow the same message list to be passed without manual prompt building. In either case, the key point is that the **LLM Adapter expects and works with the same `messages` list structure that the ResponseHandler produces**. This keeps the interface between ResponseHandler and LLM Adapter very simple: ResponseHandler doesn’t need to know anything about how to call the API; it just provides messages and gets back a dict with either content or a tool call.

### No Unnecessary Abstractions or Future-Proofing

The LLM Adapter does **not** include any abstraction beyond the minimum needed. For instance:

- No class hierarchy or factory pattern for different providers. A simple `if/elif` does the job and is easy to follow.
- No support for providers beyond the three specified; if we needed to add one later, we can extend the `if` statement. Until then, we keep the code focused.
- We don’t wrap the provider SDKs in additional layers (like a generic `LLMClient`). We call them directly. For example, we directly use `openai.ChatCompletion` and `anthropic.Anthropic` without writing wrappers around them.
- We avoid any configuration toggles that aren’t absolutely necessary. For example, we don’t include switches for things like enabling/disabling streaming at the adapter level or choosing between chat vs completion endpoints—those decisions are fixed by our design (always chat style, and streaming handled at ResponseHandler level).
- There is no legacy logic since this is a new implementation. We don’t check for deprecated environment variable names or older model versions; we assume the environment is configured correctly for one of the supported providers. If not, we error out clearly at startup.

## Example Execution Flow

To illustrate how the ResponseHandler and LLM Adapter work together, consider a concrete example conversation where the user asks a question that requires a tool:

**User:** `"What's the weather in Paris right now?"`

1. **Input Received:** The user’s message comes in through the `/input` endpoint with `user_id="u123"`, `conversation_id="c456"`, and the content `"What's the weather in Paris right now?"`. The endpoint dispatches this to the ResponseHandler (e.g., via an event bus message or a direct async call to `handle_message`).
2. **Store and Context:** `ResponseHandler.handle_message("u123", "c456", "What's the weather in Paris right now?")` is invoked.
   - It calls `memory.store_input(u123, {"role": "user", "content": "What's the weather in Paris right now?"})` to save the message. The Memory service returns a success status (or it’s fire-and-forget).
   - It then calls `history = memory.get_history(u123)`. Suppose this is the first message in the conversation, `history` might return a list with just that user message (or empty if the memory service does not include the latest yet). Let’s assume history now contains `[{"role": "user", "content": "What's the weather in Paris right now?"}]`.
   - System instructions (if any) are added. In this case, let’s say we have a system prompt instructing the assistant how to use a weather tool: e.g., _“You have access to a tool `get_weather` that provides weather info. If a question asks for current weather, respond with `{"tool": "get_weather", "input": {"location": "<LOCATION>"}}`.”_ This was provided via environment and included as a system message.
   - The `messages` list becomes:
     ```python
     messages = [
         {"role": "system", "content": "You are a helpful assistant. You have a tool named get_weather for weather queries."},
         {"role": "user", "content": "What's the weather in Paris right now?"}
     ]
     ```
3. **First LLM Call:** The ResponseHandler calls `result = await llm_adapter.generate(messages)`. The LLM (say, OpenAI GPT-4) sees the user question and the instruction about the tool. It decides that it should use the `get_weather` tool. According to our format, it outputs a JSON string: `{"tool": "get_weather", "input": {"location": "Paris"}}`.
   - If this is OpenAI with function calling, the adapter would instead get a function call for `get_weather` with argument `{"location": "Paris"}`, which we convert to the same dict format.
   - The LLM Adapter returns `{"tool": "get_weather", "input": {"location": "Paris"}}`.
4. **Tool Execution:** ResponseHandler sees `result["tool"] == "get_weather"`. It calls `_execute_tool("get_weather", {"location": "Paris"}, user_id="u123")`.
   - Suppose `_execute_tool` knows that `"get_weather"` is implemented by a simple Python function or an external weather API. For the sake of example, we have a local function `get_weather(location: str) -> str` that returns a weather summary.
   - The tool function is called and returns: `"Currently in Paris, it is 15°C with clear skies."`.
   - ResponseHandler takes this result and appends it to messages as an assistant message:
     ```python
     messages.append({"role": "assistant", "content": "Currently in Paris, it is 15°C with clear skies."})
     ```
     This simulates the assistant having “said” the result of the tool.
5. **Second LLM Call:** The loop continues. Now `messages` looks like:
   ```python
   [
     {"role": "system", "content": "You are a helpful assistant... (with tool instructions)"},
     {"role": "user", "content": "What's the weather in Paris right now?"},
     {"role": "assistant", "content": "Currently in Paris, it is 15°C with clear skies."}
   ]
   ```
   ResponseHandler calls `llm_adapter.generate(messages)` again. This time, the LLM sees that the conversation history contains the user’s question and what looks like the assistant already provided the weather info. The model’s role now is to give a final answer to the user. It uses the tool result to formulate a helpful answer, for example: **"The weather in Paris is currently 15°C with clear skies."**. It returns this as normal content.
   - The LLM Adapter receives the completion and returns `{"content": "The weather in Paris is currently 15°C with clear skies."}`.
6. **Final Answer Identified:** ResponseHandler sees a result with `"content"` and no `"tool"`. It sets `final_answer` to that content. It breaks out of the loop.
   - It may store the assistant’s answer via `memory.store_input(u123, {"role": "assistant", "content": final_answer})` for completeness of history.
7. **Streaming Output:** ResponseHandler now streams the answer. It calls `_stream_response("c456", "The weather in Paris is currently 15°C with clear skies.")`.
   - This will chunk the text and push it to the SSE channel for conversation `c456`. Immediately, the connected client (listening on `/output/stream`) starts receiving chunks, for example:
     - `data: The weather in Paris is currently 15°C wit\n\n`
     - `data: h clear skies.\n\n`
     - `data: [DONE]\n\n`
   - The client reassembles and displays: "The weather in Paris is currently 15°C with clear skies."
8. **Result:** The user gets the answer streamed to them, after a brief pause where the assistant was using the tool behind the scenes. The tool usage was invisible to the user except for the slight delay. If any step had failed (say the weather API was down), the user might have received an error message like `"ERROR: tool 'get_weather' failed: service unavailable"`, streamed in the same way.

This example demonstrates the multi-step flow in action: the LLM asked for a tool, ResponseHandler executed it and fed back the info, then the LLM produced the final answer which was streamed out. The logic is linear and easy to trace, and adding a second or third tool call would simply result in additional loop iterations with the same pattern.

## Conclusion

The design of the ResponseHandler and LLM Adapter for Cortex Core is intentionally straightforward. We avoid over-engineering, focusing on a clear step-by-step resolution of each user query:

- **Simplicity**: The code is easy to follow, with minimal indirection. Anyone reading `response_handler.py` can quickly understand how a message is processed, and `llm_adapter.py` clearly shows how each provider is invoked.
- **Direct Integration**: By using the official SDKs (OpenAI, Anthropic) or simple HTTP calls, we reduce the likelihood of integration bugs and we leverage well-tested libraries. There’s no custom protocol or DSL to maintain for LLM calls.
- **Extensibility**: While we did not add extra layers for future-proofing, this design can be extended in a controlled way. For example, adding a new provider would be a matter of adding another branch in LLM Adapter. Adding a new tool is as simple as writing a new function and hooking it up in `_execute_tool`.
- **Clarity in Operation**: Multi-step reasoning is handled in an obvious loop. Streaming is handled with a clear mechanism of queues and SSE. Errors produce clear outcomes. There are no silent fallbacks or magic – every action taken is visible in the code and (in failure cases) visible to the user.

By implementing the ResponseHandler and LLM Adapter in this manner, Cortex Core will have a solid foundation for conversational intelligence that is easy to maintain and understand. These components serve as the “brain” and “voice” of the system respectively, connecting user inputs to powerful language models and tools in a controlled, transparent way.
