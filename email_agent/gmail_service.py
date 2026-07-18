from email_agent import utils

def list_unread_emails(service):
    """
    List unread emails from the user's inbox.
    No email bodies or headers are logged to standard output.
    """
    results = service.users().messages().list(userId='me', q='is:unread').execute()
    messages = results.get('messages', [])
    print(f"Fetched {len(messages)} unread messages.")
    
    unread_emails = []
    for msg in messages[:10]:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_detail.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '(Unknown Sender)')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        body = utils.get_email_body(payload) or msg_detail.get('snippet', '')
        
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
    No email bodies or headers are logged to standard output.
    """
    msg_detail = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    payload = msg_detail.get('payload', {})
    headers = payload.get('headers', [])
    
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '(Unknown Sender)')
    date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
    body = utils.get_email_body(payload) or msg_detail.get('snippet', '')
    
    print(f"Fetched details for email ID: {message_id}")
    return {
        'id': message_id,
        'sender': sender,
        'subject': subject,
        'date': date,
        'body': body
    }

def search_emails(service, query, max_results=10):
    """
    Search messages using Gmail's query language.
    No email bodies or headers are logged to standard output.
    """
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])
    print(f"Search query returned {len(messages)} messages.")
    
    found_emails = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_detail.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '(Unknown Sender)')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        body = utils.get_email_body(payload) or msg_detail.get('snippet', '')
        
        found_emails.append({
            'id': msg['id'],
            'sender': sender,
            'subject': subject,
            'date': date,
            'body': body
        })
    return found_emails

def archive_email(service, email_id):
    """
    Archive an email by removing the 'INBOX' label.
    """
    print(f"Archiving email ID: {email_id}")
    return service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'removeLabelIds': ['INBOX']}
    ).execute()

def delete_email(service, email_id):
    """
    Delete an email by moving it to the trash.
    """
    print(f"Deleting email ID: {email_id}")
    return service.users().messages().trash(userId='me', id=email_id).execute()

def add_label_to_email(service, email_id, label_id):
    """
    Add a label to an email.
    """
    print(f"Adding label {label_id} to email ID: {email_id}")
    return service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'addLabelIds': [label_id]}
    ).execute()

def mark_as_read(service, email_id):
    """
    Mark an email as read by removing the 'UNREAD' label.
    """
    print(f"Marking email ID as read: {email_id}")
    return service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()

def mark_as_unread(service, email_id):
    """
    Mark an email as unread by adding the 'UNREAD' label.
    """
    print(f"Marking email ID as unread: {email_id}")
    return service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'addLabelIds': ['UNREAD']}
    ).execute()
