import json
from typing import List, Any
from dataclasses import asdict
from youtrack_cli.projects import Project
from youtrack_cli.tags import Tag

def format_projects_table(projects: List[Project]) -> str:

    """Format a list of projects into a human-readable text table."""
    if not projects:
        return "No projects found."
    
    headers = ["SHORT ID", "NAME"]
    col_widths = [len(headers[0]), len(headers[1])]
    
    for p in projects:
        col_widths[0] = max(col_widths[0], len(p.short_name))
        col_widths[1] = max(col_widths[1], len(p.name))
        
    lines = [
        f"{headers[0]:<{col_widths[0]}}  {headers[1]:<{col_widths[1]}}",
        f"{'-' * col_widths[0]}  {'-' * col_widths[1]}"
    ]
    for p in projects:
        lines.append(f"{p.short_name:<{col_widths[0]}}  {p.name:<{col_widths[1]}}")
        
    return "\n".join(lines)

def format_projects_json(projects: List[Project]) -> str:
    """Format a list of projects into a JSON array string."""
    data = [asdict(p) for p in projects]
    return json.dumps(data, indent=2)

def format_issue_json(issue: Any) -> str:
    """Format a single issue into a JSON string."""
    return json.dumps(asdict(issue), indent=2)

def format_issues_table(issues: list) -> str:
    """Format a list of issues into a human-readable text table."""
    if not issues:
        return "No issues found."
        
    headers = ["ID", "SUMMARY", "STATUS", "ASSIGNEE"]
    col_widths = [len(h) for h in headers]
    
    rows = []
    for issue in issues:
        issue_id = issue.id_readable or ""
        summary = issue.summary or ""
        status = issue.status or ""
        assignee = issue.assignee or ""
        
        col_widths[0] = max(col_widths[0], len(issue_id))
        col_widths[1] = max(col_widths[1], len(summary))
        col_widths[2] = max(col_widths[2], len(status))
        col_widths[3] = max(col_widths[3], len(assignee))
        
        rows.append((issue_id, summary, status, assignee))
        
    lines = [
        f"{headers[0]:<{col_widths[0]}}  {headers[1]:<{col_widths[1]}}  {headers[2]:<{col_widths[2]}}  {headers[3]:<{col_widths[3]}}",
        f"{'-' * col_widths[0]}  {'-' * col_widths[1]}  {'-' * col_widths[2]}  {'-' * col_widths[3]}"
    ]
    for row in rows:
        lines.append(f"{row[0]:<{col_widths[0]}}  {row[1]:<{col_widths[1]}}  {row[2]:<{col_widths[2]}}  {row[3]:<{col_widths[3]}}")
        
    return "\n".join(lines)

def format_issues_json(issues: list) -> str:
    """Format a list of issues into a JSON array string."""
    return json.dumps([asdict(issue) for issue in issues], indent=2)

def format_tags_table(tags: List[Tag]) -> str:
    """Format a list of tags into a human-readable text table."""
    if not tags:
        return "No tags found."
    
    headers = ["NAME"]
    col_width = len(headers[0])
    for t in tags:
        col_width = max(col_width, len(t.name))
        
    lines = [
        f"{headers[0]:<{col_width}}",
        f"{'-' * col_width}"
    ]
    for t in tags:
        lines.append(f"{t.name:<{col_width}}")
        
    return "\n".join(lines)

def format_tags_json(tags: List[Tag]) -> str:
    """Format a list of tags into a JSON array string."""
    data = [asdict(t) for t in tags]
    return json.dumps(data, indent=2)


def format_issue_types_table(types: List[str]) -> str:
    """Format a list of issue types into a human-readable text table."""
    if not types:
        return "No types found."
    
    headers = ["TYPE"]
    col_width = len(headers[0])
    for t in types:
        col_width = max(col_width, len(t))
        
    lines = [
        f"{headers[0]:<{col_width}}",
        f"{'-' * col_width}"
    ]
    for t in types:
        lines.append(f"{t:<{col_width}}")
        
    return "\n".join(lines)


def format_issue_types_json(types: List[str]) -> str:
    """Format a list of issue types into a JSON array string."""
    return json.dumps(types, indent=2)




