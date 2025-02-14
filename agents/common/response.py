from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar('T')


class RestResponse(BaseModel, Generic[T]):
    code: int = 0
    msg: str = "ok"
    data: T = None
