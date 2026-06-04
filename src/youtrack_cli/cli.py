import sys
import click
from youtrack_cli.config import save_config, ConfigError

@click.group()
def main():
    """YouTrack CLI — Interact with YouTrack from the command line."""
    pass

@main.command(name="login")
@click.option("--url", required=True, help="YouTrack base URL (e.g. https://example.youtrack.cloud)")
@click.option("--token", required=True, help="YouTrack permanent API token")
def login(url: str, token: str):
    """Configure the CLI URL and permanent token."""
    try:
        save_config(url, token)
        click.echo(f"Configuration saved. Logged in to {url}")
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@main.group(name="project")
def project_group():
    """Manage YouTrack projects."""
    pass

@project_group.command(name="list")
@click.option("--json", "json_output", is_flag=True, help="Emit JSON instead of human-readable output")
def project_list(json_output: bool):
    """List all projects."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.projects import list_projects
        from youtrack_cli.formatters import format_projects_table, format_projects_json
        
        client = get_client()
        projects = list_projects(client)
        if json_output:
            click.echo(format_projects_json(projects))
        else:
            click.echo(format_projects_table(projects))
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@project_group.command(name="create")
@click.option("--name", required=True, help="Project name")
@click.option("--id", "short_id", required=True, help="Project short ID (shortName)")
def project_create(name: str, short_id: str):
    """Create a new project."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.projects import create_project
        
        client = get_client()
        project = create_project(client, name, short_id)
        click.echo(f"Created project {project.short_name}")
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@main.group(name="issue")
def issue_group():
    """Manage YouTrack issues."""
    pass

@issue_group.command(name="create")
@click.option("--project", required=True, help="Project short ID (e.g. DEMO)")
@click.option("--summary", required=True, help="Issue summary/title")
@click.option("--description", help="Optional issue description")
@click.option("--assignee", help="Optional assignee username")
@click.option("--priority", help="Optional issue priority (e.g. Critical, Major, Normal, Minor)")
@click.option("--type", "type_name", help="Optional issue type (e.g. Bug, Feature, Task)")
@click.option("--tag", "tags", multiple=True, help="Optional tag name (can be repeated)")
@click.option("--parent", help="Optional parent Epic ID (e.g. YTCLI-50)")
@click.option("--json", "json_output", is_flag=True, help="Emit JSON instead of human-readable confirmation")
def issue_create(
    project: str,
    summary: str,
    description: str | None,
    assignee: str | None,
    priority: str | None,
    type_name: str | None,
    tags: tuple[str],
    parent: str | None,
    json_output: bool,
):
    """Create a new issue."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.issues import create_issue
        from youtrack_cli.formatters import format_issue_json
        
        client = get_client()
        issue = create_issue(
            client=client,
            project_short_name=project,
            summary=summary,
            description=description,
            assignee=assignee,
            priority=priority,
            type_name=type_name,
            tags=list(tags) if tags else None,
            parent=parent,
        )
        if json_output:
            click.echo(format_issue_json(issue))
        else:
            click.echo(f"Created issue {issue.id_readable}")
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@issue_group.command(name="list")
@click.option("--project", required=True, help="Project short ID (e.g. DEMO)")
@click.option("--tag", help="Filter by tag name")
@click.option("--status", help="Filter by status/state name")
@click.option("--assignee", help="Filter by assignee username")
@click.option("--query", "raw_query", help="Raw YouTrack query string to merge")
@click.option("--unresolved", is_flag=True, help="Restrict to unresolved (pending) issues")
@click.option("--top", type=int, default=50, help="Cap the number of issues returned (default 50; 0 for no cap)")
@click.option("--json", "json_output", is_flag=True, help="Emit JSON instead of human-readable output")
def issue_list(
    project: str,
    tag: str | None,
    status: str | None,
    assignee: str | None,
    raw_query: str | None,
    unresolved: bool,
    top: int,
    json_output: bool,
):
    """List issues in a project with filtering."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.issues import list_issues
        from youtrack_cli.formatters import format_issues_table, format_issues_json
        
        client = get_client()
        issues = list_issues(
            client=client,
            project_short_name=project,
            tag=tag,
            status=status,
            assignee=assignee,
            query=raw_query,
            unresolved=unresolved,
            top=top,
        )
        if json_output:
            click.echo(format_issues_json(issues))
        else:
            click.echo(format_issues_table(issues))
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@issue_group.command(name="move")
@click.argument("issue_id")
@click.option("--status", required=True, help="Target status name")
def issue_move(issue_id: str, status: str):
    """Move an issue to a different status."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.issues import move_issue
        
        client = get_client()
        issue = move_issue(client, issue_id, status)
        click.echo(f"Moved {issue.id_readable} to {status}")
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@issue_group.command(name="tag")
@click.argument("issue_id")
@click.option("--tag", "tag_name", required=True, help="Tag name to apply")
def issue_tag(issue_id: str, tag_name: str):
    """Apply a tag to an issue."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.issues import tag_issue
        
        client = get_client()
        tag_issue(client, issue_id, tag_name)
        click.echo(f"Tagged {issue_id} with {tag_name}")
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@issue_group.command(name="types")
@click.option("--project", required=True, help="Project short ID (e.g. DEMO)")
@click.option("--json", "json_output", is_flag=True, help="Emit JSON instead of human-readable output")
def issue_types(project: str, json_output: bool):
    """List valid type values for a project."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.issues import list_issue_types
        from youtrack_cli.formatters import format_issue_types_table, format_issue_types_json
        
        client = get_client()
        types = list_issue_types(client, project)
        if json_output:
            click.echo(format_issue_types_json(types))
        else:
            click.echo(format_issue_types_table(types))
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@issue_group.command(name="link")
@click.argument("child_id")
@click.option("--parent", "parent_id", required=True, help="Parent Epic ID (e.g. YTCLI-50)")
def issue_link(child_id: str, parent_id: str):
    """Link two issues as parent/subtask."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.issues import link_subtask

        client = get_client()
        link_subtask(client, child_id, parent_id)
        click.echo(f"Linked {child_id} under {parent_id}")
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@issue_group.command(name="comment")
@click.argument("issue_id")
@click.option("--message", required=True, help="Comment body to append to an issue")
def issue_comment(issue_id: str, message: str):
    """Append a comment to an issue."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.issues import add_comment

        client = get_client()
        add_comment(client, issue_id, message)
        click.echo(f"Added comment to {issue_id}")
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@issue_group.command(name="show")
@click.argument("issue_id")
@click.option("--json", "json_output", is_flag=True, help="Emit JSON instead of human-readable output")
def issue_show(issue_id: str, json_output: bool):
    """Show details of a single issue, including comments."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.issues import show_issue
        from youtrack_cli.formatters import format_issue_detail_table, format_issue_detail_json

        client = get_client()
        issue_detail = show_issue(client, issue_id)
        if json_output:
            click.echo(format_issue_detail_json(issue_detail))
        else:
            click.echo(format_issue_detail_table(issue_detail))
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@issue_group.command(name="update")
@click.argument("issue_id")
@click.option("--description", help="New description for full replacement")
@click.option("--summary", help="New summary for full replacement")
def issue_update(issue_id: str, description: str | None, summary: str | None):
    """Update description and/or summary of an issue."""
    if description is None and summary is None:
        raise click.UsageError("At least one of --description or --summary must be provided")
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.issues import update_issue

        client = get_client()
        issue = update_issue(client, issue_id, description=description, summary=summary)
        click.echo(f"Updated issue {issue.id_readable}")
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.group(name="tag")
def tag_group():


    """Manage YouTrack tags."""
    pass


@tag_group.command(name="create")
@click.option("--name", required=True, help="Tag name")
def tag_create(name: str):
    """Create a new tag."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.tags import create_tag
        
        client = get_client()
        tag = create_tag(client, name)
        click.echo(f"Created tag {tag.name}")
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@tag_group.command(name="list")
@click.option("--json", "json_output", is_flag=True, help="Emit JSON instead of human-readable output")
def tag_list(json_output: bool):
    """List all tags."""
    try:
        from youtrack_cli.client import get_client, YouTrackAPIError
        from youtrack_cli.tags import list_tags
        from youtrack_cli.formatters import format_tags_table, format_tags_json
        
        client = get_client()
        tags = list_tags(client)
        if json_output:
            click.echo(format_tags_json(tags))
        else:
            click.echo(format_tags_table(tags))
    except (ConfigError, YouTrackAPIError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)



if __name__ == "__main__":
    main()

