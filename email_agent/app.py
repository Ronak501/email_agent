import os
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from email_agent.database import engine
from email_agent import models
from email_agent import config, auth, gmail_service, draft_service, gemini_service, session

# Create all database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gmail Agent Service",
    description="A secure FastAPI service integrated with Google OAuth login and Gemini structured analysis.",
    version="5.0.0"
)

# Enable signed and encrypted Session Cookies
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET_KEY)

# 1. Rate Limiting Middleware (Rule 9)
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int = 20):
        super().__init__(app)
        self.limit = limit_per_minute
        self.requests = {}  # ip -> list of timestamps

    async def dispatch(self, request: Request, call_next):
        # Exclude UI, login flow, and docs from rate limiting
        if request.url.path in ["/", "/login", "/auth/callback", "/logout", "/docs", "/openapi.json"]:
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        # Keep only requests from the last 60 seconds
        self.requests[client_ip] = [t for t in self.requests.get(client_ip, []) if now - t < 60]
        
        if len(self.requests[client_ip]) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.limit} requests per minute."
            )
            
        self.requests[client_ip].append(now)
        return await call_next(request)

app.add_middleware(RateLimitMiddleware, limit_per_minute=config.RATE_LIMIT_PER_MINUTE)

# Shared schemas for Gmail endpoints
class EmailSummaryResponse(BaseModel):
    id: str
    sender: str
    subject: str
    date: str
    snippet: str
    summary: Optional[str] = None
    category: Optional[str] = "Updates"
    priority: Optional[str] = "Medium"
    action_items: Optional[List[str]] = []

class DraftCreate(BaseModel):
    body: str

class StandaloneDraftCreate(BaseModel):
    to: str
    subject: str
    body: str

class SendConfirmation(BaseModel):
    confirm: bool

class AgentQuery(BaseModel):
    query: str
    session_id: Optional[str] = "default"

class AgentResponse(BaseModel):
    response: str

# Google Sign-In & Login Flow Routes
@app.get("/login", summary="Redirect to Google login")
async def login(request: Request):
    """Redirects the caller to the official Google Sign-In portal."""
    redirect_uri = request.url_for('auth_callback')
    # Force HTTPS redirect if running behind a proxy or load balancer
    if request.headers.get("x-forwarded-proto") == "https":
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    return await session.oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback", summary="OAuth callback handler")
async def auth_callback(request: Request):
    """Processes successful Google Sign-In callback, validates the user's email, and sets the session cookie."""
    try:
        token = await session.oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(status_code=400, detail="OAuth failed to retrieve user profile.")
        
        email = user_info.get("email", "").strip().lower()
        if email not in config.ALLOWED_EMAILS:
            return HTMLResponse(
                content=f"<h3>Forbidden</h3>Access denied for email '{email}'. This agent is restricted.",
                status_code=403
            )
        
        # Save user profile info in the secure cookie session
        request.session["user"] = dict(user_info)
        return RedirectResponse(url="/")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication error: {str(e)}")

@app.get("/logout", summary="Log out user session")
def logout(request: Request):
    """Clears the secure session cookie and redirects to login."""
    request.session.clear()
    return RedirectResponse(url="/login")

# UI Root route (Protected by login check)
@app.get("/", response_class=HTMLResponse, summary="Serve the agent frontend interface")
def serve_frontend(request: Request):
    """
    Serve the premium single-page web app for the Gmail Agent.
    Redirects to /login if no valid session exists.
    """
    user = request.session.get("user")
    if not user or user.get("email", "").strip().lower() not in config.ALLOWED_EMAILS:
        return RedirectResponse(url="/login")

    template_path = os.path.join("templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Templates folder or index.html not found!</h1>", status_code=404)

    return HTMLResponse("<h1>Templates folder or index.html not found!</h1>", status_code=404)

# Secured endpoints (Rule 5 & 6)
@app.post("/agent/query", response_model=AgentResponse, dependencies=[Depends(session.get_current_user)], summary="Send a natural language query")
def agent_query(payload: AgentQuery):
    """
    Send natural language queries to the agent.
    """
    from email_agent import conversational_agent
    response_text = conversational_agent.run_agent_query(payload.query, payload.session_id)
    return AgentResponse(response=response_text)

@app.get("/emails/unread", response_model=List[EmailSummaryResponse], dependencies=[Depends(session.get_current_user)], summary="List live unread emails with summaries")
def list_unread_emails():
    """
    Retrieve unread emails and analyze them using Gemini.
    """
    try:
        service = auth.get_gmail_service()
        emails = gmail_service.list_unread_emails(service)
        
        response = []
        for email in emails:
            analysis = gemini_service.analyze_email(email['sender'], email['subject'], email['body'])
            response.append(
                EmailSummaryResponse(
                    id=email['id'],
                    sender=email['sender'],
                    subject=email['subject'],
                    date=email['date'],
                    snippet=email['body'][:200],
                    summary=analysis.get("summary"),
                    category=analysis.get("category"),
                    priority=analysis.get("priority"),
                    action_items=analysis.get("action_items")
                )
            )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gmail/Gemini API error: {str(e)}"
        )

@app.get("/emails", response_model=List[EmailSummaryResponse], dependencies=[Depends(session.get_current_user)], summary="List or search live emails")
def list_or_search_emails(q: Optional[str] = None):
    """
    List or search emails in your Gmail account.
    """
    try:
        service = auth.get_gmail_service()
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
                    summary=None
                )
            )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gmail API error: {str(e)}"
        )

@app.get("/emails/{email_id}", response_model=EmailSummaryResponse, dependencies=[Depends(session.get_current_user)], summary="Get live email details")
def get_email_details(email_id: str):
    """
    Retrieve full details of a specific live email by ID.
    """
    try:
        service = auth.get_gmail_service()
        email = gmail_service.get_email_details(service, email_id)
        analysis = gemini_service.analyze_email(email['sender'], email['subject'], email['body'])
        return EmailSummaryResponse(
            id=email['id'],
            sender=email['sender'],
            subject=email['subject'],
            date=email['date'],
            snippet=email['body'],
            summary=analysis.get("summary"),
            category=analysis.get("category"),
            priority=analysis.get("priority"),
            action_items=analysis.get("action_items")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email with ID {email_id} not found or API error: {str(e)}"
        )

@app.post("/emails/{email_id}/draft", dependencies=[Depends(session.get_current_user)], status_code=status.HTTP_201_CREATED, summary="Create a live draft reply")
def create_draft_reply(email_id: str, draft_in: DraftCreate):
    """
    Create a draft reply to a specific live email.
    """
    try:
        service = auth.get_gmail_service()
        draft = draft_service.create_draft_reply(service, email_id, draft_in.body)
        return {"status": "Draft created successfully", "draft_id": draft['id']}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create draft: {str(e)}"
        )

@app.post("/draft", dependencies=[Depends(session.get_current_user)], status_code=status.HTTP_201_CREATED, summary="Create a standalone draft email")
def create_standalone_draft(draft_in: StandaloneDraftCreate):
    """
    Create a standalone draft email (not a reply).
    """
    try:
        service = auth.get_gmail_service()
        draft = draft_service.create_draft(service, draft_in.to, draft_in.subject, draft_in.body)
        return {"status": "Draft created successfully", "draft_id": draft['id']}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create draft: {str(e)}"
        )

@app.post("/drafts/{draft_id}/send", dependencies=[Depends(session.get_current_user)], summary="Send a live email draft")
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
        service = auth.get_gmail_service()
        sent_msg = draft_service.send_draft(service, draft_id)
        return {"status": "Email sent successfully", "message_id": sent_msg['id']}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )

@app.get("/brief", dependencies=[Depends(session.get_current_user)], summary="Generate a compiled briefing of high-priority emails")
def get_daily_briefing():
    """
    Scans recent unread emails, isolates high-priority items using Gemini, and returns a compiled briefing.
    """
    try:
        service = auth.get_gmail_service()
        emails = gmail_service.list_unread_emails(service)
        
        high_priority_items = []
        for email in emails:
            analysis = gemini_service.analyze_email(email['sender'], email['subject'], email['body'])
            if analysis.get("priority", "Medium").lower() == "high":
                high_priority_items.append({
                    "sender": email['sender'],
                    "subject": email['subject'],
                    "summary": analysis.get("summary"),
                    "action_items": analysis.get("action_items", [])
                })
                
        if not high_priority_items:
            return {"briefing": "No high priority emails found today. You are all caught up!"}
            
        prompt = (
            "You are an executive personal assistant. Write a short, highly professional morning briefing "
            "summarizing the following high-priority emails. Bullet point the key action items for each email:\n\n"
        )
        for item in high_priority_items:
            prompt += f"- From: {item['sender']}\n  Subject: {item['subject']}\n  Summary: {item['summary']}\n  Action Items: {', '.join(item['action_items'])}\n\n"
            
        from google import genai
        client = genai.Client(
            vertexai=True,
            project=config.PROJECT_ID,
            location=config.REGION
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return {"briefing": response.text.strip(), "high_priority_count": len(high_priority_items)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile briefing: {str(e)}"
        )
