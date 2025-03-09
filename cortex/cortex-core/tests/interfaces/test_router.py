"""
Test suite for the router interface
"""

import pytest
from datetime import datetime
from typing import Dict, List
import uuid
import asyncio

from app.interfaces.router import (
    ActionType,
    ChannelType,
    CortexMessage,
    InputMessage,
    OutputMessage,
    RouterInterface,
    RoutingDecision
)


class MockRouter(RouterInterface):
    """Mock implementation of RouterInterface for testing"""
    
    def __init__(self):
        self.processed_messages: List[InputMessage] = []
        self.decisions: Dict[str, RoutingDecision] = {}
        self.should_fail: bool = False
    
    async def process_input(self, message: InputMessage) -> bool:
        """Process an input message"""
        if self.should_fail:
            return False
            
        self.processed_messages.append(message)
        
        # Create a dummy routing decision
        decision = RoutingDecision(
            action_type=ActionType.RESPOND,
            priority=3,
            target_channels=[message.channel_id],
            reference_id=message.message_id,
            metadata={"source": "mock_router"}
        )
        
        self.decisions[message.message_id] = decision
        return True


@pytest.fixture
def router():
    """Create a fresh router for each test"""
    return MockRouter()


@pytest.fixture
def sample_input_message():
    """Create a sample input message for testing"""
    return InputMessage(
        message_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        channel_id="test-channel",
        channel_type=ChannelType.CONVERSATION,
        content="Hello, Cortex!",
        user_id="test-user",
        workspace_id="test-workspace",
        conversation_id="test-conversation",
        metadata={"source": "test_suite"}
    )


@pytest.mark.asyncio
async def test_router_process_input(router, sample_input_message):
    """Test basic router message processing"""
    # Process the message
    result = await router.process_input(sample_input_message)
    
    # Verify
    assert result is True
    assert len(router.processed_messages) == 1
    assert router.processed_messages[0].message_id == sample_input_message.message_id
    assert router.processed_messages[0].content == "Hello, Cortex!"
    assert router.processed_messages[0].channel_id == "test-channel"
    
    # Check routing decision
    assert sample_input_message.message_id in router.decisions
    decision = router.decisions[sample_input_message.message_id]
    assert decision.action_type == "respond"
    assert decision.target_channels == ["test-channel"]
    assert decision.reference_id == sample_input_message.message_id


@pytest.mark.asyncio
async def test_router_error_handling(router, sample_input_message):
    """Test router error handling"""
    # Set router to fail
    router.should_fail = True
    
    # Process the message
    result = await router.process_input(sample_input_message)
    
    # Verify
    assert result is False
    assert len(router.processed_messages) == 0
    assert sample_input_message.message_id not in router.decisions


@pytest.mark.asyncio
async def test_router_multiple_messages(router):
    """Test processing multiple messages"""
    # Create multiple messages
    messages = []
    for i in range(5):
        message = InputMessage(
            message_id=f"msg-{i}",
            timestamp=datetime.utcnow(),
            channel_id=f"channel-{i % 2}",  # Alternate between two channels
            channel_type=ChannelType.CONVERSATION,
            content=f"Message {i}",
            user_id="test-user",
            workspace_id="test-workspace",
            conversation_id="test-conversation"
        )
        messages.append(message)
    
    # Process all messages concurrently
    tasks = [router.process_input(message) for message in messages]
    results = await asyncio.gather(*tasks)
    
    # Verify
    assert all(results)  # All should succeed
    assert len(router.processed_messages) == 5
    
    # Check decisions
    for i in range(5):
        msg_id = f"msg-{i}"
        assert msg_id in router.decisions
        assert router.decisions[msg_id].target_channels == [f"channel-{i % 2}"]
        
    # Check message order (should match order of submission)
    for i, message in enumerate(router.processed_messages):
        assert message.message_id == f"msg-{i}"
        assert message.content == f"Message {i}"


@pytest.mark.asyncio
async def test_channel_type_enum():
    """Test ChannelType enum values"""
    # Test basic enum functionality
    assert ChannelType.CONVERSATION == "conversation"
    assert ChannelType.VOICE == "voice"
    assert ChannelType.CANVAS == "canvas"
    assert ChannelType.APP == "app"
    assert ChannelType.WEBHOOK == "webhook"
    
    # Test enum in messages
    message = InputMessage(
        message_id="test",
        timestamp=datetime.utcnow(),
        channel_id="test-channel",
        channel_type=ChannelType.CLI,
        content="Test CLI message",
        user_id="test-user"
    )
    
    assert message.channel_type == ChannelType.CLI
    assert message.channel_type == "cli"


@pytest.mark.asyncio
async def test_cortex_message_models():
    """Test CortexMessage and its subclasses"""
    # Test base CortexMessage
    base_msg = CortexMessage()
    assert base_msg.message_id is not None
    assert base_msg.timestamp is not None
    assert base_msg.metadata == {}
    
    # Test InputMessage
    input_msg = InputMessage(
        channel_id="test-input",
        channel_type=ChannelType.CONVERSATION,
        content="Test input content"
    )
    assert input_msg.message_id is not None
    assert input_msg.timestamp is not None
    assert input_msg.channel_id == "test-input"
    assert input_msg.channel_type == ChannelType.CONVERSATION
    assert input_msg.content == "Test input content"
    assert input_msg.user_id is None  # Optional field
    
    # Test OutputMessage
    output_msg = OutputMessage(
        channel_id="test-output",
        channel_type=ChannelType.NOTIFICATION,
        content="Test output content",
        reference_message_id="ref-123",
        context_ids=["context-1", "context-2"]
    )
    assert output_msg.message_id is not None
    assert output_msg.timestamp is not None
    assert output_msg.channel_id == "test-output"
    assert output_msg.channel_type == ChannelType.NOTIFICATION
    assert output_msg.content == "Test output content"
    assert output_msg.reference_message_id == "ref-123"
    assert output_msg.context_ids == ["context-1", "context-2"]


@pytest.mark.asyncio
async def test_routing_decision_model():
    """Test RoutingDecision model"""
    # Test default values
    decision = RoutingDecision()
    assert decision.action_type == ActionType.PROCESS
    assert decision.priority == 3
    assert decision.target_channels == []
    assert decision.status_message is None
    assert decision.reference_id is None
    assert decision.metadata == {}
    
    # Test with custom values
    custom_decision = RoutingDecision(
        action_type=ActionType.DELEGATE,
        priority=5,
        target_channels=["channel-1", "channel-2"],
        status_message="Processing request...",
        reference_id="ref-456",
        metadata={"handler": "expert_system", "timeout": 30}
    )
    
    assert custom_decision.action_type == ActionType.DELEGATE
    assert custom_decision.priority == 5
    assert custom_decision.target_channels == ["channel-1", "channel-2"]
    assert custom_decision.status_message == "Processing request..."
    assert custom_decision.reference_id == "ref-456"
    assert custom_decision.metadata["handler"] == "expert_system"
    assert custom_decision.metadata["timeout"] == 30