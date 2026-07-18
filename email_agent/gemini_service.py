import os
import json
from pydantic import BaseModel
from typing import List
from google import genai
from google.genai import types
from email_agent import config

try:
    client = genai.Client(
        vertexai=True,
        project=config.PROJECT_ID,
        location=config.REGION
    )
    vertex_initialized = True
except Exception as e:
    vertex_initialized = False
    init_error = str(e)

class EmailAnalysis(BaseModel):
    category: str
    priority: str
    summary: str
    action_items: List[str]

def analyze_email(sender: str, subject: str, body: str) -> dict:
    """
    Analyzes an email to return structured JSON.
    No email content is logged to stdout.
    """
    default_response = {
        "category": "Updates",
        "priority": "Medium",
        "summary": "No analysis available.",
        "action_items": []
    }
    
    if not vertex_initialized:
        default_response["summary"] = f"Vertex AI client not initialized. Error: {init_error}"
        return default_response
        
    prompt = (
        f"Analyze the following email and categorize it, assess its priority level (High/Medium/Low), "
        f"provide a short 1-2 sentence summary, and list any key action items or requests.\n\n"
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"Body:\n{body}\n"
    )
    
    try:
        genai_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EmailAnalysis,
            temperature=0.1
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_config
        )
        return json.loads(response.text.strip())
    except Exception as e:
        # Avoid logging raw exception to stdout if it contains email data
        print("Structured analysis failed.")
        return default_response

def summarize_email(sender: str, subject: str, body: str) -> str:
    analysis = analyze_email(sender, subject, body)
    return analysis.get("summary", "No summary available.")
