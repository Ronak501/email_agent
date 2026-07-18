from sqlalchemy.orm import Session
from datetime import datetime
import models
import schemas

def get_unread_emails(db: Session):
    return db.query(models.Email).filter(models.Email.is_read == False).all()

def get_email_details(db: Session, email_id: int):
    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if email and not email.is_read:
        email.is_read = True
        db.commit()
        db.refresh(email)
    return email

def create_draft_reply(db: Session, email_id: int, draft_in: schemas.DraftCreate):
    original_email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not original_email:
        return None
    
    # Infer subject and recipient
    subject = original_email.subject
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"
    
    draft = models.Draft(
        original_email_id=email_id,
        recipient=original_email.sender,
        subject=subject,
        body=draft_in.body,
        is_sent=False,
        created_at=datetime.utcnow()
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft

def send_draft(db: Session, draft_id: int):
    draft = db.query(models.Draft).filter(models.Draft.id == draft_id).first()
    if not draft or draft.is_sent:
        return None
    
    # Mark draft as sent
    draft.is_sent = True
    
    # Simulate sending by inserting an outgoing email in the database
    sent_email = models.Email(
        sender="me@example.com",  # Representing user's email
        recipient=draft.recipient,
        subject=draft.subject,
        body=draft.body,
        is_read=True,  # Sender's copy is read
        received_at=datetime.utcnow()
    )
    db.add(sent_email)
    db.commit()
    db.refresh(draft)
    return draft
