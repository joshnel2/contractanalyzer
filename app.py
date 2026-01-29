"""
Moltbot Azure AI Bridge
"""
import os
import json
import logging
import requests
from flask import Flask, request, Response, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
application = app  # Azure alias


@app.route("/")
def health():
    return jsonify({"status": "Bridge Active"})


@app.route("/v1/chat/completions", methods=["POST"])
def chat():
    logger.info("Moltbot connecting...")
    
    key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    deployment = os.getenv("AZURE_DEPLOYMENT_NAME")
    
    if not all([key, endpoint, deployment]):
        return jsonify({"error": "Missing env vars"}), 500
    
    body = request.get_json()
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-15-preview"
    headers = {"Content-Type": "application/json", "api-key": key}
    
    logger.info("Relaying to Azure...")
    
    if body.get("stream"):
        def generate():
            with requests.post(url, headers=headers, json=body, stream=True, timeout=120) as r:
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk
        return Response(generate(), mimetype="text/event-stream")
    else:
        r = requests.post(url, headers=headers, json=body, timeout=120)
        return Response(r.content, status=r.status_code, mimetype="application/json")


@app.route("/chat/completions", methods=["POST"])
def chat_alt():
    return chat()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
