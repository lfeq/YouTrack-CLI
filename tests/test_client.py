import pytest
import respx
import httpx
from youtrack_cli.client import YouTrackClient, YouTrackAPIError

def test_client_headers_and_base_url():
    client = YouTrackClient("https://example.youtrack.cloud", "perm:my-token")
    assert client.base_url == "https://example.youtrack.cloud"
    assert client.token == "perm:my-token"
    assert client.client.headers["Authorization"] == "Bearer perm:my-token"
    assert client.client.headers["Accept"] == "application/json"

@respx.mock
def test_client_successful_request():
    client = YouTrackClient("https://example.youtrack.cloud", "perm:my-token")
    mock_route = respx.get("https://example.youtrack.cloud/api/users/me").respond(
        status_code=200,
        json={"id": "1-1", "login": "test-user"}
    )
    
    result = client._request("GET", "api/users/me")
    assert mock_route.called
    assert result == {"id": "1-1", "login": "test-user"}

@respx.mock
def test_client_http_error_handling_with_description():
    client = YouTrackClient("https://example.youtrack.cloud", "perm:my-token")
    respx.get("https://example.youtrack.cloud/api/users/me").respond(
        status_code=400,
        json={"error": "bad_request", "error_description": "Something went wrong in YouTrack"}
    )
    
    with pytest.raises(YouTrackAPIError) as exc_info:
        client._request("GET", "api/users/me")
    
    assert str(exc_info.value) == "Something went wrong in YouTrack"
    assert exc_info.value.status_code == 400

@respx.mock
def test_client_http_error_handling_without_description():
    client = YouTrackClient("https://example.youtrack.cloud", "perm:my-token")
    respx.get("https://example.youtrack.cloud/api/users/me").respond(
        status_code=401,
        text="Unauthorized"
    )
    
    with pytest.raises(YouTrackAPIError) as exc_info:
        client._request("GET", "api/users/me")
    
    assert "API error (HTTP 401)" in str(exc_info.value)
    assert exc_info.value.status_code == 401
