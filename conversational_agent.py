import os
from google import genai
from google.genai import types
import gmail_service

# Initialize Vertex AI GenAI Client
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "techsodh")
REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

try:
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=REGION
    )
    agent_initialized = True
except Exception as e:
    agent_initialized = False
    init_error = str(e)

def run_agent_query(user_query: str) -> str:
    """
    Runs a user natural language query through Gemini's function calling loop,
    executing Gmail tools as requested by the model, and returns the final response.
    """
    if not agent_initialized:
        return f"Agent initialization failed: {init_error}"
        
    # Get active Gmail API service session
    try:
        service = gmail_service.get_gmail_service()
    except Exception as e:
        return f"Failed to authenticate with Gmail API: {str(e)}"

    # 1. Define tools with clear docstrings and type hints for Gemini's schema inference
    def list_unread_emails() -> list:
        """
        Retrieves a list of unread emails currently in the user's inbox.
        Returns a list of dictionaries containing 'id', 'sender', 'subject', 'date', and 'body' snippets.
        """
        print("[Agent Tool Executing] list_unread_emails()")
        return gmail_service.list_unread_emails(service)

    def get_email_details(email_id: str) -> dict:
        """
        Retrieves full details of a specific email message including sender, subject, date, and body by its ID.
        """
        print(f"[Agent Tool Executing] get_email_details(email_id={email_id})")
        return gmail_service.get_email_details(service, email_id)

    def create_draft_reply(email_id: str, reply_body: str) -> dict:
        """
        Creates a draft reply to a specific email ID using the provided reply_body text.
        Returns details of the created draft.
        """
        print(f"[Agent Tool Executing] create_draft_reply(email_id={email_id}, body_length={len(reply_body)})")
        return gmail_service.create_draft_reply(service, email_id, reply_body)

    def archive_email(email_id: str) -> dict:
        """
        Archives a specific email message by removing the 'INBOX' label using its ID.
        """
        print(f"[Agent Tool Executing] archive_email(email_id={email_id})")
        return gmail_service.archive_email(service, email_id)

    def search_emails(query: str) -> list:
        """
        Searches the user's emails using Gmail query syntax (e.g. 'from:person', 'subject:report', 'is:unread').
        """
        print(f"[Agent Tool Executing] search_emails(query={query})")
        return gmail_service.search_emails(service, query)

    def delete_email(email_id: str) -> dict:
        """
        Deletes (moves to trash) a specific email by its ID.
        """
        print(f"[Agent Tool Executing] delete_email(email_id={email_id})")
        return gmail_service.delete_email(service, email_id)

    def add_label_to_email(email_id: str, label_id: str) -> dict:
        """
        Adds a Gmail label (e.g. 'STARRED', 'IMPORTANT') to a specific email ID.
        """
        print(f"[Agent Tool Executing] add_label_to_email(email_id={email_id}, label={label_id})")
        return gmail_service.add_label_to_email(service, email_id, label_id)

    def mark_as_read(email_id: str) -> dict:
        """
        Marks an email as read by removing the 'UNREAD' label.
        """
        print(f"[Agent Tool Executing] mark_as_read(email_id={email_id})")
        return gmail_service.mark_as_read(service, email_id)

    def mark_as_unread(email_id: str) -> dict:
        """
        Marks an email as unread by adding the 'UNREAD' label.
        """
        print(f"[Agent Tool Executing] mark_as_unread(email_id={email_id})")
        return gmail_service.mark_as_unread(service, email_id)

    def create_draft(to: str, subject: str, body: str) -> dict:
        """
        Creates a standalone draft email (not a reply) to the specified recipient, subject, and body content.
        """
        print(f"[Agent Tool Executing] create_draft(to={to}, subject={subject})")
        return gmail_service.create_draft(service, to, subject, body)

    # Map tool names to actual callables
    tool_map = {
        "list_unread_emails": list_unread_emails,
        "get_email_details": get_email_details,
        "create_draft_reply": create_draft_reply,
        "archive_email": archive_email,
        "search_emails": search_emails,
        "delete_email": delete_email,
        "add_label_to_email": add_label_to_email,
        "mark_as_read": mark_as_read,
        "mark_as_unread": mark_as_unread,
        "create_draft": create_draft
    }

    # 2. Configure generate content configuration with the list of tools
    config = types.GenerateContentConfig(
        tools=[
            list_unread_emails, 
            get_email_details, 
            create_draft_reply, 
            archive_email,
            search_emails,
            delete_email,
            add_label_to_email,
            mark_as_read,
            mark_as_unread,
            create_draft
        ],
        temperature=0.0,
        system_instruction=(
            "You are a helpful Email Agent powered by Gemini. You have access to tools "
            "for listing, searching, reading, replying to, archiving, deleting, labeling, "
            "marking emails as read/unread, and creating drafts. Use these tools strategically to execute user requests. "
            "When replying to emails, be polite, brief, and professional. Always confirm actions you took."
        )
    )

    try:
        # Create a new chat session to allow multi-turn tool interactions in a single request flow
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=config
        )
        
        response = chat.send_message(user_query)
        
        # 3. Tool Calling Execution Loop
        while response.function_calls:
            function_responses = []
            for call in response.function_calls:
                name = call.name
                args = call.args
                
                if name in tool_map:
                    try:
                        # Execute the tool function
                        result = tool_map[name](**args)
                        function_responses.append(
                            types.Part.from_function_response(
                                name=name,
                                response={"result": result}
                            )
                        )
                    except Exception as e:
                        function_responses.append(
                            types.Part.from_function_response(
                                name=name,
                                response={"error": str(e)}
                            )
                        )
                else:
                    function_responses.append(
                        types.Part.from_function_response(
                            name=name,
                            response={"error": f"Function {name} not found"}
                        )
                    )
            
            # Send the tool outputs back to Gemini to determine the next step
            response = chat.send_message(function_responses)
            
        return response.text
    except Exception as e:
        return f"Error running agent loop: {str(e)}"
