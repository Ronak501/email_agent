from database import SessionLocal, engine
import models
from datetime import datetime

# Recreate tables to clean start
models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)

def seed_db():
    db = SessionLocal()
    try:
        # Check if we already have emails
        if db.query(models.Email).count() == 0:
            emails = [
                models.Email(
                    sender="manager@company.com",
                    recipient="me@example.com",
                    subject="Quarterly Report Review",
                    body="Hi, could you please send me the review for the Q2 reports by EOD tomorrow? Thanks!",
                    is_read=False,
                    received_at=datetime.utcnow()
                ),
                models.Email(
                    sender="support@service.com",
                    recipient="me@example.com",
                    subject="Your Subscription Details",
                    body="Hello, this is a reminder that your subscription will renew automatically on August 1st. Please update billing if needed.",
                    is_read=False,
                    received_at=datetime.utcnow()
                ),
                models.Email(
                    sender="friend@domain.com",
                    recipient="me@example.com",
                    subject="Catch up this weekend?",
                    body="Hey! Are you free to grab coffee or dinner this Saturday? Let me know.",
                    is_read=True,  # This one is already read
                    received_at=datetime.utcnow()
                ),
            ]
            db.bulk_save_objects(emails)
            db.commit()
            print("Database successfully seeded with mock emails!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
