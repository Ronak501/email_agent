import base64
from email.mime.text import MIMEText
from email_agent import gmail_service

def create_draft(service, to: str, subject: str, body_content: str) -> dict:
    """
    Create a standalone draft email.
    """
    print(f"Creating standalone draft to: {to}")
    message = MIMEText(body_content)
    message['to'] = to
    message['subject'] = subject
    raw_message = {
        'message': {
            'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        }
    }
    return service.users().drafts().create(userId='me', body=raw_message).execute()

def create_draft_reply(service, email_id: str, body_content: str) -> dict:
    """
    Create a draft reply to a specific email ID.
    """
    print(f"Creating reply draft for email ID: {email_id}")
    original_msg = gmail_service.get_email_details(service, email_id)
    
    subject = original_msg['subject']
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"
        
    recipient = original_msg['sender']
    
    # Construct MIME email
    message = MIMEText(body_content)
    message['to'] = recipient
    message['subject'] = subject
    
    # Extract Thread ID
    original_raw = service.users().messages().get(userId='me', id=email_id).execute()
    thread_id = original_raw.get('threadId')
    
    raw_message = {
        'message': {
            'threadId': thread_id,
            'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        }
    }
    
    return service.users().drafts().create(userId='me', body=raw_message).execute()

def send_draft(service, draft_id: str) -> dict:
    """
    Send an existing draft by ID.
    """
    print(f"Sending draft ID: {draft_id}")
    return service.users().drafts().send(userId='me', body={'id': draft_id}).execute()
