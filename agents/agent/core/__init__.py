import uuid
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Union,
)

from pydantic import BaseModel


def exists(val):
    return val is not None


def concat_strings(string_list: List[str]) -> str:
    if not isinstance(string_list, list):
        raise TypeError("Input must be a list of strings.")

    if not all(isinstance(string, str) for string in string_list):
        raise TypeError("All elements in the list must be strings.")

    try:
        return "".join(string_list)
    except TypeError:
        raise TypeError("All elements in the list must be strings.")


# Utils
# Custom stopping condition
def stop_when_repeats(response: str) -> bool:
    # Stop if the word stop appears in the response
    return "stop" in response.lower()


# Parse done token
def parse_done_token(response: str) -> bool:
    """Parse the response to see if the done token is present"""
    return "<DONE>" in response


# Agent ID generator
def agent_id():
    """Generate an agent id"""
    return uuid.uuid4().hex


# Agent output types
# agent_output_type = Union[BaseModel, dict, str]
agent_output_type = Literal[
    "string", "str", "list", "json", "dict", "yaml", "json_schema"
]
ToolUsageType = Union[BaseModel, Dict[str, Any]]


class BaseDeepcoreAgent:
    pass
