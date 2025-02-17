from typing import Optional
from agents.protocol.schemas import AuthConfig

def apply_auth_config(url: str, headers: dict, auth_config: Optional[dict]) -> tuple[str, dict]:
    """Apply authentication configuration to request"""
    if not auth_config:
        return url, headers
    
    if auth_config['location'] == 'header':
        headers[auth_config['key']] = auth_config['value']
    elif auth_config['location'] == 'param':
        separator = '&' if '?' in url else '?'
        url = f"{url}{separator}{auth_config['key']}={auth_config['value']}"
    
    return url, headers

async def make_request(url: str, method: str, headers: dict = None, auth_config: Optional[dict] = None):
    """Make HTTP request with authentication"""
    headers = headers or {}
    url, headers = apply_auth_config(url, headers, auth_config)
    # ... rest of the request logic ... 