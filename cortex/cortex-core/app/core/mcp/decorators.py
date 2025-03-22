import functools
import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast, get_type_hints

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.core.mcp.exceptions import ValidationError
from app.core.mcp.registry import ResourceDefinition, ToolDefinition

# Type for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


def _extract_schema_from_pydantic(model_class: Type[BaseModel]) -> Dict[str, Any]:
    """Extract JSON schema from a Pydantic model.

    Args:
        model_class: Pydantic model class

    Returns:
        JSON schema dict
    """
    schema = model_class.model_json_schema()
    return schema


def _extract_schema_from_function(func: Callable) -> Dict[str, Any]:
    """Extract JSON schema from a function's type hints.

    Args:
        func: Function to extract schema from

    Returns:
        JSON schema dict
    """
    signature = inspect.signature(func)
    type_hints = get_type_hints(func)

    properties = {}
    required = []

    for param_name, param in signature.parameters.items():
        # Skip self and kwargs
        if param_name == "self" or param.kind == inspect.Parameter.VAR_KEYWORD:
            continue

        # Get type annotation if available
        # Unused but kept for future extensions
        _ = type_hints.get(param_name, Any)

        # Determine if parameter is required
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

        # Add to properties
        properties[param_name] = {"type": "object"}  # Simplified schema

    return {"type": "object", "properties": properties, "required": required}


def tool(
    name: Optional[str] = None, description: str = "", input_model: Optional[Type[BaseModel]] = None
) -> Callable[[F], F]:
    """Decorator to mark a method as an MCP tool.

    Args:
        name: Tool name (defaults to method name)
        description: Tool description
        input_model: Pydantic model for input validation

    Returns:
        Decorated method
    """

    def decorator(func: F) -> F:
        tool_name = name or func.__name__

        # Extract schema from input_model or function signature
        if input_model:
            schema = _extract_schema_from_pydantic(input_model)
        else:
            schema = _extract_schema_from_function(func)

        # Create tool definition
        tool_def = ToolDefinition(
            name=tool_name, func=func, schema=schema, description=description or func.__doc__ or ""
        )

        @functools.wraps(func)
        async def wrapper(self: Any, **kwargs: Any) -> Any:
            # Input validation
            if input_model:
                try:
                    validated_input = input_model(**kwargs)
                    # Convert to dict for passing to the function
                    kwargs = validated_input.model_dump()
                except PydanticValidationError as e:
                    field_errors = {str(err["loc"][0]): err["msg"] for err in e.errors()}
                    raise ValidationError(message="Input validation failed", field_errors=field_errors)

            # Call the actual function
            result = await func(self, **kwargs)
            return result

        # Attach tool definition to the wrapper
        setattr(wrapper, "_mcp_tool", tool_def)
        return cast(F, wrapper)

    return decorator


def resource(
    name: Optional[str] = None, description: str = "", params_model: Optional[Type[BaseModel]] = None
) -> Callable[[F], F]:
    """Decorator to mark a method as an MCP resource.

    Args:
        name: Resource name (defaults to method name)
        description: Resource description
        params_model: Pydantic model for params validation

    Returns:
        Decorated method
    """

    def decorator(func: F) -> F:
        resource_name = name or func.__name__

        # Extract schema from params_model or function signature
        if params_model:
            schema = _extract_schema_from_pydantic(params_model)
        else:
            schema = _extract_schema_from_function(func)

        # Create resource definition
        resource_def = ResourceDefinition(
            name=resource_name, func=func, schema=schema, description=description or func.__doc__ or ""
        )

        @functools.wraps(func)
        async def wrapper(self: Any, **kwargs: Any) -> Any:
            # Params validation
            if params_model:
                try:
                    validated_params = params_model(**kwargs)
                    # Convert to dict for passing to the function
                    kwargs = validated_params.model_dump()
                except PydanticValidationError as e:
                    field_errors = {str(err["loc"][0]): err["msg"] for err in e.errors()}
                    raise ValidationError(message="Parameter validation failed", field_errors=field_errors)

            # Call the actual function
            result = await func(self, **kwargs)
            return result

        # Attach resource definition to the wrapper
        setattr(wrapper, "_mcp_resource", resource_def)
        return cast(F, wrapper)

    return decorator
