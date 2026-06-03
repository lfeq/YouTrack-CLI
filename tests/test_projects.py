from unittest.mock import MagicMock
import pytest
from youtrack_cli.client import YouTrackClient
from youtrack_cli.projects import list_projects, create_project, Project

def test_list_projects():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = [
        {"id": "0-1", "name": "Project One", "shortName": "ONE"},
        {"id": "0-2", "name": "Project Two", "shortName": "TWO"},
    ]
    
    projects = list_projects(mock_client)
    
    assert len(projects) == 2
    assert projects[0] == Project(id="0-1", name="Project One", short_name="ONE")
    assert projects[1] == Project(id="0-2", name="Project Two", short_name="TWO")
    
    mock_client._request.assert_called_once_with("GET", "api/admin/projects?fields=id,name,shortName")

def test_create_project():
    mock_client = MagicMock(spec=YouTrackClient)
    # The first call gets the user, the second creates the project.
    mock_client._request.side_effect = [
        {"id": "user-123"},
        {"id": "0-3", "name": "New Project", "shortName": "NEW"}
    ]
    
    project = create_project(mock_client, name="New Project", short_name="NEW")
    
    assert project == Project(id="0-3", name="New Project", short_name="NEW")
    
    assert mock_client._request.call_count == 2
    mock_client._request.assert_any_call("GET", "api/users/me?fields=id")
    mock_client._request.assert_any_call(
        "POST", 
        "api/admin/projects?fields=id,name,shortName", 
        json={
            "name": "New Project",
            "shortName": "NEW",
            "leader": {"id": "user-123"}
        }
    )
