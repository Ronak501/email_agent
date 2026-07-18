from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import gmail_service
import gemini_service

app = FastAPI(
    title="Gmail Agent Service",
    description="A FastAPI service integrated with Gmail API and Gemini summaries.",
    version="2.0.0"
)

# Shared schemas for Gmail endpoints
class EmailSummaryResponse(BaseModel):
    id: str
    sender: str
    subject: str
    date: str
    snippet: str
    summary: Optional[str] = None

class DraftCreate(BaseModel):
    body: str

class SendConfirmation(BaseModel):
    confirm: bool

class AgentQuery(BaseModel):
    query: str

class AgentResponse(BaseModel):
    response: str

@app.post("/agent/query", response_model=AgentResponse, summary="Send a natural language query to the Gmail Agent")
def agent_query(payload: AgentQuery):
    """
    Send natural language queries (e.g. 'Show my unread emails') to the agent.
    The agent dynamically decides which Gmail tools to run and returns its response.
    """
    import conversational_agent
    response_text = conversational_agent.run_agent_query(payload.query)
    return AgentResponse(response=response_text)

@app.get("/emails/unread", response_model=List[EmailSummaryResponse], summary="List live unread emails with summaries")
def list_unread_emails():
    """
    Retrieve unread emails from your live Gmail account and summarize them using Gemini.
    """
    try:
        service = gmail_service.get_gmail_service()
        emails = gmail_service.list_unread_emails(service)
        
        response = []
        for email in emails:
            summary = gemini_service.summarize_email(email['sender'], email['subject'], email['body'])
            response.append(
                EmailSummaryResponse(
                    id=email['id'],
                    sender=email['sender'],
                    subject=email['subject'],
                    date=email['date'],
                    snippet=email['body'][:200],  # Return snippet of body
                    summary=summary
                )
            )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gmail/Gemini API error: {str(e)}"
        )

@app.get("/emails/{email_id}", response_model=EmailSummaryResponse, summary="Get live email details")
def get_email_details(email_id: str):
    """
    Retrieve full details of a specific live email by ID.
    """
    try:
        service = gmail_service.get_gmail_service()
        email = gmail_service.get_email_details(service, email_id)
        summary = gemini_service.summarize_email(email['sender'], email['subject'], email['body'])
        return EmailSummaryResponse(
            id=email['id'],
            sender=email['sender'],
            subject=email['subject'],
            date=email['date'],
            snippet=email['body'],
            summary=summary
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email with ID {email_id} not found or API error: {str(e)}"
        )

@app.post("/emails/{email_id}/draft", status_code=status.HTTP_201_CREATED, summary="Create a live draft reply")
def create_draft_reply(email_id: str, draft_in: DraftCreate):
    """
    Create a draft reply to a specific live email.
    Recipient and subject are automatically threaded.
    """
    try:
        service = gmail_service.get_gmail_service()
        draft = gmail_service.create_draft_reply(service, email_id, draft_in.body)
        return {"status": "Draft created successfully", "draft_id": draft['id']}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create draft: {str(e)}"
        )

@app.post("/drafts/{draft_id}/send", summary="Send a live email draft")
def send_email_draft(draft_id: str, confirmation: SendConfirmation):
    """
    Send a live Gmail draft. Requires explicit confirmation: `{"confirm": true}`.
    """
    if not confirmation.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Send confirmation is required. Set 'confirm' to true."
        )
    try:
        service = gmail_service.get_gmail_service()
        sent_msg = gmail_service.send_draft(service, draft_id)
        return {"status": "Email sent successfully", "message_id": sent_msg['id']}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )

# Schema for standalone draft creation
class StandaloneDraftCreate(BaseModel):
    to: str
    subject: str
    body: str

@app.get("/emails", response_model=List[EmailSummaryResponse], summary="List or search live emails")
def list_or_search_emails(q: Optional[str] = None):
    """
    List or search emails in your Gmail account.
    """
    try:
        service = gmail_service.get_gmail_service()
        # Fallback query if none provided
        query = q if q else "is:inbox"
        emails = gmail_service.search_emails(service, query)
        
        response = []
        for email in emails:
            response.append(
                EmailSummaryResponse(
                    id=email['id'],
                    sender=email['sender'],
                    subject=email['subject'],
                    date=email['date'],
                    snippet=email['body'][:200],
                    summary=None  # Leave empty for quick search
                )
            )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gmail API error: {str(e)}"
        )

@app.post("/draft", status_code=status.HTTP_201_CREATED, summary="Create a standalone draft email")
def create_standalone_draft(draft_in: StandaloneDraftCreate):
    """
    Create a standalone draft email (not a reply).
    """
    try:
        service = gmail_service.get_gmail_service()
        draft = gmail_service.create_draft(service, draft_in.to, draft_in.subject, draft_in.body)
        return {"status": "Draft created successfully", "draft_id": draft['id']}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create draft: {str(e)}"
        )

