# tests/auto/test_resources.py
from app.resources import REFERENCES_DIR, _build_resource_list


def test_references_dir_exists():
    assert REFERENCES_DIR.is_dir()


def test_resource_list_not_empty():
    resources = _build_resource_list()
    assert len(resources) > 0


def test_resource_uris_unique():
    resources = _build_resource_list()
    uris = [r["uri"] for r in resources]
    assert len(uris) == len(set(uris))


def test_resource_fields():
    resources = _build_resource_list()
    for r in resources:
        assert "uri" in r
        assert "name" in r
        assert "mime_type" in r
        assert r["uri"].startswith("eodhd://references/")
        assert r["mime_type"] == "text/markdown"


def test_mcp_server_reference_states_supported_python():
    """The reference served to clients must not advertise a Python older than requires-python."""
    import re
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    requires = tomllib.loads((root / "pyproject.toml").read_text())["project"]["requires-python"]
    minimum = re.fullmatch(r">=\s*(\d+\.\d+)", requires.strip())
    assert minimum, requires
    text = (REFERENCES_DIR / "general" / "sdks-and-integrations.md").read_text()
    section = text.split("### MCP Server", 1)[1].split("###", 1)[0]
    assert f"| Language | Python {minimum.group(1)}+ |" in section
