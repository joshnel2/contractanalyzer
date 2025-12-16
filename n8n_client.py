"""
n8n Workflow Integration Client

This module provides helper functions to trigger n8n workflows from your Flask app.
"""

import os
import requests
from typing import Optional, Dict, Any

N8N_WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL', 'http://localhost:5678')


def trigger_workflow(webhook_path: str, data: Dict[str, Any], timeout: int = 30) -> Optional[Dict[str, Any]]:
    """
    Trigger an n8n workflow via webhook.
    
    Args:
        webhook_path: The webhook path configured in n8n (e.g., 'contract-analyzed')
        data: The JSON data to send to the workflow
        timeout: Request timeout in seconds
        
    Returns:
        Response data from the workflow, or None if the request failed
    """
    url = f"{N8N_WEBHOOK_URL}/webhook/{webhook_path}"
    
    try:
        response = requests.post(url, json=data, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error triggering n8n workflow: {e}")
        return None


def trigger_contract_analysis_workflow(
    user_email: str,
    analysis_summary: str,
    risk_level: str = "low"
) -> Optional[Dict[str, Any]]:
    """
    Trigger the contract analysis notification workflow.
    
    Args:
        user_email: Email of the user who analyzed the contract
        analysis_summary: Summary of the analysis results
        risk_level: Risk level ('low', 'medium', 'high')
        
    Returns:
        Response from the workflow
    """
    return trigger_workflow('contract-analyzed', {
        'user_email': user_email,
        'analysis_summary': analysis_summary,
        'risk_level': risk_level
    })


# Example workflows you might want to trigger:

def trigger_new_subscription_workflow(user_email: str, plan: str = "monthly") -> Optional[Dict[str, Any]]:
    """Trigger workflow when a new subscription is created."""
    return trigger_workflow('new-subscription', {
        'user_email': user_email,
        'plan': plan,
        'event': 'subscription_created'
    })


def trigger_usage_alert_workflow(user_email: str, queries_used: int, limit: int) -> Optional[Dict[str, Any]]:
    """Trigger workflow when user is approaching usage limit."""
    return trigger_workflow('usage-alert', {
        'user_email': user_email,
        'queries_used': queries_used,
        'limit': limit,
        'percentage': (queries_used / limit) * 100
    })
