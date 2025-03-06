import logging
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
import json
import asyncio
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.schemas import (
    Message, 
    MessageRole,
    Conversation as ConversationSchema,
    ToolExecution,
    ToolExecutionStatus
)
from app.db.models import (
    Message as MessageDB,
    Conversation as ConversationDB
)
from app.core.config import get_settings
from app.core.llm import llm_client
from app.core.memory import memory_adapter
from app.core.mcp_client import mcp_client
from app.core.router import message_router

# Setup logging
logger = logging.getLogger(__name__)
settings = get_settings()

class ConversationHandler:
    """
    Handler for conversations.
    
    This class is responsible for:
    - Managing conversation state
    - Processing messages with LLM
    - Coordinating tool usage
    - Maintaining conversation context
    """
    
    def __init__(self):
        """Initialize the Conversation Handler."""
        # Maximum conversation turns before summarizing
        self.max_conversation_turns = 10
        
        # Maximum retries for message processing
        self.max_retries = 3
        
        # Pause between retries (seconds)
        self.retry_pause = 1.0
        
        # Active conversations
        # Key: conversation_id, Value: Dict with conversation state
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
        
        logger.info("ConversationHandler instance created")
    
    async def initialize(self) -> None:
        """
        Initialize the Conversation Handler.
        
        This method is called during application startup.
        """
        try:
            # Register with router
            message_router.register_message_type_handler("user_message", self.handle_user_message)
            message_router.register_message_type_handler("tool_message", self.handle_tool_message)
            
            # Load active conversations from database
            # This will be implemented in a future version
            # For now, we start with an empty active_conversations dict
            
            logger.info("ConversationHandler successfully initialized")
        except Exception as e:
            logger.error(f"Error initializing ConversationHandler: {str(e)}")
            raise
    
    async def cleanup(self) -> None:
        """
        Clean up resources used by the Conversation Handler.
        
        This method is called during application shutdown.
        """
        try:
            # Store conversation states if needed
            # For now, just clear the active conversations
            self.active_conversations.clear()
            
            logger.info("ConversationHandler resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up ConversationHandler: {str(e)}")
    
    async def create_conversation(
        self,
        db: Session,
        user_id: str,
        title: str = "New Conversation",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ConversationSchema]:
        """
        Create a new conversation.
        
        Args:
            db: Database session
            user_id: ID of the user
            title: Conversation title
            metadata: Optional metadata
            
        Returns:
            Created conversation or None
        """
        try:
            # Create conversation
            conversation = ConversationDB(
                user_id=user_id,
                title=title,
                metadata=metadata or {}
            )
            
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            # Initialize memory
            await memory_adapter.initialize_conversation(
                db,
                user_id,
                conversation.id
            )
            
            # Add system message
            system_prompt = """You are Cortex, an AI assistant developed to be helpful, harmless, and honest.
You can access various tools to help users accomplish their tasks.
Always provide thoughtful, accurate responses based on the best available information.
When you don't know something, be honest about your limitations.
"""
            
            # Create system message
            await message_router.route_system_message(
                db,
                conversation.id,
                system_prompt
            )
            
            # Convert to schema
            conversation_schema = conversation.to_schema()
            
            # Add to active conversations
            self.active_conversations[conversation.id] = {
                "id": conversation.id,
                "user_id": user_id,
                "title": title,
                "last_active": datetime.utcnow(),
                "turn_count": 0
            }
            
            logger.info(f"Created conversation {conversation.id} for user {user_id}")
            
            return conversation_schema
            
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            db.rollback()
            return None
    
    async def get_conversation(
        self,
        db: Session,
        conversation_id: str
    ) -> Optional[ConversationSchema]:
        """
        Get a conversation by ID.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            
        Returns:
            Conversation or None
        """
        try:
            # Get conversation
            conversation = db.query(ConversationDB).filter_by(id=conversation_id).first()
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found")
                return None
            
            # Get messages
            messages, _ = await message_router.get_messages(
                db,
                conversation_id,
                limit=50  # Get recent messages
            )
            
            # Convert to schema
            conversation_schema = conversation.to_schema()
            
            # Add messages
            conversation_schema.messages = messages
            
            return conversation_schema
            
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            return None
    
    async def list_conversations(
        self,
        db: Session,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "updated_at",
        sort_order: str = "desc"
    ) -> Tuple[List[ConversationSchema], int]:
        """
        List conversations for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            limit: Maximum number of conversations
            offset: Offset for pagination
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            Tuple of (conversations, total_count)
        """
        try:
            # Build query
            query = db.query(ConversationDB).filter_by(user_id=user_id)
            
            # Apply sorting
            if hasattr(ConversationDB, sort_by):
                sort_field = getattr(ConversationDB, sort_by)
                
                if sort_order.lower() == "asc":
                    query = query.order_by(sort_field)
                else:
                    query = query.order_by(desc(sort_field))
            else:
                # Default sorting
                query = query.order_by(desc(ConversationDB.updated_at))
            
            # Get total count
            total = query.count()
            
            # Get conversations
            conversations = query.offset(offset).limit(limit).all()
            
            # Convert to schemas
            return [conversation.to_schema() for conversation in conversations], total
            
        except Exception as e:
            logger.error(f"Error listing conversations: {str(e)}")
            return [], 0
    
    async def update_conversation(
        self,
        db: Session,
        conversation_id: str,
        updates: Dict[str, Any]
    ) -> Optional[ConversationSchema]:
        """
        Update a conversation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            updates: Updates to apply
            
        Returns:
            Updated conversation or None
        """
        try:
            # Get conversation
            conversation = db.query(ConversationDB).filter_by(id=conversation_id).first()
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found")
                return None
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(conversation, key) and key != "id":
                    setattr(conversation, key, value)
            
            # Update timestamp
            conversation.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(conversation)
            
            # Convert to schema
            conversation_schema = conversation.to_schema()
            
            # Update active conversation
            if conversation_id in self.active_conversations:
                self.active_conversations[conversation_id].update({
                    "title": conversation.title,
                    "last_active": datetime.utcnow()
                })
            
            # Trigger event via router
            await message_router.trigger_event("conversation_updated", {
                "user_id": conversation.user_id,
                "conversation_id": conversation_id,
                "conversation": conversation_schema.dict()
            })
            
            return conversation_schema
            
        except Exception as e:
            logger.error(f"Error updating conversation: {str(e)}")
            db.rollback()
            return None
    
    async def delete_conversation(
        self,
        db: Session,
        conversation_id: str
    ) -> bool:
        """
        Delete a conversation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            
        Returns:
            True if successful
        """
        try:
            # Get conversation
            conversation = db.query(ConversationDB).filter_by(id=conversation_id).first()
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found")
                return False
            
            user_id = conversation.user_id
            
            # Delete messages
            db.query(MessageDB).filter_by(conversation_id=conversation_id).delete()
            
            # Delete conversation
            db.query(ConversationDB).filter_by(id=conversation_id).delete()
            
            # Clear memory
            await memory_adapter.clear_conversation_memory(
                db,
                user_id,
                conversation_id
            )
            
            db.commit()
            
            # Remove from active conversations
            self.active_conversations.pop(conversation_id, None)
            
            logger.info(f"Deleted conversation {conversation_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            db.rollback()
            return False
    
    async def handle_user_message(
        self,
        db: Session,
        message: Message
    ) -> Optional[Message]:
        """
        Handle a user message.
        
        Args:
            db: Database session
            message: User message
            
        Returns:
            Assistant response message or None
        """
        try:
            conversation_id = message.conversation_id
            
            # Get conversation
            conversation = db.query(ConversationDB).filter_by(id=conversation_id).first()
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found")
                return None
            
            # Update conversation activity
            if conversation_id in self.active_conversations:
                self.active_conversations[conversation_id]["last_active"] = datetime.utcnow()
                self.active_conversations[conversation_id]["turn_count"] += 1
            else:
                # Add to active conversations
                self.active_conversations[conversation_id] = {
                    "id": conversation_id,
                    "user_id": conversation.user_id,
                    "title": conversation.title,
                    "last_active": datetime.utcnow(),
                    "turn_count": 1
                }
            
            # Get conversation history
            messages, _ = await message_router.get_messages(
                db,
                conversation_id,
                limit=20  # Reasonable context window
            )
            
            # Format messages for LLM
            formatted_messages = llm_client.format_messages(messages)
            
            # Check if this is the first user message
            is_first_message = conversation.title == "New Conversation"
            
            # Create assistant message placeholder
            assistant_message = await message_router.route_tool_message(
                db,
                conversation_id,
                "assistant",
                "I'm thinking...",  # Placeholder
                {
                    "is_complete": False
                }
            )
            
            if not assistant_message:
                logger.error(f"Failed to create assistant message for conversation {conversation_id}")
                return None
            
            # Process with LLM
            for retry in range(self.max_retries):
                try:
                    # Check if tools might be needed
                    needs_tools, tool_response = await llm_client.check_tool_use(formatted_messages)
                    
                    if needs_tools and tool_response and "tool_calls" in tool_response:
                        # Handle tool execution
                        response_content = tool_response.get("content", "")
                        
                        # Update assistant message with thinking
                        if response_content:
                            await message_router.update_message(
                                db,
                                assistant_message.id,
                                {
                                    "content": response_content,
                                    "is_complete": False
                                }
                            )
                        
                        # Process tool calls
                        final_response = await self._process_tool_calls(
                            db,
                            conversation_id,
                            assistant_message.id,
                            tool_response["tool_calls"]
                        )
                        
                        # Update assistant message with final response
                        await message_router.update_message(
                            db,
                            assistant_message.id,
                            {
                                "content": final_response,
                                "is_complete": True,
                                "role": MessageRole.ASSISTANT.value  # Change from TOOL to ASSISTANT
                            }
                        )
                    else:
                        # Generate regular response
                        response = await llm_client.generate_response(formatted_messages)
                        
                        # Update assistant message
                        await message_router.update_message(
                            db,
                            assistant_message.id,
                            {
                                "content": response,
                                "is_complete": True,
                                "role": MessageRole.ASSISTANT.value  # Change from TOOL to ASSISTANT
                            }
                        )
                    
                    # Update conversation if this is the first message
                    if is_first_message:
                        # Generate title from first exchange
                        title = await self._generate_conversation_title(
                            db,
                            conversation_id,
                            messages + [assistant_message]
                        )
                        
                        # Update conversation
                        await self.update_conversation(
                            db,
                            conversation_id,
                            {"title": title}
                        )
                    
                    # Store conversation in memory
                    await memory_adapter.store_conversation(
                        db,
                        conversation.user_id,
                        conversation_id,
                        messages + [assistant_message]
                    )
                    
                    # Extract key points
                    await memory_adapter.extract_key_points(
                        db,
                        conversation.user_id,
                        conversation_id,
                        [assistant_message]
                    )
                    
                    # Check if we should summarize the conversation
                    turn_count = self.active_conversations[conversation_id].get("turn_count", 0)
                    
                    if turn_count >= self.max_conversation_turns:
                        # Reset turn count
                        self.active_conversations[conversation_id]["turn_count"] = 0
                        
                        # Summarize conversation asynchronously
                        asyncio.create_task(self._summarize_conversation(
                            db,
                            conversation.user_id,
                            conversation_id
                        ))
                    
                    return assistant_message
                    
                except Exception as e:
                    logger.error(f"Error processing message (attempt {retry+1}): {str(e)}")
                    
                    if retry < self.max_retries - 1:
                        # Wait before retry
                        await asyncio.sleep(self.retry_pause)
                    else:
                        # Final retry failed
                        # Update assistant message with error
                        await message_router.update_message(
                            db,
                            assistant_message.id,
                            {
                                "content": "I'm sorry, but I encountered an error processing your message. Please try again.",
                                "is_complete": True,
                                "role": MessageRole.ASSISTANT.value
                            }
                        )
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"Error handling user message: {str(e)}")
            return None
    
    async def handle_tool_message(
        self,
        db: Session,
        message: Message
    ) -> None:
        """
        Handle a tool message (result of tool execution).
        
        Args:
            db: Database session
            message: Tool message
        """
        try:
            # Tool messages are typically handled during the tool execution flow
            # This handler is mainly for logging and any additional processing
            
            logger.info(f"Received tool message for conversation {message.conversation_id}")
            
            # No special handling needed beyond what's done by the router
            pass
            
        except Exception as e:
            logger.error(f"Error handling tool message: {str(e)}")
    
    async def _process_tool_calls(
        self,
        db: Session,
        conversation_id: str,
        message_id: str,
        tool_calls: List[Dict[str, Any]]
    ) -> str:
        """
        Process tool calls.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            message_id: ID of the message
            tool_calls: List of tool calls
            
        Returns:
            Final response incorporating tool results
        """
        try:
            # Process each tool call
            tool_results = []
            
            for tool_call in tool_calls:
                # Extract tool info
                tool_type = tool_call.get("type", "function")
                
                if tool_type != "function":
                    logger.warning(f"Unsupported tool type: {tool_type}")
                    continue
                
                # Get function details
                function = tool_call.get("function", {})
                tool_name = function.get("name", "")
                tool_args = function.get("arguments", "{}")
                
                # Parse arguments
                try:
                    args = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
                except json.JSONDecodeError:
                    logger.error(f"Invalid tool arguments: {tool_args}")
                    args = {}
                
                # Find matching tool
                tools = await mcp_client_manager.list_tools()
                matching_tools = [t for t in tools if t.name == tool_name]
                
                if not matching_tools:
                    logger.warning(f"Tool not found: {tool_name}")
                    tool_results.append({
                        "tool_call_id": tool_call.get("id", ""),
                        "name": tool_name,
                        "content": f"Error: Tool '{tool_name}' not found."
                    })
                    continue
                
                # Use the first matching tool
                tool = matching_tools[0]
                
                # Execute tool
                execution = await mcp_client_manager.execute_tool(
                    db,
                    tool.id,
                    conversation_id,
                    message_id,
                    args
                )
                
                if not execution:
                    logger.error(f"Failed to execute tool {tool_name}")
                    tool_results.append({
                        "tool_call_id": tool_call.get("id", ""),
                        "name": tool_name,
                        "content": f"Error: Failed to execute tool '{tool_name}'."
                    })
                    continue
                
                # Wait for execution to complete
                max_wait = 30  # seconds
                wait_time = 0
                wait_interval = 0.5
                
                while wait_time < max_wait:
                    # Check execution status
                    current_execution = await mcp_client_manager.get_execution(db, execution.id)
                    
                    if not current_execution:
                        break
                    
                    if current_execution.status == ToolExecutionStatus.COMPLETED:
                        # Extract result
                        outputs = current_execution.outputs or {}
                        result = json.dumps(outputs, indent=2)
                        
                        tool_results.append({
                            "tool_call_id": tool_call.get("id", ""),
                            "name": tool_name,
                            "content": result
                        })
                        break
                    
                    elif current_execution.status == ToolExecutionStatus.FAILED:
                        # Extract error
                        error = current_execution.error or "Unknown error"
                        
                        tool_results.append({
                            "tool_call_id": tool_call.get("id", ""),
                            "name": tool_name,
                            "content": f"Error: {error}"
                        })
                        break
                    
                    # Wait and check again
                    await asyncio.sleep(wait_interval)
                    wait_time += wait_interval
                
                # Timeout
                if wait_time >= max_wait:
                    logger.warning(f"Tool execution timed out: {tool_name}")
                    tool_results.append({
                        "tool_call_id": tool_call.get("id", ""),
                        "name": tool_name,
                        "content": "Error: Tool execution timed out."
                    })
            
            # Create tool result messages
            for result in tool_results:
                await message_router.route_tool_message(
                    db,
                    conversation_id,
                    result["name"],
                    result["content"],
                    {
                        "tool_call_id": result["tool_call_id"],
                        "tool_name": result["name"]
                    }
                )
            
            # Get updated conversation history
            messages, _ = await message_router.get_messages(
                db,
                conversation_id,
                limit=20  # Reasonable context window
            )
            
            # Format messages for LLM
            formatted_messages = llm_client.format_messages(messages)
            
            # Generate final response incorporating tool results
            final_response = await llm_client.generate_response(formatted_messages)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing tool calls: {str(e)}")
            return "I'm sorry, but I encountered an error while trying to use tools to help with your request. Please try again."
    
    async def _generate_conversation_title(
        self,
        db: Session,
        conversation_id: str,
        messages: List[Message]
    ) -> str:
        """
        Generate a title for a conversation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            messages: Conversation messages
            
        Returns:
            Generated title
        """
        try:
            # Format messages for LLM
            formatted_messages = llm_client.format_messages(messages)
            
            # Add a system prompt for title generation
            system_prompt = """Based on the conversation, generate a short, descriptive title (5-7 words maximum).
The title should capture the main topic or question being discussed.
Respond with just the title, nothing else."""
            
            title_messages = [{"role": "system", "content": system_prompt}] + formatted_messages
            
            # Generate title
            title = await llm_client.generate_response(
                title_messages,
                model="gpt-3.5-turbo",  # Use faster model
                max_tokens=20  # Short response
            )
            
            # Clean up the title
            title = title.strip()
            
            # Remove quotes if present
            if title.startswith('"') and title.endswith('"'):
                title = title[1:-1].strip()
            
            # Ensure title is not too long
            if len(title) > 100:
                title = title[:97] + "..."
            
            # Ensure we have a title
            if not title:
                title = "New Conversation"
            
            return title
            
        except Exception as e:
            logger.error(f"Error generating conversation title: {str(e)}")
            return "New Conversation"
    
    async def _summarize_conversation(
        self,
        db: Session,
        user_id: str,
        conversation_id: str
    ) -> None:
        """
        Summarize a conversation for memory.
        
        Args:
            db: Database session
            user_id: ID of the user
            conversation_id: ID of the conversation
        """
        try:
            # Get messages
            messages, _ = await message_router.get_messages(
                db,
                conversation_id,
                limit=self.max_conversation_turns * 2  # Get enough context
            )
            
            # Format messages for LLM
            formatted_messages = llm_client.format_messages(messages)
            
            # Generate summary
            summary = await llm_client.generate_conversation_summary(
                formatted_messages,
                max_length=200  # Keep it concise
            )
            
            # Store in memory
            await memory_adapter.store_memory(
                db,
                user_id,
                conversation_id,
                summary,
                memory_type="conversation_summary",
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_count": len(messages)
                }
            )
            
            logger.info(f"Summarized conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error summarizing conversation: {str(e)}")

# Create a global instance for use throughout the application
conversation_handler = ConversationHandler()