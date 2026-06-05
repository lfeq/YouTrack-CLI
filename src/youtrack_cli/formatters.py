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
        
    headers = ["ID", "PRIORITY", "STATUS", "SUMMARY", "ASSIGNEE"]
    col_widths = [len(h) for h in headers]
    
    rows = []
    for issue in issues:
        issue_id = issue.id_readable or ""
        priority = getattr(issue, "priority", "") or ""
        status = issue.status or ""
        summary = issue.summary or ""
        if getattr(issue, "blocked", False):
            summary = f"[BLOCKED] {summary}"
        assignee = issue.assignee or ""
        
        col_widths[0] = max(col_widths[0], len(issue_id))
        col_widths[1] = max(col_widths[1], len(priority))
        col_widths[2] = max(col_widths[2], len(status))
        col_widths[3] = max(col_widths[3], len(summary))
        col_widths[4] = max(col_widths[4], len(assignee))
        
        rows.append((issue_id, priority, status, summary, assignee))
        
    lines = [
        f"{headers[0]:<{col_widths[0]}}  {headers[1]:<{col_widths[1]}}  {headers[2]:<{col_widths[2]}}  {headers[3]:<{col_widths[3]}}  {headers[4]:<{col_widths[4]}}",
        f"{'-' * col_widths[0]}  {'-' * col_widths[1]}  {'-' * col_widths[2]}  {'-' * col_widths[3]}  {'-' * col_widths[4]}"
    ]
    for row in rows:
        lines.append(f"{row[0]:<{col_widths[0]}}  {row[1]:<{col_widths[1]}}  {row[2]:<{col_widths[2]}}  {row[3]:<{col_widths[3]}}  {row[4]:<{col_widths[4]}}")
        
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


def format_issue_priorities_table(priorities: List[str]) -> str:
    """Format a list of priorities into a human-readable text table."""
    if not priorities:
        return "No priorities found."
    
    headers = ["PRIORITY"]
    col_width = len(headers[0])
    for p in priorities:
        col_width = max(col_width, len(p))
        
    lines = [
        f"{headers[0]:<{col_width}}",
        f"{'-' * col_width}"
    ]
    for p in priorities:
        lines.append(f"{p:<{col_width}}")
        
    return "\n".join(lines)


def format_issue_priorities_json(priorities: List[str]) -> str:
    """Format a list of priorities into a JSON array string."""
    return json.dumps(priorities, indent=2)



def format_issue_detail_table(issue) -> str:
    """Format an issue's details and comments into a human-readable text block."""
    lines = [
        f"ID: {issue.id_readable}",
        f"Summary: {issue.summary}",
        f"Status: {issue.status or ''}",
        f"Assignee: {issue.assignee or ''}",
        "",
        "Description:",
        issue.description or "",
        ""
    ]
    
    if getattr(issue, "depends_on", None):
        lines.append("Depends on:")
        for dep in issue.depends_on:
            resolved_str = "[resolved]" if dep.get("resolved") else "[unresolved]"
            blocking_str = " (BLOCKING)" if not dep.get("resolved") else ""
            lines.append(f"- {dep['id']}: {dep['summary']} {resolved_str}{blocking_str}")
        lines.append("")

    if getattr(issue, "required_for", None):
        lines.append("Required for:")
        for req in issue.required_for:
            resolved_str = "[resolved]" if req.get("resolved") else "[unresolved]"
            lines.append(f"- {req['id']}: {req['summary']} {resolved_str}")
        lines.append("")

    lines.append("Comments:")
    if not issue.comments:
        lines.append("No comments.")
    else:
        import datetime
        for c in issue.comments:
            dt = datetime.datetime.fromtimestamp(c.created / 1000.0, tz=datetime.timezone.utc)
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            lines.append(f"[{c.author} @ {formatted_time}]")
            lines.append(c.text)
            lines.append("")
            
    return "\n".join(lines).rstrip()


def format_issue_detail_json(issue) -> str:
    """Format an issue's details and comments into a formatted JSON string."""
    return json.dumps(asdict(issue), indent=2)





