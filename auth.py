from typing import Dict, Tuple
import urllib.parse as urllibparse
import requests
import base64


# TODO handle auth tokens expiring
# TODO error handling

class AuthHandler:
    """
    Handles anything authentication related
    """
    def __init__(self, host_url: str):
        self.auth_url = "https://accounts.spotify.com/api/token"
        self.host_url = host_url
        self.redirect_uri = self.host_url + "/callback"
        self.client_id, self.client_secret = self._get_secrets()
        self.base64_encoded = base64.b64encode(("{}:{}".format(self.client_id, self.client_secret)).encode())
        self.scope = "playlist-modify-public playlist-modify-private user-read-recently-played user-top-read playlist-read-private user-follow-modify user-follow-read user-follow-modify user-read-private user-library-read user-read-email user-read-currently-playing"
        self.auth_query_parameters = {
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "client_id": self.client_id
        }
        self.url_args = "&".join(["{}={}".format(key, urllibparse.quote(val))
                                  for key, val in list(self.auth_query_parameters.items())])
        self.redirect_url = "https://accounts.spotify.com/authorize/?{}".format(self.url_args)

    def _get_secrets(self) -> Tuple[str]:
        """ Read secrets from secret.py """
        from spoticolor.secret import CLIENT_ID, CLIENT_SECRET
        return CLIENT_ID, CLIENT_SECRET

    def authorize(self, auth_token) -> Tuple[Dict, str]:
        """ Given auth token of active user auth returns header to be used to make requests for that user. """
        code_payload = {
            "grant_type": "authorization_code",
            "code": str(auth_token),
            "redirect_uri": self.redirect_uri,
        }
        header = {"Authorization": "Basic {}".format(self.base64_encoded.decode())}
        post_request = requests.post(self.auth_url, data=code_payload, headers=header)
        res = post_request.json()
        access_token, refresh_token = res["access_token"], res["refresh_token"]
        auth_header = {"Authorization": "Bearer {}".format(access_token)}
        return auth_header, refresh_token


def refresh_auth(refresh_token: str) -> Dict[str, str]:
    """
    Standalone function to refresh user auth token with refresh token since they expire
    every hour.
    Args:
      refresh_token (str): user auth refresh token, used to get new auth token
    Returns:
      auth_header (Dict[str, str]): auth header to be used to authenticate API calls
    """
    from spoticolor.secret import CLIENT_ID, CLIENT_SECRET
    base64_encoded = base64.b64encode(("{}:{}".format(CLIENT_ID, CLIENT_SECRET)).encode())
    code_payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    header = {"Authorization": "Basic" + str(base64_encoded)}
    req = requests.post("https://accounts.spotify.com/api/token", data=code_payload, headers=header)
    res = req.json()
    access_token = res.get("access_token")
    if not access_token:
        print(req.status_code, req.json())
        return None
    return {"Authorization": f"Bearer {access_token}"}
