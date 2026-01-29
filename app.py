"""
Moltbot Azure AI Bridge
=======================
A FastAPI bridge that connects Moltbot (formerly Clawdbot) to Azure AI Foundry.
Handles authentication translation and SSE streaming for real-time responses.
"""

import os
import logging
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

# Configure logging for Azure Log Stream
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Moltbot Azure AI Bridge",
    description="Bridge service connecting Moltbot to Azure AI Foundry",
    version="1.0.0"
)


def get_azure_config() -> dict:
    """
    Retrieve and validate Azure configuration from environment variables.
    
    Returns:
        dict: Azure configuration containing key, endpoint, and deployment name.
    
    Raises:
        HTTPException: If any required environment variable is missing.
    """
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME")
    
    missing_vars = []
    if not azure_key:
        missing_vars.append("AZURE_OPENAI_KEY")
    if not azure_endpoint:
        missing_vars.append("AZURE_OPENAI_ENDPOINT")
    if not deployment_name:
        missing_vars.append("AZURE_DEPLOYMENT_NAME")
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    # Remove trailing slash from endpoint if present
    azure_endpoint = azure_endpoint.rstrip("/")
    
    return {
        "key": azure_key,
        "endpoint": azure_endpoint,
        "deployment_name": deployment_name
    }


def build_azure_url(config: dict) -> str:
    """
    Construct the Azure OpenAI API URL.
    
    Args:
        config: Azure configuration dictionary.
    
    Returns:
        str: Complete Azure OpenAI API URL.
    """
    return (
        f"{config['endpoint']}/openai/deployments/{config['deployment_name']}"
        f"/chat/completions?api-version=2024-02-15-preview"
    )


async def stream_azure_response(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    body: dict
) -> AsyncGenerator[bytes, None]:
    """
    Asynchronous generator that streams SSE responses from Azure OpenAI.
    
    Args:
        client: The httpx async client.
        url: Azure OpenAI API URL.
        headers: Request headers with Azure API key.
        body: Request body containing the chat completion parameters.
    
    Yields:
        bytes: Chunks of the SSE response.
    """
    try:
        async with client.stream(
            "POST",
            url,
            headers=headers,
            json=body,
            timeout=120.0
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                logger.error(f"Azure API error: {response.status_code} - {error_body.decode()}")
                yield f"data: {{'error': 'Azure API returned status {response.status_code}'}}\n\n".encode()
                return
            
            async for chunk in response.aiter_bytes():
                yield chunk
                
    except httpx.TimeoutException:
        logger.error("Request to Azure API timed out")
        yield b"data: {'error': 'Request timed out'}\n\n"
    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        yield f"data: {{'error': 'Request failed: {str(e)}'}}\n\n".encode()


@app.get("/")
async def health_check():
    """
    Health check endpoint for Azure Web App deployment verification.
    
    Returns:
        dict: Status message indicating the bridge is active.
    """
    logger.info("Health check requested")
    return {"status": "Bridge Active"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    Main endpoint that bridges Moltbot requests to Azure AI Foundry.
    
    Intercepts incoming requests, replaces the Authorization header with
    Azure's api-key format, and streams the response back to Moltbot.
    
    Args:
        request: The incoming FastAPI request object.
    
    Returns:
        StreamingResponse or JSONResponse: The Azure API response.
    """
    logger.info("Moltbot connecting...")
    
    try:
        # Get and validate Azure configuration
        config = get_azure_config()
        
        # Parse the request body
        try:
            body = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse request body: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON in request body")
        
        # Build Azure API URL
        azure_url = build_azure_url(config)
        logger.info("Relaying to Azure...")
        
        # Prepare headers for Azure (strip Authorization, use api-key)
        azure_headers = {
            "Content-Type": "application/json",
            "api-key": config["key"]
        }
        
        # Check if streaming is requested
        is_streaming = body.get("stream", False)
        
        async with httpx.AsyncClient() as client:
            if is_streaming:
                # Return streaming response for real-time typing effect
                return StreamingResponse(
                    stream_azure_response(client, azure_url, azure_headers, body),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no"
                    }
                )
            else:
                # Non-streaming request
                try:
                    response = await client.post(
                        azure_url,
                        headers=azure_headers,
                        json=body,
                        timeout=120.0
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Azure API error: {response.status_code} - {response.text}")
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Azure API error: {response.text}"
                        )
                    
                    return JSONResponse(
                        content=response.json(),
                        status_code=200
                    )
                    
                except httpx.TimeoutException:
                    logger.error("Request to Azure API timed out")
                    raise HTTPException(status_code=504, detail="Request to Azure API timed out")
                except httpx.RequestError as e:
                    logger.error(f"Request error: {str(e)}")
                    raise HTTPException(status_code=502, detail=f"Failed to connect to Azure API: {str(e)}")
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/chat/completions")
async def chat_completions_without_v1(request: Request):
    """
    Alternative endpoint without /v1 prefix for flexibility.
    Redirects to the main chat completions handler.
    """
    return await chat_completions(request)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
