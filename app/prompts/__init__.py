# app/prompts/__init__.py

import importlib
import logging
from collections.abc import Iterable

logger = logging.getLogger("eodhd-mcp.prompts")

PROMPTS: list[str] = [
    "analyze_stock",
    "compare_stocks",
    "market_overview",
]


def _safe_register(mcp, module_name: str, attr: str = "register") -> None:
    """Import .{module_name} and call its register(mcp), logging and skipping on errors."""
    try:
        mod = importlib.import_module(f".{module_name}", package=__name__)
    except ModuleNotFoundError as e:
        logger.warning("Skipping prompt '%s': module not found (%s)", module_name, e)
        return
    except Exception as e:
        logger.error("Error importing prompt '%s': %s: %s", module_name, type(e).__name__, e)
        return

    fn = getattr(mod, attr, None)
    if not callable(fn):
        logger.warning("Skipping prompt '%s': no callable '%s()' found", module_name, attr)
        return

    try:
        fn(mcp)
        logger.info("Registered prompt: %s.%s", module_name, attr)
    except Exception as e:
        logger.error("Failed to register prompt '%s': %s: %s", module_name, type(e).__name__, e)


def _dedupe(seq: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def register_all(mcp) -> None:
    """Attempt to register every known prompt, skipping any that are missing or erroring."""
    for name in _dedupe(PROMPTS):
        _safe_register(mcp, name)
