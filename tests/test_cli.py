import os
from click.testing import CliRunner
from youtrack_cli.cli import main
from youtrack_cli.config import load_config, ConfigError

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "login" in result.output
    # Also assert commands structure / groups
    assert "Show this message and exit." in result.output

def test_cli_login_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    
    # We pass the env var YOUTRACK_CONFIG_DIR to CliRunner
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    url = "https://example.youtrack.cloud"
    token = "perm:test-token"
    
    result = runner.invoke(
        main, 
        ["login", "--url", url, "--token", token],
        env=env
    )
    
    assert result.exit_code == 0
    assert "Logged in to" in result.output or "Configuration saved" in result.output
    
    # Verify the config was actually saved
    config = load_config(config_dir=config_dir)
    assert config["url"] == url
    assert config["token"] == token

def test_cli_login_missing_args():
    runner = CliRunner()
    result = runner.invoke(main, ["login", "--url", "https://example.youtrack.cloud"])
    assert result.exit_code != 0
    assert "Error: Missing option" in result.output or "Error:" in result.output

import respx
from youtrack_cli.config import save_config

@respx.mock
def test_cli_project_list(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    mock_route = respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,name,shortName").respond(
        status_code=200,
        json=[
            {"id": "0-1", "name": "Project One", "shortName": "ONE"},
            {"id": "0-2", "name": "Project Two", "shortName": "TWO"},
        ]
    )
    
    result = runner.invoke(main, ["project", "list"], env=env)
    assert result.exit_code == 0
    assert "SHORT ID" in result.output
    assert "ONE" in result.output
    assert "Project One" in result.output
    assert "TWO" in result.output
    assert "Project Two" in result.output
    assert mock_route.called

@respx.mock
def test_cli_project_list_json(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,name,shortName").respond(
        status_code=200,
        json=[{"id": "0-1", "name": "Project One", "shortName": "ONE"}]
    )
    
    result = runner.invoke(main, ["project", "list", "--json"], env=env)
    assert result.exit_code == 0
    import json
    parsed = json.loads(result.output)
    assert len(parsed) == 1
    assert parsed[0]["short_name"] == "ONE"

@respx.mock
def test_cli_project_create_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    # Mock current user endpoint
    respx.get("https://example.youtrack.cloud/api/users/me?fields=id").respond(
        status_code=200,
        json={"id": "user-456"}
    )
    # Mock project creation endpoint
    respx.post("https://example.youtrack.cloud/api/admin/projects?fields=id,name,shortName").respond(
        status_code=200,
        json={"id": "0-9", "name": "My New Project", "shortName": "MNP"}
    )
    
    result = runner.invoke(
        main, 
        ["project", "create", "--name", "My New Project", "--id", "MNP"],
        env=env
    )
    assert result.exit_code == 0
    assert "Created project MNP" in result.output

@respx.mock
def test_cli_project_api_error(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,name,shortName").respond(
        status_code=403,
        json={"error": "forbidden", "error_description": "You do not have permission to view projects"}
    )
    
    result = runner.invoke(main, ["project", "list"], env=env)
    assert result.exit_code != 0
    assert "Error: You do not have permission to view projects" in result.output

@respx.mock
def test_cli_issue_create_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-0", "name": "Demo", "shortName": "DEMO"}]
    )
    respx.post("https://example.youtrack.cloud/api/issues?fields=id,idReadable,summary,description").respond(
        status_code=200,
        json={"id": "2-100", "idReadable": "DEMO-42", "summary": "Fix login bug"}
    )
    
    result = runner.invoke(
        main,
        ["issue", "create", "--project", "DEMO", "--summary", "Fix login bug"],
        env=env
    )
    assert result.exit_code == 0
    assert "Created issue DEMO-42" in result.output

@respx.mock
def test_cli_issue_create_with_optional_flags(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-0", "name": "Demo", "shortName": "DEMO"}]
    )
    # Check that customFields are sent correctly by matching payload in the mock if needed, or simply verify response.
    # We can inspect the request in the mock or assert respx state later.
    route = respx.post("https://example.youtrack.cloud/api/issues?fields=id,idReadable,summary,description").respond(
        status_code=200,
        json={"id": "2-100", "idReadable": "DEMO-42", "summary": "Fix login bug", "description": "some desc"}
    )
    
    result = runner.invoke(
        main,
        [
            "issue", "create",
            "--project", "DEMO",
            "--summary", "Fix login bug",
            "--description", "some desc",
            "--assignee", "john.doe",
            "--priority", "Critical",
            "--type", "Bug"
        ],
        env=env
    )
    assert result.exit_code == 0
    assert "Created issue DEMO-42" in result.output
    
    # Verify request payload
    assert route.called
    request_payload = route.calls.last.request.read().decode("utf-8")
    import json
    payload = json.loads(request_payload)
    assert payload["description"] == "some desc"
    assert len(payload["customFields"]) == 3
    assert payload["customFields"][0]["name"] == "Assignee"
    assert payload["customFields"][0]["value"]["login"] == "john.doe"
    assert payload["customFields"][1]["name"] == "Priority"
    assert payload["customFields"][1]["value"]["name"] == "Critical"
    assert payload["customFields"][2]["name"] == "Type"
    assert payload["customFields"][2]["value"]["name"] == "Bug"

@respx.mock
def test_cli_issue_create_json(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-0", "name": "Demo", "shortName": "DEMO"}]
    )
    respx.post("https://example.youtrack.cloud/api/issues?fields=id,idReadable,summary,description").respond(
        status_code=200,
        json={"id": "2-100", "idReadable": "DEMO-42", "summary": "Fix login bug", "description": "some desc"}
    )
    
    result = runner.invoke(
        main,
        ["issue", "create", "--project", "DEMO", "--summary", "Fix login bug", "--json"],
        env=env
    )
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert data["id"] == "2-100"
    assert data["id_readable"] == "DEMO-42"
    assert data["summary"] == "Fix login bug"
    assert data["description"] == "some desc"


@respx.mock
def test_cli_issue_create_with_tags(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-0", "name": "Demo", "shortName": "DEMO"}]
    )
    respx.get("https://example.youtrack.cloud/api/tags?fields=id,name").respond(
        status_code=200,
        json=[
            {"id": "6-0", "name": "AFK"},
            {"id": "6-1", "name": "HITL"},
        ]
    )
    route = respx.post("https://example.youtrack.cloud/api/issues?fields=id,idReadable,summary,description").respond(
        status_code=200,
        json={"id": "2-100", "idReadable": "DEMO-42", "summary": "Fix login bug"}
    )
    
    result = runner.invoke(
        main,
        [
            "issue", "create",
            "--project", "DEMO",
            "--summary", "Fix login bug",
            "--tag", "AFK",
            "--tag", "HITL"
        ],
        env=env
    )
    assert result.exit_code == 0
    assert "Created issue DEMO-42" in result.output
    
    assert route.called
    import json
    payload = json.loads(route.calls.last.request.read().decode("utf-8"))
    assert payload["tags"] == [{"id": "6-0"}, {"id": "6-1"}]


@respx.mock
def test_cli_issue_create_with_invalid_tag(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-0", "name": "Demo", "shortName": "DEMO"}]
    )
    respx.get("https://example.youtrack.cloud/api/tags?fields=id,name").respond(
        status_code=200,
        json=[
            {"id": "6-0", "name": "AFK"},
        ]
    )
    
    result = runner.invoke(
        main,
        [
            "issue", "create",
            "--project", "DEMO",
            "--summary", "Fix login bug",
            "--tag", "INVALID"
        ],
        env=env
    )
    assert result.exit_code != 0
    assert "Error: Tag 'INVALID' not found. Create it first with: youtrack tag create --name INVALID" in result.output


def test_cli_issue_create_missing_args(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    # Missing summary
    result = runner.invoke(main, ["issue", "create", "--project", "DEMO"], env=env)
    assert result.exit_code != 0
    assert "Error: Missing option '--summary'" in result.output
    
    # Missing project
    result = runner.invoke(main, ["issue", "create", "--summary", "Fix login bug"], env=env)
    assert result.exit_code != 0
    assert "Error: Missing option '--project'" in result.output

@respx.mock
def test_cli_issue_create_api_error(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-0", "name": "Demo", "shortName": "DEMO"}]
    )
    respx.post("https://example.youtrack.cloud/api/issues?fields=id,idReadable,summary,description").respond(
        status_code=400,
        json={"error": "bad_request", "error_description": "Summary cannot be empty"}
    )
    
    result = runner.invoke(
        main,
        ["issue", "create", "--project", "DEMO", "--summary", ""],
        env=env
    )
    assert result.exit_code != 0
    assert "Error: Summary cannot be empty" in result.output

@respx.mock
def test_cli_issue_list_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    mock_route = respx.get("https://example.youtrack.cloud/api/issues").respond(
        status_code=200,
        json=[
            {
                "id": "2-100",
                "idReadable": "DEMO-42",
                "summary": "Fix login bug",
                "customFields": [
                    {"name": "State", "value": {"name": "In Progress"}},
                    {"name": "Assignee", "value": {"login": "john.doe"}}
                ]
            }
        ]
    )
    
    result = runner.invoke(main, ["issue", "list", "--project", "DEMO"], env=env)
    assert result.exit_code == 0
    assert "ID" in result.output
    assert "SUMMARY" in result.output
    assert "STATUS" in result.output
    assert "ASSIGNEE" in result.output
    assert "DEMO-42" in result.output
    assert "Fix login bug" in result.output
    assert "In Progress" in result.output
    assert "john.doe" in result.output
    assert mock_route.called
    assert "query=project%3A+DEMO" in str(mock_route.calls.last.request.url)

@respx.mock
def test_cli_issue_list_json(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/issues").respond(
        status_code=200,
        json=[
            {
                "id": "2-100",
                "idReadable": "DEMO-42",
                "summary": "Fix login bug",
                "customFields": []
            }
        ]
    )
    
    result = runner.invoke(main, ["issue", "list", "--project", "DEMO", "--json"], env=env)
    assert result.exit_code == 0
    import json
    parsed = json.loads(result.output)
    assert len(parsed) == 1
    assert parsed[0]["id_readable"] == "DEMO-42"

@respx.mock
def test_cli_issue_list_unresolved(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    mock_route = respx.get("https://example.youtrack.cloud/api/issues").respond(
        status_code=200,
        json=[]
    )
    
    result = runner.invoke(main, ["issue", "list", "--project", "DEMO", "--unresolved"], env=env)
    assert result.exit_code == 0
    assert mock_route.called
    url_str = str(mock_route.calls.last.request.url)
    assert "query=project%3A+DEMO+%23Unresolved" in url_str
    assert "%24top=50" in url_str

@respx.mock
def test_cli_issue_list_top_custom(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    mock_route = respx.get("https://example.youtrack.cloud/api/issues").respond(
        status_code=200,
        json=[]
    )
    
    result = runner.invoke(main, ["issue", "list", "--project", "DEMO", "--top", "20"], env=env)
    assert result.exit_code == 0
    assert mock_route.called
    url_str = str(mock_route.calls.last.request.url)
    assert "%24top=20" in url_str

@respx.mock
def test_cli_issue_list_top_zero(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    mock_route = respx.get("https://example.youtrack.cloud/api/issues").respond(
        status_code=200,
        json=[]
    )
    
    result = runner.invoke(main, ["issue", "list", "--project", "DEMO", "--top", "0"], env=env)
    assert result.exit_code == 0
    assert mock_route.called
    url_str = str(mock_route.calls.last.request.url)
    assert "%24top" not in url_str

def test_cli_issue_list_missing_project(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    result = runner.invoke(main, ["issue", "list"], env=env)
    assert result.exit_code != 0
    assert "Error: Missing option '--project'" in result.output

def test_cli_issue_list_help():
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--help"])
    assert result.exit_code == 0
    assert "--project" in result.output
    assert "--tag" in result.output
    assert "--status" in result.output
    assert "--assignee" in result.output
    assert "--query" in result.output
    assert "--unresolved" in result.output
    assert "--top" in result.output
    assert "--json" in result.output

@respx.mock
def test_cli_issue_move_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    route = respx.post("https://example.youtrack.cloud/api/issues/DEMO-42?fields=id,idReadable,summary,description,customFields(name,value(name,login))").respond(
        status_code=200,
        json={
            "id": "2-100",
            "idReadable": "DEMO-42",
            "summary": "Fix login bug",
            "customFields": [
                {"name": "State", "value": {"name": "In Progress"}}
            ]
        }
    )

    result = runner.invoke(
        main,
        ["issue", "move", "DEMO-42", "--status", "In Progress"],
        env=env
    )
    assert result.exit_code == 0
    assert "Moved DEMO-42 to In Progress" in result.output
    assert route.called
    
    # Verify request payload
    request_payload = route.calls.last.request.read().decode("utf-8")
    import json
    payload = json.loads(request_payload)
    assert payload["customFields"] == [
        {
            "name": "State",
            "$type": "StateIssueCustomField",
            "value": {"name": "In Progress"}
        }
    ]

@respx.mock
def test_cli_issue_move_api_error(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    respx.post("https://example.youtrack.cloud/api/issues/DEMO-42?fields=id,idReadable,summary,description,customFields(name,value(name,login))").respond(
        status_code=400,
        json={"error": "bad_request", "error_description": "State transition not allowed"}
    )

    result = runner.invoke(
        main,
        ["issue", "move", "DEMO-42", "--status", "InvalidState"],
        env=env
    )
    assert result.exit_code != 0
    assert "Error: State transition not allowed" in result.output

def test_cli_issue_move_missing_args(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    # Missing status
    result = runner.invoke(main, ["issue", "move", "DEMO-42"], env=env)
    assert result.exit_code != 0
    assert "Error: Missing option '--status'" in result.output

    # Missing issue ID
    result = runner.invoke(main, ["issue", "move", "--status", "In Progress"], env=env)
    assert result.exit_code != 0
    assert "Error: Missing argument 'ISSUE_ID'" in result.output or "Error:" in result.output

def test_cli_issue_move_help():
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "move", "--help"])
    assert result.exit_code == 0
    assert "ISSUE_ID" in result.output
    assert "--status" in result.output


@respx.mock
def test_cli_tag_create_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    route = respx.post("https://example.youtrack.cloud/api/tags?fields=id,name").respond(
        status_code=200,
        json={"id": "6-0", "name": "backend"}
    )

    result = runner.invoke(
        main,
        ["tag", "create", "--name", "backend"],
        env=env
    )
    assert result.exit_code == 0
    assert "Created tag backend" in result.output
    assert route.called

    # Verify request payload
    request_payload = route.calls.last.request.read().decode("utf-8")
    import json
    payload = json.loads(request_payload)
    assert payload == {"name": "backend"}


@respx.mock
def test_cli_issue_tag_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    route_get = respx.get("https://example.youtrack.cloud/api/tags?fields=id,name").respond(
        status_code=200,
        json=[{"id": "6-0", "name": "backend"}]
    )
    route_post = respx.post("https://example.youtrack.cloud/api/issues/DEMO-42/tags?fields=id,name").respond(
        status_code=200,
        json={"id": "6-0", "name": "backend"}
    )

    result = runner.invoke(
        main,
        ["issue", "tag", "DEMO-42", "--tag", "backend"],
        env=env
    )
    assert result.exit_code == 0
    assert "Tagged DEMO-42 with backend" in result.output
    assert route_get.called
    assert route_post.called


@respx.mock
def test_cli_issue_tag_not_found(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    route_get = respx.get("https://example.youtrack.cloud/api/tags?fields=id,name").respond(
        status_code=200,
        json=[{"id": "6-1", "name": "frontend"}]
    )

    result = runner.invoke(
        main,
        ["issue", "tag", "DEMO-42", "--tag", "backend"],
        env=env
    )
    assert result.exit_code != 0
    assert "Error: Tag 'backend' not found" in result.output
    assert route_get.called


def test_cli_tag_create_help():
    runner = CliRunner()
    result = runner.invoke(main, ["tag", "create", "--help"])
    assert result.exit_code == 0
    assert "--name" in result.output


def test_cli_issue_tag_help():
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "tag", "--help"])
    assert result.exit_code == 0
    assert "ISSUE_ID" in result.output
    assert "--tag" in result.output


@respx.mock
def test_cli_tag_list_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    route = respx.get("https://example.youtrack.cloud/api/tags?fields=id,name").respond(
        status_code=200,
        json=[
            {"id": "6-0", "name": "backend"},
            {"id": "6-1", "name": "frontend"}
        ]
    )

    result = runner.invoke(main, ["tag", "list"], env=env)
    assert result.exit_code == 0
    assert "NAME" in result.output
    assert "backend" in result.output
    assert "frontend" in result.output
    assert route.called


@respx.mock
def test_cli_tag_list_json(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    route = respx.get("https://example.youtrack.cloud/api/tags?fields=id,name").respond(
        status_code=200,
        json=[
            {"id": "6-0", "name": "backend"}
        ]
    )

    result = runner.invoke(main, ["tag", "list", "--json"], env=env)
    assert result.exit_code == 0
    import json
    parsed = json.loads(result.output)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "backend"
    assert route.called


def test_cli_tag_list_help():
    runner = CliRunner()
    result = runner.invoke(main, ["tag", "list", "--help"])
    assert result.exit_code == 0
    assert "--json" in result.output


@respx.mock
def test_cli_issue_types_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    # Mock projects API (to resolve project ID)
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-0", "name": "Demo Project", "shortName": "DEMO"}]
    )
    # Mock custom fields API
    respx.get("https://example.youtrack.cloud/api/admin/projects/0-0/customFields?fields=field(name),bundle(values(name))").respond(
        status_code=200,
        json=[
            {
                "field": {"name": "Type"},
                "bundle": {
                    "values": [
                        {"name": "Bug"},
                        {"name": "Feature"}
                    ]
                }
            }
        ]
    )

    result = runner.invoke(main, ["issue", "types", "--project", "DEMO"], env=env)
    assert result.exit_code == 0
    assert "TYPE" in result.output
    assert "Bug" in result.output
    assert "Feature" in result.output


@respx.mock
def test_cli_issue_types_json(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-0", "name": "Demo Project", "shortName": "DEMO"}]
    )
    respx.get("https://example.youtrack.cloud/api/admin/projects/0-0/customFields?fields=field(name),bundle(values(name))").respond(
        status_code=200,
        json=[
            {
                "field": {"name": "Type"},
                "bundle": {
                    "values": [
                        {"name": "Bug"}
                    ]
                }
            }
        ]
    )

    result = runner.invoke(main, ["issue", "types", "--project", "DEMO", "--json"], env=env)
    assert result.exit_code == 0
    import json
    parsed = json.loads(result.output)
    assert parsed == ["Bug"]


@respx.mock
def test_cli_issue_types_project_not_found(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-1", "name": "Other Project", "shortName": "OTHER"}]
    )

    result = runner.invoke(main, ["issue", "types", "--project", "DEMO"], env=env)
    assert result.exit_code != 0
    assert "Error: Project with short ID 'DEMO' not found" in result.output


def test_cli_issue_types_help():
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "types", "--help"])
    assert result.exit_code == 0
    assert "--project" in result.output
    assert "--json" in result.output


def test_cli_issue_help_lists_types():
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "--help"])
    assert result.exit_code == 0
    assert "types" in result.output
    assert "List valid type values for a project" in result.output


@respx.mock
def test_cli_issue_link_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    route = respx.post("https://example.youtrack.cloud/api/commands").respond(
        status_code=200,
        json={}
    )

    result = runner.invoke(
        main,
        ["issue", "link", "DEMO-43", "--parent", "DEMO-42"],
        env=env
    )
    assert result.exit_code == 0
    assert "Linked DEMO-43 under DEMO-42" in result.output
    assert route.called

    import json
    request_payload = route.calls.last.request.read().decode("utf-8")
    payload = json.loads(request_payload)
    assert payload == {
        "query": "subtask of DEMO-42",
        "issues": [{"idReadable": "DEMO-43"}]
    }


@respx.mock
def test_cli_issue_link_api_error(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    respx.post("https://example.youtrack.cloud/api/commands").respond(
        status_code=400,
        json={"error": "bad_request", "error_description": "issue id expected: DEMO-999"}
    )

    result = runner.invoke(
        main,
        ["issue", "link", "DEMO-43", "--parent", "DEMO-999"],
        env=env
    )
    assert result.exit_code != 0
    assert "Error: issue id expected: DEMO-999" in result.output


def test_cli_issue_link_missing_args(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    # Missing --parent option
    result = runner.invoke(main, ["issue", "link", "DEMO-43"], env=env)
    assert result.exit_code != 0
    assert "Error: Missing option '--parent'" in result.output

    # Missing child ID argument
    result = runner.invoke(main, ["issue", "link", "--parent", "DEMO-42"], env=env)
    assert result.exit_code != 0
    assert "Error: Missing argument 'CHILD_ID'" in result.output or "Error:" in result.output


def test_cli_issue_link_help():
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "link", "--help"])
    assert result.exit_code == 0
    assert "CHILD_ID" in result.output
    assert "--parent" in result.output


def test_cli_issue_help_lists_link():
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "--help"])
    assert result.exit_code == 0
    assert "link" in result.output
    assert "Link two issues as parent/subtask." in result.output or "link" in result.output


@respx.mock
def test_cli_issue_create_with_parent_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-0", "name": "Demo", "shortName": "DEMO"}]
    )
    respx.post("https://example.youtrack.cloud/api/issues?fields=id,idReadable,summary,description").respond(
        status_code=200,
        json={"id": "2-100", "idReadable": "DEMO-42", "summary": "Fix login bug"}
    )
    route_cmd = respx.post("https://example.youtrack.cloud/api/commands").respond(
        status_code=200,
        json={}
    )
    
    result = runner.invoke(
        main,
        ["issue", "create", "--project", "DEMO", "--summary", "Fix login bug", "--parent", "DEMO-10"],
        env=env
    )
    assert result.exit_code == 0
    assert "Created issue DEMO-42" in result.output
    assert route_cmd.called
    
    import json
    request_payload = route_cmd.calls.last.request.read().decode("utf-8")
    payload = json.loads(request_payload)
    assert payload == {
        "query": "subtask of DEMO-10",
        "issues": [{"idReadable": "DEMO-42"}]
    }


@respx.mock
def test_cli_issue_create_with_parent_failure(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.get("https://example.youtrack.cloud/api/admin/projects?fields=id,shortName").respond(
        status_code=200,
        json=[{"id": "0-0", "name": "Demo", "shortName": "DEMO"}]
    )
    respx.post("https://example.youtrack.cloud/api/issues?fields=id,idReadable,summary,description").respond(
        status_code=200,
        json={"id": "2-100", "idReadable": "DEMO-42", "summary": "Fix login bug"}
    )
    respx.post("https://example.youtrack.cloud/api/commands").respond(
        status_code=400,
        json={"error": "bad_request", "error_description": "issue id expected: DEMO-999"}
    )
    
    result = runner.invoke(
        main,
        ["issue", "create", "--project", "DEMO", "--summary", "Fix login bug", "--parent", "DEMO-999"],
        env=env
    )
    assert result.exit_code != 0
    assert "Error: issue id expected: DEMO-999" in result.output


@respx.mock
def test_cli_issue_comment_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    mock_route = respx.post("https://example.youtrack.cloud/api/issues/DEMO-42/comments?fields=id,text,author(id,login,name),created").respond(
        status_code=200,
        json={
            "id": "comment-1",
            "text": "Task finished",
            "created": 1690000000000,
            "author": {
                "login": "john.doe",
                "name": "John Doe",
            }
        }
    )
    
    result = runner.invoke(
        main,
        ["issue", "comment", "DEMO-42", "--message", "Task finished"],
        env=env
    )
    assert result.exit_code == 0
    assert "Added comment to DEMO-42" in result.output
    assert mock_route.called


@respx.mock
def test_cli_issue_comment_api_error(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    respx.post("https://example.youtrack.cloud/api/issues/DEMO-42/comments?fields=id,text,author(id,login,name),created").respond(
        status_code=404,
        json={"error": "not_found", "error_description": "Issue not found"}
    )
    
    result = runner.invoke(
        main,
        ["issue", "comment", "DEMO-42", "--message", "Task finished"],
        env=env
    )
    assert result.exit_code != 0
    assert "Error: Issue not found" in result.output


@respx.mock
def test_cli_issue_show_table_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    url = "https://example.youtrack.cloud/api/issues/YTCLI-50?fields=id,idReadable,summary,description,customFields(name,value(name,login)),comments(id,text,author(id,login,name),created)"
    mock_route = respx.get(url).respond(
        status_code=200,
        json={
            "id": "3-50",
            "idReadable": "YTCLI-50",
            "summary": "Epic issue summary",
            "description": "Epic description",
            "customFields": [
                {
                    "name": "State",
                    "value": {"name": "In Progress"}
                }
            ],
            "comments": [
                {
                    "id": "c-1",
                    "text": "First comment",
                    "created": 1690000000000,
                    "author": {"login": "john.doe"}
                }
            ]
        }
    )
    
    result = runner.invoke(
        main,
        ["issue", "show", "YTCLI-50"],
        env=env
    )
    assert result.exit_code == 0
    assert "ID: YTCLI-50" in result.output
    assert "Summary: Epic issue summary" in result.output
    assert "Status: In Progress" in result.output
    assert "[john.doe @ 2023-07-22 04:26:40]" in result.output
    assert "First comment" in result.output
    assert mock_route.called


@respx.mock
def test_cli_issue_show_json_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    url = "https://example.youtrack.cloud/api/issues/YTCLI-50?fields=id,idReadable,summary,description,customFields(name,value(name,login)),comments(id,text,author(id,login,name),created)"
    mock_route = respx.get(url).respond(
        status_code=200,
        json={
            "id": "3-50",
            "idReadable": "YTCLI-50",
            "summary": "Epic issue summary",
            "description": "Epic description",
            "customFields": [],
            "comments": []
        }
    )
    
    result = runner.invoke(
        main,
        ["issue", "show", "YTCLI-50", "--json"],
        env=env
    )
    assert result.exit_code == 0
    import json
    parsed = json.loads(result.output)
    assert parsed["id"] == "3-50"
    assert parsed["id_readable"] == "YTCLI-50"
    assert parsed["summary"] == "Epic issue summary"
    assert parsed["comments"] == []
    assert mock_route.called


@respx.mock
def test_cli_issue_show_api_error(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}
    
    url = "https://example.youtrack.cloud/api/issues/YTCLI-50?fields=id,idReadable,summary,description,customFields(name,value(name,login)),comments(id,text,author(id,login,name),created)"
    mock_route = respx.get(url).respond(
        status_code=404,
        json={"error": "not_found", "error_description": "Issue not found"}
    )
    
    result = runner.invoke(
        main,
        ["issue", "show", "YTCLI-50"],
        env=env
    )
    assert result.exit_code != 0
    assert "Error: Issue not found" in result.output
    assert mock_route.called


@respx.mock
def test_cli_issue_update_description_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    fields = "id,idReadable,summary,description,customFields(name,value(name,login))"
    url = f"https://example.youtrack.cloud/api/issues/YTCLI-50?fields={fields}"
    mock_route = respx.post(url).respond(
        status_code=200,
        json={
            "id": "3-50",
            "idReadable": "YTCLI-50",
            "summary": "Original summary",
            "description": "Updated description",
            "customFields": []
        }
    )

    result = runner.invoke(
        main,
        ["issue", "update", "YTCLI-50", "--description", "Updated description"],
        env=env
    )
    assert result.exit_code == 0
    assert "Updated issue YTCLI-50" in result.output
    assert mock_route.called
    import json
    assert json.loads(mock_route.calls.last.request.read().decode("utf-8")) == {"description": "Updated description"}


@respx.mock
def test_cli_issue_update_summary_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    fields = "id,idReadable,summary,description,customFields(name,value(name,login))"
    url = f"https://example.youtrack.cloud/api/issues/YTCLI-50?fields={fields}"
    mock_route = respx.post(url).respond(
        status_code=200,
        json={
            "id": "3-50",
            "idReadable": "YTCLI-50",
            "summary": "Updated summary",
            "description": "Original description",
            "customFields": []
        }
    )

    result = runner.invoke(
        main,
        ["issue", "update", "YTCLI-50", "--summary", "Updated summary"],
        env=env
    )
    assert result.exit_code == 0
    assert "Updated issue YTCLI-50" in result.output
    assert mock_route.called
    import json
    assert json.loads(mock_route.calls.last.request.read().decode("utf-8")) == {"summary": "Updated summary"}


@respx.mock
def test_cli_issue_update_both_success(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    fields = "id,idReadable,summary,description,customFields(name,value(name,login))"
    url = f"https://example.youtrack.cloud/api/issues/YTCLI-50?fields={fields}"
    mock_route = respx.post(url).respond(
        status_code=200,
        json={
            "id": "3-50",
            "idReadable": "YTCLI-50",
            "summary": "Updated summary",
            "description": "Updated description",
            "customFields": []
        }
    )

    result = runner.invoke(
        main,
        ["issue", "update", "YTCLI-50", "--summary", "Updated summary", "--description", "Updated description"],
        env=env
    )
    assert result.exit_code == 0
    assert "Updated issue YTCLI-50" in result.output
    assert mock_route.called
    import json
    assert json.loads(mock_route.calls.last.request.read().decode("utf-8")) == {"summary": "Updated summary", "description": "Updated description"}


def test_cli_issue_update_missing_options_error(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    result = runner.invoke(
        main,
        ["issue", "update", "YTCLI-50"],
        env=env
    )
    assert result.exit_code != 0
    assert "Error: At least one of --description or --summary must be provided" in result.output


@respx.mock
def test_cli_issue_update_api_error(tmp_path):
    runner = CliRunner()
    config_dir = tmp_path / "youtrack-cli"
    save_config("https://example.youtrack.cloud", "perm:test-token", config_dir=config_dir)
    env = {"YOUTRACK_CONFIG_DIR": str(config_dir)}

    fields = "id,idReadable,summary,description,customFields(name,value(name,login))"
    url = f"https://example.youtrack.cloud/api/issues/YTCLI-50?fields={fields}"
    mock_route = respx.post(url).respond(
        status_code=404,
        json={"error": "not_found", "error_description": "Issue not found"}
    )

    result = runner.invoke(
        main,
        ["issue", "update", "YTCLI-50", "--description", "Updated description"],
        env=env
    )
    assert result.exit_code != 0
    assert "Error: Issue not found" in result.output
    assert mock_route.called








