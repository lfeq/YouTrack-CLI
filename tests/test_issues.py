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
            "query": "project: DEMO",
            "$top": 50
        }
    )
    
    # 2. Project + tag
    list_issues(client=mock_client, project_short_name="DEMO", tag="backend")
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login))",
            "query": "project: DEMO tag: backend",
            "$top": 50
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
            "query": 'project: DEMO priority: Critical tag: "front end" State: "In Progress" assignee: john.doe',
            "$top": 50
        }
    )

def test_list_issues_unresolved():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = []
    
    list_issues(client=mock_client, project_short_name="DEMO", unresolved=True)
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login))",
            "query": "project: DEMO #Unresolved",
            "$top": 50
        }
    )


def test_list_issues_top():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = []
    
    # 1. Default top is 50
    list_issues(client=mock_client, project_short_name="DEMO")
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login))",
            "query": "project: DEMO",
            "$top": 50
        }
    )
    
    # 2. Custom top = 10
    list_issues(client=mock_client, project_short_name="DEMO", top=10)
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login))",
            "query": "project: DEMO",
            "$top": 10
        }
    )
    
    # 3. top = 0 (no cap / omitted)
    list_issues(client=mock_client, project_short_name="DEMO", top=0)
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login))",
            "query": "project: DEMO"
        }
    )
    
    # 4. top = None (no cap / omitted)
    list_issues(client=mock_client, project_short_name="DEMO", top=None)
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login))",
            "query": "project: DEMO"
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


def test_format_issue_detail_table_populated():
    from youtrack_cli.issues import IssueDetail, Comment
    from youtrack_cli.formatters import format_issue_detail_table
    
    issue = IssueDetail(
        id="3-50",
        id_readable="YTCLI-50",
        summary="Epic issue summary",
        description="Epic description",
        status="In Progress",
        assignee="john.doe",
        comments=[
            Comment(id="c-1", text="First comment", author="john.doe", created=1690000000000),
            Comment(id="c-2", text="Second comment", author="jane.doe", created=1690001000000),
        ]
    )
    
    expected = (
        "ID: YTCLI-50\n"
        "Summary: Epic issue summary\n"
        "Status: In Progress\n"
        "Assignee: john.doe\n"
        "\n"
        "Description:\n"
        "Epic description\n"
        "\n"
        "Comments:\n"
        "[john.doe @ 2023-07-22 04:26:40]\n"
        "First comment\n"
        "\n"
        "[jane.doe @ 2023-07-22 04:43:20]\n"
        "Second comment"
    )
    assert format_issue_detail_table(issue) == expected


def test_format_issue_detail_table_empty_fields():
    from youtrack_cli.issues import IssueDetail
    from youtrack_cli.formatters import format_issue_detail_table
    
    issue = IssueDetail(
        id="3-50",
        id_readable="YTCLI-50",
        summary="Epic issue summary",
        description=None,
        status=None,
        assignee=None,
        comments=[]
    )
    
    expected = (
        "ID: YTCLI-50\n"
        "Summary: Epic issue summary\n"
        "Status: \n"
        "Assignee: \n"
        "\n"
        "Description:\n"
        "\n"
        "\n"
        "Comments:\n"
        "No comments."
    )
    assert format_issue_detail_table(issue) == expected


def test_format_issue_detail_json():
    from youtrack_cli.issues import IssueDetail, Comment
    from youtrack_cli.formatters import format_issue_detail_json
    import json
    
    issue = IssueDetail(
        id="3-50",
        id_readable="YTCLI-50",
        summary="Epic issue summary",
        description="Epic description",
        status="In Progress",
        assignee="john.doe",
        comments=[
            Comment(id="c-1", text="First comment", author="john.doe", created=1690000000000),
        ]
    )
    
    result = format_issue_detail_json(issue)
    parsed = json.loads(result)
    assert parsed["id"] == "3-50"
    assert parsed["id_readable"] == "YTCLI-50"
    assert parsed["summary"] == "Epic issue summary"
    assert parsed["description"] == "Epic description"
    assert parsed["status"] == "In Progress"
    assert parsed["assignee"] == "john.doe"
    assert parsed["comments"] == [
        {"id": "c-1", "text": "First comment", "author": "john.doe", "created": 1690000000000}
    ]



def test_link_subtask_success():
    from youtrack_cli.issues import link_subtask
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = {}

    link_subtask(mock_client, child_id="DEMO-43", parent_id="DEMO-42")

    mock_client._request.assert_called_once_with(
        "POST",
        "api/commands",
        json={
            "query": "subtask of DEMO-42",
            "issues": [{"idReadable": "DEMO-43"}]
        }
    )


def test_link_subtask_failure():
    from youtrack_cli.issues import link_subtask
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = YouTrackAPIError("API error")

    with pytest.raises(YouTrackAPIError) as exc_info:
        link_subtask(mock_client, child_id="DEMO-43", parent_id="DEMO-42")

    assert "API error" in str(exc_info.value)


def test_create_issue_with_parent_success():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = [
        [
            {"id": "0-0", "name": "Demo Project", "shortName": "DEMO"},
        ],
        {
            "id": "2-100",
            "idReadable": "DEMO-43",
            "summary": "Child issue",
        },
        {}
    ]

    issue = create_issue(
        client=mock_client,
        project_short_name="DEMO",
        summary="Child issue",
        parent="DEMO-42"
    )

    assert issue.id_readable == "DEMO-43"
    assert mock_client._request.call_count == 3
    mock_client._request.assert_any_call("GET", "api/admin/projects?fields=id,shortName")
    mock_client._request.assert_any_call(
        "POST",
        "api/issues?fields=id,idReadable,summary,description",
        json={
            "project": {"id": "0-0"},
            "summary": "Child issue",
        }
    )
    mock_client._request.assert_any_call(
        "POST",
        "api/commands",
        json={
            "query": "subtask of DEMO-42",
            "issues": [{"idReadable": "DEMO-43"}]
        }
    )


def test_create_issue_with_parent_linking_fails():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = [
        [
            {"id": "0-0", "name": "Demo Project", "shortName": "DEMO"},
        ],
        {
            "id": "2-100",
            "idReadable": "DEMO-43",
            "summary": "Child issue",
        },
        YouTrackAPIError("Linking failed")
    ]

    with pytest.raises(YouTrackAPIError) as exc_info:
        create_issue(
            client=mock_client,
            project_short_name="DEMO",
            summary="Child issue",
            parent="DEMO-42"
        )

    assert "Linking failed" in str(exc_info.value)
    # Verify that the create POST call was still made (issue was created, not rolled back)
    mock_client._request.assert_any_call(
        "POST",
        "api/issues?fields=id,idReadable,summary,description",
        json={
            "project": {"id": "0-0"},
            "summary": "Child issue",
        }
    )


def test_add_comment_success():
    from youtrack_cli.issues import add_comment, Comment
    mock_client = MagicMock(spec=YouTrackClient)
    
    mock_client._request.return_value = {
        "id": "comment-1",
        "text": "Progress update",
        "created": 1690000000000,
        "author": {
            "login": "john.doe",
            "name": "John Doe",
        }
    }
    
    comment = add_comment(mock_client, "DEMO-42", "Progress update")
    
    assert comment == Comment(
        id="comment-1",
        text="Progress update",
        author="john.doe",
        created=1690000000000
    )
    
    mock_client._request.assert_called_once_with(
        "POST",
        "api/issues/DEMO-42/comments?fields=id,text,author(id,login,name),created",
        json={"text": "Progress update"}
    )


def test_add_comment_missing_author():
    from youtrack_cli.issues import add_comment, Comment
    mock_client = MagicMock(spec=YouTrackClient)
    
    mock_client._request.return_value = {
        "id": "comment-1",
        "text": "Progress update",
        "created": 1690000000000,
        "author": None
    }
    
    comment = add_comment(mock_client, "DEMO-42", "Progress update")
    
    assert comment == Comment(
        id="comment-1",
        text="Progress update",
        author="",
        created=1690000000000
    )


def test_show_issue_success_with_comments():
    from youtrack_cli.issues import show_issue, IssueDetail, Comment
    mock_client = MagicMock(spec=YouTrackClient)
    
    mock_client._request.return_value = {
        "id": "3-50",
        "idReadable": "YTCLI-50",
        "summary": "Epic issue summary",
        "description": "Epic description",
        "customFields": [
            {
                "name": "State",
                "value": {"name": "In Progress"}
            },
            {
                "name": "Assignee",
                "value": {"login": "john.doe"}
            }
        ],
        "comments": [
            {
                "id": "7-1",
                "text": "First comment",
                "created": 1690000000000,
                "author": {"login": "john.doe"}
            }
        ]
    }
    
    issue_detail = show_issue(mock_client, "YTCLI-50")
    
    assert issue_detail.id == "3-50"
    assert issue_detail.id_readable == "YTCLI-50"
    assert issue_detail.summary == "Epic issue summary"
    assert issue_detail.description == "Epic description"
    assert issue_detail.status == "In Progress"
    assert issue_detail.assignee == "john.doe"
    assert len(issue_detail.comments) == 1
    assert issue_detail.comments[0] == Comment(
        id="7-1",
        text="First comment",
        author="john.doe",
        created=1690000000000
    )
    
    url = "api/issues/YTCLI-50?fields=id,idReadable,summary,description,customFields(name,value(name,login)),comments(id,text,author(id,login,name),created)"
    mock_client._request.assert_called_once_with("GET", url)


def test_show_issue_success_no_comments():
    from youtrack_cli.issues import show_issue, IssueDetail
    mock_client = MagicMock(spec=YouTrackClient)
    
    mock_client._request.return_value = {
        "id": "3-50",
        "idReadable": "YTCLI-50",
        "summary": "Epic issue summary",
        "description": "Epic description",
        "customFields": [],
        "comments": None
    }
    
    issue_detail = show_issue(mock_client, "YTCLI-50")
    
    assert issue_detail.id == "3-50"
    assert issue_detail.id_readable == "YTCLI-50"
    assert issue_detail.summary == "Epic issue summary"
    assert issue_detail.description == "Epic description"
    assert issue_detail.status is None
    assert issue_detail.assignee is None
    assert issue_detail.comments == []


def test_show_issue_api_error():
    from youtrack_cli.issues import show_issue
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = YouTrackAPIError("Issue not found", status_code=404)
    
    with pytest.raises(YouTrackAPIError) as exc_info:
        show_issue(mock_client, "YTCLI-999")
        
    assert "Issue not found" in str(exc_info.value)
    assert exc_info.value.status_code == 404


def test_update_issue_description():
    from youtrack_cli.issues import update_issue, Issue
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = {
        "id": "3-50",
        "idReadable": "YTCLI-50",
        "summary": "Original summary",
        "description": "New description",
        "customFields": [
            {"name": "State", "value": {"name": "In Progress"}},
            {"name": "Assignee", "value": {"login": "john.doe"}}
        ]
    }

    issue = update_issue(mock_client, "YTCLI-50", description="New description")

    assert issue == Issue(
        id="3-50",
        id_readable="YTCLI-50",
        summary="Original summary",
        description="New description",
        status="In Progress",
        assignee="john.doe"
    )

    fields = "id,idReadable,summary,description,customFields(name,value(name,login))"
    mock_client._request.assert_called_once_with(
        "POST",
        f"api/issues/YTCLI-50?fields={fields}",
        json={"description": "New description"}
    )


def test_update_issue_summary():
    from youtrack_cli.issues import update_issue, Issue
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = {
        "id": "3-50",
        "idReadable": "YTCLI-50",
        "summary": "New summary",
        "description": "Original description",
        "customFields": []
    }

    issue = update_issue(mock_client, "YTCLI-50", summary="New summary")

    assert issue == Issue(
        id="3-50",
        id_readable="YTCLI-50",
        summary="New summary",
        description="Original description",
        status=None,
        assignee=None
    )

    fields = "id,idReadable,summary,description,customFields(name,value(name,login))"
    mock_client._request.assert_called_once_with(
        "POST",
        f"api/issues/YTCLI-50?fields={fields}",
        json={"summary": "New summary"}
    )


def test_update_issue_both():
    from youtrack_cli.issues import update_issue, Issue
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = {
        "id": "3-50",
        "idReadable": "YTCLI-50",
        "summary": "New summary",
        "description": "New description",
        "customFields": []
    }

    issue = update_issue(mock_client, "YTCLI-50", description="New description", summary="New summary")

    assert issue == Issue(
        id="3-50",
        id_readable="YTCLI-50",
        summary="New summary",
        description="New description",
        status=None,
        assignee=None
    )

    fields = "id,idReadable,summary,description,customFields(name,value(name,login))"
    mock_client._request.assert_called_once_with(
        "POST",
        f"api/issues/YTCLI-50?fields={fields}",
        json={"description": "New description", "summary": "New summary"}
    )


def test_update_issue_none_raises_error():
    from youtrack_cli.issues import update_issue
    mock_client = MagicMock(spec=YouTrackClient)

    with pytest.raises(ValueError) as exc_info:
        update_issue(mock_client, "YTCLI-50")

    assert "At least one of description or summary must be provided" in str(exc_info.value)
    mock_client._request.assert_not_called()













