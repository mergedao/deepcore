import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from agents.common.response import RestResponse
from agents.middleware.auth_middleware import get_current_user, get_optional_current_user
from agents.models.db import get_db
from agents.services import open_service
from agents.exceptions import CustomAgentException, ErrorCode
from agents.common.error_messages import get_error_message

router = APIRouter()
logger = logging.getLogger(__name__)

class OpenAPIExample(BaseModel):
    """Code examples for open platform API integration"""
    curl: str
    python: str
    golang: str
    nodejs: str

@router.get("/credentials", summary="Get Open Platform API Credentials")
async def get_api_credentials(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve or generate open platform API credentials.
    
    Returns:
        - access_key: The API access key
        - secret_key: The API secret key
    """
    try:
        result = await open_service.get_or_create_credentials(user, session)
        return RestResponse(data=result)
    except CustomAgentException as e:
        logger.error(f"Error getting open platform credentials: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting open platform credentials: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )

@router.get("/example", summary="Get API Usage Examples")
async def get_example(
    user: Optional[dict] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve code examples for API integration in multiple languages.
    
    If authenticated, examples will include actual credentials.
    If not authenticated, examples will use placeholder values.
    
    Returns:
        - curl: Shell command example
        - python: Python code example
        - golang: Go code example
        - nodejs: Node.js code example
    """
    # Retrieve credentials for authenticated users
    credentials = None
    if user:
        try:
            credentials = await open_service.get_or_create_credentials(user, session)
        except Exception:
            logger.warning("Failed to get user credentials for examples", exc_info=True)
    
    ak = credentials["access_key"] if credentials else "your_access_key"
    sk = credentials["secret_key"] if credentials else "your_secret_key"
    
    curl_example = f'''# Note: Signature is valid for 5 minutes from timestamp
curl -X POST "https://api.example.com/api/agents/your-agent-id/dialogue" \\
    -H "X-Access-Key: {ak}" \\
    -H "X-Timestamp: $(date +%s)" \\
    -H "X-Signature: your_signature" \\
    -H "Content-Type: application/json" \\
    -d '{{"message": "Hello, Agent!"}}'
'''

    python_example = f'''import time
import hmac
import hashlib
import requests

def generate_signature(access_key: str, secret_key: str, timestamp: str) -> str:
    """
    Generate HMAC-SHA256 signature for API request
    Note: Signature is valid for 5 minutes from timestamp
    """
    message = f"{{access_key}}{{timestamp}}"
    return hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

# API credentials
access_key = "{ak}"
secret_key = "{sk}"  # Important: Keep this secure

# Generate request signature (valid for 5 minutes)
timestamp = str(int(time.time()))  # Current Unix timestamp
signature = generate_signature(access_key, secret_key, timestamp)

# Request headers
headers = {{
    "X-Access-Key": access_key,
    "X-Timestamp": timestamp,
    "X-Signature": signature
}}

# Make API request
response = requests.post(
    "https://api.example.com/api/agents/your-agent-id/dialogue",
    headers=headers,
    json={{"message": "Hello, Agent!"}}
)
'''

    golang_example = f'''package main

import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "fmt"
    "time"
)

// generateSignature creates HMAC-SHA256 signature for API request
// Note: Signature is valid for 5 minutes from timestamp
func generateSignature(accessKey, secretKey, timestamp string) string {{
    message := accessKey + timestamp
    h := hmac.New(sha256.New, []byte(secretKey))
    h.Write([]byte(message))
    return hex.EncodeToString(h.Sum(nil))
}}

func main() {{
    // API credentials
    accessKey := "{ak}"
    secretKey := "{sk}"  // Important: Keep this secure
    
    // Generate timestamp (signature valid for 5 minutes)
    timestamp := fmt.Sprintf("%d", time.Now().Unix())
    signature := generateSignature(accessKey, secretKey, timestamp)
    
    // Request headers
    fmt.Printf("X-Access-Key: %s\\n", accessKey)
    fmt.Printf("X-Timestamp: %s\\n", timestamp)
    fmt.Printf("X-Signature: %s\\n", signature)
}}
'''

    nodejs_example = f'''const crypto = require('crypto');

// Generate HMAC-SHA256 signature for API request
// Note: Signature is valid for 5 minutes from timestamp
function generateSignature(accessKey, secretKey, timestamp) {{
    const message = `${{accessKey}}${{timestamp}}`;
    return crypto
        .createHmac('sha256', secretKey)
        .update(message)
        .digest('hex');
}}

// API credentials
const accessKey = '{ak}';
const secretKey = '{sk}';  // Important: Keep this secure

// Generate timestamp (signature valid for 5 minutes)
const timestamp = Math.floor(Date.now() / 1000).toString();
const signature = generateSignature(accessKey, secretKey, timestamp);

// Request headers
const headers = {{
    'X-Access-Key': accessKey,
    'X-Timestamp': timestamp,
    'X-Signature': signature
}};

// Use these headers with your preferred HTTP client
// Remember: The signature will expire 5 minutes after the timestamp
'''

    return RestResponse(data=OpenAPIExample(
        curl=curl_example,
        python=python_example,
        golang=golang_example,
        nodejs=nodejs_example
    )) 
