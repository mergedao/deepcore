class ToolOutput:
    data: str = None

    def __init__(self, data: str):
        self.data = data

    def get_output(self) -> str:
        return self.data
