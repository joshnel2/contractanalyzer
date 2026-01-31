import os
import json
import logging
import azure.functions as func
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def get_ai_config():
    """
    Get Azure AI Foundry configuration from environment variables.
    
    Expected environment variables:
    - AZURE_OPENAI_ENDPOINT: Your Azure OpenAI / AI Foundry endpoint
    - AZURE_OPENAI_API_KEY: Your API key
    - AZURE_OPENAI_DEPLOYMENT_NAME: Your model deployment name (e.g., gpt-4o, gpt-4o-mini)
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    
    # Clean up endpoint
    endpoint = endpoint.rstrip("/")
    
    return endpoint, api_key, deployment


def get_api_key_from_request(req: func.HttpRequest) -> str:
    """
    Extract API key from request headers.
    Supports both OpenAI style (Authorization: Bearer) and Azure style (api-key header).
    Also supports X-API-Key header commonly used by proxies.
    """
    # Check Authorization header first (OpenAI style)
    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    # Check api-key header (Azure style)
    api_key = req.headers.get("api-key", "")
    if api_key:
        return api_key
    
    # Check X-API-Key header (common proxy style)
    x_api_key = req.headers.get("X-API-Key", "")
    if x_api_key:
        return x_api_key
    
    return ""


def create_error_response(message: str, error_type: str, status_code: int) -> func.HttpResponse:
    """Create a standardized error response in OpenAI format."""
    error_body = {
        "error": {
            "message": message,
            "type": error_type,
            "param": None,
            "code": None
        }
    }
    return func.HttpResponse(
        json.dumps(error_body),
        status_code=status_code,
        mimetype="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, api-key, X-API-Key"
        }
    )


@app.route(route="", methods=["GET", "OPTIONS"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    # Handle CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(
            "",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, api-key, X-API-Key"
            }
        )
    
    endpoint, api_key, deployment = get_ai_config()
    
    config_status = {
        "status": "healthy",
        "service": "Azure AI Foundry Bridge for Clawdbot",
        "version": "1.0.0",
        "endpoint_configured": bool(endpoint),
        "api_key_configured": bool(api_key),
        "deployment_configured": bool(deployment),
        "deployment_name": deployment if deployment else None
    }
    
    return func.HttpResponse(
        json.dumps(config_status), 
        mimetype="application/json",
        headers={
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.route(route="v1/chat/completions", methods=["POST", "OPTIONS"])
def chat_completions(req: func.HttpRequest) -> func.HttpResponse:
    """
    OpenAI-compatible chat completions endpoint.
    Proxies requests to Azure AI Foundry.
    
    This endpoint is compatible with Clawdbot's OpenAI provider format.
    Configure Clawdbot with:
    - baseUrl: https://your-function-app.azurewebsites.net/api/v1
    - apiKey: any-value (authentication handled by the bridge)
    - api: openai-completions
    """
    # Handle CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(
            "",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, api-key, X-API-Key"
            }
        )
    
    logging.info("Clawdbot chat completions request received")
    
    endpoint, api_key, deployment = get_ai_config()
    
    # Check configuration
    if not endpoint:
        logging.error("AZURE_OPENAI_ENDPOINT not configured")
        return create_error_response(
            "Server not configured: AZURE_OPENAI_ENDPOINT missing",
            "configuration_error",
            500
        )
    
    if not api_key:
        logging.error("AZURE_OPENAI_API_KEY not configured")
        return create_error_response(
            "Server not configured: AZURE_OPENAI_API_KEY missing",
            "configuration_error",
            500
        )
    
    if not deployment:
        logging.error("AZURE_OPENAI_DEPLOYMENT_NAME not configured")
        return create_error_response(
            "Server not configured: AZURE_OPENAI_DEPLOYMENT_NAME missing",
            "configuration_error",
            500
        )
    
    # Parse request body
    try:
        body = req.get_json()
    except ValueError as e:
        logging.error(f"Invalid JSON in request: {e}")
        return create_error_response(
            "Invalid JSON in request body",
            "invalid_request_error",
            400
        )
    
    # Log the incoming request model for debugging
    incoming_model = body.get("model", "not specified")
    logging.info(f"Incoming model request: {incoming_model}")
    
    # Disable streaming - Azure Functions HTTP doesn't support true streaming
    # Moltbot will fall back to non-streaming mode
    body["stream"] = False
    
    # Remove model from body - we use deployment name instead
    # The deployment name IS the model in Azure OpenAI
    body.pop("model", None)
    
    # Build Azure AI Foundry URL
    api_version = os.getenv("AZURE_AI_API_VERSION", "2024-08-01-preview")
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    
    logging.info(f"Proxying to Azure AI Foundry deployment: {deployment}")
    
    # Set headers for Azure AI Foundry
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=300)
        
        logging.info(f"Azure AI Foundry response status: {resp.status_code}")
        
        if resp.status_code != 200:
            logging.error(f"Azure AI Foundry error: {resp.text}")
            # Try to forward the error as-is if it's valid JSON
            try:
                error_json = resp.json()
                return func.HttpResponse(
                    json.dumps(error_json),
                    status_code=resp.status_code,
                    mimetype="application/json",
                    headers={"Access-Control-Allow-Origin": "*"}
                )
            except:
                return create_error_response(
                    f"Azure AI Foundry error: {resp.text}",
                    "api_error",
                    resp.status_code
                )
        
        # Parse successful response
        try:
            response_json = resp.json()
            
            # Add/override the model field to match what was requested
            # This helps Moltbot track which model was used
            if "model" not in response_json or not response_json["model"]:
                response_json["model"] = deployment
            
            return func.HttpResponse(
                json.dumps(response_json),
                status_code=200,
                mimetype="application/json",
                headers={"Access-Control-Allow-Origin": "*"}
            )
        except:
            # If response isn't JSON, return as-is
            return func.HttpResponse(
                resp.text,
                status_code=resp.status_code,
                mimetype="application/json",
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
    except requests.exceptions.Timeout:
        logging.error("Request to Azure AI Foundry timed out")
        return create_error_response(
            "Request to Azure AI Foundry timed out after 300 seconds",
            "timeout_error",
            504
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to Azure AI Foundry failed: {e}")
        return create_error_response(
            f"Failed to connect to Azure AI Foundry: {str(e)}",
            "connection_error",
            502
        )


@app.route(route="chat/completions", methods=["POST", "OPTIONS"])
def chat_completions_alt(req: func.HttpRequest) -> func.HttpResponse:
    """Alternative endpoint without v1 prefix for compatibility"""
    return chat_completions(req)


@app.route(route="v1/models", methods=["GET", "OPTIONS"])
def list_models(req: func.HttpRequest) -> func.HttpResponse:
    """
    OpenAI-compatible models list endpoint.
    Returns the configured deployment as an available model.
    
    Clawdbot uses this to discover available models.
    """
    # Handle CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(
            "",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, api-key, X-API-Key"
            }
        )
    
    _, _, deployment = get_ai_config()
    
    # Return the deployment as an available model
    model_id = deployment or "gpt-4o"
    
    models_response = {
        "object": "list",
        "data": [
            {
                "id": model_id,
                "object": "model",
                "created": 1700000000,
                "owned_by": "azure-ai-foundry",
                "permission": [],
                "root": model_id,
                "parent": None
            }
        ]
    }
    
    return func.HttpResponse(
        json.dumps(models_response),
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )


@app.route(route="models", methods=["GET", "OPTIONS"])
def list_models_alt(req: func.HttpRequest) -> func.HttpResponse:
    """Alternative models endpoint without v1 prefix"""
    return list_models(req)


@app.route(route="v1/completions", methods=["POST", "OPTIONS"])
def completions(req: func.HttpRequest) -> func.HttpResponse:
    """
    Legacy completions endpoint (non-chat).
    Most modern models don't support this, but included for completeness.
    Redirects to chat completions with a system message wrapper.
    """
    # Handle CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(
            "",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, api-key, X-API-Key"
            }
        )
    
    # Most Azure OpenAI deployments only support chat completions
    # Return a helpful error
    return create_error_response(
        "This endpoint only supports chat completions. Use /v1/chat/completions instead.",
        "invalid_request_error",
        400
    )
