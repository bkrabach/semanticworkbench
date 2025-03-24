# memory_updater.py for memory service
import datetime
import logging
from typing import Any, Dict, List, Literal, cast

from pydantic import BaseModel
from pydantic_ai import Agent

from .config import config
from .models import MemoryEntry

# Set up logger
logger = logging.getLogger(__name__)


class MemoryUpdateResult(BaseModel):
    """Result of a memory update operation."""

    updated_memory: str
    success: bool


class MemoryUpdater:
    """Service to create and update memory summaries using LLM."""

    def __init__(self):
        """Initialize the memory updater with an LLM agent."""
        # Create a Pydantic-AI agent for memory summarization
        system_prompt = (
            "You are an AI memory manager. Your job is to maintain a running summary "
            "('whiteboard memory') of a conversation or session. When given new events, "
            "update the summary to include them. The summary should be concise "
            "(no more than ~2 pages), capturing key points and decisions. "
            "Avoid verbatim repetition; integrate information logically. "
            "Only output the updated summary text, nothing else."
        )

        # Following the "Pragmatic trust" principle from Implementation Philosophy
        # Use type cast to satisfy type checking while maintaining functionality
        # For type-safety, use the 'test' model name for static checking
        # At runtime, this will still use the actual model specified in config
        self.agent = Agent(
            cast(Literal["test"], config.LLM_MODEL),
            result_type=str,
            system_prompt=system_prompt,
            model_settings={"temperature": config.LLM_TEMPERATURE},
        )

        logger.info(f"Initialized MemoryUpdater with model: {config.LLM_MODEL}")

    async def generate_initial_memory(self, messages: List[Dict[str, Any]]) -> str:
        """Create an initial memory summary from messages."""
        try:
            # Format messages for prompt
            formatted_messages = "\n".join([
                f"- {msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in messages
            ])

            user_prompt = f"""Create an initial memory summary based on these messages:

{formatted_messages}

Create a concise summary (1-2 paragraphs) capturing the key information:"""

            # Run agent with the prompt
            result = await self.agent.run(user_prompt)
            return result.data
        except Exception as e:
            logger.error(f"Error creating initial memory: {e}")
            # Fallback to a simple summary on error
            return f"Conversation with {len(messages)} messages. Last message: {messages[-1].get('content', '') if messages else 'None'}"

    async def generate_updated_memory(self, current_memory: str, new_messages: List[Dict[str, Any]]) -> str:
        """Update an existing memory with new information from recent messages."""
        try:
            # Format new messages for prompt
            formatted_messages = "\n".join([
                f"- {msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in new_messages
            ])

            user_prompt = f"""Current memory:
{current_memory}

New events:
{formatted_messages}

Update the memory accordingly:"""

            # Run agent with the prompt
            result = await self.agent.run(user_prompt)
            return result.data
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            # Return original memory on error
            return current_memory

    async def create_memory(self, conversation_id: str, messages: List[Dict[str, Any]]) -> MemoryEntry:
        """Create a new memory entry for a conversation."""
        logger.info(f"Creating initial memory for conversation: {conversation_id} with {len(messages)} messages")

        try:
            memory_content = await self.generate_initial_memory(messages)

            # Ensure the memory stays within the maximum length
            if len(memory_content) > config.MAX_MEMORY_LENGTH:
                memory_content = memory_content[: config.MAX_MEMORY_LENGTH]

            return MemoryEntry(
                conversation_id=conversation_id,
                memory_content=memory_content,
                last_updated=datetime.datetime.now().isoformat(),
            )
        except Exception as e:
            logger.error(f"Error creating initial memory: {e}")
            # Fallback to a simple summary
            fallback_content = (
                f"Conversation with {len(messages)} messages."
                f" Last message: {messages[-1].get('content', '') if messages else 'None'}"
            )
            return MemoryEntry(
                conversation_id=conversation_id,
                memory_content=fallback_content,
                last_updated=datetime.datetime.now().isoformat(),
            )

    async def update_memory(
        self, current_memory: MemoryEntry, new_messages: List[Dict[str, Any]]
    ) -> MemoryUpdateResult:
        """Update an existing memory entry with new messages."""
        logger.info(
            f"Updating memory for conversation: {current_memory.conversation_id} with {len(new_messages)} new messages"
        )

        try:
            updated_content = await self.generate_updated_memory(current_memory.memory_content, new_messages)

            # Ensure the memory stays within the maximum length
            if len(updated_content) > config.MAX_MEMORY_LENGTH:
                updated_content = updated_content[: config.MAX_MEMORY_LENGTH]

            return MemoryUpdateResult(updated_memory=updated_content, success=True)
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            return MemoryUpdateResult(updated_memory=current_memory.memory_content, success=False)
