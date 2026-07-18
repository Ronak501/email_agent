import base64

def get_email_body(payload: dict) -> str:
    """
    Recursively extracts the plain text body from a Gmail message payload.
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

def escape_html(unsafe: str) -> str:
    """Escapes HTML entities to prevent rendering arbitrary HTML in the frontend."""
    return (
        unsafe.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#039;')
    )
