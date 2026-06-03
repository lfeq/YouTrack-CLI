from unittest.mock import MagicMock
import pytest
from youtrack_cli.client import YouTrackClient, YouTrackAPIError
from youtrack_cli.issues import create_issue, Issue, list_issues, move_issue, tag_issue


def test_create_issue_basic():
    mock_client = MagicMock(spec=YouTrackClient)
    # Mocking two client request calls:
    # 1. GET api/admin/projects to map shortName to ID
    # 2. POST api/issues to create the issue
    mock_client._request.side_effect = [
        [
            {"id": "0-0", "name": "Demo Project", "shortName": "DEMO"},
            {"id": "0-1", "name": "Other Project", "shortName": "OTHER"},
        ],
        {
            "id": "2-100",
            "idReadable": "DEMO-42",
            "summary": "Fix login bug",
            "description": "User cannot login",
        }
    ]

    issue = create_issue(
        client=mock_client,
        project_short_name="DEMO",
        summary="Fix login bug",
        description="User cannot login"
    )

    assert issue == Issue(
        id="2-100",
        id_readable="DEMO-42",
        summary="Fix login bug",
        description="User cannot login"
    )

    assert mock_client._request.call_count == 2
    mock_client._request.assert_any_call("GET", "api/admin/projects?fields=id,shortName")
    mock_client._request.assert_any_call(
        "POST",
        "api/issues?fields=id,idReadable,summary,description",
        json={
            "project": {"id": "0-0"},
            "summary": "Fix login bug",
            "description": "User cannot login"
        }
    )

def test_create_issue_project_not_found():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = [
        {"id": "0-1", "name": "Other Project", "shortName": "OTHER"},
    ]

    with pytest.raises(YouTrackAPIError) as exc_info:
        create_issue(
            client=mock_client,
            project_short_name="DEMO",
            summary="Fix login bug"
        )

    assert "Project with short ID 'DEMO' not found" in str(exc_info.value)
    mock_client._request.assert_called_once_with("GET", "api/admin/projects?fields=id,shortName")

def test_create_issue_with_optional_fields():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = [
        [
            {"id": "0-0", "name": "Demo Project", "shortName": "DEMO"},
        ],
        {
            "id": "2-100",
            "idReadable": "DEMO-42",
            "summary": "Fix login bug",
            "description": "User cannot login",
        }
    ]

    issue = create_issue(
        client=mock_client,
        project_short_name="DEMO",
        summary="Fix login bug",
        description="User cannot login",
        assignee="john.doe",
        priority="Critical",
        type_name="Bug"
    )

    assert issue.id_readable == "DEMO-42"
    assert mock_client._request.call_count == 2
    mock_client._request.assert_any_call(
        "POST",
        "api/issues?fields=id,idReadable,summary,description",
        json={
            "project": {"id": "0-0"},
            "summary": "Fix login bug",
            "description": "User cannot login",
            "customFields": [
                {
                    "name": "Assignee",
                    "$type": "SingleUserIssueCustomField",
                    "value": {"login": "john.doe"}
                },
                {
                    "name": "Priority",
                    "$type": "SingleEnumIssueCustomField",
                    "value": {"name": "Critical"}
                },
                {
                    "name": "Type",
                    "$type": "SingleEnumIssueCustomField",
                    "value": {"name": "Bug"}
                }
            ]
        }
    )

def test_list_issues_query_merging():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = []
    
    # 1. Project only
    list_issues(client=mock_client, project_short_name="DEMO")
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login))",
            "query": "project: DEMO"
        }
    )
    
    # 2. Project + tag
    list_issues(client=mock_client, project_short_name="DEMO", tag="backend")
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login))",
            "query": "project: DEMO tag: backend"
        }
    )
    
    # 3. Project + tag (with space) + status + assignee + raw query
    list_issues(
        client=mock_client,
        project_short_name="DEMO",
        tag="front end",
        status="In Progress",
        assignee="john.doe",
        query="priority: Critical"
    )
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login))",
            "query": 'project: DEMO priority: Critical tag: "front end" State: "In Progress" assignee: john.doe'
        }
    )

def test_list_issues_parsing():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = [
        {
            "id": "2-100",
            "idReadable": "DEMO-42",
            "summary": "Fix login bug",
            "description": "User cannot login",
            "customFields": [
                {
                    "name": "State",
                    "value": {"name": "In Progress"}
                },
                {
                    "name": "Assignee",
                    "value": {"login": "john.doe", "name": "John Doe"}
                }
            ]
        },
        {
            "id": "2-101",
            "idReadable": "DEMO-43",
            "summary": "Add feature X",
            "customFields": []
        }
    ]
    
    issues = list_issues(client=mock_client, project_short_name="DEMO")
    
    assert len(issues) == 2
    assert issues[0] == Issue(
        id="2-100",
        id_readable="DEMO-42",
        summary="Fix login bug",
        description="User cannot login",
        status="In Progress",
        assignee="john.doe"
    )
    assert issues[1] == Issue(
        id="2-101",
        id_readable="DEMO-43",
        summary="Add feature X",
        description=None,
        status=None,
        assignee=None
    )


def test_move_issue_success():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = {
        "id": "2-100",
        "idReadable": "DEMO-42",
        "summary": "Fix login bug",
        "description": "User cannot login",
        "customFields": [
            {
                "name": "State",
                "value": {"name": "In Progress"}
            },
            {
                "name": "Assignee",
                "value": {"login": "john.doe"}
            }
        ]
    }

    issue = move_issue(client=mock_client, issue_id="DEMO-42", status="In Progress")

    assert issue == Issue(
        id="2-100",
        id_readable="DEMO-42",
        summary="Fix login bug",
        description="User cannot login",
        status="In Progress",
        assignee="john.doe"
    )

    mock_client._request.assert_called_once_with(
        "POST",
        "api/issues/DEMO-42?fields=id,idReadable,summary,description,customFields(name,value(name,login))",
        json={
            "customFields": [
                {
                    "name": "State",
                    "$type": "StateIssueCustomField",
                    "value": {"name": "In Progress"}
                }
            ]
        }
    )


def test_tag_issue_success():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = [
        [
            {"id": "6-0", "name": "backend"},
            {"id": "6-1", "name": "frontend"},
        ],
        {
            "id": "6-0",
            "name": "backend"
        }
    ]

    tag_issue(client=mock_client, issue_id="DEMO-42", tag_name="backend")

    assert mock_client._request.call_count == 2
    mock_client._request.assert_any_call("GET", "api/tags?fields=id,name")
    mock_client._request.assert_any_call(
        "POST",
        "api/issues/DEMO-42/tags?fields=id,name",
        json={"id": "6-0"}
    )


def test_tag_issue_not_found():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = [
        {"id": "6-1", "name": "frontend"},
    ]

    with pytest.raises(YouTrackAPIError) as exc_info:
        tag_issue(client=mock_client, issue_id="DEMO-42", tag_name="backend")

    assert "Tag 'backend' not found" in str(exc_info.value)
    mock_client._request.assert_called_once_with("GET", "api/tags?fields=id,name")


def test_create_issue_with_single_tag():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = [
        [
            {"id": "0-0", "name": "Demo Project", "shortName": "DEMO"},
        ],
        [
            {"id": "6-0", "name": "AFK"},
        ],
        {
            "id": "2-100",
            "idReadable": "DEMO-42",
            "summary": "Fix login bug",
            "description": "User cannot login",
        }
    ]

    issue = create_issue(
        client=mock_client,
        project_short_name="DEMO",
        summary="Fix login bug",
        description="User cannot login",
        tags=["AFK"]
    )

    assert issue.id_readable == "DEMO-42"
    assert mock_client._request.call_count == 3
    mock_client._request.assert_any_call("GET", "api/admin/projects?fields=id,shortName")
    mock_client._request.assert_any_call("GET", "api/tags?fields=id,name")
    mock_client._request.assert_any_call(
        "POST",
        "api/issues?fields=id,idReadable,summary,description",
        json={
            "project": {"id": "0-0"},
            "summary": "Fix login bug",
            "description": "User cannot login",
            "tags": [{"id": "6-0"}]
        }
    )


def test_create_issue_with_multiple_tags():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = [
        [
            {"id": "0-0", "name": "Demo Project", "shortName": "DEMO"},
        ],
        [
            {"id": "6-0", "name": "AFK"},
            {"id": "6-1", "name": "HITL"},
        ],
        {
            "id": "2-100",
            "idReadable": "DEMO-42",
            "summary": "Fix login bug",
        }
    ]

    issue = create_issue(
        client=mock_client,
        project_short_name="DEMO",
        summary="Fix login bug",
        tags=["AFK", "HITL"]
    )

    assert issue.id_readable == "DEMO-42"
    assert mock_client._request.call_count == 3
    mock_client._request.assert_any_call("GET", "api/admin/projects?fields=id,shortName")
    mock_client._request.assert_any_call("GET", "api/tags?fields=id,name")
    mock_client._request.assert_any_call(
        "POST",
        "api/issues?fields=id,idReadable,summary,description",
        json={
            "project": {"id": "0-0"},
            "summary": "Fix login bug",
            "tags": [{"id": "6-0"}, {"id": "6-1"}]
        }
    )


def test_create_issue_tag_not_found():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = [
        [
            {"id": "0-0", "name": "Demo Project", "shortName": "DEMO"},
        ],
        [
            {"id": "6-0", "name": "AFK"},
        ]
    ]

    with pytest.raises(YouTrackAPIError) as exc_info:
        create_issue(
            client=mock_client,
            project_short_name="DEMO",
            summary="Fix login bug",
            tags=["AFK", "HITL"]
        )

    assert "Tag 'HITL' not found. Create it first with: youtrack tag create --name HITL" in str(exc_info.value)
    assert mock_client._request.call_count == 2
    mock_client._request.assert_any_call("GET", "api/admin/projects?fields=id,shortName")
    mock_client._request.assert_any_call("GET", "api/tags?fields=id,name")
    for call in mock_client._request.call_args_list:
        assert call[0][0] != "POST"


def test_list_issue_types_success():
    from youtrack_cli.issues import list_issue_types
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = [
        [
            {"id": "0-0", "name": "Demo Project", "shortName": "DEMO"},
        ],
        [
            {
                "field": {"name": "Assignee"},
                "bundle": None
            },
            {
                "field": {"name": "Type"},
                "bundle": {
                    "values": [
                        {"name": "Bug"},
                        {"name": "Feature"},
                        {"name": "Task"}
                    ]
                }
            }
        ]
    ]

    types = list_issue_types(mock_client, "DEMO")
    assert types == ["Bug", "Feature", "Task"]
    assert mock_client._request.call_count == 2
    mock_client._request.assert_any_call("GET", "api/admin/projects?fields=id,shortName")
    mock_client._request.assert_any_call(
        "GET",
        "api/admin/projects/0-0/customFields?fields=field(name),bundle(values(name))"
    )


def test_list_issue_types_project_not_found():
    from youtrack_cli.issues import list_issue_types
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = [
        {"id": "0-1", "name": "Other Project", "shortName": "OTHER"},
    ]

    with pytest.raises(YouTrackAPIError) as exc_info:
        list_issue_types(mock_client, "DEMO")

    assert "Project with short ID 'DEMO' not found" in str(exc_info.value)
    assert mock_client._request.call_count == 1
    mock_client._request.assert_called_once_with("GET", "api/admin/projects?fields=id,shortName")


def test_list_issue_types_no_type_field():
    from youtrack_cli.issues import list_issue_types
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = [
        [
            {"id": "0-0", "name": "Demo Project", "shortName": "DEMO"},
        ],
        [
            {
                "field": {"name": "Assignee"},
                "bundle": None
            }
        ]
    ]

    types = list_issue_types(mock_client, "DEMO")
    assert types == []
    assert mock_client._request.call_count == 2
    mock_client._request.assert_any_call("GET", "api/admin/projects?fields=id,shortName")
    mock_client._request.assert_any_call(
        "GET",
        "api/admin/projects/0-0/customFields?fields=field(name),bundle(values(name))"
    )


def test_format_issue_types_table_empty():
    from youtrack_cli.formatters import format_issue_types_table
    assert format_issue_types_table([]) == "No types found."


def test_format_issue_types_table_non_empty():
    from youtrack_cli.formatters import format_issue_types_table
    types = ["Bug", "Feature", "Task"]
    expected = (
        "TYPE   \n"
        "-------\n"
        "Bug    \n"
        "Feature\n"
        "Task   "
    )
    assert format_issue_types_table(types) == expected


def test_format_issue_types_json():
    from youtrack_cli.formatters import format_issue_types_json
    import json
    types = ["Bug", "Feature"]
    result = format_issue_types_json(types)
    parsed = json.loads(result)
    assert parsed == ["Bug", "Feature"]






