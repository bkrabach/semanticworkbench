import logging
from typing import Dict, List, Any, Optional, Union, Set, Callable, Awaitable
import asyncio
import json
from datetime import datetime
import uuid
from functools import lru_cache
import re
import weakref
import traceback
import os

from cortex_core.core.config import get_settings
from cortex_core.core.router import message_router
from cortex_core.models.schemas import MCPServer, MCPTool, MCPToolParameter, ToolExecution, ToolExecutionStatus

# We'll use a simplified MCP client implementation for the PoC
# In a real implementation, this would use the FastMCP client library
# from fastmcp import MCPClient

# Setup logging
logger = logging.getLogger(__name__)
settings = get_settings()

class MCPClientManager:
    """
    Manager for MCP client connections.
    
    This class is responsible for:
    - Managing connections to FastMCP servers
    - Discovering and registering tools provided by MCP servers
    - Handling tool execution requests from the Conversation Handler
    - Managing serialization and deserialization of tool inputs/outputs
    """
    
    def __init__(self):
        """Initialize the MCP Client Manager."""
        # MCP server connections
        # Key: server_id, Value: server_info dict with connection details
        self.servers: Dict[str, Dict[str, Any]] = {}
        
        # Available tools
        # Key: tool_id, Value: MCPTool
        self.tools: Dict[str, MCPTool] = {}
        
        # Server tools
        # Key: server_id, Value: Dict[tool_name, tool_id]
        self.server_tools: Dict[str, Dict[str, str]] = {}
        
        # Tool executions
        # Key: execution_id, Value: ToolExecution
        self.executions: Dict[str, ToolExecution] = {}
        
        # Mock tools for PoC
        self.mock_tools_enabled = settings.mock_mcp_tools if hasattr(settings, 'mock_mcp_tools') else True
        
        # Register with router for events
        message_router.register_component("mcp_client", self)
        
        logger.info("MCPClientManager initialized")
    
    async def initialize(self) -> None:
        """Initialize MCP connections."""
        try:
            # In a real implementation, we would load MCP server config from settings
            # For the PoC, we'll create mock servers
            
            if self.mock_tools_enabled:
                # Add mock servers
                await self._add_mock_servers()
                
                # Register mock tools
                await self._register_mock_tools()
            else:
                # Load configured MCP servers
                server_configs = settings.mcp_servers if hasattr(settings, 'mcp_servers') else []
                
                for server_config in server_configs:
                    # Create server ID
                    server_id = str(uuid.uuid4())
                    
                    # Create server
                    server = MCPServer(
                        id=server_id,
                        name=server_config.get("name", "Unknown Server"),
                        url=server_config.get("url", ""),
                        status="connecting"
                    )
                    
                    # Add server
                    self.servers[server_id] = {
                        "server": server,
                        "connection": None
                    }
                    
                    # Connect to server (async)
                    asyncio.create_task(self._connect_to_server(server_id))
            
            # Subscribe to cleanup event
            await message_router.subscribe_to_event(
                "mcp_client",
                "system_shutdown",
                self._handle_system_shutdown
            )
                
        except Exception as e:
            logger.error(f"Error initializing MCP clients: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _add_mock_servers(self) -> None:
        """Add mock servers for development and testing."""
        # Add weather server
        weather_server_id = str(uuid.uuid4())
        weather_server = MCPServer(
            id=weather_server_id,
            name="Weather MCP Server",
            url="mock://weather",
            status="connected"
        )
        
        self.servers[weather_server_id] = {
            "server": weather_server,
            "connection": "mock",
            "type": "weather"
        }
        
        # Add news server
        news_server_id = str(uuid.uuid4())
        news_server = MCPServer(
            id=news_server_id,
            name="News MCP Server",
            url="mock://news",
            status="connected"
        )
        
        self.servers[news_server_id] = {
            "server": news_server,
            "connection": "mock",
            "type": "news"
        }
        
        # Add calculator server
        calc_server_id = str(uuid.uuid4())
        calc_server = MCPServer(
            id=calc_server_id,
            name="Calculator MCP Server",
            url="mock://calculator",
            status="connected"
        )
        
        self.servers[calc_server_id] = {
            "server": calc_server,
            "connection": "mock",
            "type": "calculator"
        }
        
        logger.info(f"Added {len(self.servers)} mock MCP servers")
    
    async def _register_mock_tools(self) -> None:
        """Register mock tools from mock servers."""
        # Initialize server tools dict for each server
        for server_id in self.servers:
            self.server_tools[server_id] = {}
        
        # Weather server tools
        for server_id, server_info in self.servers.items():
            if server_info.get("type") == "weather":
                # Get weather forecast tool
                tool_id = str(uuid.uuid4())
                
                tool = MCPTool(
                    id=tool_id,
                    server_id=server_id,
                    name="get_weather",
                    description="Get the current weather for a location",
                    parameters=[
                        MCPToolParameter(
                            name="location",
                            type="string",
                            description="The city or location to get weather for",
                            required=True
                        ),
                        MCPToolParameter(
                            name="units",
                            type="string",
                            description="Temperature units (celsius or fahrenheit)",
                            required=False,
                            default="celsius"
                        )
                    ]
                )
                
                # Add tool
                self.tools[tool_id] = tool
                
                # Add to server tools
                self.server_tools[server_id][tool.name] = tool_id
                
                # Add to server
                self.servers[server_id]["server"].tools.append(tool)
                
                # Get forecast tool
                tool_id = str(uuid.uuid4())
                
                tool = MCPTool(
                    id=tool_id,
                    server_id=server_id,
                    name="get_forecast",
                    description="Get the weather forecast for a location",
                    parameters=[
                        MCPToolParameter(
                            name="location",
                            type="string",
                            description="The city or location to get forecast for",
                            required=True
                        ),
                        MCPToolParameter(
                            name="days",
                            type="integer",
                            description="Number of days (1-5)",
                            required=False,
                            default=3
                        ),
                        MCPToolParameter(
                            name="units",
                            type="string",
                            description="Temperature units (celsius or fahrenheit)",
                            required=False,
                            default="celsius"
                        )
                    ]
                )
                
                # Add tool
                self.tools[tool_id] = tool
                
                # Add to server tools
                self.server_tools[server_id][tool.name] = tool_id
                
                # Add to server
                self.servers[server_id]["server"].tools.append(tool)
            
            elif server_info.get("type") == "news":
                # Get news tool
                tool_id = str(uuid.uuid4())
                
                tool = MCPTool(
                    id=tool_id,
                    server_id=server_id,
                    name="get_news",
                    description="Get the latest news headlines",
                    parameters=[
                        MCPToolParameter(
                            name="category",
                            type="string",
                            description="News category (world, business, tech, sports, etc.)",
                            required=False,
                            default="general"
                        ),
                        MCPToolParameter(
                            name="count",
                            type="integer",
                            description="Number of headlines to return",
                            required=False,
                            default=5
                        )
                    ]
                )
                
                # Add tool
                self.tools[tool_id] = tool
                
                # Add to server tools
                self.server_tools[server_id][tool.name] = tool_id
                
                # Add to server
                self.servers[server_id]["server"].tools.append(tool)
                
                # Search news tool
                tool_id = str(uuid.uuid4())
                
                tool = MCPTool(
                    id=tool_id,
                    server_id=server_id,
                    name="search_news",
                    description="Search for news articles",
                    parameters=[
                        MCPToolParameter(
                            name="query",
                            type="string",
                            description="Search query",
                            required=True
                        ),
                        MCPToolParameter(
                            name="count",
                            type="integer",
                            description="Number of articles to return",
                            required=False,
                            default=5
                        )
                    ]
                )
                
                # Add tool
                self.tools[tool_id] = tool
                
                # Add to server tools
                self.server_tools[server_id][tool.name] = tool_id
                
                # Add to server
                self.servers[server_id]["server"].tools.append(tool)
            
            elif server_info.get("type") == "calculator":
                # Simple calculator tool
                tool_id = str(uuid.uuid4())
                
                tool = MCPTool(
                    id=tool_id,
                    server_id=server_id,
                    name="calculate",
                    description="Perform a calculation",
                    parameters=[
                        MCPToolParameter(
                            name="expression",
                            type="string",
                            description="Mathematical expression to evaluate",
                            required=True
                        )
                    ]
                )
                
                # Add tool
                self.tools[tool_id] = tool
                
                # Add to server tools
                self.server_tools[server_id][tool.name] = tool_id
                
                # Add to server
                self.servers[server_id]["server"].tools.append(tool)
                
                # Unit conversion tool
                tool_id = str(uuid.uuid4())
                
                tool = MCPTool(
                    id=tool_id,
                    server_id=server_id,
                    name="convert_units",
                    description="Convert between different units",
                    parameters=[
                        MCPToolParameter(
                            name="value",
                            type="number",
                            description="Value to convert",
                            required=True
                        ),
                        MCPToolParameter(
                            name="from_unit",
                            type="string",
                            description="Source unit",
                            required=True
                        ),
                        MCPToolParameter(
                            name="to_unit",
                            type="string",
                            description="Target unit",
                            required=True
                        )
                    ]
                )
                
                # Add tool
                self.tools[tool_id] = tool
                
                # Add to server tools
                self.server_tools[server_id][tool.name] = tool_id
                
                # Add to server
                self.servers[server_id]["server"].tools.append(tool)
        
        logger.info(f"Registered {len(self.tools)} mock tools")
    
    async def _connect_to_server(
        self,
        server_id: str
    ) -> bool:
        """
        Connect to an MCP server.
        
        Args:
            server_id: Server ID
            
        Returns:
            True if connected successfully
        """
        try:
            # Check if server exists
            if server_id not in self.servers:
                logger.warning(f"Server {server_id} not found")
                return False
            
            # Get server
            server_info = self.servers[server_id]
            server = server_info["server"]
            
            # Update status
            server.status = "connecting"
            
            # Get URL
            url = server.url
            
            logger.info(f"Connecting to MCP server at {url}")
            
            # In a real implementation, we would use the FastMCP client library
            # For the PoC, we'll simulate connection
            await asyncio.sleep(0.5)
            
            # Create client
            # client = MCPClient(url)
            # await client.connect()
            
            # Update server info
            server_info["connection"] = "connected"  # client in real implementation
            server.status = "connected"
            
            # Discover tools
            await self._discover_tools(server_id)
            
            logger.info(f"Connected to MCP server {server.name} at {url}")
            
            return True
            
        except Exception as e:
            if server_id in self.servers:
                self.servers[server_id]["server"].status = "error"
                
            logger.error(f"Error connecting to MCP server: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    async def _discover_tools(
        self,
        server_id: str
    ) -> int:
        """
        Discover tools from an MCP server.
        
        Args:
            server_id: Server ID
            
        Returns:
            Number of tools discovered
        """
        try:
            # Check if server exists
            if server_id not in self.servers:
                logger.warning(f"Server {server_id} not found")
                return 0
            
            # Get server
            server_info = self.servers[server_id]
            server = server_info["server"]
            connection = server_info["connection"]
            
            # Check connection
            if connection == "connected":
                # In a real implementation, we would query the MCP server for tools
                # For the PoC, we'll simulate tool discovery
                logger.info(f"Discovering tools from server {server.name}")
                
                # Simulate delay
                await asyncio.sleep(0.2)
                
                # Mock tools - in a real implementation these would come from the server
                tool_data = [
                    {
                        "name": "sample_tool_1",
                        "description": "A sample tool for demonstration",
                        "parameters": [
                            {
                                "name": "param1",
                                "type": "string",
                                "description": "A sample parameter",
                                "required": True
                            },
                            {
                                "name": "param2",
                                "type": "integer",
                                "description": "Another sample parameter",
                                "required": False,
                                "default": 42
                            }
                        ]
                    },
                    {
                        "name": "sample_tool_2",
                        "description": "Another sample tool",
                        "parameters": [
                            {
                                "name": "query",
                                "type": "string",
                                "description": "Search query",
                                "required": True
                            }
                        ]
                    }
                ]
                
                # Initialize server tools dict if needed
                if server_id not in self.server_tools:
                    self.server_tools[server_id] = {}
                
                # Process tools
                for tool_data_item in tool_data:
                    tool_id = str(uuid.uuid4())
                    
                    # Create parameters
                    parameters = []
                    
                    for param_data in tool_data_item.get("parameters", []):
                        parameter = MCPToolParameter(
                            name=param_data["name"],
                            type=param_data["type"],
                            description=param_data.get("description", ""),
                            required=param_data.get("required", False),
                            default=param_data.get("default")
                        )
                        
                        parameters.append(parameter)
                    
                    # Create tool
                    tool = MCPTool(
                        id=tool_id,
                        server_id=server_id,
                        name=tool_data_item["name"],
                        description=tool_data_item.get("description", ""),
                        parameters=parameters
                    )
                    
                    # Add tool
                    self.tools[tool_id] = tool
                    
                    # Add to server tools
                    self.server_tools[server_id][tool.name] = tool_id
                    
                    # Add to server
                    server.tools.append(tool)
                
                logger.info(f"Discovered {len(tool_data)} tools from server {server.name}")
                
                return len(tool_data)
            else:
                logger.warning(f"Cannot discover tools from server {server.name}: not connected")
                return 0
                
        except Exception as e:
            logger.error(f"Error discovering tools: {str(e)}")
            logger.error(traceback.format_exc())
            return 0
    
    async def _handle_system_shutdown(
        self,
        data: Dict[str, Any]
    ) -> None:
        """
        Handle system shutdown event.
        
        Args:
            data: Event data
        """
        await self.cleanup()
    
    async def execute_tool(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool.
        
        Args:
            data: Execution data
                conversation_id: Conversation ID
                message_id: Message ID
                tool_name: Tool name
                server_id: Optional server ID (if not provided, will search for tool)
                inputs: Tool inputs
            
        Returns:
            Execution result
        """
        try:
            # Extract data
            conversation_id = data.get("conversation_id")
            message_id = data.get("message_id")
            tool_name = data.get("tool_name")
            server_id = data.get("server_id")
            inputs = data.get("inputs", {})
            
            # Validate data
            if not conversation_id:
                raise ValueError("Missing conversation_id")
            
            if not message_id:
                raise ValueError("Missing message_id")
            
            if not tool_name:
                raise ValueError("Missing tool_name")
            
            # Find tool
            tool_id = None
            
            if server_id:
                # Check if server exists
                if server_id not in self.servers:
                    raise ValueError(f"Server {server_id} not found")
                
                # Check if server has tool
                if server_id not in self.server_tools or tool_name not in self.server_tools[server_id]:
                    raise ValueError(f"Tool {tool_name} not found on server {server_id}")
                
                tool_id = self.server_tools[server_id][tool_name]
            else:
                # Search all servers for tool
                for srv_id, tools in self.server_tools.items():
                    if tool_name in tools:
                        tool_id = tools[tool_name]
                        server_id = srv_id
                        break
                
                if not tool_id:
                    raise ValueError(f"Tool {tool_name} not found on any server")
            
            # Get tool
            tool = self.tools.get(tool_id)
            
            if not tool:
                raise ValueError(f"Tool {tool_id} not found")
            
            # Create execution ID
            execution_id = str(uuid.uuid4())
            
            # Create execution
            execution = ToolExecution(
                id=execution_id,
                conversation_id=conversation_id,
                message_id=message_id,
                tool_id=tool_id,
                server_id=server_id,
                status=ToolExecutionStatus.PENDING,
                inputs=inputs
            )
            
            # Add execution
            self.executions[execution_id] = execution
            
            # Trigger event
            await message_router.trigger_event(
                "tool_execution_started",
                {
                    "execution_id": execution_id,
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "tool_id": tool_id,
                    "tool_name": tool_name,
                    "inputs": inputs
                }
            )
            
            # Get server info
            server_info = self.servers.get(server_id)
            
            if not server_info:
                raise ValueError(f"Server {server_id} not found")
            
            # Execute tool
            logger.info(f"Executing tool {tool_name} with inputs {inputs}")
            
            # Update status
            execution.status = ToolExecutionStatus.IN_PROGRESS
            execution.updated_at = datetime.utcnow()
            
            # In a real implementation, we would use the MCP client to execute the tool
            # For the PoC, we'll simulate execution with mock responses
            result = await self._execute_mock_tool(tool, inputs)
            
            # Update execution
            execution.status = ToolExecutionStatus.COMPLETED
            execution.updated_at = datetime.utcnow()
            execution.outputs = result
            
            # Trigger event
            await message_router.trigger_event(
                "tool_execution_completed",
                {
                    "execution_id": execution_id,
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "tool_id": tool_id,
                    "tool_name": tool_name,
                    "inputs": inputs,
                    "outputs": result,
                    "status": ToolExecutionStatus.COMPLETED
                }
            )
            
            logger.info(f"Tool {tool_name} execution completed")
            
            return {
                "execution_id": execution_id,
                "result": result,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error executing tool: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Try to create a useful error response
            error_msg = str(e)
            
            # Create execution ID if we have enough information
            execution_id = str(uuid.uuid4())
            conversation_id = data.get("conversation_id")
            message_id = data.get("message_id")
            tool_name = data.get("tool_name")
            server_id = data.get("server_id")
            inputs = data.get("inputs", {})
            
            if conversation_id and message_id:
                # Create minimal execution record for the error
                execution = ToolExecution(
                    id=execution_id,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    tool_id=tool_name,  # Use tool name as ID in error case
                    server_id=server_id or "unknown",
                    status=ToolExecutionStatus.FAILED,
                    inputs=inputs,
                    error=error_msg
                )
                
                # Add execution
                self.executions[execution_id] = execution
                
                # Trigger event
                await message_router.trigger_event(
                    "tool_execution_failed",
                    {
                        "execution_id": execution_id,
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                        "tool_name": tool_name,
                        "inputs": inputs,
                        "error": error_msg,
                        "status": ToolExecutionStatus.FAILED
                    }
                )
            
            return {
                "execution_id": execution_id,
                "error": error_msg,
                "status": "failed"
            }
    
    async def _execute_mock_tool(
        self,
        tool: MCPTool,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a mock tool for development and testing.
        
        Args:
            tool: Tool to execute
            inputs: Tool inputs
            
        Returns:
            Tool result
        """
        # Simulate execution delay
        await asyncio.sleep(0.5)
        
        # Get tool name and server ID
        tool_name = tool.name
        server_id = tool.server_id
        
        # Get server type
        server_info = self.servers.get(server_id)
        
        if not server_info:
            raise ValueError(f"Server {server_id} not found")
        
        server_type = server_info.get("type", "unknown")
        
        # Process based on server type and tool name
        if server_type == "weather":
            if tool_name == "get_weather":
                # Get weather
                location = inputs.get("location", "Unknown location")
                units = inputs.get("units", "celsius")
                
                # Generate mock data
                import random
                
                temp_range = (10, 30) if units == "celsius" else (50, 90)
                temperature = round(random.uniform(*temp_range), 1)
                
                conditions = random.choice([
                    "Clear", "Partly cloudy", "Cloudy", "Rainy", "Thunderstorm", "Snowy"
                ])
                
                humidity = random.randint(30, 95)
                wind_speed = round(random.uniform(0, 30), 1)
                
                unit_symbol = "°C" if units == "celsius" else "°F"
                
                return {
                    "location": location,
                    "temperature": temperature,
                    "unit": unit_symbol,
                    "conditions": conditions,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "updated": datetime.utcnow().isoformat()
                }
                
            elif tool_name == "get_forecast":
                # Get forecast
                location = inputs.get("location", "Unknown location")
                days = min(inputs.get("days", 3), 5)  # Max 5 days
                units = inputs.get("units", "celsius")
                
                # Generate mock data
                import random
                
                temp_range = (5, 35) if units == "celsius" else (40, 95)
                unit_symbol = "°C" if units == "celsius" else "°F"
                
                today = datetime.utcnow().date()
                
                forecast = []
                
                for i in range(days):
                    day_date = today + asyncio.timedelta(days=i)
                    
                    day_data = {
                        "date": day_date.isoformat(),
                        "day": day_date.strftime("%A"),
                        "high": round(random.uniform(*temp_range), 1),
                        "low": round(random.uniform(temp_range[0] - 10, temp_range[0] + 5), 1),
                        "unit": unit_symbol,
                        "conditions": random.choice([
                            "Clear", "Partly cloudy", "Cloudy", "Rainy", "Thunderstorm", "Snowy"
                        ]),
                        "precipitation": round(random.uniform(0, 100), 1)
                    }
                    
                    forecast.append(day_data)
                
                return {
                    "location": location,
                    "forecast": forecast,
                    "units": units,
                    "updated": datetime.utcnow().isoformat()
                }
        
        elif server_type == "news":
            if tool_name == "get_news":
                # Get news
                category = inputs.get("category", "general")
                count = min(inputs.get("count", 5), 10)  # Max 10 articles
                
                # Mock news sources
                sources = [
                    "Associated Press", "Reuters", "BBC", "CNN", 
                    "The Guardian", "Al Jazeera", "The New York Times"
                ]
                
                # Mock article templates by category
                templates = {
                    "general": [
                        "Breaking News: {event} Reported in {location}",
                        "Officials Announce {policy} Initiative",
                        "Study Finds {discovery} Could Impact {field}",
                        "{person} Speaks Out on {topic}",
                        "New Report Shows Trends in {industry}"
                    ],
                    "world": [
                        "{country} Announces New Policy on {issue}",
                        "Leaders Meet to Discuss {global_issue}",
                        "International Tensions Rise Over {dispute}",
                        "Treaty Signed Between {country} and {country2}",
                        "Humanitarian Crisis Develops in {region}"
                    ],
                    "business": [
                        "{company} Reports {percent}% {direction} in Quarterly Earnings",
                        "Markets React to {event} with {movement}",
                        "{company} Announces New {product_type}",
                        "Economic Indicators Show {trend} in {sector}",
                        "Merger Between {company} and {company2} Announced"
                    ],
                    "tech": [
                        "New {device} Unveiled by {company}",
                        "Researchers Develop {technology} for {application}",
                        "{company} Addresses {issue} in Latest Update",
                        "Study Shows Impact of {technology} on {field}",
                        "Breakthrough in {tech_field} Could Enable {capability}"
                    ],
                    "sports": [
                        "{team} Defeats {team2} in {match_type}",
                        "Athlete {person} Breaks Record for {sport}",
                        "{team} Announces New {role}",
                        "Controversy in {sport} Tournament Over {issue}",
                        "Season Outlook: What to Expect from {team}"
                    ]
                }
                
                # Default to general if category not found
                templates_for_category = templates.get(category, templates["general"])
                
                # Generate mock news
                import random
                
                # Sample data for templates
                mock_data = {
                    "event": ["Conference", "Election", "Protest", "Festival", "Summit"],
                    "location": ["New York", "London", "Tokyo", "Berlin", "Sydney"],
                    "policy": ["Environmental", "Healthcare", "Education", "Economic", "Security"],
                    "discovery": ["AI Algorithm", "Medical Treatment", "Renewable Energy Source", "Archaeological Find"],
                    "field": ["Healthcare", "Education", "Climate Science", "Agriculture", "Urban Planning"],
                    "person": ["John Smith", "Maria Garcia", "Ahmed Hassan", "Sarah Johnson", "Li Wei"],
                    "topic": ["Climate Change", "Public Health", "Technology Ethics", "Economic Recovery"],
                    "industry": ["Technology", "Healthcare", "Finance", "Manufacturing", "Agriculture"],
                    "country": ["France", "Brazil", "India", "South Korea", "Nigeria"],
                    "country2": ["Canada", "Japan", "Germany", "Australia", "Mexico"],
                    "global_issue": ["Climate Action", "Refugee Crisis", "Trade Relations", "Nuclear Disarmament"],
                    "dispute": ["Border Conflict", "Trade Tariffs", "Fishing Rights", "Diplomatic Tensions"],
                    "region": ["Southeast Asia", "Eastern Europe", "West Africa", "Central America"],
                    "company": ["TechCorp", "Global Innovations", "Sunrise Industries", "Apex Financial", "EcoSolutions"],
                    "company2": ["DataDynamics", "Starlight Enterprises", "BlueOcean Industries", "Green Future Inc"],
                    "percent": [5, 10, 15, 20, 25],
                    "direction": ["Increase", "Decrease", "Growth", "Decline", "Improvement"],
                    "movement": ["Sharp Rise", "Modest Decline", "Volatility", "Stabilization"],
                    "product_type": ["Service", "Platform", "Device", "Subscription Plan", "Enterprise Solution"],
                    "trend": ["Growth", "Contraction", "Stability", "Recovery", "Disruption"],
                    "sector": ["Retail", "Energy", "Healthcare", "Transportation", "Communication"],
                    "device": ["Smartphone", "Wearable Device", "Smart Home System", "VR Headset", "Tablet"],
                    "technology": ["AI System", "Blockchain Solution", "Quantum Computing Method", "Neural Interface"],
                    "application": ["Healthcare", "Remote Work", "Urban Planning", "Education", "Environmental Monitoring"],
                    "issue": ["Security Vulnerability", "Privacy Concern", "Performance Problem", "Compliance Issue"],
                    "tech_field": ["Artificial Intelligence", "Quantum Computing", "Biotechnology", "Robotics"],
                    "capability": ["Faster Processing", "Sustainable Energy", "Medical Treatments", "Space Exploration"],
                    "team": ["Rovers", "Eagles", "United", "Titans", "Legends"],
                    "team2": ["Warriors", "Phoenix", "Olympians", "Thunder", "Stars"],
                    "match_type": ["Championship Final", "Season Opener", "Playoff", "Tournament"],
                    "sport": ["100m Sprint", "Marathon", "High Jump", "Swimming"],
                    "role": ["Coach", "Manager", "Director", "Strategy Consultant"]
                }
                
                # Helper function to format template
                def format_template(template):
                    result = template
                    
                    for key, values in mock_data.items():
                        placeholder = "{" + key + "}"
                        if placeholder in result:
                            result = result.replace(placeholder, str(random.choice(values)))
                    
                    return result
                
                # Generate articles
                articles = []
                
                for i in range(count):
                    template = random.choice(templates_for_category)
                    headline = format_template(template)
                    source = random.choice(sources)
                    
                    article = {
                        "headline": headline,
                        "source": source,
                        "category": category,
                        "published": (datetime.utcnow() - asyncio.timedelta(hours=random.randint(1, 24))).isoformat(),
                        "url": f"https://example.com/news/{i}-{category}"
                    }
                    
                    articles.append(article)
                
                return {
                    "category": category,
                    "articles": articles,
                    "updated": datetime.utcnow().isoformat()
                }
                
            elif tool_name == "search_news":
                # Search news
                query = inputs.get("query", "")
                count = min(inputs.get("count", 5), 10)  # Max 10 articles
                
                if not query:
                    return {
                        "error": "Search query is required"
                    }
                
                # Mock news sources
                sources = [
                    "Associated Press", "Reuters", "BBC", "CNN", 
                    "The Guardian", "Al Jazeera", "The New York Times"
                ]
                
                # Generate mock search results
                import random
                
                # Generate articles
                articles = []
                
                for i in range(count):
                    # Generate headline that includes the query
                    words_before = random.randint(0, 3)
                    words_after = random.randint(0, 3)
                    
                    before_words = [
                        "Breaking:", "New:", "Update:", "Report:", "Analysis:"
                    ]
                    
                    after_words = [
                        "says report", "experts claim", "officials confirm", "sources say", "analysis shows"
                    ]
                    
                    headline = ""
                    
                    if words_before > 0:
                        headline += random.choice(before_words) + " "
                    
                    headline += query
                    
                    if words_after > 0:
                        headline += ", " + random.choice(after_words)
                    
                    source = random.choice(sources)
                    
                    article = {
                        "headline": headline,
                        "source": source,
                        "relevance": round(random.uniform(0.5, 1.0), 2),
                        "published": (datetime.utcnow() - asyncio.timedelta(hours=random.randint(1, 72))).isoformat(),
                        "url": f"https://example.com/news/search/{i}-{query.replace(' ', '-')}"
                    }
                    
                    articles.append(article)
                
                return {
                    "query": query,
                    "results": articles,
                    "updated": datetime.utcnow().isoformat()
                }
        
        elif server_type == "calculator":
            if tool_name == "calculate":
                # Calculate
                expression = inputs.get("expression", "")
                
                if not expression:
                    return {
                        "error": "Expression is required"
                    }
                
                # Parse and evaluate expression
                try:
                    # Sanitize expression (very important in a real app!)
                    # For the mock, we'll allow only basic math operators
                    import re
                    
                    # Check if expression contains only allowed characters
                    if not re.match(r'^[0-9\+\-\*\/\(\)\.\s]+$', expression):
                        raise ValueError("Expression contains invalid characters")
                    
                    # Evaluate expression
                    result = eval(expression)
                    
                    return {
                        "expression": expression,
                        "result": result
                    }
                    
                except Exception as e:
                    return {
                        "expression": expression,
                        "error": f"Error evaluating expression: {str(e)}"
                    }
                
            elif tool_name == "convert_units":
                # Convert units
                value = inputs.get("value")
                from_unit = inputs.get("from_unit", "").lower()
                to_unit = inputs.get("to_unit", "").lower()
                
                if value is None:
                    return {
                        "error": "Value is required"
                    }
                
                if not from_unit:
                    return {
                        "error": "Source unit is required"
                    }
                
                if not to_unit:
                    return {
                        "error": "Target unit is required"
                    }
                
                # Simple conversion factors for common units
                conversion_factors = {
                    # Length
                    "m_to_ft": 3.28084,
                    "ft_to_m": 0.3048,
                    "km_to_mi": 0.621371,
                    "mi_to_km": 1.60934,
                    "cm_to_in": 0.393701,
                    "in_to_cm": 2.54,
                    
                    # Weight/Mass
                    "kg_to_lb": 2.20462,
                    "lb_to_kg": 0.453592,
                    "g_to_oz": 0.035274,
                    "oz_to_g": 28.3495,
                    
                    # Volume
                    "l_to_gal": 0.264172,
                    "gal_to_l": 3.78541,
                    "ml_to_oz": 0.033814,
                    "oz_to_ml": 29.5735,
                    
                    # Temperature
                    "c_to_f": lambda c: c * 9/5 + 32,
                    "f_to_c": lambda f: (f - 32) * 5/9
                }
                
                # Create conversion key
                key = f"{from_unit}_to_{to_unit}"
                
                # Check if conversion is supported
                if key in conversion_factors:
                    factor = conversion_factors[key]
                    
                    if callable(factor):
                        # For functions like temperature conversion
                        result = factor(value)
                    else:
                        # For simple multiplication factors
                        result = value * factor
                    
                    return {
                        "value": value,
                        "from_unit": from_unit,
                        "to_unit": to_unit,
                        "result": round(result, 4)
                    }
                else:
                    return {
                        "error": f"Conversion from {from_unit} to {to_unit} is not supported"
                    }
        
        # Default tool response for unknown tools
        return {
            "tool": tool_name,
            "inputs": inputs,
            "result": "This is a simulated result for a mock tool. In a real implementation, this would call an MCP server.",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_tool_by_name(
        self,
        tool_name: str
    ) -> Optional[MCPTool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Tool if found
        """
        # Search all servers for tool
        for server_id, tools in self.server_tools.items():
            if tool_name in tools:
                tool_id = tools[tool_name]
                return self.tools.get(tool_id)
        
        return None
    
    async def get_tool_by_id(
        self,
        tool_id: str
    ) -> Optional[MCPTool]:
        """
        Get a tool by ID.
        
        Args:
            tool_id: Tool ID
            
        Returns:
            Tool if found
        """
        return self.tools.get(tool_id)
    
    async def get_tools(
        self,
        server_id: Optional[str] = None
    ) -> List[MCPTool]:
        """
        Get all tools.
        
        Args:
            server_id: Optional server ID to filter by
            
        Returns:
            List of tools
        """
        if server_id:
            # Get tools for server
            if server_id not in self.server_tools:
                return []
            
            tools = []
            
            for tool_name, tool_id in self.server_tools[server_id].items():
                tool = self.tools.get(tool_id)
                
                if tool:
                    tools.append(tool)
            
            return tools
        else:
            # Get all tools
            return list(self.tools.values())
    
    async def get_servers(self) -> List[MCPServer]:
        """
        Get all servers.
        
        Returns:
            List of servers
        """
        return [server_info["server"] for server_info in self.servers.values()]
    
    async def get_execution(
        self,
        execution_id: str
    ) -> Optional[ToolExecution]:
        """
        Get a tool execution.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Tool execution if found
        """
        return self.executions.get(execution_id)
    
    async def get_execution_by_message(
        self,
        message_id: str
    ) -> List[ToolExecution]:
        """
        Get tool executions for a message.
        
        Args:
            message_id: Message ID
            
        Returns:
            List of tool executions
        """
        return [
            execution for execution in self.executions.values()
            if execution.message_id == message_id
        ]
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Close connections to MCP servers
            for server_id, server_info in list(self.servers.items()):
                # Skip mock connections
                if server_info.get("connection") == "mock":
                    continue
                
                logger.info(f"Disconnecting from MCP server {server_info['server'].name}")
                
                # In a real implementation, we would close the MCP client
                # For the PoC, we'll just simulate disconnection
                await asyncio.sleep(0.1)
                
                # Update status
                server_info["server"].status = "disconnected"
                server_info["connection"] = None
            
            # Clear data
            self.executions.clear()
            
            logger.info("MCPClientManager cleaned up")
            
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

# Create a global instance for use throughout the application
mcp_client = MCPClientManager()