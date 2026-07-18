from email_agent.conversational_agent import run_agent_query

def main():
    print("==================================================")
    print("      Welcome to Gmail Gemini Agent Chat!         ")
    print("==================================================")
    print("Ask natural language queries like:")
    print(" - 'Show my unread emails.'")
    print(" - 'Read the email from Janvi Rajwani.'")
    print(" - 'Reply to the latest LinkedIn invitation politely.'")
    print(" - 'Archive the email from Grammarly.'")
    print("Type 'exit' or 'quit' to close the chat.\n")
    
    # Simple interactive terminal chat loop
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            print("Agent: Thinking...")
            response = run_agent_query(user_input)
            print(f"Agent: {response}\n")
            print("-" * 50)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Agent: Encountered an error: {e}\n")

if __name__ == "__main__":
    main()
