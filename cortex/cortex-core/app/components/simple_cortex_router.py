"""
Simple Cortex Router Implementation
A basic implementation of the Cortex Router interface
"""

from typing import Dict, List, Optional, Any, Tuple
import uuid
import json
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.utils.logger import logger
from app.interfaces.router import CortexRouterInterface, RouterRequest, RoutingDecision
from app.api.sse import send_event_to_conversation
from app.database.models import Conversation


class SimpleCortexRouter(CortexRouterInterface):
    """
    Simple implementation of the Cortex Router
    
    This is a placeholder implementation that simply echoes the input
    and returns a basic routing decision. It will be enhanced in the future
    to include more sophisticated routing logic.
    """
    
    async def route(self, request: RouterRequest) -> RoutingDecision:
        """
        Route an incoming message
        
        Currently just returns a basic "respond" decision for all inputs
        
        Args:
            request: The incoming request to be routed
            
        Returns:
            A routing decision indicating how to process the request
        """
        logger.info(f"Routing request for conversation {request.conversation_id}")
        
        # Generate a unique request ID for tracking
        request_id = str(uuid.uuid4())
        
        # For now, we just echo the input with a simple decision
        # In the future, this will be enhanced with LLM-based routing
        return RoutingDecision(
            action_type="respond",
            priority=3,
            status_message="Processing your request...",
            metadata={
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_length": len(request.content)
            }
        )
    
    async def process_feedback(self, request_id: str, success: bool, metadata: Dict[str, Any]) -> None:
        """
        Process feedback about a previous routing decision
        
        Currently just logs the feedback
        
        Args:
            request_id: ID of the original request
            success: Whether the routing was successful
            metadata: Additional information about the result
        """
        logger.info(f"Received feedback for request {request_id}: success={success}")
        # In the future, this will be used for learning and improving routing decisions
    
    async def process_message(
        self, 
        conversation_id: str, 
        user_message: str,
        user_metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> None:
        """
        Process a user message and handle the complete flow of generating and storing a response
        
        This is the main entry point from the conversation API
        
        Args:
            conversation_id: ID of the conversation
            user_message: Content of the user's message
            user_metadata: Optional metadata for the user message
            db: Database session
        """
        # Get conversation for workspace_id
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            # Conversation might have been deleted
            logger.warning(f"Conversation {conversation_id} not found for message processing")
            return
        
        # Show typing indicator
        await self._send_typing_indicator(conversation_id, True)
        
        # Create router request
        now = datetime.now(timezone.utc)
        request = RouterRequest(
            content=user_message,
            conversation_id=conversation_id,
            workspace_id=conversation.workspace_id,
            timestamp=now,
            metadata=user_metadata or {}
        )
        
        # Get routing decision
        decision = await self.route(request)
        
        # Send status message if available
        if decision.status_message:
            await send_event_to_conversation(
                conversation_id,
                "status_update",
                {
                    "message": decision.status_message,
                    "timestamp": now.isoformat()
                }
            )
        
        # Wait to simulate processing time based on priority
        wait_time = self.get_wait_time(decision.priority)
        logger.info(f"Waiting {wait_time} seconds before sending response for conversation {conversation_id}")
        await asyncio.sleep(wait_time)
        
        # Generate response based on decision
        # For now, just echo the input
        response_text = f"ECHO: {user_message}"
        logger.info(f"Generated response for conversation {conversation_id}: {response_text}")
        
        # Create message entry with timezone-aware UTC datetime
        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Create response object
        response = {
            "id": message_id,
            "content": response_text,
            "role": "assistant",
            "created_at_utc": now,
            "metadata": {
                "router_decision": decision.action_type,
                "router_priority": decision.priority,
                **decision.metadata
            }
        }
        
        # Parse entries and add new response
        try:
            entries = json.loads(conversation.entries)
        except json.JSONDecodeError:
            entries = []
        
        entries.append(response)
        
        # Update conversation with new response
        conversation.entries = json.dumps(entries, cls=DateTimeEncoder)
        conversation.last_active_at_utc = now
        
        # Commit changes to database
        db.commit()
        logger.info(f"Saved assistant response to conversation {conversation_id}")
        
        # Send message received event
        await send_event_to_conversation(
            conversation_id,
            "message_received",
            {
                "id": response["id"],
                "content": response["content"],
                "role": response["role"],
                "created_at_utc": response["created_at_utc"].isoformat(),  # Convert to ISO string for transport
                "metadata": response["metadata"]
            }
        )
        logger.info(f"Sent message_received event for conversation {conversation_id}")
        
        # Turn off typing indicator
        await self._send_typing_indicator(conversation_id, False)
        
        # Process feedback for this decision
        await self.process_feedback(
            decision.metadata.get("request_id", "unknown"),
            True,  # Assume success for now
            {"response_length": len(response_text)}
        )
    
    async def stream_message(
        self,
        conversation_id: str,
        user_message: str,
        user_metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Tuple[Any, Any, Any]:
        """
        Process a streaming message request
        
        Returns generator functions and metadata needed by the streaming endpoint
        
        Args:
            conversation_id: ID of the conversation
            user_message: Content of the user's message
            user_metadata: Optional metadata for the user message
            db: Database session
            
        Returns:
            Tuple containing (response_generator, assistant_message_id, response_metadata)
        """
        # Get conversation for workspace_id
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            # Conversation might have been deleted
            logger.warning(f"Conversation {conversation_id} not found for message processing")
            return None, None, None
        
        # Create a unique message ID
        assistant_message_id = str(uuid.uuid4())
        
        # Create router request
        now = datetime.now(timezone.utc)
        request = RouterRequest(
            content=user_message,
            conversation_id=conversation_id,
            workspace_id=conversation.workspace_id,
            timestamp=now,
            metadata=user_metadata or {}
        )
        
        # Get routing decision
        decision = await self.route(request)
        
        # Create metadata for the response
        response_metadata = {
            "router_decision": decision.action_type,
            "router_priority": decision.priority,
            **decision.metadata
        }
        
        # Send status message if available
        if decision.status_message:
            await send_event_to_conversation(
                conversation_id,
                "status_update",
                {
                    "message": decision.status_message,
                    "timestamp": now.isoformat()
                }
            )
        
        # Send typing indicator
        await self._send_typing_indicator(conversation_id, True)
        
        # Create response generator function
        async def response_generator():
            # Initial message with role
            yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant'}}]})}\n\n"
            
            # Wait to simulate processing time based on priority
            wait_time = self.get_wait_time(decision.priority)
            logger.info(f"Waiting {wait_time} seconds before streaming response for conversation {conversation_id}")
            await asyncio.sleep(wait_time)
            
            # Generate a simple echo response
            response_text = f"ECHO: {user_message}"
            logger.info(f"Streaming response for conversation {conversation_id}")
            
            assistant_content = ""
            
            for chunk in response_text.split():
                # Wait a bit to simulate thinking/typing
                await asyncio.sleep(0.1)
                
                # Send the chunk
                assistant_content += chunk + " "
                chunk_data = {
                    "id": assistant_message_id,
                    "created": int(datetime.now(timezone.utc).timestamp()),
                    "model": "simulation",
                    "choices": [
                        {
                            "delta": {
                                "content": chunk + " "
                            },
                            "index": 0
                        }
                    ]
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
            
            # Final chunk with stop reason
            final_data = {
                "id": assistant_message_id,
                "created": int(datetime.now(timezone.utc).timestamp()),
                "model": "simulation",
                "choices": [
                    {
                        "delta": {},
                        "finish_reason": "stop",
                        "index": 0
                    }
                ]
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
            # Process feedback
            await self.process_feedback(
                decision.metadata.get("request_id", "unknown"),
                True,  # Assume success for now
                {"response_length": len(response_text)}
            )
            
            # Save the response to conversation
            try:
                # Get fresh conversation object
                latest_conversation = db.query(Conversation).filter(
                    Conversation.id == conversation_id
                ).first()
                
                if latest_conversation:
                    try:
                        entries = json.loads(latest_conversation.entries)
                    except json.JSONDecodeError:
                        entries = []
                    
                    # Add assistant response with timezone-aware UTC datetime
                    now = datetime.now(timezone.utc)
                    assistant_entry = {
                        "id": assistant_message_id,
                        "content": response_text,
                        "role": "assistant",
                        "created_at_utc": now,
                        "metadata": response_metadata
                    }
                    
                    entries.append(assistant_entry)
                    latest_conversation.entries = json.dumps(entries, cls=DateTimeEncoder)
                    latest_conversation.last_active_at_utc = now
                    db.commit()
                    
                    # Send message_received event
                    await send_event_to_conversation(
                        conversation_id,
                        "message_received",
                        {
                            "id": assistant_message_id,
                            "content": response_text,
                            "role": "assistant",
                            "created_at_utc": now.isoformat(),
                            "metadata": response_metadata
                        }
                    )
                    
                    # Turn off typing indicator
                    await self._send_typing_indicator(conversation_id, False)
            
            except Exception as e:
                logger.error(f"Error saving assistant response: {e}")
        
        return response_generator, assistant_message_id, response_metadata
    
    def get_wait_time(self, priority: int) -> float:
        """
        Get wait time based on priority level
        
        Args:
            priority: Priority level (1-5)
            
        Returns:
            Wait time in seconds
        """
        # Higher priority = less wait time
        return max(0.5, 6 - priority)  # 1-5 seconds based on priority (5-1)
        
    async def _send_typing_indicator(self, conversation_id: str, is_typing: bool) -> None:
        """
        Send typing indicator to the conversation
        
        Args:
            conversation_id: ID of the conversation
            is_typing: Whether typing is active
        """
        await send_event_to_conversation(
            conversation_id,
            "typing_indicator",
            {
                "isTyping": is_typing,
                "role": "assistant"
            }
        )
        logger.info(f"{'Started' if is_typing else 'Stopped'} typing indicator for conversation {conversation_id}")


# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)