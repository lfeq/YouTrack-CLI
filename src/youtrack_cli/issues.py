from dataclasses import dataclass, field
from typing import Optional, List
from youtrack_cli.client import YouTrackClient, YouTrackAPIError

@dataclass
class Issue:
    id: str
    id_readable: str
    summary: str
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    blocked: bool = False



@dataclass
class Comment:
    id: str
    text: str
    author: str
    created: int


def create_issue(
    client: YouTrackClient,
    project_short_name: str,
    summary: str,
    description: Optional[str] = None,
    assignee: Optional[str] = None,
    priority: Optional[str] = None,
    type_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    parent: Optional[str] = None,
) -> Issue:
    """Create a new issue in YouTrack."""
    # 1. Fetch projects to map shortName to ID
    projects_data = client._request("GET", "api/admin/projects?fields=id,shortName")
    
    project_id = None
    # Look up matching project shortName (exact match, case-sensitive/insensitive?)
    # Since shortName is typically capitalized (e.g. DEMO), let's find the match.
    for project in projects_data:
        if project["shortName"].upper() == project_short_name.upper():
            project_id = project["id"]
            break
            
    if not project_id:
        raise YouTrackAPIError(f"Project with short ID '{project_short_name}' not found")
        
    # 2. Build the POST payload
    payload = {
        "project": {
            "id": project_id
        },
        "summary": summary,
    }
    
    if description is not None:
        payload["description"] = description
        
    # 3. Add custom fields if provided
    custom_fields = []
    if assignee:
        custom_fields.append({
            "name": "Assignee",
            "$type": "SingleUserIssueCustomField",
            "value": {
                "login": assignee
            }
        })
    if priority:
        custom_fields.append({
            "name": "Priority",
            "$type": "SingleEnumIssueCustomField",
            "value": {
                "name": priority
            }
        })
    if type_name:
        custom_fields.append({
            "name": "Type",
            "$type": "SingleEnumIssueCustomField",
            "value": {
                "name": type_name
            }
        })
        
    if custom_fields:
        payload["customFields"] = custom_fields

    # Resolve tags if provided
    if tags:
        tags_data = client._request("GET", "api/tags?fields=id,name")
        resolved_tags = []
        for tag_name in tags:
            tag_id = None
            for tag in tags_data:
                if tag["name"] == tag_name:
                    tag_id = tag["id"]
                    break
            if not tag_id:
                raise YouTrackAPIError(f"Tag '{tag_name}' not found. Create it first with: youtrack tag create --name {tag_name}")
            resolved_tags.append({"id": tag_id})
        payload["tags"] = resolved_tags
        
    # 4. POST payload to create the issue
    data = client._request("POST", "api/issues?fields=id,idReadable,summary,description", json=payload)
    
    if parent:
        link_subtask(client, data["idReadable"], parent)

    return Issue(
        id=data["id"],
        id_readable=data["idReadable"],
        summary=data["summary"],
        description=data.get("description")
    )

def list_issues(
    client: YouTrackClient,
    project_short_name: str,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    query: Optional[str] = None,
    unresolved: bool = False,
    top: Optional[int] = 50,
    all: bool = False,
) -> List[Issue]:
    """List issues in a project with filtering."""
    # 1. Build the query string
    query_str = build_issue_list_query(
        project_short_name=project_short_name,
        tag=tag,
        status=status,
        assignee=assignee,
        query=query,
        all=all,
    )
    
    # 2. Call the REST API
    fields = "id,idReadable,summary,description,customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,resolved,summary))"
    params = {
        "fields": fields,
        "query": query_str
    }
    if top is not None and top > 0:
        params["$top"] = top
        
    data = client._request(
        "GET",
        "api/issues",
        params=params
    )
    
    # 3. Parse the issues
    issues = []
    for item in data:
        item_status = None
        item_assignee = None
        item_priority = None
        for field in item.get("customFields", []):
            field_name = field.get("name")
            field_value = field.get("value")
            if field_value:
                if field_name == "State":
                    if isinstance(field_value, dict):
                        item_status = field_value.get("name")
                    else:
                        item_status = str(field_value)
                elif field_name == "Assignee":
                    if isinstance(field_value, dict):
                        item_assignee = field_value.get("login") or field_value.get("name")
                    else:
                        item_assignee = str(field_value)
                elif field_name == "Priority":
                    if isinstance(field_value, dict):
                        item_priority = field_value.get("name")
                    else:
                        item_priority = str(field_value)
                        
        _, _, blocked = parse_dependency_links(item.get("links"))
        issues.append(
            Issue(
                id=item["id"],
                id_readable=item["idReadable"],
                summary=item["summary"],
                description=item.get("description"),
                status=item_status,
                assignee=item_assignee,
                priority=item_priority,
                blocked=blocked
            )
        )

        
    return issues


def move_issue(client: YouTrackClient, issue_id: str, status: str) -> Issue:
    """Move an issue to a new status (State)."""
    payload = {
        "customFields": [
            {
                "name": "State",
                "$type": "StateIssueCustomField",
                "value": {
                    "name": status
                }
            }
        ]
    }
    fields = "id,idReadable,summary,description,customFields(name,value(name,login))"
    data = client._request(
        "POST",
        f"api/issues/{issue_id}?fields={fields}",
        json=payload
    )
    
    item_status = None
    item_assignee = None
    item_priority = None
    for field in data.get("customFields", []):
        field_name = field.get("name")
        field_value = field.get("value")
        if field_value:
            if field_name == "State":
                if isinstance(field_value, dict):
                    item_status = field_value.get("name")
                else:
                    item_status = str(field_value)
            elif field_name == "Assignee":
                if isinstance(field_value, dict):
                    item_assignee = field_value.get("login") or field_value.get("name")
                else:
                    item_assignee = str(field_value)
            elif field_name == "Priority":
                if isinstance(field_value, dict):
                    item_priority = field_value.get("name")
                else:
                    item_priority = str(field_value)
                    
    return Issue(
        id=data["id"],
        id_readable=data["idReadable"],
        summary=data["summary"],
        description=data.get("description"),
        status=item_status,
        assignee=item_assignee,
        priority=item_priority
    )


def tag_issue(client: YouTrackClient, issue_id: str, tag_name: str) -> None:
    """Apply an existing tag to an issue."""
    # 1. Fetch tags to find the matching tag by name
    tags_data = client._request("GET", "api/tags?fields=id,name")

    tag_id = None
    for tag in tags_data:
        if tag["name"] == tag_name:
            tag_id = tag["id"]
            break

    if not tag_id:
        raise YouTrackAPIError(f"Tag '{tag_name}' not found")

    # 2. Add the tag to the issue
    client._request(
        "POST",
        f"api/issues/{issue_id}/tags?fields=id,name",
        json={"id": tag_id}
    )


def list_issue_types(client: YouTrackClient, project_short_name: str) -> List[str]:
    """List valid issue types for a project."""
    # 1. Fetch projects to map shortName to ID
    projects_data = client._request("GET", "api/admin/projects?fields=id,shortName")
    
    project_id = None
    for project in projects_data:
        if project["shortName"].upper() == project_short_name.upper():
            project_id = project["id"]
            break
            
    if not project_id:
        raise YouTrackAPIError(f"Project with short ID '{project_short_name}' not found")
        
    # 2. Fetch project custom fields
    url = f"api/admin/projects/{project_id}/customFields?fields=field(name),bundle(values(name))"
    custom_fields = client._request("GET", url)
    
    # 3. Filter for the "Type" custom field and extract its values
    for cf in custom_fields:
        field = cf.get("field")
        if field and isinstance(field, dict) and field.get("name") == "Type":
            bundle = cf.get("bundle")
            if bundle and isinstance(bundle, dict):
                values = bundle.get("values")
                if isinstance(values, list):
                    return [val["name"] for val in values if isinstance(val, dict) and "name" in val]
                    
    return []


def list_issue_priorities(client: YouTrackClient, project_short_name: str) -> List[str]:
    """List valid issue priorities for a project."""
    # 1. Fetch projects to map shortName to ID
    projects_data = client._request("GET", "api/admin/projects?fields=id,shortName")
    
    project_id = None
    for project in projects_data:
        if project["shortName"].upper() == project_short_name.upper():
            project_id = project["id"]
            break
            
    if not project_id:
        raise YouTrackAPIError(f"Project with short ID '{project_short_name}' not found")
        
    # 2. Fetch project custom fields
    url = f"api/admin/projects/{project_id}/customFields?fields=field(name),bundle(values(name))"
    custom_fields = client._request("GET", url)
    
    # 3. Filter for the "Priority" custom field and extract its values
    for cf in custom_fields:
        field = cf.get("field")
        if field and isinstance(field, dict) and field.get("name") == "Priority":
            bundle = cf.get("bundle")
            if bundle and isinstance(bundle, dict):
                values = bundle.get("values")
                if isinstance(values, list):
                    return [val["name"] for val in values if isinstance(val, dict) and "name" in val]
                    
    return []



def link_subtask(client: YouTrackClient, child_id: str, parent_id: str) -> None:
    """Create a Subtask relationship making child_id a subtask of parent_id."""
    client._request(
        "POST",
        "api/commands",
        json={
            "query": f"subtask of {parent_id}",
            "issues": [{"idReadable": child_id}]
        }
    )


def add_dependency(client: YouTrackClient, issue_id: str, target_id: str) -> None:
    """Create a dependency relationship making issue_id depend on target_id."""
    client._request(
        "POST",
        "api/commands",
        json={
            "query": f"depends on {target_id}",
            "issues": [{"idReadable": issue_id}]
        }
    )


def remove_dependency(client: YouTrackClient, issue_id: str, target_id: str) -> None:
    """Remove a dependency relationship making issue_id no longer depend on target_id."""
    client._request(
        "POST",
        "api/commands",
        json={
            "query": f"remove depends on {target_id}",
            "issues": [{"idReadable": issue_id}]
        }
    )



def add_comment(client: YouTrackClient, issue_id: str, message: str) -> Comment:
    """Append a comment to an issue."""
    url = f"api/issues/{issue_id}/comments?fields=id,text,author(id,login,name),created"
    payload = {"text": message}
    data = client._request("POST", url, json=payload)
    
    author_name = ""
    author_data = data.get("author")
    if isinstance(author_data, dict):
        author_name = author_data.get("login") or author_data.get("name") or ""
    elif author_data:
        author_name = str(author_data)
        
    return Comment(
        id=data["id"],
        text=data["text"],
        author=author_name,
        created=data.get("created", 0)
    )


@dataclass
class IssueDetail:
    id: str
    id_readable: str
    summary: str
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    comments: List[Comment] = None
    depends_on: List[dict] = field(default_factory=list)
    required_for: List[dict] = field(default_factory=list)



def show_issue(client: YouTrackClient, issue_id: str) -> IssueDetail:
    """Fetch a single issue including its description and its comments in one request."""
    url = f"api/issues/{issue_id}?fields=id,idReadable,summary,description,customFields(name,value(name,login)),comments(id,text,author(id,login,name),created),links(direction,linkType(name),issues(idReadable,resolved,summary))"
    data = client._request("GET", url)
    
    item_status = None
    item_assignee = None
    for field in data.get("customFields", []):
        field_name = field.get("name")
        field_value = field.get("value")
        if field_value:
            if field_name == "State":
                if isinstance(field_value, dict):
                    item_status = field_value.get("name")
                else:
                    item_status = str(field_value)
            elif field_name == "Assignee":
                if isinstance(field_value, dict):
                    item_assignee = field_value.get("login") or field_value.get("name")
                else:
                    item_assignee = str(field_value)

    comments = []
    for comment_data in data.get("comments", []) or []:
        author_name = ""
        author_data = comment_data.get("author")
        if isinstance(author_data, dict):
            author_name = author_data.get("login") or author_data.get("name") or ""
        elif author_data:
            author_name = str(author_data)
            
        comments.append(
            Comment(
                id=comment_data["id"],
                text=comment_data["text"],
                author=author_name,
                created=comment_data.get("created", 0)
            )
        )
        
    depends_on, required_for, _ = parse_dependency_links(data.get("links"))

    return IssueDetail(
        id=data["id"],
        id_readable=data["idReadable"],
        summary=data["summary"],
        description=data.get("description"),
        status=item_status,
        assignee=item_assignee,
        comments=comments,
        depends_on=depends_on,
        required_for=required_for
    )


def update_issue(
    client: YouTrackClient,
    issue_id: str,
    description: Optional[str] = None,
    summary: Optional[str] = None,
) -> Issue:
    """Full-replace update of description and/or summary of an issue."""
    if description is None and summary is None:
        raise ValueError("At least one of description or summary must be provided")

    payload = {}
    if description is not None:
        payload["description"] = description
    if summary is not None:
        payload["summary"] = summary

    fields = "id,idReadable,summary,description,customFields(name,value(name,login))"
    data = client._request(
        "POST",
        f"api/issues/{issue_id}?fields={fields}",
        json=payload
    )

    item_status = None
    item_assignee = None
    for field in data.get("customFields", []):
        field_name = field.get("name")
        field_value = field.get("value")
        if field_value:
            if field_name == "State":
                if isinstance(field_value, dict):
                    item_status = field_value.get("name")
                else:
                    item_status = str(field_value)
            elif field_name == "Assignee":
                if isinstance(field_value, dict):
                    item_assignee = field_value.get("login") or field_value.get("name")
                else:
                    item_assignee = str(field_value)

    return Issue(
        id=data["id"],
        id_readable=data["idReadable"],
        summary=data["summary"],
        description=data.get("description"),
        status=item_status,
        assignee=item_assignee
    )


def build_issue_list_query(
    project_short_name: str,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    query: Optional[str] = None,
    all: bool = False,
) -> str:
    """Build YouTrack issue query string based on inputs."""
    parts = [f"project: {project_short_name}"]
    if query:
        parts.append(query)
    if tag:
        tag_val = f'"{tag}"' if ' ' in tag else tag
        parts.append(f"tag: {tag_val}")
    if status:
        status_val = f'"{status}"' if ' ' in status else status
        parts.append(f"State: {status_val}")
    if assignee:
        assignee_val = f'"{assignee}"' if ' ' in assignee else assignee
        parts.append(f"assignee: {assignee_val}")

    if not (all or status or query):
        parts.append("#Unresolved")

    has_sort_by = False
    if query and "sort by" in query.lower():
        has_sort_by = True

    if not has_sort_by:
        parts.append("sort by: priority asc, State asc")

    return " ".join(parts)


def parse_dependency_links(links: Optional[List[dict]]) -> tuple[List[dict], List[dict], bool]:
    """Parse raw links from YouTrack to extract depends_on, required_for, and blocked status."""
    depends_on = []
    required_for = []
    blocked = False

    if not links:
        return depends_on, required_for, blocked

    for link in links:
        link_type = link.get("linkType")
        if not link_type or link_type.get("name") != "Depend":
            continue

        direction = link.get("direction")
        issues = link.get("issues") or []

        for issue in issues:
            id_readable = issue.get("idReadable")
            summary = issue.get("summary", "")
            resolved = issue.get("resolved", False)

            item = {
                "id": id_readable,
                "summary": summary,
                "resolved": resolved
            }

            if direction == "OUTWARD":
                depends_on.append(item)
                if not resolved:
                    blocked = True
            elif direction == "INWARD":
                required_for.append(item)

    return depends_on, required_for, blocked










