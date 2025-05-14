from schwab_api import Schwab
import os
import json

# Path to the token file (created by create_placeholder_token.py)
TOKEN_PATH = "/home/ubuntu/token.json"

def validate_schwab_client_with_placeholder_token():
    print(f"Attempting to initialize Schwab client with token file: {TOKEN_PATH}")
    
    if not os.path.exists(TOKEN_PATH):
        print(f"ERROR: Token file not found at {TOKEN_PATH}. Please ensure it was created.")
        return False

    try:
        # Load API key and callback URL from the token file itself
        with open(TOKEN_PATH, 'r') as f:
            token_data = json.load(f)
        
        api_key = token_data.get("api_key")
        app_secret = token_data.get("app_secret") # Added app_secret
        callback_url = token_data.get("callback_url")

        if not all([api_key, app_secret, callback_url]):
            print("ERROR: API key, App Secret, or callback URL missing from token.json.")
            return False

        print(f"Initializing Schwab client with API Key: {api_key[:5]}... (masked), App Secret: {app_secret[:5]}... (masked)")
        
        # Initialize the Schwab client using the token_path
        # The library will attempt to load the token from this path.
        client = Schwab(
            api_key=api_key, 
            app_secret=app_secret, 
            callback_url=callback_url, 
            token_path=TOKEN_PATH
        )
        
        print("Schwab client initialized.")
        
        # With a placeholder token, check_auth() is expected to fail or return False
        # as no real authentication has occurred.
        print("Attempting client.check_auth() (expected to be False with placeholder token)...")
        auth_status = client.check_auth()
        print(f"client.check_auth() returned: {auth_status}")
        
        if not auth_status:
            print("As expected, client.check_auth() is False. This means the client initialized but is not yet authenticated.")
            print("This confirms the placeholder token allows client initialization.")
            print("The actual authentication will occur when the dashboard tries to make an API call.")
            return True # Successful initialization for placeholder purposes
        else:
            print("Unexpected: client.check_auth() returned True with a placeholder token. This is unusual.")
            return False

    except Exception as e:
        print(f"An error occurred during Schwab client validation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if validate_schwab_client_with_placeholder_token():
        print("\nValidation with placeholder token successful for initialization purposes.")
    else:
        print("\nValidation with placeholder token failed.")

