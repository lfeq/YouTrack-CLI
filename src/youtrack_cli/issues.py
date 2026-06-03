from dataclasses import dataclass
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


def create_issue(
    client: YouTrackClient,
    project_short_name: str,
    summary: str,
    description: Optional[str] = None,
    assignee: Optional[str] = None,
    priority: Optional[str] = None,
    type_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
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
) -> List[Issue]:
    """List issues in a project with filtering."""
    # 1. Build the query string
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
        
    query_str = " ".join(parts)
    
    # 2. Call the REST API
    fields = "id,idReadable,summary,description,customFields(name,value(name,login))"
    data = client._request(
        "GET",
        "api/issues",
        params={
            "fields": fields,
            "query": query_str
        }
    )
    
    # 3. Parse the issues
    issues = []
    for item in data:
        item_status = None
        item_assignee = None
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
                        
        issues.append(
            Issue(
                id=item["id"],
                id_readable=item["idReadable"],
                summary=item["summary"],
                description=item.get("description"),
                status=item_status,
                assignee=item_assignee
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




