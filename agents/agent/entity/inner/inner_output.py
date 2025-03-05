from abc import ABC


class Output(ABC):

    def to_stream(self) -> str:
        pass