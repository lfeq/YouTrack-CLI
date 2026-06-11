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
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))",
            "query": "project: DEMO #Unresolved sort by: priority asc, State asc",
            "$top": 50
        }
    )
    
    # 2. Project + tag
    list_issues(client=mock_client, project_short_name="DEMO", tag="backend")
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))",
            "query": "project: DEMO tag: backend #Unresolved sort by: priority asc, State asc",
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
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))",
            "query": 'project: DEMO priority: Critical tag: "front end" State: "In Progress" assignee: john.doe sort by: priority asc, State asc',
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
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))",
            "query": "project: DEMO #Unresolved sort by: priority asc, State asc",
            "$top": 50
        }
    )

def test_list_issues_all():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = []
    
    list_issues(client=mock_client, project_short_name="DEMO", all=True)
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))",
            "query": "project: DEMO sort by: priority asc, State asc",
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
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))",
            "query": "project: DEMO #Unresolved sort by: priority asc, State asc",
            "$top": 50
        }
    )
    
    # 2. Custom top = 10
    list_issues(client=mock_client, project_short_name="DEMO", top=10)
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))",
            "query": "project: DEMO #Unresolved sort by: priority asc, State asc",
            "$top": 10
        }
    )
    
    # 3. top = 0 (no cap / omitted)
    list_issues(client=mock_client, project_short_name="DEMO", top=0)
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))",
            "query": "project: DEMO #Unresolved sort by: priority asc, State asc"
        }
    )
    
    # 4. top = None (no cap / omitted)
    list_issues(client=mock_client, project_short_name="DEMO", top=None)
    mock_client._request.assert_called_with(
        "GET",
        "api/issues",
        params={
            "fields": "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))",
            "query": "project: DEMO #Unresolved sort by: priority asc, State asc"
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


def test_list_issues_priority_parsing():
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
                },
                {
                    "name": "Priority",
                    "value": {"name": "Critical"}
                }
            ]
        }
    ]
    
    issues = list_issues(client=mock_client, project_short_name="DEMO")
    
    assert len(issues) == 1
    assert issues[0].priority == "Critical"


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


def test_format_issue_priorities_table_empty():
    from youtrack_cli.formatters import format_issue_priorities_table
    assert format_issue_priorities_table([]) == "No priorities found."


def test_format_issue_priorities_table_non_empty():
    from youtrack_cli.formatters import format_issue_priorities_table
    priorities = ["Critical", "Major", "Normal", "Minor"]
    expected = (
        "PRIORITY\n"
        "--------\n"
        "Critical\n"
        "Major   \n"
        "Normal  \n"
        "Minor   "
    )
    assert format_issue_priorities_table(priorities) == expected


def test_format_issue_priorities_json():
    from youtrack_cli.formatters import format_issue_priorities_json
    import json
    priorities = ["Critical", "Major"]
    result = format_issue_priorities_json(priorities)
    parsed = json.loads(result)
    assert parsed == ["Critical", "Major"]



def test_list_issue_priorities_success():
    from youtrack_cli.issues import list_issue_priorities
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
                "field": {"name": "Priority"},
                "bundle": {
                    "values": [
                        {"name": "Critical"},
                        {"name": "Major"},
                        {"name": "Normal"},
                        {"name": "Minor"}
                    ]
                }
            }
        ]
    ]

    priorities = list_issue_priorities(mock_client, "DEMO")
    assert priorities == ["Critical", "Major", "Normal", "Minor"]
    assert mock_client._request.call_count == 2
    mock_client._request.assert_any_call("GET", "api/admin/projects?fields=id,shortName")
    mock_client._request.assert_any_call(
        "GET",
        "api/admin/projects/0-0/customFields?fields=field(name),bundle(values(name))"
    )


def test_list_issue_priorities_project_not_found():
    from youtrack_cli.issues import list_issue_priorities
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = [
        {"id": "0-1", "name": "Other Project", "shortName": "OTHER"},
    ]

    with pytest.raises(YouTrackAPIError) as exc_info:
        list_issue_priorities(mock_client, "DEMO")

    assert "Project with short ID 'DEMO' not found" in str(exc_info.value)
    assert mock_client._request.call_count == 1
    mock_client._request.assert_called_once_with("GET", "api/admin/projects?fields=id,shortName")


def test_list_issue_priorities_no_priority_field():
    from youtrack_cli.issues import list_issue_priorities
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

    priorities = list_issue_priorities(mock_client, "DEMO")
    assert priorities == []
    assert mock_client._request.call_count == 2
    mock_client._request.assert_any_call("GET", "api/admin/projects?fields=id,shortName")
    mock_client._request.assert_any_call(
        "GET",
        "api/admin/projects/0-0/customFields?fields=field(name),bundle(values(name))"
    )




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
    
    url = "api/issues/YTCLI-50?fields=id,idReadable,summary,description,customFields(name,value(name,login)),comments(id,text,author(id,login,name),created),links(direction,linkType(name),issues(idReadable,resolved,summary))"
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


def test_build_issue_list_query_default():
    from youtrack_cli.issues import build_issue_list_query
    query = build_issue_list_query(project_short_name="YTCLI")
    assert query == "project: YTCLI #Unresolved sort by: priority asc, State asc"


def test_build_issue_list_query_all():
    from youtrack_cli.issues import build_issue_list_query
    query = build_issue_list_query(project_short_name="YTCLI", all=True)
    assert query == "project: YTCLI sort by: priority asc, State asc"


def test_build_issue_list_query_status():
    from youtrack_cli.issues import build_issue_list_query
    query = build_issue_list_query(project_short_name="YTCLI", status="Fixed")
    assert query == "project: YTCLI State: Fixed sort by: priority asc, State asc"
    
    query_space = build_issue_list_query(project_short_name="YTCLI", status="In Progress")
    assert query_space == 'project: YTCLI State: "In Progress" sort by: priority asc, State asc'


def test_build_issue_list_query_raw_query_no_sort():
    from youtrack_cli.issues import build_issue_list_query
    query = build_issue_list_query(project_short_name="YTCLI", query="priority: Critical")
    assert query == "project: YTCLI priority: Critical sort by: priority asc, State asc"


def test_build_issue_list_query_raw_query_with_sort():
    from youtrack_cli.issues import build_issue_list_query
    # with lowercase sort by
    query1 = build_issue_list_query(project_short_name="YTCLI", query="assignee: me sort by: created desc")
    assert query1 == "project: YTCLI assignee: me sort by: created desc"

    # with uppercase SORT BY
    query2 = build_issue_list_query(project_short_name="YTCLI", query="assignee: me SORT BY: created desc")
    assert query2 == "project: YTCLI assignee: me SORT BY: created desc"


def test_build_issue_list_query_composition():
    from youtrack_cli.issues import build_issue_list_query
    query = build_issue_list_query(project_short_name="YTCLI", tag="backend", assignee="lorenz")
    assert query == "project: YTCLI tag: backend assignee: lorenz #Unresolved sort by: priority asc, State asc"


def test_build_issue_list_query_status_and_all():
    from youtrack_cli.issues import build_issue_list_query
    query = build_issue_list_query(project_short_name="YTCLI", status="Fixed", all=True)
    assert query == "project: YTCLI State: Fixed sort by: priority asc, State asc"


def test_add_dependency_success():
    from youtrack_cli.issues import add_dependency
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = {}

    add_dependency(mock_client, issue_id="DEMO-43", target_id="DEMO-42")

    mock_client._request.assert_called_once_with(
        "POST",
        "api/commands",
        json={
            "query": "depends on DEMO-42",
            "issues": [{"idReadable": "DEMO-43"}]
        }
    )


def test_add_dependency_failure():
    from youtrack_cli.issues import add_dependency
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = YouTrackAPIError("API error")

    with pytest.raises(YouTrackAPIError) as exc_info:
        add_dependency(mock_client, issue_id="DEMO-43", target_id="DEMO-42")

    assert "API error" in str(exc_info.value)


def test_remove_dependency_success():
    from youtrack_cli.issues import remove_dependency
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = {}

    remove_dependency(mock_client, issue_id="DEMO-43", target_id="DEMO-42")

    mock_client._request.assert_called_once_with(
        "POST",
        "api/commands",
        json={
            "query": "remove depends on DEMO-42",
            "issues": [{"idReadable": "DEMO-43"}]
        }
    )


def test_remove_dependency_failure():
    from youtrack_cli.issues import remove_dependency
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.side_effect = YouTrackAPIError("API error")

    with pytest.raises(YouTrackAPIError) as exc_info:
        remove_dependency(mock_client, issue_id="DEMO-43", target_id="DEMO-42")

    assert "API error" in str(exc_info.value)


def test_parse_dependency_links():
    from youtrack_cli.issues import parse_dependency_links

    # 1. Empty/None links
    assert parse_dependency_links([]) == ([], [], False)
    assert parse_dependency_links(None) == ([], [], False)

    # 2. Outward dependencies (depends_on)
    links = [
        {
            "direction": "OUTWARD",
            "linkType": {"name": "Depend"},
            "issues": [
                {"idReadable": "DEMO-42", "summary": "Prereq 1", "resolved": False},
                {"idReadable": "DEMO-43", "summary": "Prereq 2", "resolved": True}
            ]
        }
    ]
    depends_on, required_for, blocked = parse_dependency_links(links)
    assert depends_on == [
        {"id": "DEMO-42", "summary": "Prereq 1", "resolved": False},
        {"id": "DEMO-43", "summary": "Prereq 2", "resolved": True}
    ]
    assert required_for == []
    assert blocked is True

    # 3. Incoming dependencies (required_for)
    links = [
        {
            "direction": "INWARD",
            "linkType": {"name": "Depend"},
            "issues": [
                {"idReadable": "DEMO-44", "summary": "Subsequent 1", "resolved": False}
            ]
        }
    ]
    depends_on, required_for, blocked = parse_dependency_links(links)
    assert depends_on == []
    assert required_for == [
        {"id": "DEMO-44", "summary": "Subsequent 1", "resolved": False}
    ]
    assert blocked is False

    # 4. Mixed unresolved / resolved outgoing dependencies
    links = [
        {
            "direction": "OUTWARD",
            "linkType": {"name": "Depend"},
            "issues": [
                {"idReadable": "DEMO-43", "summary": "Prereq 2", "resolved": True}
            ]
        }
    ]
    depends_on, required_for, blocked = parse_dependency_links(links)
    assert blocked is False

    # 5. Unrelated link types ignored
    links = [
        {
            "direction": "OUTWARD",
            "linkType": {"name": "Subtask"},
            "issues": [
                {"idReadable": "DEMO-45", "summary": "Epic parent", "resolved": False}
            ]
        }
    ]
    depends_on, required_for, blocked = parse_dependency_links(links)
    assert depends_on == []
    assert required_for == []
    assert blocked is False


def test_list_issues_with_dependencies():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = [
        {
            "id": "2-100",
            "idReadable": "DEMO-42",
            "summary": "Fix login bug",
            "customFields": [],
            "links": [
                {
                    "direction": "OUTWARD",
                    "linkType": {"name": "Depend"},
                    "issues": [
                        {"idReadable": "DEMO-43", "summary": "Unresolved dep", "resolved": False}
                    ]
                }
            ]
        },
        {
            "id": "2-101",
            "idReadable": "DEMO-43",
            "summary": "Unresolved dep",
            "customFields": [],
            "links": []
        }
    ]

    issues = list_issues(client=mock_client, project_short_name="DEMO")
    assert len(issues) == 2
    assert issues[0].blocked is True
    assert issues[1].blocked is False

    # Check that requested fields now include links(...)
    expected_fields = "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))"
    mock_client._request.assert_called_once_with(
        "GET",
        "api/issues",
        params={
            "fields": expected_fields,
            "query": "project: DEMO #Unresolved sort by: priority asc, State asc",
            "$top": 50
        }
    )


def test_format_issues_table_blocked():
    from youtrack_cli.formatters import format_issues_table
    from youtrack_cli.issues import Issue

    issues = [
        Issue(
            id="1",
            id_readable="DEMO-42",
            summary="Blocked issue summary",
            description="desc",
            status="Submitted",
            assignee="bob",
            priority="Normal",
            blocked=True
        ),
        Issue(
            id="2",
            id_readable="DEMO-43",
            summary="Normal issue summary",
            description="desc",
            status="Submitted",
            assignee="bob",
            priority="Normal",
            blocked=False
        )
    ]

    output = format_issues_table(issues)
    assert "[BLOCKED] Blocked issue summary" in output
    assert "Normal issue summary" in output
    assert "[BLOCKED] Normal issue summary" not in output


def test_show_issue_with_dependencies():
    from youtrack_cli.issues import show_issue
    mock_client = MagicMock(spec=YouTrackClient)

    mock_client._request.return_value = {
        "id": "3-50",
        "idReadable": "YTCLI-50",
        "summary": "Epic issue summary",
        "description": "Epic description",
        "customFields": [],
        "comments": [],
        "links": [
            {
                "direction": "OUTWARD",
                "linkType": {"name": "Depend"},
                "issues": [
                    {"idReadable": "YTCLI-42", "summary": "Fix login bug", "resolved": False},
                    {"idReadable": "YTCLI-43", "summary": "Add tags", "resolved": True}
                ]
            },
            {
                "direction": "INWARD",
                "linkType": {"name": "Depend"},
                "issues": [
                    {"idReadable": "YTCLI-44", "summary": "Release version 1.0.0", "resolved": False}
                ]
            }
        ]
    }

    issue_detail = show_issue(mock_client, "YTCLI-50")
    assert issue_detail.depends_on == [
        {"id": "YTCLI-42", "summary": "Fix login bug", "resolved": False},
        {"id": "YTCLI-43", "summary": "Add tags", "resolved": True}
    ]
    assert issue_detail.required_for == [
        {"id": "YTCLI-44", "summary": "Release version 1.0.0", "resolved": False}
    ]

    expected_url = "api/issues/YTCLI-50?fields=id,idReadable,summary,description,customFields(name,value(name,login)),comments(id,text,author(id,login,name),created),links(direction,linkType(name),issues(idReadable,resolved,summary))"
    mock_client._request.assert_called_once_with("GET", expected_url)


def test_format_issue_detail_table_dependencies():
    from youtrack_cli.formatters import format_issue_detail_table
    from youtrack_cli.issues import IssueDetail

    issue = IssueDetail(
        id="3-50",
        id_readable="YTCLI-50",
        summary="Epic issue summary",
        description="Epic description",
        status="Open",
        assignee="bob",
        comments=[],
        depends_on=[
            {"id": "YTCLI-42", "summary": "Fix login bug", "resolved": False},
            {"id": "YTCLI-43", "summary": "Add tags", "resolved": True}
        ],
        required_for=[
            {"id": "YTCLI-44", "summary": "Release version 1.0.0", "resolved": False}
        ]
    )

    output = format_issue_detail_table(issue)
    assert "Depends on:" in output
    assert "- YTCLI-42: Fix login bug [unresolved] (BLOCKING)" in output
    assert "- YTCLI-43: Add tags [resolved]" in output
    assert "Required for:" in output
    assert "- YTCLI-44: Release version 1.0.0 [unresolved]" in output


def test_parse_subtask_links_basics():
    from youtrack_cli.issues import parse_subtask_links

    # 1. Empty/None links
    assert parse_subtask_links([]) == (None, [])
    assert parse_subtask_links(None) == (None, [])

    # 2. Non-Subtask link types ignored
    links = [
        {
            "direction": "OUTWARD",
            "linkType": {"name": "Depend"},
            "issues": [
                {"idReadable": "DEMO-42", "summary": "Dependency 1", "resolved": False}
            ]
        }
    ]
    assert parse_subtask_links(links) == (None, [])


def test_parse_subtask_links_directionality():
    from youtrack_cli.issues import parse_subtask_links

    # 1. INWARD maps to parent (single dict)
    links = [
        {
            "direction": "INWARD",
            "linkType": {"name": "Subtask"},
            "issues": [
                {"idReadable": "YTCLI-41", "summary": "Epic summary", "resolved": False}
            ]
        }
    ]
    parent, subtasks = parse_subtask_links(links)
    assert parent == {"id": "YTCLI-41", "summary": "Epic summary", "resolved": False}
    assert subtasks == []

    # 2. OUTWARD maps to subtasks list
    links = [
        {
            "direction": "OUTWARD",
            "linkType": {"name": "Subtask"},
            "issues": [
                {"idReadable": "YTCLI-42", "summary": "Subtask 1", "resolved": False},
                {"idReadable": "YTCLI-43", "summary": "Subtask 2", "resolved": True}
            ]
        }
    ]
    parent, subtasks = parse_subtask_links(links)
    assert parent is None
    assert subtasks == [
        {"id": "YTCLI-42", "summary": "Subtask 1", "resolved": False},
        {"id": "YTCLI-43", "summary": "Subtask 2", "resolved": True}
    ]

    # 3. BOTH direction is skipped
    links = [
        {
            "direction": "BOTH",
            "linkType": {"name": "Subtask"},
            "issues": [
                {"idReadable": "YTCLI-44", "summary": "Both summary", "resolved": False}
            ]
        }
    ]
    parent, subtasks = parse_subtask_links(links)
    assert parent is None
    assert subtasks == []

    # 4. Multiple INWARD links: first wins, others ignored
    links = [
        {
            "direction": "INWARD",
            "linkType": {"name": "Subtask"},
            "issues": [
                {"idReadable": "YTCLI-41", "summary": "Epic 1", "resolved": False},
                {"idReadable": "YTCLI-45", "summary": "Epic 2", "resolved": True}
            ]
        }
    ]
    parent, subtasks = parse_subtask_links(links)
    assert parent == {"id": "YTCLI-41", "summary": "Epic 1", "resolved": False}
    assert subtasks == []


def test_show_issue_with_hierarchy_and_dependencies():
    from youtrack_cli.issues import show_issue
    mock_client = MagicMock(spec=YouTrackClient)

    mock_client._request.return_value = {
        "id": "3-50",
        "idReadable": "YTCLI-50",
        "summary": "Epic issue summary",
        "description": "Epic description",
        "customFields": [],
        "comments": [],
        "links": [
            {
                "direction": "OUTWARD",
                "linkType": {"name": "Depend"},
                "issues": [
                    {"idReadable": "YTCLI-42", "summary": "Fix login bug", "resolved": False}
                ]
            },
            {
                "direction": "INWARD",
                "linkType": {"name": "Subtask"},
                "issues": [
                    {"idReadable": "YTCLI-41", "summary": "Parent Epic", "resolved": True}
                ]
            },
            {
                "direction": "OUTWARD",
                "linkType": {"name": "Subtask"},
                "issues": [
                    {"idReadable": "YTCLI-43", "summary": "Subtask task", "resolved": False}
                ]
            }
        ]
    }

    issue_detail = show_issue(mock_client, "YTCLI-50")
    # Verify dependencies are still parsed correctly
    assert issue_detail.depends_on == [
        {"id": "YTCLI-42", "summary": "Fix login bug", "resolved": False}
    ]
    # Verify parent and subtasks are parsed correctly
    assert issue_detail.parent == {"id": "YTCLI-41", "summary": "Parent Epic", "resolved": True}
    assert issue_detail.subtasks == [
        {"id": "YTCLI-43", "summary": "Subtask task", "resolved": False}
    ]


def test_format_issue_detail_table_hierarchy():
    from youtrack_cli.formatters import format_issue_detail_table
    from youtrack_cli.issues import IssueDetail

    issue = IssueDetail(
        id="3-50",
        id_readable="YTCLI-50",
        summary="Mid-tree issue summary",
        description="Description",
        status="Open",
        assignee="bob",
        comments=[],
        parent={"id": "YTCLI-41", "summary": "Parent Epic", "resolved": True},
        subtasks=[
            {"id": "YTCLI-43", "summary": "Subtask task", "resolved": False}
        ]
    )

    output = format_issue_detail_table(issue)
    assert "Parent: YTCLI-41: Parent Epic [resolved]" in output
    assert "Subtasks:" in output
    assert "- YTCLI-43: Subtask task [unresolved]" in output


def test_format_issue_detail_table_no_hierarchy():
    from youtrack_cli.formatters import format_issue_detail_table
    from youtrack_cli.issues import IssueDetail

    issue = IssueDetail(
        id="3-50",
        id_readable="YTCLI-50",
        summary="No hierarchy summary",
        description="Description",
        status="Open",
        assignee="bob",
        comments=[]
    )

    output = format_issue_detail_table(issue)
    assert "Parent:" not in output
    assert "Subtasks:" not in output


def test_format_issue_detail_json_hierarchy():
    from youtrack_cli.formatters import format_issue_detail_json
    from youtrack_cli.issues import IssueDetail
    import json

    issue = IssueDetail(
        id="3-50",
        id_readable="YTCLI-50",
        summary="Epic issue summary",
        description="Epic description",
        status="In Progress",
        assignee="john.doe",
        comments=[],
        parent={"id": "YTCLI-41", "summary": "Parent Epic", "resolved": True},
        subtasks=[
            {"id": "YTCLI-43", "summary": "Subtask task", "resolved": False}
        ]
    )

    result = format_issue_detail_json(issue)
    parsed = json.loads(result)
    assert parsed["parent"] == {"id": "YTCLI-41", "summary": "Parent Epic", "resolved": True}
    assert parsed["subtasks"] == [
        {"id": "YTCLI-43", "summary": "Subtask task", "resolved": False}
    ]
