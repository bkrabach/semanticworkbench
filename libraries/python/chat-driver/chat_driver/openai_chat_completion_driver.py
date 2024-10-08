import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, List

from context.context import Context, ContextProtocol
from events import BaseEvent, MessageEvent
from function_registry.function_registry import FunctionRegistry
from openai import APIConnectionError, APIStatusError, AsyncOpenAI, NotGiven, RateLimitError
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.completion_create_params import ResponseFormat

from .logger import Logger

DEFAULT_MAX_RETRIES = 3
TEXT_RESPONSE_FORMAT: ResponseFormat = {"type": "text"}
DEFAULT_DATA_DIR = Path(".data") / "chat_driver"

# TODO: Make the chat driver handle json and json schema responses.
JSON_OBJECT_RESPONSE_FORMAT: ResponseFormat = {"type": "json_object"}
# {"type": "json_schema", "json_schema": {"name": "test", "schema": {}}}


@dataclass
class ChatDriverConfig:
    openai_client: AsyncOpenAI
    model: str
    instructions: str = "You are a helpful assistant."
    messages: list[ChatCompletionMessageParam] = field(default_factory=list)
    context: ContextProtocol | None = None
    data_dir: Path | None = None  # Override the default data dir.
    commands: list[Callable] = field(default_factory=list)
    functions: list[Callable] = field(default_factory=list)


class ChatDriver:
    def __init__(self, config: ChatDriverConfig) -> None:
        # A context object holds information about the current session, such as
        # the session ID, the user ID, and the conversation ID. It also provides
        # a method to emit events. If you do not supply one, one will be created
        # for you with a random session ID.
        self.context = config.context or Context()

        # A local data directory is used to store all chat driver data.
        self.data_dir = config.data_dir or DEFAULT_DATA_DIR

        # The data directory is used to store all session data for the chat.
        self.session_dir = self.data_dir / self.context.session_id
        if not self.session_dir.exists():
            self.session_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging.
        self.logger = Logger(__name__, self.context)

        # Load messages from file if they exist.
        init_messages: list[ChatCompletionMessageParam] = config.messages or []
        self.messages_file = self.session_dir / "messages.json"
        if not self.messages_file.exists():
            self.messages_file.write_text(json.dumps(init_messages, indent=2))
            self.messages = init_messages
        else:
            messages = json.loads(self.messages_file.read_text())
            messages.extend(init_messages)
            self.messages = messages

        # Now set up the OpenAI client, model, and instructions.
        self.client = config.openai_client
        self.model = config.model
        self.update_instructions(config.instructions)

        # Functions that you register with the chat driver will be available to
        # for GPT to call while generating a response. If the model generates a
        # call to a function, the function will be executed, the result passed
        # back to the model, and the model will continue generating the
        # response.
        self.function_registry = FunctionRegistry(self.context, config.functions)
        self.functions = self.function_registry.functions

        # Commands are functions that can be called by the user by typing a
        # command in the chat. When a command is received, the chat driver will
        # execute the corresponding function and return the result to the user
        # directly.
        self.command_registry = FunctionRegistry(self.context, config.commands)
        self.commands = self.command_registry.functions

    def clear_session_data(self) -> None:
        self.messages = []
        self.messages_file.write_text(json.dumps(self.messages, indent=2))

    def add_message(self, message: ChatCompletionMessageParam) -> None:
        self.messages.append(message)
        self.messages_file.write_text(json.dumps(self.messages, indent=2))

    def add_error_message(self, message: str) -> None:
        error_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": f"Error: {message}",
        }
        self.add_message(error_message)

    # Commands are available to be run by the user message.
    def register_command(self, function: Callable) -> None:
        self.command_registry.register_function(function)

    def register_commands(self, functions: list[Callable]) -> None:
        self.command_registry.register_functions(functions)

    # Functions are available to be called by the model during response
    # generation.
    def register_function(self, function: Callable) -> None:
        self.function_registry.register_function(function)

    def register_functions(self, functions: list[Callable]) -> None:
        self.function_registry.register_functions(functions)

    # Sometimes we want to register a function to be used by both the user and
    # the model.
    def register_function_and_command(self, function: Callable) -> None:
        self.register_command(function)
        self.register_function(function)

    def register_functions_and_commands(self, functions: list[Callable]) -> None:
        self.register_commands(functions)
        self.register_functions(functions)

    def get_functions(self) -> list[Callable]:
        return [function.fn for function in self.function_registry.get_functions()]

    def get_commands(self) -> list[Callable]:
        commands = [function.fn for function in self.command_registry.get_functions()]
        return commands

    def _get_tools(self) -> Iterable[ChatCompletionToolParam]:
        # Only the "functions" tool is available in the Chat API.
        # https://platform.openai.com/docs/guides/function-calling

        functions: List[ChatCompletionToolParam] = []
        for function in [func.schema for func in self.function_registry.get_functions()]:
            functions.append(
                ChatCompletionToolParam(**{
                    "type": "function",
                    "function": function,
                })
            )

        return functions

    def _format_instructions(
        self, messages: List[ChatCompletionMessageParam], input_parameters: dict[str, Any] | None = None
    ) -> List[ChatCompletionMessageParam]:
        # Shallow copy the messages list so we're not replacing the original.
        messages = messages.copy()

        if not messages:
            return messages

        # Grab the system message.
        message = messages[0]
        if message["role"] != "system":
            return messages

        # Replace template variables in instructions.
        message = message.copy()
        if input_parameters:
            for key, value in input_parameters.items():
                try:
                    message["content"] = str(message["content"]).format(**{key: value})
                except KeyError:
                    pass

        # Replace the first message with the updated message.
        messages[0] = message
        return messages

    def update_instructions(self, instructions: str) -> None:
        """Update the instructions for the chat driver. Generally you'll just
        set the instructions when you instantiate a new chat driver. But hey,
        you can change them with this if you really want. This method makes sure
        the rest of the messages are preserved."""

        # If the first message is a system message, delete it:
        if self.messages and self.messages[0]["role"] == "system":
            self.messages = self.messages[1:]

        # Add a new system message with the new instructions.
        system_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": instructions,
        }
        self.messages = [system_message, *self.messages]

    async def respond(
        self,
        message: str,
        response_format: ResponseFormat = TEXT_RESPONSE_FORMAT,
        instruction_parameters: dict[str, Any] | None = None,
    ) -> BaseEvent:
        """Respond to a user message.

        If the user message is a command, the command will be executed and the
        result returned.

        Otherwise, the message will be passed to the chat completion API and the
        response returned.

        The api response might be a request to call functions registered with
        the chat driver. If so, we execute the functions and give the results
        back to the model for the final response generation."""

        # If the message contains a command, execute it.
        if message.startswith("/"):
            command_string = message[1:]
            try:
                results = await self.command_registry.execute_function_string_with_string_response(command_string)
                return MessageEvent(message=results)
            except Exception as e:
                self.add_error_message(f"Error: {e}")
                return MessageEvent(message="Error!", metadata={"error": str(e)})

        # Otherwise, generate a response.
        user_message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": message,
        }
        self.add_message(user_message)

        completion_args = {
            "messages": (
                self._format_instructions(self.messages, instruction_parameters)
                if instruction_parameters
                else self.messages
            ),
            "model": "gpt-4o",
            "tools": self._get_tools(),
            "response_format": response_format,
        }
        metadata: dict[str, Any] = {"completion_args": completion_args}
        self.logger.debug("Chat completion args.", data=completion_args)
        if not completion_args["tools"]:
            completion_args["tools"] = NotGiven()

        try:
            completion = await self.client.chat.completions.create(**completion_args)
            log_data = {
                "messages": completion_args["messages"],
                "model": completion_args["model"],
                "tools": completion_args["tools"],
                "response_format": completion_args["response_format"],
            }
            metadata["completion_response"] = completion.model_dump()
            self.logger.debug("Chat Completion response.", data=log_data)
        except APIConnectionError as e:
            msg = f"The server could not be reached: {e.__cause__}"
            self.logger.error(msg)
            self.add_error_message(msg)
            metadata["error"] = str(e)
            return MessageEvent(message="The server could not be reached.", metadata=metadata)
        except RateLimitError:
            msg = "A 429 status code was received; we should back off a bit."
            self.logger.error(msg)
            self.add_error_message(msg)
            return MessageEvent(message="Rate limit error.", metadata=metadata)
        except APIStatusError as e:
            msg = f"Another non-200-range status code was received. {e.status_code}: {e.response}"
            self.logger.error(msg)
            self.add_error_message(msg)
            metadata["error"] = str(e)
            return MessageEvent(message="API status error.", metadata=metadata)

        # Get response and add to messages.
        response_message = completion.choices[0].message
        tool_calls = response_message.tool_calls
        assistant_response = ChatCompletionAssistantMessageParam(**response_message.model_dump())
        self.add_message(assistant_response)
        metadata["assistant_response"] = assistant_response

        # If the response includes function tool calls, execute them and pass
        # the result back to the API.
        if tool_calls:
            for tool_call in tool_calls:
                function = tool_call.function
                if self.function_registry.has_function(function.name):
                    # Call function.
                    self.logger.debug("Function call.", data={"name": function.name, "arguments": function.arguments})
                    try:
                        kwargs: dict[str, Any] = json.loads(function.arguments)
                        value = await self.function_registry.execute_function(function.name, (), kwargs)
                    except Exception as e:
                        self.logger.error("Error.", data={"error": e})
                        value = f"Error: {e}"

                    # Create function message.
                    content = ""
                    if response_format["type"] == "text":
                        content = str(value)
                    elif response_format["type"] == "json_object":
                        content = json.dumps(value)
                    function_call_result_message: ChatCompletionToolMessageParam = {
                        "role": "tool",
                        "content": content,
                        "tool_call_id": tool_call.id,
                    }
                    self.add_message(function_call_result_message)
                    self.logger.debug("Function response.", data={"content": content})
                    metadata["function_call_result_message"] = function_call_result_message

            # Call assistant for final response.
            assistant_tool_completion_args = {
                "messages": (
                    self._format_instructions(self.messages, instruction_parameters)
                    if instruction_parameters
                    else self.messages
                ),
                "model": "gpt-4o",
            }
            self.logger.debug("Calling Completions API with tool response.", data=assistant_tool_completion_args)
            metadata["assistant_tool_completion_args"] = assistant_tool_completion_args
            completion = await self.client.chat.completions.create(**assistant_tool_completion_args)

            # Add assistant response to messages.
            assistant_tool_response = ChatCompletionAssistantMessageParam(**completion.choices[0].message.model_dump())
            self.add_message(assistant_tool_response)
            self.logger.debug("Assistant tool response.", data=assistant_tool_response)
            metadata["assistant_tool_response"] = assistant_tool_response

            # TODO: Check if it's another tool call?

        # Return the last message.
        last_message: ChatCompletionMessageParam = self.messages[-1]
        if last_message.get("role") == "assistant":
            content = last_message.get("content")
            return MessageEvent(message=str(content), metadata=metadata)

        return MessageEvent(message="No response.", metadata=metadata)
