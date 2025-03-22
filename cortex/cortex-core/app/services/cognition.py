import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.mcp.decorators import resource

logger = logging.getLogger(__name__)


class CognitionService:
    """
    Cognition Service provides context retrieval and analysis capabilities.

    This service acts as the "brain" of the system, retrieving relevant context
    from the Memory Service to enhance user interactions.
    """

    def __init__(self, memory_service=None):
        """
        Initialize the Cognition Service.

        Args:
            memory_service: Direct reference to MemoryService (for in-process use in Phase 3)
        """
        self.memory_service = memory_service
        self.initialized = False
        logger.info("Cognition service created")

    async def initialize(self) -> None:
        """
        Initialize the Cognition Service.

        This is called when the service is first connected to.
        """
        if self.initialized:
            return

        logger.info("Initializing Cognition Service...")

        # Verify Memory Service access
        if not self.memory_service:
            logger.error("Memory Service reference is required")
            raise ValueError("Memory Service reference is required")

        # Set initialized flag
        self.initialized = True
        logger.info("Cognition Service initialized")

    async def shutdown(self) -> None:
        """
        Shutdown the Cognition Service.

        This is called when the application is shutting down.
        """
        if not self.initialized:
            return

        logger.info("Shutting down Cognition Service...")

        # Clear initialized flag
        self.initialized = False
        logger.info("Cognition Service shut down")

    @resource(name="context")
    async def get_context(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: Optional[int] = 10,
        recency_weight: Optional[float] = 0.5,
    ) -> Dict[str, Any]:
        """
        Get relevant context for a user based on their history and optional query.

        Args:
            user_id: The unique user identifier
            query: Optional search query to filter context
            limit: Maximum number of items to return (default: 10)
            recency_weight: Weight to apply to recency in ranking (0-1, default: 0.5)

        Returns:
            Dictionary containing context information
        """
        try:
            # Validate user_id
            if not user_id:
                return {"context": [], "user_id": "", "query": query, "count": 0, "error": "User ID is required"}

            # Retrieve user history from Memory Service
            history = []
            if limit:
                # Get double the limit to have more items for ranking
                history = await self.memory_service.get_limited_history(user_id, str(limit * 2))
            else:
                history = await self.memory_service.get_history(user_id)

            # If no history, return empty context
            if not history:
                return {"context": [], "user_id": user_id, "query": query, "count": 0}

            # Process and rank items
            ranked_items = self._rank_context_items(history, query, recency_weight or 0.5)

            # Limit results
            context_items = ranked_items[:limit] if limit else ranked_items

            return {"context": context_items, "user_id": user_id, "query": query, "count": len(context_items)}
        except Exception as e:
            logger.error(f"Error generating context for user {user_id}: {e}")
            return {"context": [], "user_id": user_id, "query": query, "count": 0, "error": str(e)}

    def _rank_context_items(
        self, items: List[Dict[str, Any]], query: Optional[str], recency_weight: float
    ) -> List[Dict[str, Any]]:
        """
        Rank context items based on relevance and recency.

        Args:
            items: History items to rank
            query: Optional query to rank against
            recency_weight: Weight for recency (0-1)

        Returns:
            Ranked list of items
        """
        # Convert timestamps to datetime objects
        for item in items:
            if "timestamp" in item:
                try:
                    item["_datetime"] = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    # If timestamp can't be parsed, use current time
                    item["_datetime"] = datetime.now()
            else:
                item["_datetime"] = datetime.now()

        # Sort by recency (newest first)
        items_by_recency = sorted(items, key=lambda x: x.get("_datetime", datetime.min), reverse=True)

        # If query provided, calculate relevance
        if query:
            for item in items:
                # Simple relevance calculation
                item["_relevance"] = self._calculate_relevance(item, query)

            # Sort by combined score
            ranked_items = sorted(
                items,
                key=lambda x: (
                    (1 - recency_weight) * x.get("_relevance", 0)
                    + recency_weight * (1.0 - items_by_recency.index(x) / max(len(items), 1))
                ),
                reverse=True,
            )
        else:
            # If no query, sort by recency only
            ranked_items = items_by_recency

        # Remove temporary ranking fields
        for item in ranked_items:
            if "_datetime" in item:
                del item["_datetime"]
            if "_relevance" in item:
                del item["_relevance"]

        return ranked_items

    def _calculate_relevance(self, item: Dict[str, Any], query: str) -> float:
        """
        Calculate relevance score for an item against a query.

        Args:
            item: The history item
            query: The search query

        Returns:
            Relevance score (0-1)
        """
        if not query:
            return 0.0

        query_terms = query.lower().split()

        # Search in item content
        content = ""
        if "content" in item:
            content = item["content"].lower()
        elif "message" in item:
            content = item["message"].lower()

        # Simple term matching
        matches = sum(1 for term in query_terms if term in content)
        if not query_terms:
            return 0.0

        # Return proportion of matching terms
        return matches / len(query_terms)

    @resource(name="analyze_conversation")
    async def analyze_conversation(
        self, user_id: str, conversation_id: str, analysis_type: Optional[str] = "summary"
    ) -> Dict[str, Any]:
        """
        Analyze a conversation for patterns and insights.

        Args:
            user_id: The unique user identifier
            conversation_id: The conversation ID to analyze
            analysis_type: Type of analysis to perform (summary, topics, sentiment)

        Returns:
            Dictionary containing analysis results
        """
        try:
            # Validate parameters
            if not user_id or not conversation_id:
                return {
                    "type": analysis_type,
                    "results": {},
                    "conversation_id": conversation_id,
                    "error": "User ID and conversation ID are required",
                }

            # Get conversation history from Memory Service
            conversation_items = await self.memory_service.get_conversation(conversation_id)

            # We have both the user_id and conversation items here
            # Could filter for user's messages if needed in the future

            if not conversation_items:
                return {
                    "type": analysis_type,
                    "results": {},
                    "conversation_id": conversation_id,
                    "error": "Conversation not found",
                }

            # Perform requested analysis
            if analysis_type == "summary":
                results = self._generate_conversation_summary(conversation_items)
            elif analysis_type == "topics":
                results = self._extract_conversation_topics(conversation_items)
            elif analysis_type == "sentiment":
                results = self._analyze_conversation_sentiment(conversation_items)
            else:
                return {
                    "type": analysis_type,
                    "results": {},
                    "conversation_id": conversation_id,
                    "error": f"Unknown analysis type: {analysis_type}",
                }

            return {"type": analysis_type, "results": results, "conversation_id": conversation_id}
        except Exception as e:
            logger.error(f"Error analyzing conversation {conversation_id}: {e}")
            return {"type": analysis_type, "results": {}, "conversation_id": conversation_id, "error": str(e)}

    def _generate_conversation_summary(self, conversation_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of the conversation.

        Args:
            conversation_items: List of conversation messages

        Returns:
            Dictionary with summary information
        """
        # Simple count-based summary for Phase 3
        # In Phase 4, this could use an LLM for better summarization
        message_count = len(conversation_items)

        # Count messages by sender
        senders: Dict[str, int] = {}
        for item in conversation_items:
            sender = item.get("user_id", "unknown")
            senders[sender] = senders.get(sender, 0) + 1

        # Extract timestamps for duration calculation
        timestamps = []
        for item in conversation_items:
            if "timestamp" in item:
                try:
                    ts = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
                    timestamps.append(ts)
                except (ValueError, TypeError):
                    pass

        # Calculate duration if possible
        duration_seconds: float = 0.0
        if len(timestamps) >= 2:
            duration_seconds = (max(timestamps) - min(timestamps)).total_seconds()

        return {
            "message_count": message_count,
            "participants": len(senders),
            "duration_seconds": duration_seconds,
            "participant_counts": senders,
        }

    def _extract_conversation_topics(self, conversation_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract topics from the conversation.

        Args:
            conversation_items: List of conversation messages

        Returns:
            Dictionary with topic information
        """
        # Simple keyword-based topic extraction
        # In Phase 4, this could use an LLM for better topic extraction

        # Combine all content
        combined_content = " ".join([item.get("content", "") for item in conversation_items])

        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "of", "to", "in", "is", "it", "that", "this", "for", "with"}

        # Split into words and count frequencies
        words = combined_content.lower().split()
        word_counts: Dict[str, int] = {}

        for word in words:
            if word not in stop_words and len(word) > 3:
                word_counts[word] = word_counts.get(word, 0) + 1

        # Get top keywords
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        topics = sorted_words[:10]

        return {"keywords": [{"word": word, "count": count} for word, count in topics], "word_count": len(words)}

    def _analyze_conversation_sentiment(self, conversation_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze sentiment in the conversation.

        Args:
            conversation_items: List of conversation messages

        Returns:
            Dictionary with sentiment information
        """
        # Very simple rule-based sentiment analysis
        # In Phase 4, this could use an LLM or dedicated sentiment model

        positive_words = {
            "good",
            "great",
            "excellent",
            "amazing",
            "awesome",
            "fantastic",
            "wonderful",
            "happy",
            "like",
            "love",
        }
        negative_words = {
            "bad",
            "terrible",
            "awful",
            "horrible",
            "disappointing",
            "sad",
            "hate",
            "dislike",
            "wrong",
            "problem",
        }

        positive_count = 0
        negative_count = 0

        for item in conversation_items:
            content = item.get("content", "").lower()

            # Count positive and negative words
            for word in positive_words:
                if word in content:
                    positive_count += 1

            for word in negative_words:
                if word in content:
                    negative_count += 1

        # Calculate simple sentiment score (-1 to 1)
        total = positive_count + negative_count
        sentiment_score: float = 0.0
        if total > 0:
            sentiment_score = (positive_count - negative_count) / total

        return {"sentiment_score": sentiment_score, "positive_count": positive_count, "negative_count": negative_count}

    @resource(name="search_history")
    async def search_history(
        self, user_id: str, query: str, limit: Optional[int] = 10, include_conversations: Optional[bool] = True
    ) -> Dict[str, Any]:
        """
        Search user history for specific terms or patterns.

        Args:
            user_id: The unique user identifier
            query: Search query string
            limit: Maximum number of results to return (default: 10)
            include_conversations: Whether to include conversation data (default: True)

        Returns:
            Dictionary containing search results
        """
        try:
            # Validate parameters
            if not user_id or not query:
                return {"results": [], "count": 0, "query": query, "error": "User ID and query are required"}

            # Get user history from Memory Service
            history = await self.memory_service.get_history(user_id)

            # Perform search
            results = []
            query_terms = query.lower().split()

            for item in history:
                # Extract content
                content = ""
                if "content" in item:
                    content = item["content"].lower()
                elif "message" in item:
                    content = item["message"].lower()

                # Check if any query term matches
                if any(term in content for term in query_terms):
                    # If including conversations, add conversation data
                    if include_conversations and "conversation_id" in item:
                        conversation_id = item["conversation_id"]

                        # Add a flag to indicate we'll fetch conversation data
                        # Avoid copying the entire conversation for efficiency
                        item["_has_conversation"] = True
                        item["_conversation_id"] = conversation_id

                    results.append(item)

            # Sort by relevance
            scored_results = [(item, self._calculate_relevance(item, query)) for item in results]
            scored_results.sort(key=lambda x: x[1], reverse=True)

            # Limit results
            limited_results = (
                [item for item, _ in scored_results[:limit]] if limit else [item for item, _ in scored_results]
            )

            # If we're including conversations and have results with conversation IDs
            if include_conversations and any("_has_conversation" in item for item in limited_results):
                # Fetch conversation data for all items in a single iteration
                conversation_ids = set(
                    item["_conversation_id"] for item in limited_results if "_has_conversation" in item
                )

                # Fetch conversations and build a lookup map
                conversation_data = {}
                for conv_id in conversation_ids:
                    conversation = await self.memory_service.get_conversation(conv_id)
                    if conversation:
                        # For each conversation, create a simple summary
                        conversation_data[conv_id] = {
                            "message_count": len(conversation),
                            "participants": len(set(msg.get("user_id", "") for msg in conversation)),
                            "first_message": conversation[0]["content"] if conversation else "",
                        }

                # Add conversation data to results
                for item in limited_results:
                    if "_has_conversation" in item:
                        conv_id = item["_conversation_id"]
                        if conv_id in conversation_data:
                            item["_conversation_data"] = conversation_data[conv_id]

                        # Remove temporary fields
                        del item["_has_conversation"]
                        del item["_conversation_id"]

            return {"results": limited_results, "count": len(limited_results), "query": query}
        except Exception as e:
            logger.error(f"Error searching history for user {user_id}: {e}")
            return {"results": [], "count": 0, "query": query, "error": str(e)}
