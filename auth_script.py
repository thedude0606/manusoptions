import schwabdev
import os
from dotenv import load_dotenv

load_dotenv()

APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")

print(f"APP_KEY: {APP_KEY}")
print(f"CALLBACK_URL: {CALLBACK_URL}")

# This function will be called by the schwabdev library when it needs user input
# or to notify the user about an event, like opening a URL.
def handle_redirect_uri(message, importance=0):
    print(f"Schwabdev notification (importance {importance}): {message}")
    # We expect the message to contain the URL the user needs to open.
    # We will pass this URL back to the user.
    global auth_url_for_user
    if "https://api.schwabapi.com/v1/oauth/authorize?client_id=" in message:
        auth_url_for_user = message

auth_url_for_user = None

try:
    # The tokens_file path should be absolute for clarity and to avoid issues with working directory
    client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, tokens_file="/home/ubuntu/manusoptions/tokens.json", capture_callback=False, call_on_notify=handle_redirect_uri)
    
    if auth_url_for_user:
        print(f"Please open this URL in your browser to authenticate: {auth_url_for_user}")
    elif client.tokens and client.tokens.access_token:
        print("Existing token found and seems valid. Verifying...")
        try:
            # Corrected method name: client.account_linked() instead of client.accounts_linked()
            linked_accounts_response = client.account_linked()
            if linked_accounts_response.ok:
                 print("Authentication successful. Linked accounts retrieved.")
                 print(linked_accounts_response.json())
            else:
                print(f"Could not retrieve linked accounts. Status: {linked_accounts_response.status_code}, Response: {linked_accounts_response.text}")
                print("Attempting to refresh token.")
                client.tokens.update_refresh_token() # This will call handle_redirect_uri if user input is needed
                if auth_url_for_user:
                    print(f"Please open this URL in your browser to authenticate: {auth_url_for_user}")
                else:
                    print("Token refresh attempted. If authentication still fails, manual intervention may be needed or the auth URL was not captured.")
        except Exception as api_call_e:
            print(f"Error during API call to verify token: {api_call_e}")
            print("Attempting to refresh token.")
            client.tokens.update_refresh_token()
            if auth_url_for_user:
                print(f"Please open this URL in your browser to authenticate: {auth_url_for_user}")

    else:
        print("No valid token found or auth URL not captured as expected. The library should have prompted for the auth URL via call_on_notify.")
        print("If you were not prompted with an auth URL, there might be an issue with token file or initial auth flow.")
        if not (client.tokens and client.tokens.access_token):
             print("Forcing token update process.")
             client.tokens.update_refresh_token() # This will call handle_redirect_uri if user input is needed
             if auth_url_for_user:
                print(f"Please open this URL in your browser to authenticate: {auth_url_for_user}")
             else:
                print("Could not retrieve authentication URL automatically after forced update. Please check tokens.json or library behavior.")

except Exception as e:
    print(f"An error occurred: {e}")

