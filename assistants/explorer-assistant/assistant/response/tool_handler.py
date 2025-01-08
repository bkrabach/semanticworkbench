import json
import logging

logger = logging.getLogger(__name__)


def parse_tool_response(content: str):
    """Parse the assistant's response to check for tool usage."""
    try:
        start = content.find("{")
        while start != -1:
            brace_count = 0
            in_string = False
            escape = False
            for i in range(start, len(content)):
                char = content[i]
                if char == '"' and not escape:
                    in_string = not in_string
                elif char == "\\" and in_string:
                    # Handle escaped characters inside strings
                    escape = not escape
                elif not in_string:
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            # Found the complete JSON object
                            json_str = content[start : i + 1]
                            try:
                                action = json.loads(json_str)
                                # Extract tool_name and arguments
                                tool_name = action.get("tool_name") or action.get("action")
                                arguments = action.get("arguments", {})
                                if tool_name:
                                    # Return the action and the remaining content
                                    remaining_content = content[i + 1 :].strip()
                                    return {"tool_name": tool_name, "arguments": arguments}, remaining_content
                            except json.JSONDecodeError:
                                # If JSON decoding fails, continue searching
                                pass
                            break
                # Reset escape flag if necessary
                if char != "\\" and escape:
                    escape = False
            else:
                # Reached the end without finding a complete JSON object
                break
            # Look for the next '{' in the content
            start = content.find("{", i + 1)
    except Exception as e:
        logger.exception(f"Error parsing tool response: {e}")
    return None, content
