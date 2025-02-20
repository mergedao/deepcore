import json
import logging
from typing import List

from agents.models.entity import ToolInfo
from agents.utils.parser import extract_md_code

looger = logging.getLogger(__name__)

def convert_tool_into_openai_schema(api_tool: List[ToolInfo]):
    """Convert a list of ToolInfo objects into an OpenAI API schema."""
    tool_schemas = []
    for tool in api_tool:
        tool_schemas.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        })

    api_schema = {
        "type": "api",
        "functions": [
            schema for schema in tool_schemas
        ],
    }
    return json.dumps(api_schema, indent=4)


def parse_and_execute_json(json: str):
    """Parse and execute a JSON string."""
    try:
        json_string = extract_md_code(json)
        data = json.loads(json_string)
        return data
    except json.JSONDecodeError as e:
        looger.error(f"Invalid JSON: {e}")
    return None