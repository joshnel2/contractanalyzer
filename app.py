"""
Moltbot Azure AI Bridge
=======================
A Flask bridge that connects Moltbot (formerly Clawdbot) to Azure AI Foundry.
"""

import os
import logging
import requests
from flask import Flask, request, Response, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


def get_azure_config():
    """Get and validate Azure configuration from environment variables."""
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME")
    
    missing = []
    if not azure_key:
        missing.append("AZURE_OPENAI_KEY")
    if not azure_endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not deployment_name:
        missing.append("AZURE_DEPLOYMENT_NAME")
    
    if missing:
        return None, f"Missing environment variables: {', '.join(missing)}"
    
    return {
        "key": azure_key,
        "endpoint": azure_endpoint.rstrip("/"),
        "deployment_name": deployment_name
    }, None


def build_azure_url(config):
    """Build the Azure OpenAI API URL."""
    return (
        f"{config['endpoint']}/openai/deployments/{config['deployment_name']}"
        f"/chat/completions?api-version=2024-02-15-preview"
    )


def stream_response(azure_url, headers, body):
    """Stream the response from Azure OpenAI."""
    try:
        with requests.post(azure_url, headers=headers, json=body, stream=True, timeout=120) as resp:
            if resp.status_code != 200:
                yield f"data: {{'error': 'Azure returned {resp.status_code}'}}\n\n"
                return
            for chunk in resp.iter_content(chunk_size=None):
                if chunk:
                    yield chunk
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"data: {{'error': '{str(e)}'}}\n\n"


@app.route("/")
def health_check():
    """Health check endpoint."""
    logger.info("Health check requested")
    return jsonify({"status": "Bridge Active"})


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    """Main endpoint for Moltbot requests."""
    logger.info("Moltbot connecting...")
    
    config, error = get_azure_config()
    if error:
        logger.error(error)
        return jsonify({"error": error}), 500
    
    try:
        body = request.get_json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON"}), 400
    
    azure_url = build_azure_url(config)
    logger.info("Relaying to Azure...")
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config["key"]
    }
    
    is_streaming = body.get("stream", False)
    
    if is_streaming:
        return Response(
            stream_response(azure_url, headers, body),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        try:
            resp = requests.post(azure_url, headers=headers, json=body, timeout=120)
            if resp.status_code != 200:
                return jsonify({"error": f"Azure error: {resp.text}"}), resp.status_code
            return jsonify(resp.json())
        except requests.Timeout:
            return jsonify({"error": "Request timed out"}), 504
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/chat/completions", methods=["POST"])
def chat_completions_alt():
    """Alternative endpoint without /v1."""
    return chat_completions()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
