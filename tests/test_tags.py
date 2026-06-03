from unittest.mock import MagicMock
import pytest
from youtrack_cli.client import YouTrackClient
from youtrack_cli.tags import create_tag, list_tags, Tag

def test_create_tag():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = {
        "id": "6-0",
        "name": "backend"
    }

    tag = create_tag(mock_client, name="backend")

    assert tag == Tag(id="6-0", name="backend")
    mock_client._request.assert_called_once_with(
        "POST",
        "api/tags?fields=id,name",
        json={"name": "backend"}
    )

def test_list_tags():
    mock_client = MagicMock(spec=YouTrackClient)
    mock_client._request.return_value = [
        {"id": "6-0", "name": "backend"},
        {"id": "6-1", "name": "frontend"}
    ]

    tags = list_tags(mock_client)

    assert tags == [
        Tag(id="6-0", name="backend"),
        Tag(id="6-1", name="frontend")
    ]
    mock_client._request.assert_called_once_with(
        "GET",
        "api/tags?fields=id,name"
    )

def test_format_tags_table_empty():
    from youtrack_cli.formatters import format_tags_table
    assert format_tags_table([]) == "No tags found."

def test_format_tags_table_non_empty():
    from youtrack_cli.formatters import format_tags_table
    tags = [Tag(id="1", name="bug"), Tag(id="2", name="critical")]
    expected = (
        "NAME    \n"
        "--------\n"
        "bug     \n"
        "critical"
    )
    assert format_tags_table(tags) == expected

def test_format_tags_json():
    from youtrack_cli.formatters import format_tags_json
    import json
    tags = [Tag(id="1", name="bug")]
    result = format_tags_json(tags)
    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["id"] == "1"
    assert parsed[0]["name"] == "bug"


