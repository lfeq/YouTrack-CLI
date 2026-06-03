from dataclasses import dataclass
from typing import List
from youtrack_cli.client import YouTrackClient

@dataclass
class Tag:
    id: str
    name: str

def create_tag(client: YouTrackClient, name: str) -> Tag:
    """Create a new tag in YouTrack."""
    payload = {
        "name": name
    }
    data = client._request("POST", "api/tags?fields=id,name", json=payload)
    return Tag(
        id=data["id"],
        name=data["name"]
    )

def list_tags(client: YouTrackClient) -> List[Tag]:
    """List all tags visible to the authenticated user."""
    data = client._request("GET", "api/tags?fields=id,name")
    return [Tag(id=item["id"], name=item["name"]) for item in data]

