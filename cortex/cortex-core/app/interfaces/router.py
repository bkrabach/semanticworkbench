"""
Cortex Router Interface
Defines the contract for routing messages to appropriate handlers
"""

from typing import Dict, List, Optional, Any, Protocol, Tuple
from abc import ABC, abstractmethod
from pydantic import BaseModel
from datetime import datetime


class RouterRequest(BaseModel):
    """Input request to be routed"""
    
    content: str
    conversation_id: str
    workspace_id: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime


class RoutingDecision(BaseModel):
    """Routing decision made by the router"""
    
    action_type: str  # "respond", "process", "retrieve_memory", "delegate", "ignore"
    priority: int = 1  # 1 (lowest) to 5 (highest)
    target_system: Optional[str] = None
    status_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class CortexRouterInterface(ABC):
    """
    Interface for the Cortex Router
    Responsible for determining how to handle incoming messages
    from various input channels
    """
    
    @abstractmethod
    async def route(self, request: RouterRequest) -> RoutingDecision:
        """
        Determine how to route an incoming message
        
        Args:
            request: The incoming request to be routed
            
        Returns:
            A routing decision indicating how to process the request
        """
        pass
    
    @abstractmethod
    async def process_feedback(self, request_id: str, success: bool, metadata: Dict[str, Any]) -> None:
        """
        Process feedback about a previous routing decision
        
        Args:
            request_id: ID of the original request
            success: Whether the routing was successful
            metadata: Additional information about the result
        """
        pass