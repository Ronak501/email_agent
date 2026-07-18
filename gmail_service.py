import os
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    """
    Authenticates the user and returns the Gmail API service resource.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def get_email_body(payload):
    """
    Helper to recursively extract plain text body from a Gmail message payload.
    """
    if 'parts' in payload:
        for part in payload['parts']:
            body = get_email_body(part)
            if body:
                return body
    elif payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8')
    return ""

def list_unread_emails(service):
    """
    List unread emails from the user's inbox.
    """
    results = service.users().messages().list(userId='me', q='is:unread').execute()
    messages = results.get('messages', [])
    
    unread_emails = []
    for msg in messages[:10]:  # Limit to 10 for display/performance
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_detail.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '(Unknown Sender)')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        body = get_email_body(payload) or msg_detail.get('snippet', '')
        
        unread_emails.append({
            'id': msg['id'],
            'sender': sender,
            'subject': subject,
            'date': date,
            'body': body
        })
    return unread_emails

def get_email_details(service, message_id):
    """
    Get full details of a specific email by ID.
    """
    msg_detail = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    payload = msg_detail.get('payload', {})
    headers = payload.get('headers', [])
    
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '(Unknown Sender)')
    date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
    body = get_email_body(payload) or msg_detail.get('snippet', '')
    
    return {
        'id': message_id,
        'sender': sender,
        'subject': subject,
        'date': date,
        'body': body
    }

def create_draft_reply(service, email_id, body_content):
    """
    Create a draft reply to a specific email ID.
    """
    original_msg = get_email_details(service, email_id)
    
    subject = original_msg['subject']
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"
        
    recipient = original_msg['sender']
    
    # Construct MIME email
    message = MIMEText(body_content)
    message['to'] = recipient
    message['subject'] = subject
    
    # Extract Thread ID to keep conversation threading
    original_raw = service.users().messages().get(userId='me', id=email_id).execute()
    thread_id = original_raw.get('threadId')
    
    # Create the raw message dictionary
    raw_message = {
        'message': {
            'threadId': thread_id,
            'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        }
    }
    
    draft = service.users().drafts().create(userId='me', body=raw_message).execute()
    return draft

def send_draft(service, draft_id):
    """
    Send an existing draft by ID.
    """
    return service.users().drafts().send(userId='me', body={'id': draft_id}).execute()

def archive_email(service, email_id):
    """
    Archive an email by removing the 'INBOX' label.
    """
    return service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'removeLabelIds': ['INBOX']}
    ).execute()

def search_emails(service, query, max_results=10):
    """
    Search messages using Gmail's query language (e.g. 'from:boss', 'is:unread', etc.).
    """
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])
    
    found_emails = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_detail.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '(Unknown Sender)')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        body = get_email_body(payload) or msg_detail.get('snippet', '')
        
        found_emails.append({
            'id': msg['id'],
            'sender': sender,
            'subject': subject,
            'date': date,
            'body': body
        })
    return found_emails

def delete_email(service, email_id):
    """
    Delete an email by moving it to the trash.
    """
    return service.users().messages().trash(userId='me', id=email_id).execute()

def add_label_to_email(service, email_id, label_id):
    """
    Add a label (e.g., 'IMPORTANT', 'SPAM', or custom label ID) to an email.
    """
    return service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'addLabelIds': [label_id]}
    ).execute()

def mark_as_read(service, email_id):
    """
    Mark an email as read by removing the 'UNREAD' label.
    """
    return service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()

def mark_as_unread(service, email_id):
    """
    Mark an email as unread by adding the 'UNREAD' label.
    """
    return service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'addLabelIds': ['UNREAD']}
    ).execute()

def create_draft(service, to, subject, body_content):
    """
    Create a standalone draft email.
    """
    message = MIMEText(body_content)
    message['to'] = to
    message['subject'] = subject
    raw_message = {
        'message': {
            'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        }
    }
    return service.users().drafts().create(userId='me', body=raw_message).execute()



