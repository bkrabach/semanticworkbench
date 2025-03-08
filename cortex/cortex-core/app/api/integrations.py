"""
API endpoints for integrations with Domain Expert services via MCP.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel

from app.components.integration_hub import IntegrationHub, get_integration_hub
from app.exceptions import ServiceError
from app.api.auth import get_current_user


router = APIRouter(prefix="/experts")


class ToolCall(BaseModel):
    """Request model for calling a tool on a domain expert"""
    arguments: Dict[str, Any]


@router.get("/", response_model=List[str])
async def list_experts(
    integration_hub: IntegrationHub = Depends(get_integration_hub),
    _user = Depends(get_current_user)
):
    """
    List all available domain experts
    """
    try:
        return await integration_hub.list_experts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list experts: {str(e)}")


@router.get("/{expert_name}/tools", response_model=Dict[str, Any])
async def list_expert_tools(
    expert_name: str,
    integration_hub: IntegrationHub = Depends(get_integration_hub),
    _user = Depends(get_current_user)
):
    """
    List all tools available from a specific domain expert
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
    _user = Depends(get_current_user)
):
    """
    Invoke a tool on a specific domain expert
    """
    try:
        return await integration_hub.invoke_expert_tool(
            expert_name=expert_name,
            tool_name=tool_name,
            arguments=tool_call.arguments
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
    _user = Depends(get_current_user)
):
    """
    Read a resource from a specific domain expert
    """
    try:
        return await integration_hub.read_expert_resource(
            expert_name=expert_name,
            uri=uri
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read resource: {str(e)}")