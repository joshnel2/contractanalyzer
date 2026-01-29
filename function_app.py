"""
Moltbot Azure AI Bridge - Azure Functions
==========================================
Serverless bridge connecting Moltbot to Azure AI Foundry.
"""

import os
import json
import logging
import azure.functions as func
import requests

app = func.FunctionApp()


def get_azure_config():
    """Get Azure OpenAI configuration from environment."""
    key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_DEPLOYMENT_NAME")
    
    missing = []
    if not key:
        missing.append("AZURE_OPENAI_KEY")
    if not endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not deployment:
        missing.append("AZURE_DEPLOYMENT_NAME")
    
    if missing:
        return None, f"Missing: {', '.join(missing)}"
    
    return {"key": key, "endpoint": endpoint.rstrip("/"), "deployment": deployment}, None


def build_url(config):
    """Build Azure OpenAI API URL."""
    return f"{config['endpoint']}/openai/deployments/{config['deployment']}/chat/completions?api-version=2024-02-15-preview"


@app.route(route="", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    logging.info("Health check")
    return func.HttpResponse(
        json.dumps({"status": "Bridge Active"}),
        mimetype="application/json"
    )


@app.route(route="v1/chat/completions", methods=["POST"])
def chat_completions(req: func.HttpRequest) -> func.HttpResponse:
    """Main endpoint - bridges Moltbot to Azure OpenAI."""
    logging.info("Moltbot connecting...")
    
    config, error = get_azure_config()
    if error:
        logging.error(error)
        return func.HttpResponse(json.dumps({"error": error}), status_code=500, mimetype="application/json")
    
    try:
        body = req.get_json()
    except:
        return func.HttpResponse(json.dumps({"error": "Invalid JSON"}), status_code=400, mimetype="application/json")
    
    logging.info("Relaying to Azure...")
    
    url = build_url(config)
    headers = {"Content-Type": "application/json", "api-key": config["key"]}
    
    # Force non-streaming for Functions (streaming requires different approach)
    body["stream"] = False
    
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=120)
        return func.HttpResponse(resp.text, status_code=resp.status_code, mimetype="application/json")
    except requests.Timeout:
        return func.HttpResponse(json.dumps({"error": "Timeout"}), status_code=504, mimetype="application/json")
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")


@app.route(route="chat/completions", methods=["POST"])
def chat_completions_alt(req: func.HttpRequest) -> func.HttpResponse:
    """Alternative endpoint without /v1."""
    return chat_completions(req)
