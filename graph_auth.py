# graph_auth.py
# ==============
# Handles authentication with Microsoft Graph API.
# Uses DELEGATED auth flow — user logs in once via browser,
# then the token is cached and reused silently.
# Other modules call get_headers() to get the auth header for API requests.

import os
import json
import msal
from config import TENANT_ID, CLIENT_ID, CLIENT_SECRET, PROJECT_DIR, MAILBOX

# Scopes needed for reading/sending mail
SCOPES = [
    "Mail.Read",
    "Mail.Send",
    "Mail.ReadWrite",
    "User.Read"
]

# Token cache file — stores the refresh token so you don't have to
# log in every time you run the script.
TOKEN_CACHE_FILE = os.path.join(PROJECT_DIR, "token_cache.json")


class GraphAuth:
    def __init__(self):
        # Set up the token cache. MSAL can serialize/deserialize it
        # to a file so tokens persist between runs.
        self.cache = msal.SerializableTokenCache()

        # Load existing cache from disk if it exists
        if os.path.exists(TOKEN_CACHE_FILE):
            with open(TOKEN_CACHE_FILE, "r") as f:
                self.cache.deserialize(f.read())

        # Create the MSAL app object.
        # "consumers" authority allows personal Microsoft accounts (outlook.com)
        self.app = msal.PublicClientApplication(
            CLIENT_ID,
            authority="https://login.microsoftonline.com/consumers",
            token_cache=self.cache
        )

    def _save_cache(self):
        """Save the token cache to disk if it changed."""
        if self.cache.has_state_changed:
            with open(TOKEN_CACHE_FILE, "w") as f:
                f.write(self.cache.serialize())

    def get_token(self):
        """
        Get an access token from Microsoft.
        
        First tries to get a cached token silently (no user interaction).
        If no cached token exists, opens a browser for the user to log in.
        After first login, subsequent runs are fully silent.
        """
        # Check if there's already a cached account we can use
        accounts = self.app.get_accounts()

        if accounts:
            # Try to get a token silently using the cached refresh token
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                print("[AUTH] Token acquired silently (cached).")
                self._save_cache()
                return result["access_token"]

        # No cached token — need interactive login.
        # This opens a browser window for the user to sign in.
        print("[AUTH] No cached token found. Opening browser for login...")
        print("[AUTH] Log in with the " + MAILBOX + " account.")

        result = self.app.acquire_token_interactive(
            scopes=SCOPES,
            prompt="select_account"
        )

        if "access_token" in result:
            print("[AUTH] Token acquired successfully via browser login.")
            self._save_cache()
            return result["access_token"]
        else:
            error_msg = result.get("error_description", "Unknown error")
            raise Exception(f"[AUTH] Failed to get token: {error_msg}")

    def get_headers(self):
        """
        Returns HTTP headers ready for Graph API requests.
        """
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
