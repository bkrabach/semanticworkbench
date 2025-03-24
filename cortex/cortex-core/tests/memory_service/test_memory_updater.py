import datetime
from typing import Generic, TypeVar
from unittest import mock

import pytest

from memory_service.memory_updater import MemoryUpdateResult, MemoryUpdater
from memory_service.models import MemoryEntry

# Define a generic type variable for our mock
T = TypeVar("T")

class MockAgentResults(Generic[T]):
    """Mock for Pydantic-AI Agent Results."""
    
    def __init__(self, data: T):
        self._data = data
        
    @property
    def data(self) -> T:
        return self._data
    
    def __await__(self):
        async def _coro():
            return self
        return _coro().__await__()


class TestMemoryUpdater:
    """Tests for the MemoryUpdater class."""

    def setup_method(self):
        """Set up mocks for each test."""
        # Patch the Agent class
        self.agent_patch = mock.patch("memory_service.memory_updater.Agent")
        self.mock_agent_class = self.agent_patch.start()
        
        self.mock_agent = mock.MagicMock()
        self.mock_agent_class.return_value = self.mock_agent

    def teardown_method(self):
        """Clean up after each test."""
        self.agent_patch.stop()

    @pytest.mark.asyncio
    async def test_generate_initial_memory(self):
        """Test generating initial memory from messages."""
        # Set up the mock agent response
        expected_summary = "This is a summary of the conversation."
        self.mock_agent.run.return_value = MockAgentResults(expected_summary)
        
        # Create test messages
        messages = [
            {"role": "user", "content": "Hello, AI!"},
            {"role": "assistant", "content": "Hi there! How can I help you?"}
        ]
        
        # Call the method
        updater = MemoryUpdater()
        result = await updater.generate_initial_memory(messages)
        
        # Check the result
        assert result == expected_summary
        
        # Verify the agent was called with the expected prompt
        self.mock_agent.run.assert_called_once()
        call_args = self.mock_agent.run.call_args[0][0]
        assert "Create an initial memory summary" in call_args
        assert "Hello, AI!" in call_args
        assert "Hi there! How can I help you?" in call_args

    @pytest.mark.asyncio
    async def test_generate_initial_memory_error_handling(self):
        """Test error handling when generating initial memory fails."""
        # Make the agent raise an exception
        self.mock_agent.run.side_effect = Exception("Test error")
        
        # Create test messages
        messages = [
            {"role": "user", "content": "Hello, AI!"},
            {"role": "assistant", "content": "Hi there! How can I help you?"}
        ]
        
        # Call the method
        updater = MemoryUpdater()
        result = await updater.generate_initial_memory(messages)
        
        # Check that a fallback result was returned
        assert "Conversation with 2 messages" in result
        assert "Hi there! How can I help you?" in result

    @pytest.mark.asyncio
    async def test_generate_updated_memory(self):
        """Test updating existing memory with new messages."""
        # Set up the mock agent response
        current_memory = "User asked for help. Assistant greeted them."
        expected_update = "User asked for help. Assistant greeted them and provided information about Python."
        self.mock_agent.run.return_value = MockAgentResults(expected_update)
        
        # Create test messages
        new_messages = [
            {"role": "user", "content": "Tell me about Python."},
            {"role": "assistant", "content": "Python is a versatile programming language..."}
        ]
        
        # Call the method
        updater = MemoryUpdater()
        result = await updater.generate_updated_memory(current_memory, new_messages)
        
        # Check the result
        assert result == expected_update
        
        # Verify the agent was called with the expected prompt
        self.mock_agent.run.assert_called_once()
        call_args = self.mock_agent.run.call_args[0][0]
        assert "Current memory:" in call_args
        assert current_memory in call_args
        assert "New events:" in call_args
        assert "Tell me about Python." in call_args
        assert "Python is a versatile programming language..." in call_args

    @pytest.mark.asyncio
    async def test_generate_updated_memory_error_handling(self):
        """Test error handling when updating memory fails."""
        # Make the agent raise an exception
        self.mock_agent.run.side_effect = Exception("Test error")
        
        # Create test data
        current_memory = "User asked for help. Assistant greeted them."
        new_messages = [{"role": "user", "content": "Tell me about Python."}]
        
        # Call the method
        updater = MemoryUpdater()
        result = await updater.generate_updated_memory(current_memory, new_messages)
        
        # Check that the original memory was returned
        assert result == current_memory

    @pytest.mark.asyncio
    async def test_create_memory(self):
        """Test creating a new memory entry."""
        # Set up the mock agent response
        expected_summary = "This is a summary of the conversation."
        self.mock_agent.run.return_value = MockAgentResults(expected_summary)
        
        # Create test messages
        messages = [
            {"role": "user", "content": "Hello, AI!"},
            {"role": "assistant", "content": "Hi there! How can I help you?"}
        ]
        
        # Mock datetime to get consistent test results
        datetime_mock = mock.patch("memory_service.memory_updater.datetime")
        mock_datetime = datetime_mock.start()
        mock_datetime.datetime.now.return_value = datetime.datetime(2023, 1, 1, 12, 0, 0)
        
        try:
            # Call the method
            updater = MemoryUpdater()
            result = await updater.create_memory("test-convo-123", messages)
            
            # Check the result
            assert isinstance(result, MemoryEntry)
            assert result.conversation_id == "test-convo-123"
            assert result.memory_content == expected_summary
            assert result.last_updated == "2023-01-01T12:00:00"
        finally:
            datetime_mock.stop()

    @pytest.mark.asyncio
    async def test_create_memory_with_long_content(self):
        """Test that memory content is truncated if too long."""
        # Set up the mock agent response with long content
        long_content = "A" * 3000  # Longer than MAX_MEMORY_LENGTH (2000)
        self.mock_agent.run.return_value = MockAgentResults(long_content)
        
        # Create test messages
        messages = [{"role": "user", "content": "Hello"}]
        
        # Mock config's MAX_MEMORY_LENGTH
        config_patch = mock.patch("memory_service.memory_updater.config.MAX_MEMORY_LENGTH", 2000)
        config_patch.start()
        
        try:
            # Call the method
            updater = MemoryUpdater()
            result = await updater.create_memory("test-convo-123", messages)
            
            # Check that the content was truncated
            assert len(result.memory_content) == 2000
            assert result.memory_content == "A" * 2000
        finally:
            config_patch.stop()

    @pytest.mark.asyncio
    async def test_create_memory_error_handling(self):
        """Test error handling when creating memory fails."""
        # Make the agent raise an exception
        self.mock_agent.run.side_effect = Exception("Test error")
        
        # Create test messages
        messages = [
            {"role": "user", "content": "Hello, AI!"},
            {"role": "assistant", "content": "Hi there! How can I help you?"}
        ]
        
        # Call the method
        updater = MemoryUpdater()
        result = await updater.create_memory("test-convo-123", messages)
        
        # Check that a fallback entry was created
        assert isinstance(result, MemoryEntry)
        assert result.conversation_id == "test-convo-123"
        assert "Conversation with 2 messages" in result.memory_content
        assert "Hi there! How can I help you?" in result.memory_content

    @pytest.mark.asyncio
    async def test_update_memory(self):
        """Test updating an existing memory entry."""
        # Set up the mock agent response
        expected_update = "Updated memory content"
        self.mock_agent.run.return_value = MockAgentResults(expected_update)
        
        # Create test data
        current_memory = MemoryEntry(
            conversation_id="test-convo-123",
            memory_content="Original memory content",
            last_updated="2023-01-01T12:00:00"
        )
        new_messages = [{"role": "user", "content": "New message"}]
        
        # Call the method
        updater = MemoryUpdater()
        result = await updater.update_memory(current_memory, new_messages)
        
        # Check the result
        assert isinstance(result, MemoryUpdateResult)
        assert result.updated_memory == expected_update
        assert result.success is True

    @pytest.mark.asyncio
    async def test_update_memory_with_long_content(self):
        """Test that updated memory content is truncated if too long."""
        # Set up the mock agent response with long content
        long_content = "A" * 3000  # Longer than MAX_MEMORY_LENGTH (2000)
        self.mock_agent.run.return_value = MockAgentResults(long_content)
        
        # Create test data
        current_memory = MemoryEntry(
            conversation_id="test-convo-123",
            memory_content="Original memory content",
            last_updated="2023-01-01T12:00:00"
        )
        new_messages = [{"role": "user", "content": "New message"}]
        
        # Mock config's MAX_MEMORY_LENGTH
        config_patch = mock.patch("memory_service.memory_updater.config.MAX_MEMORY_LENGTH", 2000)
        config_patch.start()
        
        try:
            # Call the method
            updater = MemoryUpdater()
            result = await updater.update_memory(current_memory, new_messages)
            
            # Check that the content was truncated
            assert len(result.updated_memory) == 2000
            assert result.updated_memory == "A" * 2000
        finally:
            config_patch.stop()

    @pytest.mark.asyncio
    async def test_update_memory_error_handling(self):
        """Test error handling when updating memory fails."""
        # Patch the generate_updated_memory method to raise an exception
        with mock.patch.object(MemoryUpdater, "generate_updated_memory") as mock_gen_method:
            mock_gen_method.side_effect = Exception("Test error")
            
            # Create test data
            current_memory = MemoryEntry(
                conversation_id="test-convo-123",
                memory_content="Original memory content",
                last_updated="2023-01-01T12:00:00"
            )
            new_messages = [{"role": "user", "content": "New message"}]
            
            # Call the method
            updater = MemoryUpdater()
            result = await updater.update_memory(current_memory, new_messages)
            
            # Check the result
            assert isinstance(result, MemoryUpdateResult)
            assert result.updated_memory == "Original memory content"
            assert result.success is False