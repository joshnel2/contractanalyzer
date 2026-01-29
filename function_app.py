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


@app.route(route="", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    endpoint, api_key, deployment = get_ai_config()
    
    config_status = {
        "status": "Bridge Active",
        "endpoint_configured": bool(endpoint),
        "api_key_configured": bool(api_key),
        "deployment_configured": bool(deployment),
    }
    
    return func.HttpResponse(
        json.dumps(config_status), 
        mimetype="application/json"
    )


@app.route(route="v1/chat/completions", methods=["POST"])
def chat_completions(req: func.HttpRequest) -> func.HttpResponse:
    """
    OpenAI-compatible chat completions endpoint.
    Proxies requests to Azure AI Foundry.
    """
    logging.info("MOLT Bot request received")
    
    endpoint, api_key, deployment = get_ai_config()
    
    # Check configuration
    if not endpoint:
        logging.error("AZURE_OPENAI_ENDPOINT not configured")
        return func.HttpResponse(
            json.dumps({"error": {"message": "AZURE_OPENAI_ENDPOINT not configured", "type": "configuration_error"}}),
            status_code=500,
            mimetype="application/json"
        )
    
    if not api_key:
        logging.error("AZURE_OPENAI_API_KEY not configured")
        return func.HttpResponse(
            json.dumps({"error": {"message": "AZURE_OPENAI_API_KEY not configured", "type": "configuration_error"}}),
            status_code=500,
            mimetype="application/json"
        )
    
    if not deployment:
        logging.error("AZURE_OPENAI_DEPLOYMENT_NAME not configured")
        return func.HttpResponse(
            json.dumps({"error": {"message": "AZURE_OPENAI_DEPLOYMENT_NAME not configured", "type": "configuration_error"}}),
            status_code=500,
            mimetype="application/json"
        )
    
    # Parse request body
    try:
        body = req.get_json()
    except ValueError as e:
        logging.error(f"Invalid JSON in request: {e}")
        return func.HttpResponse(
            json.dumps({"error": {"message": "Invalid JSON in request body", "type": "invalid_request_error"}}),
            status_code=400,
            mimetype="application/json"
        )
    
    # Disable streaming for simplicity (MOLT Bot doesn't need it)
    body["stream"] = False
    
    # Remove model from body if present - we use deployment name
    body.pop("model", None)
    
    # Build Azure AI Foundry URL
    # Works for both Azure OpenAI resources and AI Foundry endpoints
    api_version = os.getenv("AZURE_AI_API_VERSION", "2024-08-01-preview")
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    
    logging.info(f"Proxying request to Azure AI Foundry: {endpoint}/openai/deployments/{deployment}/...")
    
    # Set headers - api-key header works for both Azure OpenAI and AI Foundry
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=180)
        
        logging.info(f"Azure AI Foundry response status: {resp.status_code}")
        
        if resp.status_code != 200:
            logging.error(f"Azure AI Foundry error: {resp.text}")
        
        return func.HttpResponse(
            resp.text,
            status_code=resp.status_code,
            mimetype="application/json"
        )
        
    except requests.exceptions.Timeout:
        logging.error("Request to Azure AI Foundry timed out")
        return func.HttpResponse(
            json.dumps({"error": {"message": "Request timed out", "type": "timeout_error"}}),
            status_code=504,
            mimetype="application/json"
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to Azure AI Foundry failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": {"message": f"Failed to connect to Azure AI Foundry: {str(e)}", "type": "connection_error"}}),
            status_code=502,
            mimetype="application/json"
        )


@app.route(route="chat/completions", methods=["POST"])
def chat_completions_alt(req: func.HttpRequest) -> func.HttpResponse:
    """Alternative endpoint without v1 prefix"""
    return chat_completions(req)


@app.route(route="v1/models", methods=["GET"])
def list_models(req: func.HttpRequest) -> func.HttpResponse:
    """
    OpenAI-compatible models list endpoint.
    Returns the configured deployment as available model.
    """
    _, _, deployment = get_ai_config()
    
    models_response = {
        "object": "list",
        "data": [
            {
                "id": deployment or "gpt-4o",
                "object": "model",
                "created": 1700000000,
                "owned_by": "azure"
            }
        ]
    }
    
    return func.HttpResponse(
        json.dumps(models_response),
        mimetype="application/json"
    )


@app.route(route="models", methods=["GET"])
def list_models_alt(req: func.HttpRequest) -> func.HttpResponse:
    """Alternative models endpoint without v1 prefix"""
    return list_models(req)
