from dataclasses import dataclass
from typing import List
from youtrack_cli.client import YouTrackClient

@dataclass
class Project:
    id: str
    name: str
    short_name: str

def list_projects(client: YouTrackClient) -> List[Project]:
    """Fetch all projects from YouTrack and return them as Project domain objects."""
    data = client._request("GET", "api/admin/projects?fields=id,name,shortName")
    return [
        Project(
            id=item["id"],
            name=item["name"],
            short_name=item["shortName"]
        )
        for item in data
    ]

def create_project(client: YouTrackClient, name: str, short_name: str) -> Project:
    """Create a new project in YouTrack."""
    # 1. Fetch current user to use as project leader
    me_data = client._request("GET", "api/users/me?fields=id")
    leader_id = me_data["id"]
    
    # 2. POST payload to create project
    payload = {
        "name": name,
        "shortName": short_name,
        "leader": {
            "id": leader_id
        }
    }
    data = client._request("POST", "api/admin/projects?fields=id,name,shortName", json=payload)
    return Project(
        id=data["id"],
        name=data["name"],
        short_name=data["shortName"]
    )
