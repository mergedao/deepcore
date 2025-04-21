import base64

import aiohttp
from starlette.responses import JSONResponse


def add_cors_headers(response: JSONResponse):
    # response.headers["Access-Control-Allow-Origin"] = "*"
    # response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    # response.headers["Access-Control-Allow-Headers"] = "*"
    return response


async def url_to_base64(image_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            response.raise_for_status()
            content = await response.read()
            encoded_data = base64.b64encode(content).decode("utf-8")
            return "data:image/png;base64," + encoded_data
