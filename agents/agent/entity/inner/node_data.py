"""NodeMessage Class"""
from typing import Optional


class NodeMessage:
    message: str = ""
    tool_name: str = ""

    def __init__(self, message: str, tool_name: Optional[str] = None):
        """Constructor for the class"""
        self.message = message
        self.tool_name = tool_name

    def to_dict(self):
        data = {}
        for key, value in self.__dict__.items():
            if value:
                data[key] = value
        return data
