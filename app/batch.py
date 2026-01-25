# app/batch.py
"""
Batch processing utilities for EODHD MCP Server.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from app.api_client import make_request
from app.config import EODHD_API_BASE


class BatchProcessor:
    """Process multiple API requests in parallel with rate limiting."""

    def __init__(self, max_concurrent: int = 10, delay_between: float = 0.1):
        """
        Initialize batch processor.

        Args:
            max_concurrent: Maximum concurrent requests
            delay_between: Delay between requests in seconds
        """
        self.max_concurrent = max_concurrent
        self.delay_between = delay_between
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _fetch_with_semaphore(
        self,
        url: str,
        identifier: str
    ) -> Dict[str, Any]:
        """Fetch URL with semaphore rate limiting."""
        async with self._semaphore:
            await asyncio.sleep(self.delay_between)
            result = await make_request(url)
            return {"identifier": identifier, "data": result}

    async def process(
        self,
        items: List[Dict[str, str]],
        url_builder: Callable[[Dict], str]
    ) -> Dict[str, Any]:
        """
        Process multiple items in parallel.

        Args:
            items: List of items to process, each with an 'id' field
            url_builder: Function to build URL from item

        Returns:
            Dict with results and errors
        """
        tasks = []
        for item in items:
            identifier = item.get("id", str(item))
            url = url_builder(item)
            tasks.append(self._fetch_with_semaphore(url, identifier))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success = {}
        errors = []

        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif isinstance(result, dict):
                identifier = result.get("identifier")
                data = result.get("data")
                if data and not (isinstance(data, dict) and data.get("error")):
                    success[identifier] = data
                else:
                    error_msg = data.get("error", "Unknown error") if isinstance(data, dict) else "No data"
                    errors.append(f"{identifier}: {error_msg}")

        return {
            "results": success,
            "count": len(success),
            "total": len(items),
            "errors": errors if errors else None
        }


# Pre-configured batch processor
batch_processor = BatchProcessor(max_concurrent=10, delay_between=0.1)


async def batch_quotes(symbols: List[str]) -> Dict[str, Any]:
    """
    Fetch quotes for multiple symbols.

    Args:
        symbols: List of ticker symbols (e.g., ['AAPL.US', 'MSFT.US'])

    Returns:
        Dict with quotes for each symbol
    """
    items = [{"id": s, "symbol": s} for s in symbols]

    def url_builder(item):
        return f"{EODHD_API_BASE}/real-time/{item['symbol']}?fmt=json"

    return await batch_processor.process(items, url_builder)


async def batch_eod(symbols: List[str], date: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch EOD data for multiple symbols.

    Args:
        symbols: List of ticker symbols
        date: Optional date in YYYY-MM-DD format

    Returns:
        Dict with EOD data for each symbol
    """
    items = [{"id": s, "symbol": s} for s in symbols]

    def url_builder(item):
        url = f"{EODHD_API_BASE}/eod/{item['symbol']}?fmt=json&order=d&limit=1"
        if date:
            url += f"&from={date}&to={date}"
        return url

    return await batch_processor.process(items, url_builder)


async def batch_fundamentals(
    symbols: List[str],
    filter_fields: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch fundamentals for multiple symbols.

    Args:
        symbols: List of ticker symbols
        filter_fields: Optional comma-separated list of fields to return

    Returns:
        Dict with fundamentals for each symbol
    """
    items = [{"id": s, "symbol": s} for s in symbols]

    def url_builder(item):
        url = f"{EODHD_API_BASE}/fundamentals/{item['symbol']}"
        if filter_fields:
            url += f"?filter={filter_fields}"
        return url

    return await batch_processor.process(items, url_builder)


async def compare_symbols(
    symbols: List[str],
    metrics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Compare multiple symbols side by side.

    Args:
        symbols: List of ticker symbols to compare
        metrics: Optional list of metrics to include

    Returns:
        Dict with comparison data
    """
    default_metrics = [
        "General::Name",
        "General::Sector",
        "General::Industry",
        "Highlights::MarketCapitalization",
        "Highlights::PERatio",
        "Highlights::DividendYield",
        "Highlights::ProfitMargin",
        "Highlights::ReturnOnEquityTTM"
    ]

    filter_str = ",".join(metrics or default_metrics)
    result = await batch_fundamentals(symbols, filter_str)

    if result.get("results"):
        comparison = []
        for symbol, data in result["results"].items():
            entry = {"symbol": symbol}
            if isinstance(data, dict):
                entry.update(data)
            comparison.append(entry)

        result["comparison"] = comparison

    return result
