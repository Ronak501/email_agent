import os
from gmail_service import get_gmail_service, list_unread_emails
from gemini_service import summarize_email

def main():
    print("=== Gmail & Gemini Agent CLI ===")
    
    # Check Gemini API Key
    if not os.getenv("GEMINI_API_KEY"):
        print("\n[WARNING] GEMINI_API_KEY environment variable is not set.")
        print("Please set it to get actual Gemini AI summaries, otherwise mock summaries will be shown.\n")
        
    print("Initiating Gmail authentication...")
    try:
        service = get_gmail_service()
        print("Successfully authenticated with Gmail API!")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    print("\nFetching unread emails from your inbox...")
    try:
        unread_emails = list_unread_emails(service)
        if not unread_emails:
            print("No unread emails found in your inbox!")
            return
            
        print(f"Found {len(unread_emails)} unread emails. Processing summaries with Gemini...\n")
        for i, email in enumerate(unread_emails, 1):
            print(f"{i}. FROM: {email['sender']}")
            print(f"   SUBJECT: {email['subject']}")
            print(f"   DATE: {email['date']}")
            
            # Summarize using Gemini
            summary = summarize_email(email['sender'], email['subject'], email['body'])
            print(f"   GEMINI SUMMARY: {summary}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Failed to fetch or summarize emails: {e}")

if __name__ == "__main__":
    main()
