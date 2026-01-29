import os
import json
import logging
import azure.functions as func
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(json.dumps({"status": "Bridge Active"}), mimetype="application/json")


@app.route(route="v1/chat/completions", methods=["POST"])
def chat_completions(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Moltbot connecting...")
    
    key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    deployment = os.getenv("AZURE_DEPLOYMENT_NAME")
    
    if not all([key, endpoint, deployment]):
        return func.HttpResponse(json.dumps({"error": "Missing env vars"}), status_code=500, mimetype="application/json")
    
    body = req.get_json()
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-15-preview"
    headers = {"Content-Type": "application/json", "api-key": key}
    
    body["stream"] = False
    
    logging.info("Relaying to Azure...")
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    return func.HttpResponse(resp.text, status_code=resp.status_code, mimetype="application/json")


@app.route(route="chat/completions", methods=["POST"])
def chat_completions_alt(req: func.HttpRequest) -> func.HttpResponse:
    return chat_completions(req)
