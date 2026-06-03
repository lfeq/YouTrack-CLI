import httpx
from typing import Any
from youtrack_cli.config import resolve_token, load_config, ConfigError

class YouTrackAPIError(Exception):
    """Exception raised for errors in the YouTrack REST API."""
    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

class YouTrackClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            }
        )

    def _request(self, method: str, url: str, **kwargs) -> Any:
        try:
            # We want to make sure we support relative paths properly with httpx.Client.
            # httpx.Client(base_url="...") treats relative URLs nicely, but let's make sure
            # any leading slash is resolved or avoided to prevent messing with the base_url.
            # e.g., if url starts with /, strip it to append to base_url/
            req_url = url.lstrip("/")
            response = self.client.request(method, req_url, **kwargs)
        except httpx.RequestError as e:
            raise YouTrackAPIError(f"HTTP request failed: {e}") from e

        if response.is_error:
            message = f"API error (HTTP {response.status_code})"
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    desc = err_data.get("error_description") or err_data.get("error") or err_data.get("message")
                    if desc:
                        message = str(desc)
            except Exception:
                pass
            raise YouTrackAPIError(message, status_code=response.status_code, response_text=response.text)
            
        try:
            # If the response is empty (e.g. status code 204 No Content), return an empty dict or similar
            if response.status_code == 204 or not response.text:
                return {}
            return response.json()
        except Exception as e:
            raise YouTrackAPIError(f"Failed to parse JSON response: {e}") from e

def get_client(config_dir=None) -> YouTrackClient:
    """Helper function to create a YouTrackClient using the configured url and resolved token."""
    config = load_config(config_dir)
    token = resolve_token(config_dir)
    return YouTrackClient(config["url"], token)
