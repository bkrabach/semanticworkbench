from typing import Dict, Any

class McpClient:
    """Type stub for McpClient class"""
    
    def __init__(self, client_info: Dict[str, Any], transport_options: Dict[str, Any]) -> None:
        """Initialize the MCP client"""
        ...
        
    async def initialize(self) -> None:
        """Initialize the client connection"""
        ...
        
    async def tools_list(self) -> Dict[str, Any]:
        """List available tools"""
        ...
        
    async def tools_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the server"""
        ...
        
    async def resources_read(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the server"""
        ...
        
    async def shutdown(self) -> None:
        """Shut down the client connection"""
        ...