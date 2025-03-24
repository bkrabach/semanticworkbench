"""
Service discovery for MCP services.

This module provides service discovery mechanisms for finding and connecting to MCP services.
"""

import asyncio
import logging
import os
from typing import Dict, Optional, Union

import httpx

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """
    Simple service discovery for MCP services.
    
    Maps service names to network endpoints and monitors their health.
    """
    
    def __init__(self) -> None:
        """Initialize the service discovery registry."""
        self.services: Dict[str, str] = {}
        self.health_status: Dict[str, Optional[bool]] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """
        Initialize service discovery from environment variables.
        """
        # Read service endpoints from environment
        self.services = {
            "memory": os.getenv("MEMORY_SERVICE_URL", "http://localhost:9000"),
            "cognition": os.getenv("COGNITION_SERVICE_URL", "http://localhost:9100")
        }
        
        logger.info(f"Initialized service discovery with services: {', '.join(self.services.keys())}")
        for service, url in self.services.items():
            logger.info(f"  - {service}: {url}")
        
        # Initialize health status
        self.health_status = {service: None for service in self.services}
        
        # Start health check background task
        if not self._health_check_task:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
    async def register(self, service_name: str, endpoint: str) -> None:
        """
        Register a service endpoint.
        
        Args:
            service_name: The service name
            endpoint: The service endpoint URL
        """
        self.services[service_name] = endpoint
        self.health_status[service_name] = None
        logger.info(f"Registered service {service_name} at {endpoint}")
        
    async def resolve(self, service_name: str) -> Optional[str]:
        """
        Resolve a service name to an endpoint.
        
        Args:
            service_name: The service name
            
        Returns:
            The service endpoint URL or None if not found
        """
        endpoint = self.services.get(service_name)
        if not endpoint:
            logger.warning(f"Service {service_name} not found in registry")
        return endpoint
        
    async def is_healthy(self, service_name: str) -> bool:
        """
        Check if a service is healthy.
        
        Args:
            service_name: The service name
            
        Returns:
            True if healthy, False otherwise
        """
        return self.health_status.get(service_name, False) == True
    
    async def get_all_services(self) -> Dict[str, str]:
        """
        Get all registered services and their endpoints.
        
        Returns:
            Dictionary of service names to endpoints
        """
        return self.services.copy()
    
    async def get_healthy_services(self) -> Dict[str, str]:
        """
        Get all healthy services and their endpoints.
        
        Returns:
            Dictionary of healthy service names to endpoints
        """
        return {
            service: endpoint 
            for service, endpoint in self.services.items()
            if self.health_status.get(service) == True
        }
        
    async def _health_check_loop(self) -> None:
        """Background task for checking service health."""
        try:
            while True:
                async with httpx.AsyncClient() as client:
                    for service_name, endpoint in self.services.items():
                        try:
                            # Try to call health endpoint
                            response = await client.get(
                                f"{endpoint}/health",
                                timeout=5.0
                            )
                            
                            # Update health status
                            new_status = response.status_code == 200
                            old_status = self.health_status.get(service_name)
                            
                            if new_status != old_status:
                                if new_status:
                                    logger.info(f"Service {service_name} is now healthy")
                                else:
                                    logger.warning(f"Service {service_name} is now unhealthy (HTTP {response.status_code})")
                                
                            self.health_status[service_name] = new_status
                            
                        except Exception as e:
                            if self.health_status.get(service_name):
                                logger.warning(f"Service {service_name} is now unhealthy: {e}")
                            self.health_status[service_name] = False
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
        except asyncio.CancelledError:
            logger.info("Health check loop cancelled")
        except Exception as e:
            logger.error(f"Error in health check loop: {e}", exc_info=True)
            
    async def close(self) -> None:
        """Clean up resources."""
        if self._health_check_task:
            # Check if task is a real asyncio.Task or a mock
            is_mock = hasattr(self._health_check_task, 'mock_calls')
            
            try:
                # Always cancel the task
                if hasattr(self._health_check_task, 'cancel'):
                    self._health_check_task.cancel()
                
                # Only await real tasks, not mocks
                if not is_mock:
                    try:
                        await self._health_check_task
                    except asyncio.CancelledError:
                        # This is expected when cancelling a task
                        pass
            except Exception as e:
                # Log any issues but continue cleanup
                logger.warning(f"Error while closing health check task: {e}")
            finally:
                # Always clear the task reference
                self._health_check_task = None
            
            
# Global instance
service_discovery = ServiceDiscovery()