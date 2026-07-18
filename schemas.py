from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class EmailBase(BaseModel):
    sender: str
    recipient: str
    subject: str
    body: str
    is_read: bool = False

class EmailCreate(EmailBase):
    pass

class EmailResponse(EmailBase):
    id: int
    received_at: datetime

    class Config:
        from_attributes = True

class DraftBase(BaseModel):
    recipient: str
    subject: str
    body: str

class DraftCreate(BaseModel):
    body: str  # Creating a reply draft only requires the body from the user (recipient/subject can be inferred)

class DraftResponse(DraftBase):
    id: int
    original_email_id: Optional[int] = None
    is_sent: bool
    created_at: datetime

    class Config:
        from_attributes = True

class SendConfirmation(BaseModel):
    confirm: bool
