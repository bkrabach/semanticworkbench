"""
API endpoints for integrations with Domain Expert services via MCP.

This module provides REST API endpoints for interacting with Domain Expert services
using the Model Context Protocol (MCP). It exposes functionality for discovering
experts, listing their tools, invoking tools, and accessing resources.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.components.integration_hub import IntegrationHub, get_integration_hub
from app.exceptions import ServiceError

router = APIRouter(prefix="/experts")


class ToolCall(BaseModel):
    """Request model for calling a tool on a domain expert"""

    arguments: Dict[str, Any]


class ExpertStatus(BaseModel):
    """Response model for domain expert status information"""

    name: str
    endpoint: str
    type: str
    available: bool
    state: str
    last_error: str | None = None
    capabilities: List[str] = []


@router.get("/", response_model=List[str])
async def list_experts(integration_hub: IntegrationHub = Depends(get_integration_hub), _user=Depends(get_current_user)):
    """
    List all available domain experts.

    Returns a list of expert names that can be used to call tools and access resources.
    """
    try:
        return await integration_hub.list_experts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list experts: {str(e)}")


@router.get("/status", response_model=Dict[str, ExpertStatus])
async def get_expert_status(
    integration_hub: IntegrationHub = Depends(get_integration_hub), _user=Depends(get_current_user)
):
    """
    Get status information for all domain experts.

    Returns detailed connection status, availability, capabilities, and error information
    for all configured domain experts. This endpoint is useful for monitoring and
    diagnostics of domain expert services.
    """
    try:
        return await integration_hub.get_expert_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get expert status: {str(e)}")


@router.get("/{expert_name}/tools", response_model=Dict[str, Any])
async def list_expert_tools(
    expert_name: str, integration_hub: IntegrationHub = Depends(get_integration_hub), _user=Depends(get_current_user)
):
    """
    List all tools available from a specific domain expert.

    Returns a dictionary containing tool definitions with their names, descriptions,
    and input schemas as defined by the MCP specification.
    """
    try:
        return await integration_hub.list_expert_tools(expert_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.post("/{expert_name}/tools/{tool_name}", response_model=Dict[str, Any])
async def invoke_expert_tool(
    expert_name: str,
    tool_name: str,
    tool_call: ToolCall,
    integration_hub: IntegrationHub = Depends(get_integration_hub),
    _user=Depends(get_current_user),
):
    """
    Invoke a tool on a specific domain expert.

    Executes the specified tool with the provided arguments and returns the result.
    Tool parameters are validated against the tool's input schema before being sent
    to the domain expert.
    """
    try:
        return await integration_hub.invoke_expert_tool(
            expert_name=expert_name, tool_name=tool_name, arguments=tool_call.arguments
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invoke tool: {str(e)}")


@router.get("/{expert_name}/resources/{uri:path}", response_model=Dict[str, Any])
async def read_expert_resource(
    expert_name: str,
    uri: str,
    integration_hub: IntegrationHub = Depends(get_integration_hub),
    _user=Depends(get_current_user),
):
    """
    Read a resource from a specific domain expert.

    Retrieves the content of a resource identified by the given URI from the specified
    domain expert. Resources can include text content, binary data, or structured
    information that the domain expert provides.
    """
    try:
        return await integration_hub.read_expert_resource(expert_name=expert_name, uri=uri)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read resource: {str(e)}")
