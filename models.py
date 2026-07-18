from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, index=True)
    recipient = Column(String, index=True)
    subject = Column(String)
    body = Column(String)
    is_read = Column(Boolean, default=False)
    received_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to drafts if any replies are made to this email
    drafts = relationship("Draft", back_populates="original_email")

class Draft(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, index=True)
    original_email_id = Column(Integer, ForeignKey("emails.id"), nullable=True)
    recipient = Column(String)
    subject = Column(String)
    body = Column(String)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    original_email = relationship("Email", back_populates="drafts")
