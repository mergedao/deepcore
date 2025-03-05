import logging
from typing import Optional

from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agents.common.error_messages import get_error_message
from agents.common.response import RestResponse
from agents.exceptions import CustomAgentException, ErrorCode
from agents.middleware.auth_middleware import get_current_user, get_optional_current_user
from agents.models.db import get_db
from agents.services import open_service

router = APIRouter()
logger = logging.getLogger(__name__)

class OpenAPIExample(BaseModel):
    """Code examples for open platform API integration"""
    curl: str
    python: str
    golang: str
    nodejs: str

class TokenRequest(BaseModel):
    """Request model for token generation"""
    access_key: str
    secret_key: str

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
    
    # Signature authentication example
    curl_signature_example = f'''# Method 1: Using signature authentication (valid for 5 minutes)
curl -X POST "https://api.example.com/api/agents/your-agent-id/dialogue" \\
    -H "X-Access-Key: {ak}" \\
    -H "X-Timestamp: $(date +%s)" \\
    -H "X-Signature: your_signature" \\
    -H "Content-Type: application/json" \\
    -d '{{"message": "Hello, Agent!"}}'
'''

    # Token authentication example
    curl_token_example = f'''# Method 2: Using token authentication (simpler, permanent)
# Step 1: Get token (only need to do this once, token is permanent)
curl -X POST "https://api.example.com/api/open/token" \\
    -H "Content-Type: application/json" \\
    -d '{{"access_key": "{ak}", "secret_key": "{sk}"}}'

# If you need to reset token (optional)
curl -X POST "https://api.example.com/api/open/token/reset" \\
    -H "X-API-Token: your_token" \\
    -H "Content-Type: application/json"

# Step 2: Use token to call API
curl -X POST "https://api.example.com/api/agents/your-agent-id/dialogue" \\
    -H "X-API-Token: your_token" \\
    -H "Content-Type: application/json" \\
    -d '{{"message": "Hello, Agent!"}}'
'''

    # Merge both authentication methods example
    curl_example = curl_signature_example + "\n" + curl_token_example

    # Python example - Signature authentication
    python_signature_example = f'''# Method 1: Using signature authentication
import time
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

    # Python example - Token authentication
    python_token_example = f'''# Method 2: Using Token authentication (simpler, permanent)
import requests

# Step 1: Get token (only need to do this once, token is permanent)
token_response = requests.post(
    "https://api.example.com/api/open/token",
    json={{
        "access_key": "{ak}",
        "secret_key": "{sk}"
    }}
)
token_data = token_response.json()["data"]
token = token_data["token"]

# If you need to reset token (optional)
# reset_response = requests.post(
#     "https://api.example.com/api/open/token/reset",
#     headers={{"X-API-Token": token}}
# )
# token_data = reset_response.json()["data"]
# token = token_data["token"]

# Step 2: Use token to call API
headers = {{
    "X-API-Token": token
}}

response = requests.post(
    "https://api.example.com/api/agents/your-agent-id/dialogue",
    headers=headers,
    json={{"message": "Hello, Agent!"}}
)
'''

    # Merge both authentication methods example
    python_example = python_signature_example + "\n\n" + python_token_example

    # Go example - Signature authentication
    golang_signature_example = f'''// Method 1: Using signature authentication
package main

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

    # Go example - Token authentication
    golang_token_example = f'''// Method 2: Using Token authentication (simpler, permanent)
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io/ioutil"
    "net/http"
)

func main() {{
    // Step 1: Get token (only need to do this once, token is permanent)
    tokenURL := "https://api.example.com/api/open/token"
    tokenReqBody := []byte(`{{"access_key": "{ak}", "secret_key": "{sk}"}}`)
    
    tokenReq, _ := http.NewRequest("POST", tokenURL, bytes.NewBuffer(tokenReqBody))
    tokenReq.Header.Set("Content-Type", "application/json")
    
    client := &http.Client{{}}
    tokenResp, err := client.Do(tokenReq)
    if err != nil {{
        fmt.Println("Error getting token:", err)
        return
    }}
    defer tokenResp.Body.Close()
    
    tokenRespBody, _ := ioutil.ReadAll(tokenResp.Body)
    fmt.Println("Token response:", string(tokenRespBody))
    
    // Parse token (simplified example, in real applications you should properly parse JSON)
    // Assume we've already extracted the token from the response
    token := "your_token_from_response"
    
    // If you need to reset token (optional)
    /*
    resetURL := "https://api.example.com/api/open/token/reset"
    resetReq, _ := http.NewRequest("POST", resetURL, nil)
    resetReq.Header.Set("Content-Type", "application/json")
    resetReq.Header.Set("X-API-Token", token)
    
    resetResp, err := client.Do(resetReq)
    if err != nil {{
        fmt.Println("Error resetting token:", err)
        return
    }}
    defer resetResp.Body.Close()
    
    resetRespBody, _ := ioutil.ReadAll(resetResp.Body)
    fmt.Println("Reset token response:", string(resetRespBody))
    
    // Parse new token
    // token = "your_new_token_from_response"
    */
    
    // Step 2: Use token to call API
    apiURL := "https://api.example.com/api/agents/your-agent-id/dialogue"
    apiReqBody := []byte(`{{"message": "Hello, Agent!"}}`)
    
    apiReq, _ := http.NewRequest("POST", apiURL, bytes.NewBuffer(apiReqBody))
    apiReq.Header.Set("Content-Type", "application/json")
    apiReq.Header.Set("X-API-Token", token)
    
    apiResp, err := client.Do(apiReq)
    if err != nil {{
        fmt.Println("Error calling API:", err)
        return
    }}
    defer apiResp.Body.Close()
    
    apiRespBody, _ := ioutil.ReadAll(apiResp.Body)
    fmt.Println("API response:", string(apiRespBody))
}}
'''

    golang_example = golang_signature_example + "\n\n" + golang_token_example

    # Node.js example - Signature authentication
    nodejs_signature_example = f'''// Method 1: Using signature authentication
const crypto = require('crypto');

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

    # Node.js example - Token authentication
    nodejs_token_example = f'''// Method 2: Using Token authentication (simpler, permanent)
const fetch = require('node-fetch');

// Step 1: Get token (only need to do this once, token is permanent)
async function getToken() {{
    const tokenResponse = await fetch('https://api.example.com/api/open/token', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json'
        }},
        body: JSON.stringify({{
            access_key: '{ak}',
            secret_key: '{sk}'
        }})
    }});
    
    const tokenData = await tokenResponse.json();
    return tokenData.data.token;
}}

// If you need to reset token (optional)
async function resetToken(token) {{
    const resetResponse = await fetch('https://api.example.com/api/open/token/reset', {{
        method: 'POST',
        headers: {{
            'X-API-Token': token
        }}
    }});
    
    const resetData = await resetResponse.json();
    return resetData.data.token;
}}

// Step 2: Use token to call API
async function callAPI() {{
    const token = await getToken();
    
    // If you need to reset token (optional)
    // const newToken = await resetToken(token);
    
    const apiResponse = await fetch('https://api.example.com/api/agents/your-agent-id/dialogue', {{
        method: 'POST',
        headers: {{
            'X-API-Token': token
        }},
        body: JSON.stringify({{
            message: 'Hello, Agent!'
        }})
    }});
    
    const apiData = await apiResponse.json();
    console.log(apiData);
}}

callAPI().catch(console.error);
'''

    # Merge both authentication methods example
    nodejs_example = nodejs_signature_example + "\n\n" + nodejs_token_example

    return RestResponse(data=OpenAPIExample(
        curl=curl_example,
        python=python_example,
        golang=golang_example,
        nodejs=nodejs_example
    )) 

@router.post("/token", summary="Get Open Platform API Token")
async def get_api_token(
    request: TokenRequest = Body(...),
    session: AsyncSession = Depends(get_db)
):
    """
    Get Open Platform API Token.
    
    This endpoint allows users to obtain an API token using their access_key and secret_key,
    which can be used for authentication via the X-API-Token header.
    
    If the user already has a stored token, it will be returned;
    otherwise, a new token will be generated and stored.
    
    Returns:
        - token: Encrypted token
        - expires_at: Token expiration timestamp
    """
    try:
        # Verify access_key and secret_key
        credentials = await open_service.get_credentials(request.access_key, session)
        if not credentials or credentials.secret_key != request.secret_key:
            return RestResponse(
                code=ErrorCode.INVALID_CREDENTIALS,
                msg="Invalid access key or secret key"
            )
        
        # Check if there is a stored token
        stored_token = await open_service.get_token(request.access_key, session)
        
        if stored_token:
            # Verify the stored token
            payload = open_service.verify_token(stored_token)
            if payload:
                # If the token is valid, return it directly
                return RestResponse(data={
                    "token": stored_token,
                    "expires_at": payload.get("exp"),
                    "token_type": "Bearer"
                })
        
        # If there is no token or the token is invalid, generate a new token
        token_data = await open_service.generate_token(request.access_key, session)
        return RestResponse(data=token_data)
    except CustomAgentException as e:
        logger.error(f"Error generating open platform token: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error generating open platform token: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )

@router.post("/token/reset", summary="Reset Open Platform API Token")
async def reset_api_token(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Reset Open Platform API Token.
    
    This endpoint allows users to reset their Open Platform API Token. After reset, the old token will be invalidated,
    and the new token must be used for authentication.
    
    Returns:
        - token: New encrypted token
        - expires_at: Token expiration timestamp
    """
    try:
        # Get the user's access_key
        credentials = await open_service.get_or_create_credentials(user, session)
        access_key = credentials["access_key"]
        
        # Reset token
        token_data = await open_service.reset_token(access_key, session)
        return RestResponse(data=token_data)
    except CustomAgentException as e:
        logger.error(f"Error resetting open platform token: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error resetting open platform token: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        ) 