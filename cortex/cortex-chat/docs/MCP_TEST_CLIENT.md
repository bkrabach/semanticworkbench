# How to Use the MCP Test Client

1. Open the client in your browser:
    open /home/brkrabac/repos/semanticworkbench/cortex/cortex-chat/mcp-test-client.html
2. (Or navigate to it using your file browser)
3. Log in with your credentials (default: mailto:user@example.com / password123)
4. Select a workspace and conversation
5. Test the following Phase 3 features:

    **Test 1: Chat with Context Feature**

    The chat tab allows testing the integration between the Response Handler and Cognition Service:

    1. Enable "Use context from Cognition Service" toggle
    2. Observe the context that will be used in your next message
    3. Type a message related to previous conversations
    4. Send the message and connect to the SSE stream
    5. The response should demonstrate knowledge from previous messages

    **What this verifies:** The Response Handler is properly retrieving context from the Cognition Service and using it in the LLM prompt.

    **Test 2: Context Retrieval API**

    The "Context Retrieval" tab lets you directly test the Cognition Service's context retrieval capabilities:

    1. Enter an optional query to filter context
    2. Set the limit and recency weight
    3. Click "Get Context"
    4. Examine the ranked context items returned by the Cognition Service

    **What this verifies:** The Cognition Service's context retrieval tool is properly ranking and returning relevant context based on recency and query.

    **Test 3: Conversation Analysis**

    The "Conversation Analysis" tab allows testing of the analysis features:

    1. Select an analysis type (summary, topics, sentiment)
    2. Click "Analyze Conversation"
    3. View the structured analysis results

    **What this verifies:** The Cognition Service's analysis tools are properly processing conversation data to extract insights.

    **Test 4: History Search**

    The "Search" tab enables testing of the history search capabilities:

    1. Enter a search query
    2. Set the limit and whether to include conversation data
    3. Click "Search History"
    4. View the search results with relevance ranking

    **What this verifies:** The Cognition Service's search functionality is properly finding and ranking relevant messages.

**How This Works Under the Hood**

The test client makes API calls to the various MCP endpoints:

- `/cognition/context` - Gets relevant context for conversations
- `/cognition/analyze` - Analyzes a conversation
- `/cognition/search` - Searches through conversation history
- `/input` - Sends a message with optional context from Cognition Service
- `/output/stream` - Receives SSE events with responses

Each tab in the interface corresponds to a specific MCP capability in Phase 3. The debug panel shows the raw API responses to help you understand exactly what's happening.

**Expected Results**

When the MCP architecture is functioning correctly, you should observe:

1. Context-aware responses: The system references your conversation history appropriately
2. Relevance ranking: Context items are sorted by relevance to your query
3. Multi-faceted analysis: Different analysis types provide different insights
4. Effective search: Search results match your query terms
5. Proper SSE communication: Real-time updates through SSE connection

Any failures in these tests would indicate issues with the MCP implementation, particularly with the Cognition Service integration.

This comprehensive test suite aligns perfectly with the implementation philosophy of ruthless simplicity and architectural integrity with minimal implementation. It directly tests the end-to-end flows that are critical to the system's functionality.
