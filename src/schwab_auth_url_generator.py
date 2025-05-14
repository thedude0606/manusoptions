from schwab_api.auth import client_from_login_flow
import os

# Schwab API credentials
API_KEY = "kQjNEtGHLhWUE0ZCdiaAkLDUfjBGT8G0"
APP_SECRET = "dYPIYuVJiIuHMc1Y"
CALLBACK_URL = "https://127.0.0.1:8080"
TOKEN_PATH = "./token.json"  # Store token in a local file

def initiate_auth_and_get_url():
    """Initiates the Schwab API authentication flow and prints the URL for user authorization."""
    try:
        # This will launch a browser instance for the user to log in.
        # The user needs to complete the login and then copy the URL from the browser's address bar
        # after being redirected to the CALLBACK_URL.
        print("Attempting to initiate Schwab API authentication...")
        print(f"Using API Key: {API_KEY}")
        print(f"Using Callback URL: {CALLBACK_URL}")
        print(f"Token will be saved to: {TOKEN_PATH}")
        
        # The client_from_login_flow function will handle opening the browser.
        # We need to inform the user about this process.
        print("A browser window should open for you to log in to Schwab.")
        print(f"After logging in, you will be redirected to: {CALLBACK_URL}")
        print("Please copy the ENTIRE URL from your browser's address bar after redirection and provide it when prompted.")

        # This function call will block until the user provides the callback URL in the terminal.
        # The library itself handles printing the auth URL and prompting for the callback URL.
        client = client_from_login_flow(api_key=API_KEY, app_secret=APP_SECRET, callback_url=CALLBACK_URL, token_path=TOKEN_PATH, asyncio=False, headless=False)
        
        if client and client.session.authorized():
            print("Successfully authenticated and token saved!")
            return client
        else:
            print("Authentication failed or was cancelled.")
            return None

    except Exception as e:
        print(f"An error occurred during the authentication process: {e}")
        return None

if __name__ == "__main__":
    client = initiate_auth_and_get_url()
    if client:
        print("Schwab API client is ready.")
    else:
        print("Failed to obtain Schwab API client.")

