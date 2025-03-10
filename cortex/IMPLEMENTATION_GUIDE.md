# Cortex Core Simplification Guide

## Overview

This guide outlines a significant simplification of the Cortex Core messaging architecture to improve reliability, maintainability, and comprehensibility. The current system is over-engineered with multiple indirection layers that make the basic messaging flow difficult to reason about and prone to subtle failures.

## Current Architecture Issues

1. **Excessive Indirection**: Multiple layers transmit messages through complex event chains
2. **Thread-based Router**: The CortexRouter uses a threading model that adds complexity
3. **Complex SSE Implementation**: The SSE system has redundant connection handling
4. **Brittle Event Routing**: Events can be lost or misrouted due to complex logic
5. **Over-generalized Components**: Components support features not needed in the core use case
6. **High Debug Overhead**: Verbose logging in lieu of simpler architecture

## Proposed Architecture

```mermaid
graph TD
    subgraph "Client"
        Client[Web Client]
    end

    subgraph "API Layer"
        API[API Endpoint]
    end

    subgraph "Router"
        MessageQueue[Message Queue]
        RouterLogic[Router Logic]
    end

    subgraph "Database"
        DB[Message Storage]
    end

    subgraph "SSE System"
        SSEManager[SSE Manager]
        ClientConnections[Client Connections]
    end

    %% Flow
    Client -->|1. HTTP POST| API
    API -->|2. Save Message| DB
    API -->|3. Queue Message| MessageQueue
    MessageQueue -->|4. Process| RouterLogic
    RouterLogic -->|5. Show Typing| SSEManager
    RouterLogic -->|6. Save Response| DB
    RouterLogic -->|7. Send Response| SSEManager
    SSEManager -->|8. Deliver to| ClientConnections
    ClientConnections -->|9. SSE Events| Client
```

The key improvements are:

1. **Asyncio-based Router**: Replace thread model with asyncio for cleaner async handling
2. **Direct Output Targeting**: Route messages directly to output channels
3. **Simplified Event Flow**: Clear, predictable message paths
4. **Reduced Connection Management**: Streamlined SSE implementation
5. **Focused Component Responsibilities**: Each component has a single clear job

## Implementation Steps

### 1. Update CortexRouter

```python
class CortexRouter(RouterInterface):
    def __init__(self):
        """Initialize the router with proper async queue"""
        self.event_system = get_event_system()
        self.message_queue = asyncio.Queue()  # Replace threading.Queue
        self.logger = logging.getLogger(__name__)
        self.running = True
        # Start the background task to process messages
        self.processing_task = asyncio.create_task(self._process_messages())
    
    async def process_input(self, message: InputMessage) -> bool:
        """
        Fire-and-forget message acceptance - simply queue the message
        Returns True if message was accepted, False if rejected
        """
        try:
            # Queue message for asynchronous processing
            await self.message_queue.put(message)
            self.logger.info(f"Queued message {message.message_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error queuing message: {e}")
            return False
    
    async def _process_messages(self):
        """Continuously process messages from the queue"""
        while self.running:
            try:
                # Get message from queue (with timeout to allow for clean shutdown)
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                # Process the message
                await self._handle_message(message)
                
                # Mark task as done
                self.message_queue.task_done()
            except asyncio.TimeoutError:
                # This is expected during normal operation
                pass
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
    
    async def _handle_message(self, message: InputMessage):
        """Process a single message"""
        try:
            # Make a routing decision - autonomous decision making
            decision = await self._make_routing_decision(message)
            
            if decision.action_type == ActionType.RESPOND:
                # Show typing indicator for each target
                for channel_id in decision.target_channels:
                    await self._send_typing_indicator(channel_id, message.conversation_id, True)
                
                # Wait desired time
                await asyncio.sleep(5)
                
                # Generate response content
                response_content = f"ECHO: {message.content}"
                
                # Send message to all targets
                for channel_id in decision.target_channels:
                    await self._send_message_to_channel(
                        channel_id=channel_id,
                        conversation_id=message.conversation_id,
                        content=response_content,
                        reference_message_id=message.message_id
                    )
                    
                    # Hide typing indicator
                    await self._send_typing_indicator(channel_id, message.conversation_id, False)
            
            # Other action types can be handled similarly
            
        except Exception as e:
            self.logger.error(f"Error handling message {message.message_id}: {e}")
    
    async def _make_routing_decision(self, message: InputMessage) -> RoutingDecision:
        """Decide how to handle this message"""
        # For now, simply route back to the same channel
        # In future, this could consider available channels, message content, etc.
        return RoutingDecision(
            action_type=ActionType.RESPOND,
            priority=3,
            target_channels=[message.channel_id],
            status_message="Processing your request..."
        )
    
    async def _send_typing_indicator(self, channel_id: str, conversation_id: str, is_typing: bool):
        """Send a typing indicator to a specific conversation channel"""
        if not conversation_id:
            return
            
        # Get SSE service
        sse_service = get_sse_service()
            
        # Send directly to SSE - simple, direct path
        await sse_service.connection_manager.send_event(
            "conversation",
            conversation_id,
            "typing_indicator",
            {
                "conversation_id": conversation_id,
                "isTyping": is_typing,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            },
            republish=False  # Simpler direct path
        )
    
    async def _send_message_to_channel(self, channel_id: str, conversation_id: str, 
                                      content: str, reference_message_id: str):
        """Send a message to a specific channel"""
        if not conversation_id:
            return
            
        # Save to database first - if this is a conversation
        message_id = str(uuid.uuid4())
        if conversation_id:
            try:
                from app.database.connection import db
                from app.database.repositories.conversation_repository import ConversationRepository
                
                with db.get_db() as db_session:
                    repo = ConversationRepository(db_session)
                    db_message = repo.add_message(
                        conversation_id=conversation_id,
                        content=content,
                        role="assistant",
                        metadata={"source": "router_echo"}
                    )
                    # Use the database-generated ID if available
                    if hasattr(db_message, 'id') and db_message.id:
                        message_id = db_message.id
            except Exception as e:
                self.logger.error(f"Error saving message to database: {e}")
        
        # Get SSE service
        sse_service = get_sse_service()
            
        # Send directly to SSE - simple, direct path
        await sse_service.connection_manager.send_event(
            "conversation",
            conversation_id,
            "message_received",
            {
                "id": message_id,
                "content": content,
                "role": "assistant",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "metadata": {"source": "cortex_router"},
                "conversation_id": conversation_id
            },
            republish=False  # Simpler direct path
        )
```

### 2. Simplify ConversationOutputPublisher

```python
class ConversationOutputPublisher(OutputPublisherInterface):
    """
    Output publisher for conversation messages
    
    This component is retained for backward compatibility but simplified.
    It now directly forwards message events to the SSE system.
    """
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.channel_id = f"conversation-{conversation_id}"
        self.logger = logging.getLogger(__name__)
        self.event_system = get_event_system()
        self.subscriptions = []
    
    async def _subscribe_to_events(self):
        """Subscribe to events for this channel"""
        message_pattern = f"output.{ChannelType.CONVERSATION}.message"
        subscription_id = await self.event_system.subscribe(message_pattern, self._handle_message_event)
        self.subscriptions.append(subscription_id)
    
    async def _handle_message_event(self, event_type: str, payload):
        """Handle message events from the event system"""
        # Extract the message from the payload
        message_data = payload.data.get("message")
        if not message_data:
            return
            
        # Check if this message is for our channel
        if getattr(message_data, "channel_id", None) != self.channel_id:
            return
            
        # Check if this message has our conversation ID
        conversation_id = getattr(message_data, "conversation_id", None)
        if conversation_id and str(conversation_id) != str(self.conversation_id):
            return
            
        # Forward to SSE directly
        await self.publish(message_data)
    
    async def publish(self, message: OutputMessage) -> bool:
        """Publish a message to SSE"""
        try:
            # Get SSE service
            sse_service = get_sse_service()
            
            # Prepare event data
            event_data = {
                "id": message.message_id,
                "content": message.content,
                "role": "assistant",
                "created_at_utc": message.timestamp.isoformat(),
                "metadata": message.metadata or {},
                "conversation_id": self.conversation_id
            }
            
            # Send directly to SSE
            await sse_service.connection_manager.send_event(
                "conversation",
                self.conversation_id,
                "message_received",
                event_data,
                republish=False
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
            return False
```

### 3. Simplify SSE Connection Manager

The `SSEStarletteManager` should be simplified to reduce complexity:

```python
class SSEStarletteManager(SSEConnectionManager):
    """Simplified SSE Connection Manager implementation"""
    
    def __init__(self):
        # Simple storage model for connections
        self.connections = {
            "global": [],
            "user": collections.defaultdict(list),
            "workspace": collections.defaultdict(list),
            "conversation": collections.defaultdict(list)
        }
        # Map connection IDs to queues
        self.connection_queues = {}
    
    async def send_event(self, channel_type, resource_id, event_type, data, republish=False):
        """Send an event to a channel - simplified implementation"""
        if not resource_id or not channel_type:
            return False
            
        # Normalize resource ID
        resource_id = str(resource_id)
        
        # Log the event
        logger.info(f"Sending {event_type} to {channel_type}/{resource_id}")
        
        # Get connections for this resource
        connections = []
        if channel_type == "global":
            connections = self.connections["global"]
        elif resource_id in self.connections[channel_type]:
            connections = self.connections[channel_type][resource_id]
        
        # Direct delivery to all connections
        success = False
        for conn in connections:
            queue = self.connection_queues.get(conn.id)
            if queue:
                try:
                    # Format the event
                    event_data = {
                        "event": event_type,
                        "data": json.dumps(data)
                    }
                    # Put in queue
                    await queue.put(event_data)
                    success = True
                except Exception as e:
                    logger.error(f"Error sending event to queue: {e}")
        
        return success
```

### 4. Update API Endpoint

Simplify the `/conversations/{conversation_id}/messages` endpoint to directly call the router:

```python
@router.post("/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    message_request: AddMessageRequest,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """Add a message to a conversation and route it"""
    # Add message to database via service
    message = await service.add_message(
        conversation_id=conversation_id,
        content=message_request.content,
        role=message_request.role,
        metadata=message_request.metadata,
    )
    
    # Return error if message wasn't added
    if not message:
        raise HTTPException(
            status_code=404, 
            detail=f"Conversation with ID {conversation_id} not found"
        )
    
    # Create input message for router
    input_message = InputMessage(
        message_id=str(uuid.uuid4()),
        channel_id=f"conversation-{conversation_id}",
        channel_type=ChannelType.CONVERSATION,
        content=message_request.content,
        user_id=str(user.id),
        workspace_id=message.workspace_id,
        conversation_id=conversation_id,
        timestamp=datetime.now(timezone.utc),
        metadata={"source": "api"}
    )
    
    # Get router and process input asynchronously
    router = get_router()
    asyncio.create_task(router.process_input(input_message))
    
    # Return acknowledgment
    return {
        "status": "message_received",
        "message_id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "metadata": message.metadata
    }
```

## Benefits of Simplification

1. **Reduced Code**: Eliminate ~1000-1500 lines of code
2. **Clear Flow Path**: Single path for messages with clear direction
3. **Better Reliability**: Fewer points of failure, simpler error handling
4. **Easier Debugging**: Less code to trace through, clearer logs
5. **Maintainability**: Easier for new developers to understand
6. **Testability**: Simpler components are easier to test
7. **Performance**: Less overhead from complex event chains

## Validation Strategy

1. **Basic Echo Test**: Send a message through the API, confirm echo response
2. **Connection Stability Test**: Keep connection open for extended period
3. **Concurrent User Test**: Multiple users sending messages simultaneously
4. **Error Recovery Test**: Verify system recovers from component failures
5. **End-to-End Test**: Full API → Router → SSE → Client flow with timing

## Implementation Approach

1. **Staged Refactoring**: Replace components one at a time with simplified versions
2. **Parallel Systems**: Keep old system running while testing new implementation
3. **Feature Flags**: Toggle between implementations to compare behavior
4. **Migration Strategy**: Once validated, remove deprecated components

## Key Guidelines

1. **Prefer Directness**: Always favor direct calls over complex event chains
2. **Simplify State**: Minimize shared state and complex connection tracking
3. **Single Responsibility**: Each component should do one thing well
4. **Clear Error Boundaries**: Isolate failures to prevent cascading errors
5. **Metrics & Logging**: Add instrumentation at key points to verify operation

Remember: For this pre-production system, it's better to implement a clean, simple design from the start rather than optimizing for hypothetical future requirements.