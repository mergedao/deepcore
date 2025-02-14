import logging

import fastapi
from fastapi.responses import ORJSONResponse

from agents.common.response import RestResponse
from agents.exceptions import ErrorCode, CustomAgentException

logger = logging.getLogger(__name__)


async def exception_handler(request: fastapi.Request, exc):
    """"""
    if exc.__class__ in [CustomAgentException]:
        ret = RestResponse(code=exc.ErrorCode, msg=exc.message)
        return ORJSONResponse(
            ret.model_dump(),
            status_code=200
        )
    logger.error("Global Exception handler", exc_info=True)
    ret = RestResponse(code=ErrorCode.INTERNAL_ERROR, msg='The server is busy')
    return ORJSONResponse(
        ret.model_dump(),
        status_code=200
    )
