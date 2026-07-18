import os
from google import genai

# Initialize the new Google GenAI Client with Vertex AI settings
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "techsodh")
REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

try:
    # Instantiating Client with vertexai=True tells the SDK to call Vertex AI endpoints
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=REGION
    )
    vertex_initialized = True
except Exception as e:
    vertex_initialized = False
    init_error = str(e)

def summarize_email(sender: str, subject: str, body: str) -> str:
    """
    Summarizes the content of an email using Vertex AI Gemini model via the google-genai SDK.
    """
    if not vertex_initialized:
        return f"Vertex AI client not initialized. Error: {init_error}"
        
    prompt = (
        f"You are an assistant summarizing inbox emails. Provide a short, 1-2 sentence summary "
        f"of the following email, highlighting key requests or action items.\n\n"
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"Body:\n{body}\n"
    )
    
    try:
        # Calls the unified model name "gemini-2.5-flash" via Vertex AI
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Error generating summary via Vertex AI GenAI SDK: {str(e)}"
