from app.resources import _build_resource_list, REFERENCES_DIR

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
