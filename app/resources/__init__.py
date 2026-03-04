# app/resources/__init__.py

import logging
from pathlib import Path

logger = logging.getLogger("eodhd-mcp.resources")

REFERENCES_DIR = Path(__file__).parent / "references"

# ---------------------------------------------------------------------------
# Category → tag mapping
# ---------------------------------------------------------------------------
_CATEGORY_TAGS: dict[str, set[str]] = {
    "general": {"general", "reference"},
    "endpoints": {"endpoint", "reference"},
    "subscriptions": {"subscription", "plans"},
}


def _title_from_stem(stem: str) -> str:
    """Convert a file stem like 'historical-stock-prices' → 'Historical Stock Prices'."""
    return stem.replace("-", " ").replace("_", " ").title()


def _build_resource_list() -> list[dict]:
    """
    Walk the references directory and return a list of dicts describing each
    resource to register:
        uri, name, description, mime_type, tags, file_path
    """
    resources: list[dict] = []

    if not REFERENCES_DIR.is_dir():
        logger.warning("References directory not found: %s", REFERENCES_DIR)
        return resources

    for md_file in sorted(REFERENCES_DIR.rglob("*.md")):
        rel = md_file.relative_to(REFERENCES_DIR)
        parts = rel.parts  # e.g. ("general", "authentication.md") or ("workflows.md",)

        stem = md_file.stem  # filename without .md

        # Build URI:  eodhd://references/<relative path without .md>
        uri_path = str(rel.with_suffix(""))  # e.g. "general/authentication"
        uri = f"eodhd://references/{uri_path}"

        # Determine category from first directory component (if any)
        category = parts[0] if len(parts) > 1 else "general"
        tags = set(_CATEGORY_TAGS.get(category, set()))

        # Human-readable name
        if stem.lower() == "readme":
            name = f"{_title_from_stem(category)} Overview"
            description = f"Overview and index for {category} reference documentation."
        else:
            name = _title_from_stem(stem)
            description = f"EODHD API reference: {name}."

        resources.append(
            {
                "uri": uri,
                "name": name,
                "description": description,
                "mime_type": "text/markdown",
                "tags": tags,
                "file_path": md_file,
            }
        )

    return resources


def register_all(mcp) -> None:
    """Register every markdown file under references/ as an MCP resource."""
    resource_defs = _build_resource_list()

    for rdef in resource_defs:
        file_path: Path = rdef["file_path"]
        uri: str = rdef["uri"]

        try:
            # Use a closure to capture the current file_path
            def _make_reader(fp: Path):
                def _read() -> str:
                    return fp.read_text(encoding="utf-8")
                return _read

            mcp.resource(
                uri=uri,
                name=rdef["name"],
                description=rdef["description"],
                mime_type=rdef["mime_type"],
                tags=rdef["tags"],
            )(_make_reader(file_path))

            logger.debug("Registered resource: %s", uri)

        except Exception as e:
            logger.error(
                "Failed to register resource '%s': %s: %s",
                uri,
                type(e).__name__,
                e,
            )

    logger.info("Registered %d resources from %s", len(resource_defs), REFERENCES_DIR)
