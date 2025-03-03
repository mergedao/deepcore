import logging
from typing import Dict, Any, AsyncGenerator, Union
from typing import Optional

import aiohttp
from aiohttp import ClientTimeout
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class AsyncHttpClient:
    """Asynchronous HTTP client that supports both streaming and non-streaming requests"""
    
    def __init__(
        self,
        base_url: str = "",
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 60,
        max_retries: int = 3
    ):
        """
        Initialize HTTP client
        
        Args:
            base_url: Base URL for API requests
            headers: Request headers
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.headers = headers or {}
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def init_session(self):
        """Initialize aiohttp session"""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=self.timeout
            )

    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_full_url(self, base_url: str, path: str) -> str:
        """Get complete URL by combining base URL and path"""
        if path.startswith(('http://', 'https://')):
            return path
        return f"{base_url}/{path.lstrip('/')}"

    def _apply_auth_config(self, url: str, headers: dict, auth_config: Optional[Dict]) -> tuple[str, dict]:
        """Apply authentication configuration to request"""
        if not auth_config:
            return url, headers
        
        if auth_config.get('location') == 'header':
            headers[auth_config['key']] = auth_config['value']
        elif auth_config.get('location') == 'param':
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}{auth_config['key']}={auth_config['value']}"
        
        return url, headers

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def request(
        self,
        method: str,
        base_url: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        auth_config: Optional[Dict] = None,
        stream: bool = False
    ) -> Union[Dict, str, AsyncGenerator[str, None]]:
        """
        Send HTTP request
        
        Args:
            method: HTTP method
            path: Request path
            params: URL parameters
            json_data: JSON request body
            data: Form data
            headers: Additional request headers
            auth_config: Authentication configuration in format {"location": "header"/"param", "key": "key_name", "value": "key_value"}
            stream: Whether to use streaming response
            
        Returns:
            If stream=False: Response data as dict or string
            If stream=True: Async generator for streaming response
        """
        await self.init_session()
        if not self._session:
            raise RuntimeError("Session not initialized")

        merged_headers = {**self.headers}
        if headers:
            merged_headers.update(headers)

        url = self._get_full_url(base_url, path)
        url, merged_headers = self._apply_auth_config(url, merged_headers, auth_config)
        logger.info(f"Sending HTTP request: {method} {url}")
        try:
            async with self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                data=data,
                headers=merged_headers
            ) as response:
                if stream:
                    async for data in self._handle_stream_response(response):
                        yield data
                else:
                    yield await self._handle_normal_response(response)
                    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {str(e)}", exc_info=True)
            raise

    async def _handle_normal_response(self, response: aiohttp.ClientResponse) -> Union[Dict, str]:
        """Handle normal (non-streaming) response"""
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return await response.json()
        return await response.text()

    async def _handle_stream_response(self, response: aiohttp.ClientResponse) -> AsyncGenerator[str, None]:
        """Handle streaming response"""
        async for chunk in response.content.iter_any():
            yield chunk.decode('utf-8')

# Create a default client instance
async_client = AsyncHttpClient()